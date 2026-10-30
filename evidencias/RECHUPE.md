# Evidências — modelo de rechupe

Execução de 2026-10-29T17:14:38+00:00. **O modelo é real (treinado, registrado no Unity Catalog e servido), mas o dataset é sintético** — gerado com uma relação metalúrgica plausível só para a demo. JSON bruto: [`rechupe.json`](rechupe.json). Gerado por `scripts/evidencias_rechupe.py`; treino em `notebooks/10_rechupe_model.py`.

## 1. Registro no Unity Catalog e MLflow

Modelo `dadosapp.fundalis_ia.rechupe_model` · aliases: champion → v2

| versão | status | criado em (UTC) | run MLflow | AUC (teste, logado no treino) | artefatos |
|---|---|---|---|---|---|
| v1 | READY | 2026-10-27T20:14:50+00:00 | `rechupe_gb` FINISHED (`a54c9ab55a37…`) | 0.9006 | model |
| v2 | READY | 2026-10-28T13:58:21+00:00 | `rechupe_gb` FINISHED (`81ad879f948c…`) | 0.9006 | shap_global.json, model |

v1 devolvia só a probabilidade; **v2** devolve também `shap_base` e `shap_json` (TreeExplainer calculado dentro do modelo).

## 2. Endpoint de Model Serving

`fundalis_rechupe` · READY · atualização: NOT_UPDATING

- servindo `dadosapp.fundalis_ia.rechupe_model` **v2** · Small · scale-to-zero: True

## 3. Dataset de treino (sintético)

`dadosapp.fundalis_ia.rechupe_treino`: **9.000 corridas** · taxa de rechupe 41.6%

| tipo de ferro | massalote | corridas | taxa de rechupe |
|---|---|---|---|
| Cinzento | não | 2024 | 58.3% |
| Cinzento | sim | 2082 | 15.5% |
| Nodular | não | 1750 | 68.6% |
| Nodular | sim | 1812 | 24.7% |
| Vermicular | não | 664 | 66.9% |
| Vermicular | sim | 668 | 22.3% |

| parâmetro | mín | média | máx |
|---|---|---|---|
| Temperatura de vazamento (°C) | 1330.0 | 1410.18 | 1500.0 |
| Módulo geométrico (cm) | 0.3 | 1.81 | 6.0 |
| Espessura de parede (mm) | 4.0 | 22.05 | 87.2 |
| Carbono (%C) | 2.9 | 3.5 | 4.1 |
| Silício (%Si) | 1.4 | 2.3 | 3.2 |
| Inoculação (kg/t) | 0.0 | 0.3 | 0.6 |
| Tempo de solidificação (s) | 10.0 | 268.67 | 2094.0 |
| Taxa de resfriamento (°C/s) | 0.1 | 2.33 | 6.98 |

## 4. Avaliação escorando o endpoint servido

Amostra determinística de **1750 corridas** do dataset (hash de 20% das linhas) enviada ao endpoint `fundalis_rechupe`. A amostra mistura linhas de treino e de teste, então serve como checagem de consistência do modelo servido; a métrica de generalização é a AUC de teste logada no MLflow (seção 1).

| métrica | valor |
|---|---|
| AUC | 0.8965 |
| acurácia (corte 0,5) | 0.8217 |
| Brier score | 0.1226 |
| matriz (corte 0,5) | VP 517 · FP 104 · FN 208 · VN 921 |
| aditividade do SHAP (base + Σ SHAP − logit p) | erro máx 0.0027 · médio 0.00032 |

Calibração por decil de probabilidade prevista:

| decil | p média prevista | taxa real |
|---|---|---|
| 1 | 0.04 | 0.034 |
| 2 | 0.071 | 0.074 |
| 3 | 0.115 | 0.109 |
| 4 | 0.179 | 0.143 |
| 5 | 0.257 | 0.229 |
| 6 | 0.368 | 0.36 |
| 7 | 0.511 | 0.526 |
| 8 | 0.71 | 0.731 |
| 9 | 0.896 | 0.943 |
| 10 | 0.968 | 0.994 |

## 5. Sensibilidade (um parâmetro por vez, demais no caso de referência)

Referência: Tipo de ferro = Nodular, Temperatura de vazamento (°C) = 1420.0, Módulo geométrico (cm) = 2.0, Espessura de parede (mm) = 24.0, Carbono (%C) = 3.5, Silício (%Si) = 2.3, Inoculação (kg/t) = 0.2, Tempo de solidificação (s) = 220.0, Taxa de resfriamento (°C/s) = 1.5, Massalote/alimentador = 0

- **Massalote/alimentador**: não: 92% → sim: 28%
- **Tipo de ferro**: Cinzento: 87% → Vermicular: 91% → Nodular: 92%
- **Módulo geométrico (cm)**: 0.5: 54% → 1.0: 64% → 2.0: 92% → 3.0: 94% → 4.0: 94% → 5.0: 94%
- **Temperatura de vazamento (°C)**: 1340: 87% → 1380: 90% → 1420: 92% → 1460: 95% → 1500: 95%
- **Inoculação (kg/t)**: 0.0: 94% → 0.1: 94% → 0.2: 92% → 0.4: 87% → 0.6: 80%
- **Carbono (%C)**: 3.0: 94% → 3.3: 92% → 3.6: 90% → 3.9: 87%

