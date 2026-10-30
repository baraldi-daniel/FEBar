"""Fundalis IA — cria tudo do zero num workspace Databricks a partir de config.env.

Uso:
    cp config.example.env config.env   # ajuste nomes/perfil
    pip install databricks-sdk "psycopg[binary]"
    python3 bootstrap.py               # roda todas as etapas (idempotente: pode rodar de novo)
    python3 bootstrap.py --etapas app,docs   # só algumas etapas
    python3 bootstrap.py --listar            # mostra as etapas

Cada etapa verifica o que já existe e só cria o que falta. Os ids gerados (host do Lakebase, service principal do
app, id do Genie, URL do app…) ficam em .build/estado.json e em .env (lido pelos scripts de evidência).
Única etapa manual: service policies do AI Gateway (só pela UI) — veja o README.
"""
import argparse, json, os, re, shutil, subprocess, sys, time, urllib.error, urllib.request

RAIZ = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(RAIZ, ".build")
ESTADO_ARQ = os.path.join(BUILD, "estado.json")
PG_DB = "databricks_postgres"          # nome do banco na conexão Postgres
PG_DB_ID = "databricks-postgres"       # id do mesmo banco na API do Lakebase (recursos do app, CDC)
CDF_ID = "cadastro_cdc"


# ----------------------------------------------------------------------------- configuração
def le_config(caminho):
    if not os.path.exists(caminho):
        sys.exit(f"Arquivo {caminho} não encontrado. Copie config.example.env para config.env e ajuste.")
    c = {}
    for linha in open(caminho, encoding="utf-8"):
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            k, v = linha.split("=", 1)
            c[k.strip()] = v.strip().strip('"').strip("'")
    obrig = ["DATABRICKS_CONFIG_PROFILE", "CATALOG", "SCHEMA", "CDC_SCHEMA", "LAKEBASE_PROJECT", "AGENT_SERVICE_NAME",
             "AGENT_FOUNDATION_MODEL", "EMB_SERVICE", "RECHUPE_ENDPOINT", "APP_NAME"]
    falta = [k for k in obrig if not c.get(k)]
    if falta:
        sys.exit(f"Faltam no config.env: {', '.join(falta)}")
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,29}", c["APP_NAME"]):
        sys.exit("APP_NAME: use de 2 a 30 caracteres minúsculos, dígitos ou hífen, começando por letra.")
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,62}", c["LAKEBASE_PROJECT"]):
        sys.exit("LAKEBASE_PROJECT: use minúsculas, dígitos ou hífen.")
    c.setdefault("APP_TITLE", "Fundalis IA")
    c.setdefault("GENIE_TITLE", "Fundalis IA — Vendas, Leads & Documentos")
    c["FQ"] = f"{c['CATALOG']}.{c['SCHEMA']}"
    c["FQ_CDC"] = f"{c['CATALOG']}.{c['CDC_SCHEMA']}"
    c["AGENT_SERVICE"] = f"{c['FQ']}.{c['AGENT_SERVICE_NAME']}"
    c["INFERENCE_TABLE"] = f"{c['AGENT_SERVICE']}_payload"
    c["LB_BRANCH"] = f"projects/{c['LAKEBASE_PROJECT']}/branches/production"
    c["LB_ENDPOINT"] = f"{c['LB_BRANCH']}/endpoints/primary"
    c["LB_DATABASE"] = f"{c['LB_BRANCH']}/databases/{PG_DB_ID}"
    c["CDF_CONFIG"] = f"{c['LB_DATABASE']}/cdf-configs/{CDF_ID}"
    return c


def le_estado():
    try:
        return json.load(open(ESTADO_ARQ))
    except Exception:  # noqa: BLE001
        return {}


def grava_estado(e):
    os.makedirs(BUILD, exist_ok=True)
    json.dump(e, open(ESTADO_ARQ, "w"), indent=2, ensure_ascii=False)


def troca_nomes(texto, c):
    """Os arquivos do repositório usam os nomes padrão (dadosapp.fundalis_ia / dadosapp.fundalis_cdc);
    aqui viram os nomes do config.env."""
    t = texto.replace("dadosapp.fundalis_cdc", c["FQ_CDC"]).replace("dadosapp.fundalis_ia", c["FQ"])
    t = re.sub(r"\bCATALOG dadosapp\b", f"CATALOG {c['CATALOG']}", t)
    return t


