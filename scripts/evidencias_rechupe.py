"""Evidências do modelo de rechupe: registro no UC, run do MLflow, endpoint servido, dataset sintético, avaliação
escorando o ENDPOINT, curvas de sensibilidade, aditividade do SHAP e casos de texto livre pelo app.
Gera evidencias/RECHUPE.md e evidencias/rechupe.json.

Uso:  APP_URL=https://<app>.databricksapps.com DATABRICKS_CONFIG_PROFILE=<perfil> WAREHOUSE_ID=<id> \\
      python3 scripts/evidencias_rechupe.py"""
import datetime, json, math, os, re, urllib.request
from databricks.sdk import WorkspaceClient

PERFIL = os.environ["DATABRICKS_CONFIG_PROFILE"]
APP = os.environ["APP_URL"].rstrip("/")
WH = os.environ["WAREHOUSE_ID"]
FQ = os.getenv("APP_FQ", "dadosapp.fundalis_ia")
MODELO, ENDPOINT, TREINO = f"{FQ}.rechupe_model", os.getenv("RECHUPE_ENDPOINT", "fundalis_rechupe"), f"{FQ}.rechupe_treino"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "evidencias")
w = WorkspaceClient(profile=PERFIL)
NUM = ["temp_vazamento_c", "modulo_geometrico_cm", "espessura_parede_mm", "teor_carbono_pct", "teor_silicio_pct",
       "inoculacao_kg_t", "tempo_solidificacao_s", "taxa_resfriamento_cs", "usa_massalote"]
LBL = {"tipo_ferro": "Tipo de ferro", "temp_vazamento_c": "Temperatura de vazamento (°C)", "modulo_geometrico_cm": "Módulo geométrico (cm)",
       "espessura_parede_mm": "Espessura de parede (mm)", "teor_carbono_pct": "Carbono (%C)", "teor_silicio_pct": "Silício (%Si)",
       "inoculacao_kg_t": "Inoculação (kg/t)", "tempo_solidificacao_s": "Tempo de solidificação (s)",
       "taxa_resfriamento_cs": "Taxa de resfriamento (°C/s)", "usa_massalote": "Massalote/alimentador"}


def sql(q):
    import time
    r = w.statement_execution.execute_statement(warehouse_id=WH, statement=q, wait_timeout="50s")
    while r.status.state.value in ("PENDING", "RUNNING"):
        time.sleep(2)
        r = w.statement_execution.get_statement(r.statement_id)
    if r.status.state.value != "SUCCEEDED":
        raise RuntimeError(r.status.error.message)
    cols = [c.name for c in r.manifest.schema.columns]
    return [dict(zip(cols, row)) for row in (r.result.data_array or [])]


def escora(registros):
    out = []
    for i in range(0, len(registros), 500):
        out += w.api_client.do("POST", f"/serving-endpoints/{ENDPOINT}/invocations",
                               body={"dataframe_records": registros[i:i + 500]})["predictions"]
    return out


def auc(y, p):
    pares = sorted(zip(p, y))
    rank, i = [0.0] * len(pares), 0
    while i < len(pares):                     # ranks médios p/ empates (Mann-Whitney)
        j = i
        while j + 1 < len(pares) and pares[j + 1][0] == pares[i][0]:
            j += 1
        for k in range(i, j + 1):
            rank[k] = (i + j) / 2 + 1
        i = j + 1
    pos = sum(1 for _, yy in pares if yy == 1)
    neg = len(pares) - pos
    soma = sum(r for r, (_, yy) in zip(rank, pares) if yy == 1)
    return (soma - pos * (pos + 1) / 2) / (pos * neg)


def app_rechupe(texto):
    tok = json.loads(os.popen(f"databricks auth token -p {PERFIL}").read())["access_token"]
    r = urllib.request.Request(APP + "/api/rechupe", data=json.dumps({"texto": texto}).encode(), method="POST",
                               headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=300).read())