Direções esperadas pela metalurgia: massalote reduz muito o risco; módulo maior e vazamento mais quente aumentam; mais inoculação e mais carbono (CE maior) reduzem; ferro cinzento tende a se auto-alimentar melhor que o nodular.

## 6. Importância global (média |SHAP| no conjunto de teste)

| # | parâmetro | média |SHAP| |
|---|---|---|
| 1 | Massalote/alimentador | 1.304 |
| 2 | Módulo geométrico (cm) | 0.719 |
| 3 | Tipo de ferro | 0.269 |
| 4 | Inoculação (kg/t) | 0.244 |
| 5 | Carbono (%C) | 0.233 |
| 6 | Tempo de solidificação (s) | 0.231 |
| 7 | Espessura de parede (mm) | 0.193 |
| 8 | Taxa de resfriamento (°C/s) | 0.188 |
| 9 | Temperatura de vazamento (°C) | 0.175 |
| 10 | Silício (%Si) | 0.130 |

## 7. Casos em texto livre pelo app (LLM extrai → endpoint → SHAP → explicação)

> Cabeçote em ferro cinzento, espessura 12 mm, 3,6% C e 2,4% Si, com alimentador, vazado a 1400 °C.

**4.9% (Baixo)** · assumidos pela IA: Módulo geométrico (cm), Inoculação (kg/t), Tempo de solidificação (s), Taxa de resfriamento (°C/s) · maiores contribuições: Massalote/alimentador = sim (-1.20), Módulo geométrico (cm) = 1 (-0.57), Tipo de ferro = Cinzento (-0.24)

_O modelo previu risco baixo de rechupe (5%) porque os fatores dominantes empurram fortemente a predição para baixo. O maior impacto vem do massalote/alimentador presente (SHAP −1.205), que garante reservatório de metal líquido para compensar a contração durante a solidificação. Em seguida, o módulo geométrico = 1 cm (SHAP −0.569) indica peça com solidificação relativamente rápida e controlada, e o ferro cinzento (SHAP −0.241) favorece a expansão da grafita, reduzindo a tendência ao vazio interno. Em sentido contrário, apenas a inoculação = 0,3 kg/t puxou levemente para cima (SHAP +0.113), mas seu efeito é pequeno e insuficiente para alterar o resultado final._

> Carcaça de diferencial nodular, seção espessa de 50 mm, módulo alto, sem resfriador nem massalote, inoculação 0,1 kg/t, vazamento a 1470 °C.

**98.5% (Alto)** · assumidos pela IA: Módulo geométrico (cm), Carbono (%C), Silício (%Si), Tempo de solidificação (s), Taxa de resfriamento (°C/s) · maiores contribuições: Massalote/alimentador = não (+1.51), Módulo geométrico (cm) = 4,17 (+1.22), Tempo de solidificação (s) = 1200 (+0.53)

_O modelo previu risco Alto (99%) principalmente pela ausência de massalote/alimentador (SHAP +1.509), pois sem reservatório de metal líquido não há compensação da contração volumétrica durante a solidificação, favorecendo o rechupe. O segundo fator foi o módulo geométrico elevado de 4,17 cm (SHAP +1.223), que indica seção robusta com solidificação lenta e tendência a vazios internos. Contribuiu também o tempo de solidificação de 1200 s (SHAP +0.534), reforçando esse resfriamento prolongado. Em sentido contrário, apenas o carbono em 3,6% (SHAP -0.113) e o silício em 2,4% (SHAP -0.065) reduziram levemente o risco, pela maior expansão grafítica, mas de forma insuficiente para alterar a predição._

> Cubo de roda em ferro vermicular, parede de 25 mm, 3,7% C, 2,5% Si, inoculação 0,3 kg/t, com massalote, vazamento a 1420 °C.

**18.6% (Baixo)** · assumidos pela IA: Módulo geométrico (cm), Tempo de solidificação (s), Taxa de resfriamento (°C/s) · maiores contribuições: Massalote/alimentador = sim (-1.52), Módulo geométrico (cm) = 2,08 (+0.47), Carbono (%C) = 3,7 (-0.36)

_O principal fator foi a presença de massalote/alimentador (SHAP -1.519), que reduz fortemente o risco por fornecer metal líquido durante a contração na solidificação, compensando o volume e evitando o vazio de rechupe. O teor de carbono de 3,7% (SHAP -0.356) também reduziu o risco, pois favorece a expansão grafítica que contrabalança a contração. Em sentido contrário, o módulo geométrico de 2,08 cm (SHAP +0.474) foi o maior fator de aumento, já que módulos elevados retardam a solidificação e concentram o ponto quente, favorecendo o rechupe. Mesmo assim, a forte ação do massalote predominou, resultando na probabilidade final de 19%, classificada como risco Baixo._