# ----------------------------------------------------------------------------- utilitários
class Ctx:
    def __init__(self, c):
        from databricks.sdk import WorkspaceClient
        self.c = c
        self.w = WorkspaceClient(profile=c["DATABRICKS_CONFIG_PROFILE"])
        self.me = self.w.current_user.me().user_name
        self.e = le_estado()
        self.host = self.w.config.host.rstrip("/")

    def api(self, metodo, caminho, corpo=None, query=None):
        return self.w.api_client.do(metodo, caminho, body=corpo, query=query)

    def cli(self, *args, json_out=True, check=True):
        cmd = ["databricks", *args, "-p", self.c["DATABRICKS_CONFIG_PROFILE"]] + (["-o", "json"] if json_out else [])
        r = subprocess.run(cmd, capture_output=True, text=True)
        if check and r.returncode != 0:
            raise RuntimeError(f"{' '.join(args[:3])}: {(r.stderr or r.stdout).strip()[:500]}")
        if not json_out:
            return r.stdout
        try:
            return json.loads(r.stdout) if r.stdout.strip() else {}
        except json.JSONDecodeError:
            return {"_texto": r.stdout}

    def sql(self, q):
        w = self.w
        r = w.statement_execution.execute_statement(warehouse_id=self.e["warehouse_id"], statement=q, wait_timeout="50s")
        while r.status.state.value in ("PENDING", "RUNNING"):
            time.sleep(2)
            r = w.statement_execution.get_statement(r.statement_id)
        if r.status.state.value != "SUCCEEDED":
            raise RuntimeError(f"SQL falhou: {r.status.error.message[:400]}\n--- {q[:300]}")
        cols = [x.name for x in r.manifest.schema.columns] if r.manifest and r.manifest.schema else []
        return [dict(zip(cols, row)) for row in ((r.result.data_array or []) if r.result else [])]

    def sql_arquivo(self, arq, extra=None):
        texto = troca_nomes(open(os.path.join(RAIZ, arq), encoding="utf-8").read(), self.c)
        for k, v in (extra or {}).items():
            texto = texto.replace("{{" + k + "}}", v)
        for st in [s for s in texto.split(";;") if s.strip()]:
            self.sql(st)

    def pg(self):
        import psycopg
        tok = self.cli("postgres", "generate-database-credential", self.c["LB_ENDPOINT"])["token"]
        return psycopg.connect(host=self.e["lakebase_host"], dbname=PG_DB, user=self.me, password=tok,
                               sslmode="require", autocommit=True)

    def env_scripts(self):
        """Variáveis que os scripts auxiliares (scripts/*.py) leem."""
        e, c = self.e, self.c
        return {**os.environ, "DATABRICKS_CONFIG_PROFILE": c["DATABRICKS_CONFIG_PROFILE"],
                "WAREHOUSE_ID": e.get("warehouse_id", ""), "LAKEBASE_HOST": e.get("lakebase_host", ""),
                "LAKEBASE_USER": self.me, "LAKEBASE_ENDPOINT": c["LB_ENDPOINT"], "APP_SP_CLIENT_ID": e.get("app_sp", ""),
                "GENIE_SPACE_ID": e.get("genie_space_id", ""), "APP_URL": e.get("app_url", ""), "APP_FQ": c["FQ"],
                "GENIE_TITLE": c["GENIE_TITLE"], "RECHUPE_ENDPOINT": c["RECHUPE_ENDPOINT"],
                "APP_INFERENCE_TABLE": c["INFERENCE_TABLE"]}


def espera(descricao, fn, timeout=900, pausa=10):
    t0 = time.time()
    while True:
        r = fn()
        if r:
            return r
        if time.time() - t0 > timeout:
            raise TimeoutError(f"tempo esgotado esperando {descricao}")
        print(f"   … aguardando {descricao} ({int(time.time() - t0)} s)")
        time.sleep(pausa)


def ok(msg):
    print(f"   ✓ {msg}")