def main():
    ev = {"gerado_em": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    # 1) registro no UC + run do MLflow
    rm = w.api_client.do("GET", f"/api/2.1/unity-catalog/models/{MODELO}", query={"include_aliases": "true"})
    versoes = []
    for v in w.model_versions.list(MODELO):
        mv = w.model_versions.get(MODELO, v.version)
        run = w.api_client.do("GET", "/api/2.0/mlflow/runs/get", query={"run_id": mv.run_id})["run"]
        arts = w.api_client.do("GET", "/api/2.0/mlflow/artifacts/list", query={"run_id": mv.run_id}).get("files", [])
        versoes.append({"versao": mv.version, "status": str(mv.status.value if mv.status else ""), "run_id": mv.run_id,
                        "criado_em": datetime.datetime.fromtimestamp(mv.created_at / 1000, datetime.timezone.utc).isoformat(timespec="seconds"),
                        "run_nome": run["info"].get("run_name"), "run_status": run["info"].get("status"),
                        "metricas": {m["key"]: m["value"] for m in run["data"].get("metrics", [])},
                        "artefatos": [a["path"] for a in arts]})
    ev["registro"] = {"modelo": MODELO, "aliases": rm.get("aliases"), "versoes": sorted(versoes, key=lambda x: int(x["versao"]))}
    # 2) endpoint
    e = w.serving_endpoints.get(ENDPOINT)
    ev["endpoint"] = {"nome": e.name, "estado": str(e.state.ready.value), "update": str(e.state.config_update.value),
                      "servindo": [{"modelo": s.entity_name, "versao": s.entity_version, "tamanho": s.workload_size,
                                    "scale_to_zero": s.scale_to_zero_enabled} for s in e.config.served_entities]}
    # 3) dataset sintético
    ev["dataset"] = sql(f"SELECT count(*) n, round(avg(rechupe), 4) taxa FROM {TREINO}")[0]
    ev["dataset_por_grupo"] = sql(f"""SELECT tipo_ferro, usa_massalote, count(*) n, round(avg(rechupe), 3) taxa_rechupe
                                       FROM {TREINO} GROUP BY ALL ORDER BY tipo_ferro, usa_massalote""")
    ev["dataset_stats"] = sql("SELECT " + ", ".join(
        f"'{c}' AS f_{i}, round(min({c}),2) AS mn_{i}, round(avg({c}),2) AS md_{i}, round(max({c}),2) AS mx_{i}"
        for i, c in enumerate(NUM[:-1])) + f" FROM {TREINO}")[0]
    # 4) avaliação escorando o endpoint numa amostra determinística (20% das linhas por hash)
    amostra = sql(f"SELECT * FROM {TREINO} WHERE abs(xxhash64(temp_vazamento_c, modulo_geometrico_cm, teor_carbono_pct, "
                  f"inoculacao_kg_t)) % 5 = 0 LIMIT 2000")
    regs = [{"tipo_ferro": r["tipo_ferro"], **{c: float(r[c]) for c in NUM}} for r in amostra]
    for r in regs:
        r["usa_massalote"] = int(r["usa_massalote"])
    y = [int(r["rechupe"]) for r in amostra]
    pred = escora(regs)
    p = [float(x["prob_rechupe"]) for x in pred]
    acc = sum((pp >= 0.5) == bool(yy) for pp, yy in zip(p, y)) / len(y)
    tp = sum(1 for pp, yy in zip(p, y) if pp >= 0.5 and yy)
    fp = sum(1 for pp, yy in zip(p, y) if pp >= 0.5 and not yy)
    fn = sum(1 for pp, yy in zip(p, y) if pp < 0.5 and yy)
    tn = len(y) - tp - fp - fn
    dec = []
    ordem = sorted(range(len(p)), key=lambda i: p[i])
    for k in range(10):
        idx = ordem[k * len(p) // 10:(k + 1) * len(p) // 10]
        dec.append({"decil": k + 1, "p_media": round(sum(p[i] for i in idx) / len(idx), 3), "taxa_real": round(sum(y[i] for i in idx) / len(idx), 3)})
    erros = []
    for pr in pred:
        c = json.loads(pr["shap_json"])
        pp = min(max(float(pr["prob_rechupe"]), 1e-4), 1 - 1e-4)
        erros.append(abs(pr["shap_base"] + sum(c.values()) - math.log(pp / (1 - pp))))
    ev["avaliacao"] = {"n": len(y), "auc": round(auc(y, p), 4), "acuracia_0_5": round(acc, 4),
                       "brier": round(sum((pp - yy) ** 2 for pp, yy in zip(p, y)) / len(y), 4),
                       "matriz": {"tp": tp, "fp": fp, "fn": fn, "tn": tn}, "calibracao": dec,
                       "shap_aditividade_erro_max": round(max(erros), 4), "shap_aditividade_erro_medio": round(sum(erros) / len(erros), 5)}
    # 5) sensibilidade: varia 1 parâmetro por vez a partir de um caso de referência
    ref = {"tipo_ferro": "Nodular", "temp_vazamento_c": 1420.0, "modulo_geometrico_cm": 2.0, "espessura_parede_mm": 24.0,
           "teor_carbono_pct": 3.5, "teor_silicio_pct": 2.3, "inoculacao_kg_t": 0.2, "tempo_solidificacao_s": 220.0,
           "taxa_resfriamento_cs": 1.5, "usa_massalote": 0}
    grades = {"usa_massalote": [0, 1], "tipo_ferro": ["Cinzento", "Vermicular", "Nodular"],
              "modulo_geometrico_cm": [0.5, 1.0, 2.0, 3.0, 4.0, 5.0], "temp_vazamento_c": [1340, 1380, 1420, 1460, 1500],
              "inoculacao_kg_t": [0.0, 0.1, 0.2, 0.4, 0.6], "teor_carbono_pct": [3.0, 3.3, 3.6, 3.9]}
    sens = {}
    for k, vals in grades.items():
        pr = escora([{**ref, k: v} for v in vals])
        sens[k] = [{"valor": v, "prob": round(float(x["prob_rechupe"]), 3)} for v, x in zip(vals, pr)]
    ev["sensibilidade"] = {"referencia": ref, "curvas": sens}
    ev["shap_global"] = sql(f"SELECT feature, round(importancia, 4) importancia, rank FROM {FQ}.rechupe_shap_global ORDER BY rank")
    # 6) texto livre pelo app (LLM extrai → endpoint → SHAP → explicação)
    casos = ["Cabeçote em ferro cinzento, espessura 12 mm, 3,6% C e 2,4% Si, com alimentador, vazado a 1400 °C.",
             "Carcaça de diferencial nodular, seção espessa de 50 mm, módulo alto, sem resfriador nem massalote, inoculação 0,1 kg/t, vazamento a 1470 °C.",
             "Cubo de roda em ferro vermicular, parede de 25 mm, 3,7% C, 2,5% Si, inoculação 0,3 kg/t, com massalote, vazamento a 1420 °C."]
    ev["casos_app"] = []
    for t in casos:
        r = app_rechupe(t)
        ev["casos_app"].append({"texto": t, "prob": r["prob_rechupe"], "classe": r["classe_risco"], "assumidos": r.get("assumidos"),
                                "features": r["features"], "top_shap": (r.get("shap") or [])[:3], "explicacao": r.get("explicacao")})
    s = json.dumps(ev, ensure_ascii=False, default=str)
    s = re.sub(r"/Users/[^/\"]+@[^/\"]+", "/Users/<usuário>", s)
    ev = json.loads(s)
    json.dump(ev, open(os.path.join(SAIDA, "rechupe.json"), "w"), ensure_ascii=False, indent=2)
    open(os.path.join(SAIDA, "RECHUPE.md"), "w").write(relatorio(ev))
    print("ok →", SAIDA)


def relatorio(ev):
    a, en, reg = ev["avaliacao"], ev["endpoint"], ev["registro"]
    L = ["# Evidências — modelo de rechupe", "",
         f"Execução de {ev['gerado_em']}. **O modelo é real (treinado, registrado no Unity Catalog e servido), mas o dataset é "
         "sintético** — gerado com uma relação metalúrgica plausível só para a demo. JSON bruto: [`rechupe.json`](rechupe.json). "
         "Gerado por `scripts/evidencias_rechupe.py`; treino em `notebooks/10_rechupe_model.py`.", "",
         "## 1. Registro no Unity Catalog e MLflow", "",
         f"Modelo `{reg['modelo']}` · aliases: " + (", ".join(str(x.get("alias_name")) + " → v" + str(x.get("version_num")) for x in reg.get("aliases") or []) or "—"), "",
         "| versão | status | criado em (UTC) | run MLflow | AUC (teste, logado no treino) | artefatos |", "|---|---|---|---|---|---|"]
    L += [f"| v{v['versao']} | {v['status']} | {v['criado_em']} | `{v['run_nome']}` {v['run_status']} (`{v['run_id'][:12]}…`) | "
          f"{v['metricas'].get('auc', float('nan')):.4f} | {', '.join(v['artefatos'])} |" for v in reg["versoes"]]
    L += ["", "v1 devolvia só a probabilidade; **v2** devolve também `shap_base` e `shap_json` (TreeExplainer calculado dentro do modelo).", "",
          "## 2. Endpoint de Model Serving", "",
          f"`{en['nome']}` · {en['estado']} · atualização: {en['update']}", ""]
    L += [f"- servindo `{s['modelo']}` **v{s['versao']}** · {s['tamanho']} · scale-to-zero: {s['scale_to_zero']}" for s in en["servindo"]]
    d = ev["dataset"]
    L += ["", "## 3. Dataset de treino (sintético)", "",
          f"`{TREINO}`: **{int(d['n']):,} corridas** · taxa de rechupe {float(d['taxa']) * 100:.1f}%".replace(",", "."), "",
          "| tipo de ferro | massalote | corridas | taxa de rechupe |", "|---|---|---|---|"]
    L += [f"| {g['tipo_ferro']} | {'sim' if int(g['usa_massalote']) else 'não'} | {g['n']} | {float(g['taxa_rechupe']) * 100:.1f}% |" for g in ev["dataset_por_grupo"]]
    st = ev["dataset_stats"]
    L += ["", "| parâmetro | mín | média | máx |", "|---|---|---|---|"]
    i = 0
    while f"f_{i}" in st:
        L.append(f"| {LBL[st[f'f_{i}']]} | {st[f'mn_{i}']} | {st[f'md_{i}']} | {st[f'mx_{i}']} |")
        i += 1
    m = a["matriz"]
    L += ["", "## 4. Avaliação escorando o endpoint servido", "",
          f"Amostra determinística de **{a['n']} corridas** do dataset (hash de 20% das linhas) enviada ao endpoint `{en['nome']}`. "
          "A amostra mistura linhas de treino e de teste, então serve como checagem de consistência do modelo servido; a métrica "
          "de generalização é a AUC de teste logada no MLflow (seção 1).", "",
          f"| métrica | valor |", "|---|---|",
          f"| AUC | {a['auc']} |", f"| acurácia (corte 0,5) | {a['acuracia_0_5']} |", f"| Brier score | {a['brier']} |",
          f"| matriz (corte 0,5) | VP {m['tp']} · FP {m['fp']} · FN {m['fn']} · VN {m['tn']} |",
          f"| aditividade do SHAP (base + Σ SHAP − logit p) | erro máx {a['shap_aditividade_erro_max']} · médio {a['shap_aditividade_erro_medio']} |", "",
          "Calibração por decil de probabilidade prevista:", "", "| decil | p média prevista | taxa real |", "|---|---|---|"]
    L += [f"| {c['decil']} | {c['p_media']} | {c['taxa_real']} |" for c in a["calibracao"]]
    se = ev["sensibilidade"]
    L += ["", "## 5. Sensibilidade (um parâmetro por vez, demais no caso de referência)", "",
          "Referência: " + ", ".join(f"{LBL[k]} = {v}" for k, v in se["referencia"].items()), ""]
    for k, pts in se["curvas"].items():
        L.append(f"- **{LBL[k]}**: " + " → ".join(f"{('sim' if p['valor'] else 'não') if k == 'usa_massalote' else p['valor']}: {p['prob'] * 100:.0f}%" for p in pts))
    L += ["", "Direções esperadas pela metalurgia: massalote reduz muito o risco; módulo maior e vazamento mais quente aumentam; "
          "mais inoculação e mais carbono (CE maior) reduzem; ferro cinzento tende a se auto-alimentar melhor que o nodular.", "",
          "## 6. Importância global (média |SHAP| no conjunto de teste)", "", "| # | parâmetro | média |SHAP| |", "|---|---|---|"]
    L += [f"| {g['rank']} | {LBL.get(g['feature'], g['feature'])} | {float(g['importancia']):.3f} |" for g in ev["shap_global"]]
    L += ["", "## 7. Casos em texto livre pelo app (LLM extrai → endpoint → SHAP → explicação)", ""]
    for c in ev["casos_app"]:
        L += [f"> {c['texto']}", "",
              f"**{c['prob'] * 100:.1f}% ({c['classe']})** · assumidos pela IA: {', '.join(LBL.get(x, x) for x in c['assumidos'] or []) or 'nenhum'} · "
              "maiores contribuições: " + ", ".join(f"{x['label']} = {x['valor']} ({x['shap']:+.2f})" for x in c["top_shap"]), "",
              f"_{c['explicacao']}_", ""]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
