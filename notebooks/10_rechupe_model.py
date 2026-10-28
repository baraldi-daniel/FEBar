# Databricks notebook source
# MAGIC %md
# MAGIC # Preditor de Rechupe (contração) — modelo de ML com dados sintéticos
# MAGIC Treina um classificador de probabilidade de **rechupe** (defeito de contração na solidificação)
# MAGIC a partir de parâmetros de processo de fundição, registra no Unity Catalog e serve num endpoint.
# MAGIC Os dados são **sintéticos**, gerados com uma relação metalúrgica plausível (só p/ POC/demo).

# COMMAND ----------
# MAGIC %pip install "mlflow-skinny[databricks]" scikit-learn shap "numpy==1.26.4"
# MAGIC dbutils.library.restartPython()

# COMMAND ----------
import numpy as np, pandas as pd
rng = np.random.default_rng(42)
N = 9000

tipos = np.array(["Cinzento", "Nodular", "Vermicular"])
tipo_ferro = rng.choice(tipos, size=N, p=[0.45, 0.40, 0.15])

temp_vazamento_c    = rng.normal(1410, 35, N).clip(1330, 1500)          # °C
modulo_geometrico_cm= rng.gamma(2.0, 0.9, N).clip(0.3, 6.0)             # cm (V/A)
espessura_parede_mm = (modulo_geometrico_cm*12 + rng.normal(0,6,N)).clip(4, 90)  # mm
teor_carbono_pct    = rng.normal(3.5, 0.22, N).clip(2.9, 4.1)           # %C
teor_silicio_pct    = rng.normal(2.3, 0.35, N).clip(1.4, 3.2)           # %Si
inoculacao_kg_t     = rng.uniform(0.0, 0.6, N)                          # kg/t
tempo_solidificacao_s = (modulo_geometrico_cm**2 * 55 + rng.normal(0,40,N)).clip(10, 2500)
taxa_resfriamento_cs= (3.5/ (modulo_geometrico_cm+0.3) + rng.normal(0,0.4,N)).clip(0.1, 12)
usa_massalote       = rng.integers(0, 2, N)                             # 0/1 (alimentador/massalote)

carbono_equivalente = teor_carbono_pct + teor_silicio_pct/3.0
# efeito do tipo de ferro (nodular tende a exigir mais alimentação; cinzento se auto-alimenta via grafita)
tipo_efeito = np.select(
    [tipo_ferro=="Nodular", tipo_ferro=="Vermicular", tipo_ferro=="Cinzento"],
    [0.45, 0.20, -0.35], default=0.0)

# score de risco (quanto maior, maior a chance de rechupe)
z = (
    0.95*(modulo_geometrico_cm - 1.8)          # módulo alto + sem alimentação → cavidade de contração
    - 1.60*usa_massalote                        # massalote/alimentador reduz muito o rechupe
    + 0.9*modulo_geometrico_cm*(1-usa_massalote)
    + 0.010*(temp_vazamento_c - 1400)           # vazar quente → mais contração líquida
    - 1.35*(carbono_equivalente - 4.3)          # CE alto → expansão da grafita "auto-alimenta"
    - 2.10*inoculacao_kg_t                       # inoculação → nucleação de grafita → menos rechupe
    + 0.015*(espessura_parede_mm - 20)
    + tipo_efeito
    + rng.normal(0, 0.85, N)                     # ruído
)
prob = 1/(1+np.exp(-z))
rechupe = (rng.uniform(0,1,N) < prob).astype(int)

df = pd.DataFrame({
    "tipo_ferro": tipo_ferro,
    "temp_vazamento_c": temp_vazamento_c.round(0),
    "modulo_geometrico_cm": modulo_geometrico_cm.round(2),
    "espessura_parede_mm": espessura_parede_mm.round(1),
    "teor_carbono_pct": teor_carbono_pct.round(2),
    "teor_silicio_pct": teor_silicio_pct.round(2),
    "inoculacao_kg_t": inoculacao_kg_t.round(3),
    "tempo_solidificacao_s": tempo_solidificacao_s.round(0),
    "taxa_resfriamento_cs": taxa_resfriamento_cs.round(2),
    "usa_massalote": usa_massalote,
    "rechupe": rechupe,
})
print(df["rechupe"].mean(), "taxa de rechupe"); df.head()

# COMMAND ----------
# grava os dados sintéticos p/ rastreabilidade
spark.createDataFrame(df).write.mode("overwrite").option("overwriteSchema","true").saveAsTable("dadosapp.fundalis_ia.rechupe_treino")
print("dadosapp.fundalis_ia.rechupe_treino:", spark.table("dadosapp.fundalis_ia.rechupe_treino").count())

# COMMAND ----------
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score, classification_report

NUM = ["temp_vazamento_c","modulo_geometrico_cm","espessura_parede_mm","teor_carbono_pct",
       "teor_silicio_pct","inoculacao_kg_t","tempo_solidificacao_s","taxa_resfriamento_cs","usa_massalote"]
CAT = ["tipo_ferro"]
X = df[NUM+CAT]; y = df["rechupe"]
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=7, stratify=y)

pre = ColumnTransformer([("num", StandardScaler(), NUM),
                         ("cat", OneHotEncoder(handle_unknown="ignore"), CAT)])
clf = Pipeline([("pre", pre), ("gb", GradientBoostingClassifier(random_state=7))])
clf.fit(Xtr, ytr)
auc = roc_auc_score(yte, clf.predict_proba(Xte)[:,1])
print("AUC:", round(auc,3)); print(classification_report(yte, clf.predict(Xte)))