# ----------------------------------------------------------------------------- etapas
def etapa_preflight(x):
    """Confere autenticação, warehouse e as features que o app usa."""
    c, e = x.c, x.e
    ok(f"autenticado como {x.me} em {x.host}")
    wid = c.get("WAREHOUSE_ID") or e.get("warehouse_id")
    if not wid:
        whs = list(x.w.warehouses.list())
        srv = [h for h in whs if getattr(h, "enable_serverless_compute", False)] or whs
        if not srv:
            raise RuntimeError("Nenhum SQL warehouse encontrado — crie um (serverless) ou informe WAREHOUSE_ID.")
        wid = srv[0].id
        ok(f"warehouse escolhido: {srv[0].name} ({wid})")
    e["warehouse_id"] = wid
    x.w.warehouses.get(wid)
    servicos = json.dumps(x.cli("ai-gateway", "list-model-services"))
    for nome in (c["AGENT_FOUNDATION_MODEL"], c["EMB_SERVICE"]):
        base = nome.split(".")[-1].replace("databricks-", "")      # system.ai.databricks-claude-opus-4-8 → claude-opus-4-8
        if base not in servicos:
            raise RuntimeError(f"'{nome}' não está disponível no AI Gateway deste workspace — ajuste AGENT_FOUNDATION_MODEL/EMB_SERVICE")
    ok(f"modelos disponíveis no AI Gateway: {c['AGENT_FOUNDATION_MODEL']}, {c['EMB_SERVICE']}")
    x.cli("postgres", "list-projects")
    ok("AI Gateway, Lakebase e SQL warehouse acessíveis")


def etapa_uc(x):
    """Catálogo, schemas, tabelas de demonstração, máscaras de PII, tabelas de documentos/assuntos e volumes."""
    c = x.c
    try:
        x.w.catalogs.get(c["CATALOG"])
        ok(f"catálogo {c['CATALOG']} já existe")
    except Exception:  # noqa: BLE001
        kw = {"storage_root": c["CATALOG_STORAGE_ROOT"]} if c.get("CATALOG_STORAGE_ROOT") else {}
        x.w.catalogs.create(name=c["CATALOG"], comment="Dados FICTÍCIOS do app Fundalis IA", **kw)
        ok(f"catálogo {c['CATALOG']} criado")
    for s in (c["SCHEMA"], c["CDC_SCHEMA"]):
        x.sql(f"CREATE SCHEMA IF NOT EXISTS `{c['CATALOG']}`.`{s}`")
    ok(f"schemas {c['FQ']} e {c['FQ_CDC']}")
    for arq in ("scripts/seed_uc_1.sql", "scripts/seed_uc_2.sql", "scripts/gov.sql"):
        x.sql_arquivo(arq)
        ok(arq)
    for p in [u.strip() for u in (c.get("PII_USERS") or "").split(",") if u.strip()]:
        x.sql(f"MERGE INTO {c['FQ']}.pii_access t USING (SELECT '{p}' principal) s ON t.principal = s.principal "
              "WHEN NOT MATCHED THEN INSERT *")
        ok(f"PII liberada para {p}")


def etapa_lakebase(x):
    """Projeto Lakebase (Postgres), DDL (cadastro + memória do agente) e 400 leads fictícios."""
    c, e = x.c, x.e
    projetos = x.cli("postgres", "list-projects")
    nomes = [p.get("name") for p in (projetos if isinstance(projetos, list) else projetos.get("projects", []))]
    if f"projects/{c['LAKEBASE_PROJECT']}" not in nomes:
        x.cli("postgres", "create-project", c["LAKEBASE_PROJECT"],
              "--json", json.dumps({"spec": {"display_name": c.get("APP_TITLE", "Fundalis IA"), "pg_version": 17}}))
        ok(f"projeto Lakebase {c['LAKEBASE_PROJECT']} criado")
    else:
        ok(f"projeto Lakebase {c['LAKEBASE_PROJECT']} já existe")

    def host():
        try:
            eps = x.cli("postgres", "list-endpoints", c["LB_BRANCH"])
            eps = eps if isinstance(eps, list) else eps.get("endpoints", [])
            return ((eps[0].get("status") or {}).get("hosts") or {}).get("host") if eps else None
        except RuntimeError:
            return None
    e["lakebase_host"] = espera("endpoint do Lakebase", host, timeout=900)
    ok(f"host {e['lakebase_host']}")
    with x.pg() as conn:
        for st in [t.strip() for t in open(os.path.join(RAIZ, "scripts/ddl_lakebase.sql"), encoding="utf-8").read().split(";") if t.strip()]:
            conn.execute(st)
        n = conn.execute("SELECT count(*) FROM cadastro.leads").fetchone()[0]
    ok("DDL aplicado (cadastro.leads, cadastro.lead_anexos, agente.doc_chunks/llm_cache/conversas/prompts + pgvector)")
    if n == 0:
        subprocess.run([sys.executable, "seed_leads.py"], cwd=os.path.join(RAIZ, "scripts"), env=x.env_scripts(), check=True)
        ok("400 leads fictícios inseridos")
    else:
        ok(f"cadastro.leads já tem {n} linhas")


def etapa_cdc(x):
    """CDC Lakebase → Unity Catalog e as views com máscara de PII."""
    c = x.c
    cfgs = json.dumps(x.cli("postgres", "list-cdf-configs", c["LB_DATABASE"], check=False))
    if CDF_ID not in cfgs:
        x.cli("postgres", "create-cdf-config", c["LB_DATABASE"], c["CATALOG"], c["CDC_SCHEMA"], "cadastro", "--cdf-config-id", CDF_ID)
        ok("cdf-config criado")
    else:
        ok("cdf-config já existe")

    def tabelas():
        try:
            nomes = {t.name for t in x.w.tables.list(catalog_name=c["CATALOG"], schema_name=c["CDC_SCHEMA"])}
            return {"lb_leads_history", "lb_lead_anexos_history"} <= nomes
        except Exception:  # noqa: BLE001
            return False
    espera("tabelas lb_*_history do CDC no Unity Catalog", tabelas, timeout=1200, pausa=20)
    x.sql_arquivo("scripts/views.sql")
    ok(f"views {c['FQ']}.leads / leads_anexos (PII mascarada) e função buscar_documentos")


def etapa_gateway(x):
    """Model service do agente (Opus 4.8) no AI Gateway + inference table."""
    c = x.c
    nome = f"model-services/{c['AGENT_SERVICE']}"
    existe = x.cli("ai-gateway", "get-model-service", nome, check=False)
    if not existe or "error" in json.dumps(existe).lower()[:200] or "_texto" in existe:
        corpo = {"comment": f"Agente {c.get('APP_TITLE', 'Fundalis IA')} — guardrails no prompt e inference table",
                 "config": {"routing": {"destinations": [{
                     "destination_type": "DESTINATION_TYPE_PAY_PER_TOKEN_FOUNDATION_MODEL", "name": "principal",
                     "pay_per_token_config": {"model": f"models/{c['AGENT_FOUNDATION_MODEL']}"}, "traffic_percentage": 100}]}}}
        x.cli("ai-gateway", "create-model-service", f"schemas/{c['FQ']}", c["AGENT_SERVICE_NAME"], "--json", json.dumps(corpo))
        ok(f"model service {c['AGENT_SERVICE']} criado")
    else:
        ok(f"model service {c['AGENT_SERVICE']} já existe")
    cfg = x.cli("ai-gateway", "get-model-service", nome)
    if not ((cfg.get("config") or {}).get("inference_table") or {}).get("table"):
        x.cli("ai-gateway", "update-model-service", nome, "config.inference_table", "--json",
              json.dumps({"config": {"inference_table": {"parent": f"schemas/{c['FQ']}", "table_name_prefix": c["AGENT_SERVICE_NAME"]}}}))
        ok(f"inference table {c['INFERENCE_TABLE']} ligada")
    else:
        ok("inference table já ligada")