# COMMAND ----------
# Explicabilidade: SHAP (TreeExplainer) sobre o GradientBoosting, no espaço já pré-processado.
# As colunas one-hot de tipo_ferro são somadas de volta numa única feature "tipo_ferro".
import shap
pre_fit, gb = clf.named_steps["pre"], clf.named_steps["gb"]
GRUPO = [n.split("__", 1)[1] for n in pre_fit.get_feature_names_out()]
GRUPO = ["tipo_ferro" if g.startswith("tipo_ferro_") else g for g in GRUPO]

def shap_por_feature(explainer, X):
    Xt = pre_fit.transform(X[NUM+CAT]); Xt = Xt.toarray() if hasattr(Xt, "toarray") else Xt
    sv = np.asarray(explainer.shap_values(Xt))
    if sv.ndim == 3: sv = sv[..., -1]
    out = pd.DataFrame(0.0, index=range(len(X)), columns=NUM+CAT)
    for j, g in enumerate(GRUPO): out[g] += sv[:, j]
    return out

expl = shap.TreeExplainer(gb)
base_logodds = float(np.ravel(expl.expected_value)[-1])
sv_te = shap_por_feature(expl, Xte)
glob = (sv_te.abs().mean().sort_values(ascending=False).rename("importancia").reset_index().rename(columns={"index": "feature"}))
glob["rank"] = range(1, len(glob) + 1)
spark.createDataFrame(glob).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("dadosapp.fundalis_ia.rechupe_shap_global")
print("base (log-odds):", round(base_logodds, 3)); glob

# COMMAND ----------
import mlflow, cloudpickle
from mlflow.models import infer_signature
mlflow.set_registry_uri("databricks-uc")

class RechupeModel(mlflow.pyfunc.PythonModel):
    def load_context(self, context):
        import cloudpickle
        with open(context.artifacts["pipeline"], "rb") as f:
            self.pipe = cloudpickle.load(f)
        self.num = NUM; self.cat = CAT
        import shap
        pre, gb = self.pipe.named_steps["pre"], self.pipe.named_steps["gb"]
        self.pre, self.expl = pre, shap.TreeExplainer(gb)
        g = [n.split("__", 1)[1] for n in pre.get_feature_names_out()]
        self.grupo = ["tipo_ferro" if x.startswith("tipo_ferro_") else x for x in g]
        self.base = float(__import__("numpy").ravel(self.expl.expected_value)[-1])
    def predict(self, context, model_input):
        import pandas as pd
        if isinstance(model_input, dict):
            model_input = pd.DataFrame(model_input)
        for c in NUM:
            if c in model_input: model_input[c] = pd.to_numeric(model_input[c], errors="coerce")
        model_input = model_input.reindex(columns=NUM+CAT)
        import json, numpy as np
        X = model_input[NUM+CAT]
        p = self.pipe.predict_proba(X)[:,1]
        Xt = self.pre.transform(X); Xt = Xt.toarray() if hasattr(Xt, "toarray") else Xt
        sv = np.asarray(self.expl.shap_values(Xt))
        if sv.ndim == 3: sv = sv[..., -1]
        out = []
        for i, prob in enumerate(p):
            contrib = {}
            for j, g in enumerate(self.grupo): contrib[g] = contrib.get(g, 0.0) + float(sv[i, j])
            classe = "Alto" if prob>=0.6 else ("Médio" if prob>=0.3 else "Baixo")
            out.append({"prob_rechupe": float(round(prob,4)), "classe_risco": classe,
                        "shap_base": round(self.base, 5), "shap_json": json.dumps({k: round(v, 5) for k, v in contrib.items()})})
        return pd.DataFrame(out)

# salva o pipeline sklearn como artefato do pyfunc
with open("/tmp/rechupe_pipe.pkl","wb") as f:
    cloudpickle.dump(clf, f)

ex_in = Xte.head(3)
ex_out = pd.DataFrame([{"prob_rechupe":0.1,"classe_risco":"Baixo","shap_base":0.0,"shap_json":"{}"}])
sig = infer_signature(ex_in, ex_out)

with mlflow.start_run(run_name="rechupe_gb") as run:
    mlflow.log_metric("auc", float(auc))
    mlflow.log_dict(glob.to_dict(orient="records"), "shap_global.json")
    info = mlflow.pyfunc.log_model(
        artifact_path="model",
        python_model=RechupeModel(),
        artifacts={"pipeline": "/tmp/rechupe_pipe.pkl"},
        signature=sig,
        input_example=ex_in,
        pip_requirements=[f"scikit-learn=={__import__('sklearn').__version__}", f"cloudpickle=={cloudpickle.__version__}", f"shap=={shap.__version__}", "pandas", "numpy"],
        registered_model_name="dadosapp.fundalis_ia.rechupe_model",
    )
print("registrado:", info.model_uri)

# COMMAND ----------
# marca a versão nova como 'Champion' (alias) p/ o serving apontar de forma estável
from mlflow.tracking import MlflowClient
c = MlflowClient(registry_uri="databricks-uc")
mv = max(c.search_model_versions("name='dadosapp.fundalis_ia.rechupe_model'"), key=lambda m:int(m.version))
c.set_registered_model_alias("dadosapp.fundalis_ia.rechupe_model", "Champion", mv.version)
print("versão", mv.version, "→ alias Champion")

# COMMAND ----------
# sanity check do pyfunc com SHAP (soma das contribuições + base = logit da probabilidade)
m = mlflow.pyfunc.load_model(f"models:/dadosapp.fundalis_ia.rechupe_model/{mv.version}")
r = m.predict(Xte.head(2)); print(r)
import json, math
c = json.loads(r.iloc[0]["shap_json"]); pr = r.iloc[0]["prob_rechupe"]
print("check:", round(r.iloc[0]["shap_base"] + sum(c.values()), 3), "≈", round(math.log(pr/(1-pr)), 3))