def etapa_modelo(x):
    """Treina o modelo de rechupe (notebook serverless), registra no UC e serve no Model Serving."""
    c, e = x.c, x.e
    modelo = f"{c['FQ']}.rechupe_model"
    pasta = c.get("WORKSPACE_DIR") or f"/Workspace/Users/{x.me}/{c['APP_NAME']}"
    e["workspace_dir"] = pasta
    versoes = []
    try:
        versoes = [int(v.version) for v in x.w.model_versions.list(modelo)]
    except Exception:  # noqa: BLE001
        pass
    if not versoes:
        os.makedirs(BUILD, exist_ok=True)
        nb = os.path.join(BUILD, "10_rechupe_model.py")
        open(nb, "w", encoding="utf-8").write(troca_nomes(open(os.path.join(RAIZ, "notebooks/10_rechupe_model.py"), encoding="utf-8").read(), c))
        x.cli("workspace", "mkdirs", pasta, json_out=False)
        x.cli("workspace", "import", f"{pasta}/10_rechupe_model", "--file", nb, "--language", "PYTHON", "--format", "SOURCE",
              "--overwrite", json_out=False)
        run = x.api("POST", "/api/2.2/jobs/runs/submit", {
            "run_name": f"{c['APP_NAME']}_rechupe_model",
            "tasks": [{"task_key": "treino", "notebook_task": {"notebook_path": f"{pasta}/10_rechupe_model"}, "environment_key": "default"}],
            "environments": [{"environment_key": "default", "spec": {"client": "3"}}]})
        print(f"   treinando (run {run['run_id']})…")

        def terminou():
            st = x.api("GET", "/api/2.2/jobs/runs/get", query={"run_id": run["run_id"]})["state"]
            return st if st.get("life_cycle_state") in ("TERMINATED", "INTERNAL_ERROR", "SKIPPED") else None
        st = espera("treino do modelo", terminou, timeout=2400, pausa=20)
        if st.get("result_state") != "SUCCESS":
            raise RuntimeError(f"treino falhou: {st}")
        versoes = [int(v.version) for v in x.w.model_versions.list(modelo)]
        ok(f"modelo {modelo} registrado (versões {versoes})")
    else:
        ok(f"modelo {modelo} já registrado (versões {versoes})")
    v = str(max(versoes))
    entidade = {"name": f"rechupe_model-{v}", "entity_name": modelo, "entity_version": v, "workload_size": "Small", "scale_to_zero_enabled": True}
    try:
        ep = x.api("GET", f"/api/2.0/serving-endpoints/{c['RECHUPE_ENDPOINT']}")
        atual = [s.get("entity_version") for s in (ep.get("config") or {}).get("served_entities", [])]
        if v not in atual and not ep.get("pending_config"):
            x.api("PUT", f"/api/2.0/serving-endpoints/{c['RECHUPE_ENDPOINT']}/config", {"served_entities": [entidade]})
            ok(f"endpoint {c['RECHUPE_ENDPOINT']} atualizando para v{v}")
        else:
            ok(f"endpoint {c['RECHUPE_ENDPOINT']} já serve v{v}")
    except Exception as ex:  # noqa: BLE001
        if "does not exist" not in str(ex) and "RESOURCE_DOES_NOT_EXIST" not in str(ex) and "not found" not in str(ex).lower():
            raise
        x.api("POST", "/api/2.0/serving-endpoints", {"name": c["RECHUPE_ENDPOINT"], "config": {"served_entities": [entidade]}})
        ok(f"endpoint {c['RECHUPE_ENDPOINT']} criado (fica pronto em ~10–20 min; o resto continua)")


def etapa_genie(x):
    """Genie space (tabelas + trechos dos PDFs + função de busca nos documentos)."""
    out = subprocess.run([sys.executable, "cria_genie.py"], cwd=os.path.join(RAIZ, "scripts"), env=x.env_scripts(),
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(out.stderr[-800:])
    x.e["genie_space_id"] = out.stdout.strip().splitlines()[-1]
    ok(f"Genie space {x.e['genie_space_id']}")


def _app_yaml(c):
    linhas = ["command: [uvicorn, app:app, --host, 0.0.0.0, --port, \"8000\"]", "env:"]
    env = [("APP_CATALOG", c["CATALOG"]), ("APP_SCHEMA", c["SCHEMA"]), ("APP_WAREHOUSE_ID", None, "sql-warehouse"),
           ("APP_AGENT_SERVICE", c["AGENT_SERVICE"]), ("APP_INFERENCE_TABLE", c["INFERENCE_TABLE"]),
           ("APP_EMB_ENDPOINT", c["EMB_SERVICE"]), ("APP_RECHUPE_ENDPOINT", c["RECHUPE_ENDPOINT"]),
           ("APP_LB_ENDPOINT", c["LB_ENDPOINT"]), ("APP_CDF_CONFIG", c["CDF_CONFIG"]),
           ("APP_GENIE_TITLE", c["GENIE_TITLE"]), ("APP_PRODUTO", c.get("APP_TITLE", "Fundalis IA")),
           ("APP_GENIE_SPACE_ID", None, "genie-space")]
    for item in env:
        linhas.append(f"- name: {item[0]}")
        linhas.append(f"  valueFrom: {item[2]}" if item[1] is None else f"  value: {json.dumps(item[1], ensure_ascii=False)}")
    return "\n".join(linhas) + "\n"


def etapa_app(x):
    """Databricks App: cria, liga os recursos, dá as permissões ao service principal e faz o deploy."""
    c, e = x.c, x.e
    recursos = [{"name": "sql-warehouse", "sql_warehouse": {"id": e["warehouse_id"], "permission": "CAN_USE"}},
                {"name": "lakebase", "postgres": {"branch": c["LB_BRANCH"], "database": c["LB_DATABASE"], "permission": "CAN_CONNECT_AND_CREATE"}}]
    try:
        app = x.api("GET", f"/api/2.0/apps/{c['APP_NAME']}")
        ok(f"app {c['APP_NAME']} já existe")
    except Exception:  # noqa: BLE001
        app = x.api("POST", "/api/2.0/apps", {"name": c["APP_NAME"], "description": f"{c.get('APP_TITLE')} — Lakebase + AI Gateway + Genie (dados fictícios)",
                                              "user_api_scopes": ["sql", "dashboards.genie", "serving.serving-endpoints"],
                                              "resources": recursos})
        ok(f"app {c['APP_NAME']} criado")
    espera("compute do app ficar ativo", lambda: (x.api("GET", f"/api/2.0/apps/{c['APP_NAME']}").get("compute_status") or {}).get("state") == "ACTIVE",
           timeout=1200, pausa=15)
    app = x.api("GET", f"/api/2.0/apps/{c['APP_NAME']}")
    e["app_sp"], e["app_url"] = app["service_principal_client_id"], app.get("url")
    ok(f"service principal {e['app_sp']} · {e['app_url']}")
    # recursos completos (Genie + endpoint de rechupe) — concedem CAN_RUN / CAN_QUERY ao SP
    recursos += [{"name": "genie-space", "genie_space": {"name": c["GENIE_TITLE"], "space_id": e["genie_space_id"], "permission": "CAN_RUN"}},
                 {"name": "rechupe", "serving_endpoint": {"name": c["RECHUPE_ENDPOINT"], "permission": "CAN_QUERY"}}]
    x.api("PATCH", f"/api/2.0/apps/{c['APP_NAME']}", {"name": c["APP_NAME"], "user_api_scopes": ["sql", "dashboards.genie", "serving.serving-endpoints"],
                                                       "resources": recursos})
    ok("recursos do app: warehouse, lakebase, genie-space, rechupe")
    # Unity Catalog → SP do app (e usuários do app, se configurados)
    x.sql_arquivo("scripts/grants_sp.sql", {"APP_SP": e["app_sp"]})
    for u in [u.strip() for u in (c.get("APP_USERS") or "").split(",") if u.strip()]:
        x.sql(f"GRANT USE CATALOG ON CATALOG `{c['CATALOG']}` TO `{u}`")
        x.sql(f"GRANT USE SCHEMA, SELECT, EXECUTE, READ VOLUME ON SCHEMA {c['FQ']} TO `{u}`")
        ok(f"acesso aos dados para {u}")
    ok("grants no Unity Catalog")
    # Lakebase: CAN_USE no projeto (status do CDC) + privilégios no Postgres para o papel do SP
    x.cli("permissions", "update", "database-projects", c["LAKEBASE_PROJECT"], "--json",
          json.dumps({"access_control_list": [{"service_principal_name": e["app_sp"], "permission_level": "CAN_USE"}]}))
    sp = e["app_sp"]

    def papel():
        with x.pg() as conn:
            return conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (sp,)).fetchone()
    espera("papel do service principal no Postgres", papel, timeout=600, pausa=15)
    with x.pg() as conn:
        for g in [f'GRANT USAGE ON SCHEMA cadastro, agente TO "{sp}"',
                  f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA cadastro, agente TO "{sp}"',
                  f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA cadastro, agente TO "{sp}"',
                  f'ALTER DEFAULT PRIVILEGES IN SCHEMA cadastro, agente GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{sp}"',
                  f'ALTER DEFAULT PRIVILEGES IN SCHEMA cadastro, agente GRANT USAGE, SELECT ON SEQUENCES TO "{sp}"']:
            conn.execute(g)
    ok("grants no Postgres (cadastro, agente)")
    # código: cópia em .build/app com app.yaml gerado do config → sync → deploy
    destino = os.path.join(BUILD, "app")
    shutil.rmtree(destino, ignore_errors=True)
    shutil.copytree(os.path.join(RAIZ, "app"), destino, ignore=shutil.ignore_patterns("__pycache__", ".databricks", "*.pyc"))
    open(os.path.join(destino, "app.yaml"), "w", encoding="utf-8").write(_app_yaml(c))
    pasta = e.get("workspace_dir") or c.get("WORKSPACE_DIR") or f"/Workspace/Users/{x.me}/{c['APP_NAME']}"
    e["workspace_dir"] = pasta
    x.cli("sync", destino, f"{pasta}/app", json_out=False)
    dep = x.api("POST", f"/api/2.0/apps/{c['APP_NAME']}/deployments", {"source_code_path": f"{pasta}/app", "mode": "SNAPSHOT"})

    def deploy():
        d = x.api("GET", f"/api/2.0/apps/{c['APP_NAME']}/deployments/{dep['deployment_id']}")
        st = (d.get("status") or {}).get("state")
        if st == "FAILED":
            raise RuntimeError(f"deploy falhou: {(d.get('status') or {}).get('message')}")
        return st == "SUCCEEDED"
    espera("deploy do app", deploy, timeout=900, pausa=15)
    ok(f"deploy concluído → {e['app_url']}")


def _app_http(x, metodo, caminho, corpo=None, arquivo=None, campos=None, timeout=300):
    tok = x.cli("auth", "token")["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    if arquivo:
        lim = "----fundalis" + str(int(time.time()))
        partes = []
        for k, v in (campos or {}).items():
            partes.append(f"--{lim}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
        partes.append(f"--{lim}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{os.path.basename(arquivo)}\"\r\n"
                      "Content-Type: application/pdf\r\n\r\n".encode() + open(arquivo, "rb").read() + b"\r\n")
        dados = b"".join(partes) + f"--{lim}--\r\n".encode()
        h["Content-Type"] = f"multipart/form-data; boundary={lim}"
    else:
        dados = json.dumps(corpo).encode() if corpo is not None else None
        if dados:
            h["Content-Type"] = "application/json"
    r = urllib.request.Request(x.e["app_url"] + caminho, data=dados, method=metodo, headers=h)
    return urllib.request.urlopen(r, timeout=timeout).read().decode()


def etapa_docs(x):
    """Envia os PDFs fictícios da base de conhecimento pelo próprio app (ai_parse_document → Delta + pgvector)."""
    lista = json.loads(_app_http(x, "GET", "/api/docs/lista")).get("documentos") or []
    ja = {d["arquivo"] for d in lista}
    docs = [("catalogo_tecnico_2026.pdf", "Catálogo Técnico 2026", "Catálogo técnico"),
            ("manual_qualidade_defeitos.pdf", "Manual de Qualidade — Defeitos", "Qualidade"),
            ("politica_comercial_2026.pdf", "Política Comercial 2026", "Política comercial"),
            ("relatorio_operacoes_3t26.pdf", "Relatório de Operações 3T26", "Operações")]
    enviados = []
    for arq, titulo, cat in docs:
        if arq in ja:
            ok(f"{arq} já indexado")
            continue
        _app_http(x, "POST", "/api/docs/upload", arquivo=os.path.join(RAIZ, "pdfs", arq),
                  campos={"titulo": titulo, "categoria": cat, "descricao": "Documento fictício da Fundalis"})
        enviados.append(arq)
    if enviados:
        def prontos():
            st = json.loads(_app_http(x, "GET", "/api/docs/status")).get("processos") or {}
            erros = {k: v.get("erro") for k, v in st.items() if v.get("estado") == "erro"}
            if erros:
                raise RuntimeError(f"processamento falhou: {erros}")
            return all((st.get(a) or {}).get("estado") == "ok" for a in enviados)
        espera("ai_parse_document + embeddings dos PDFs", prontos, timeout=900, pausa=15)
        ok(f"{len(enviados)} PDF(s) processados")


def etapa_teste(x):
    """Smoke test: saúde, painel, agente (Genie + RAG + guardrail) e rechupe."""
    c = x.c
    assert json.loads(_app_http(x, "GET", "/api/health")).get("ok")
    k = json.loads(_app_http(x, "GET", "/api/kpis"))
    ok(f"painel: receita R$ {float(k.get('receita_total') or 0) / 1e6:.1f} mi")
    final = {}
    for linha in _app_http(x, "POST", "/api/chat/stream", {"pergunta": "Qual o desconto para 8 mil peças por ano?", "usar_cache": False}, timeout=400).splitlines():
        if linha.strip() and json.loads(linha).get("tipo") == "final":
            final = json.loads(linha)
    ok(f"agente: {final.get('ferramentas')} → {(final.get('resposta') or '')[:120]}")
    bloq = {}
    for linha in _app_http(x, "POST", "/api/chat/stream", {"pergunta": "Qual o sentido da vida?", "usar_cache": False}).splitlines():
        if linha.strip() and json.loads(linha).get("tipo") == "final":
            bloq = json.loads(linha)
    ok(f"guardrail: bloqueado={bloq.get('bloqueado')} ({bloq.get('assunto')})")
    try:
        ep = x.api("GET", f"/api/2.0/serving-endpoints/{c['RECHUPE_ENDPOINT']}")
        if (ep.get("state") or {}).get("ready") == "READY":
            r = json.loads(_app_http(x, "POST", "/api/rechupe", {"texto": "Bloco nodular, parede de 45 mm, vazado a 1465 °C, sem massalote, inoculação 0,1 kg/t."}))
            ok(f"rechupe: {r['prob_rechupe'] * 100:.0f}% ({r['classe_risco']}) com {len(r.get('shap') or [])} valores SHAP")
        else:
            print(f"   ! endpoint {c['RECHUPE_ENDPOINT']} ainda não está pronto — rode `python3 bootstrap.py --etapas teste` depois")
    except urllib.error.HTTPError as ex:
        print(f"   ! rechupe: {ex}")


ETAPAS = [("preflight", etapa_preflight), ("uc", etapa_uc), ("lakebase", etapa_lakebase), ("cdc", etapa_cdc),
          ("gateway", etapa_gateway), ("modelo", etapa_modelo), ("genie", etapa_genie), ("app", etapa_app),
          ("docs", etapa_docs), ("teste", etapa_teste)]


def grava_env(x):
    """.env para os scripts de evidência/ajuda (scripts/*.py) — ignorado pelo git."""
    env = x.env_scripts()
    chaves = ["DATABRICKS_CONFIG_PROFILE", "WAREHOUSE_ID", "LAKEBASE_HOST", "LAKEBASE_USER", "LAKEBASE_ENDPOINT", "APP_SP_CLIENT_ID",
              "GENIE_SPACE_ID", "APP_URL", "APP_FQ", "GENIE_TITLE", "RECHUPE_ENDPOINT", "APP_INFERENCE_TABLE"]
    open(os.path.join(RAIZ, ".env"), "w").write("".join(f"{k}={env.get(k, '')}\n" for k in chaves))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=os.path.join(RAIZ, "config.env"))
    ap.add_argument("--etapas", help="lista separada por vírgula (padrão: todas)")
    ap.add_argument("--listar", action="store_true")
    a = ap.parse_args()
    if a.listar:
        for n, f in ETAPAS:
            print(f"{n:10s} {f.__doc__}")
        return
    c = le_config(a.config)
    x = Ctx(c)
    escolhidas = [s.strip() for s in a.etapas.split(",")] if a.etapas else [n for n, _ in ETAPAS]
    desconhecidas = set(escolhidas) - {n for n, _ in ETAPAS}
    if desconhecidas:
        sys.exit(f"etapas desconhecidas: {desconhecidas}")
    if "preflight" not in escolhidas:
        x.e.setdefault("warehouse_id", c.get("WAREHOUSE_ID") or x.e.get("warehouse_id"))
    for n, f in ETAPAS:
        if n not in escolhidas:
            continue
        print(f"\n▶ {n} — {f.__doc__}")
        t0 = time.time()
        f(x)
        grava_estado(x.e)
        grava_env(x)
        print(f"   ({int(time.time() - t0)} s)")
    print(f"\nPronto. App: {x.e.get('app_url')}\nEstado em {ESTADO_ARQ}; variáveis dos scripts em .env.")
    print("Passo manual opcional: service policies do AI Gateway (README → 'Service policies').")


if __name__ == "__main__":
    main()
