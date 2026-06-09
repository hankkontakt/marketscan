# Spec 01 — #1: ML-ranker (LambdaRank) + läckagefri validering (#4 inviks)

> **Repo:** `stock-scanner-fix` (ML-hjärnan). Loopen som loggar utfall ligger i
> `marketscan/backend_worker`.
> **Mål:** Höja Rank IC från **0.027 → > 0.05** (helst 0.08+), BEVISAT med
> läckagefri walk-forward, och låt modellen lära av faktiska utfall (omträning).
> **Läs först:** master-planen §2, §6.1, §7. Läs sedan dessa befintliga filer HELT
> innan du rör kod: `core/ml_ranker.py`, `core/ml_evaluation.py`, `core/ml_predictor.py`
> (åtminstone topp + funktionerna `TECH_FEATURES`, `_per_date_ic`, `build_training_data`/
> `_add_cross_sectional_target`), `scripts/train_ranker.py`, `scripts/eval_model.py`,
> `marketscan/backend_worker/outcome_filler.py`, `marketscan/backend_worker/ml_trainer.py`.

---

## 0. Bakgrund (vad som redan finns)

- `core/ml_ranker.py` implementerar **redan** LightGBM LambdaRank med faktor-features
  (`score_value`…`score_sentiment`), regim-feature (`regime_score`), tidsviktning,
  och walk-forward (`_walk_forward_validate`). Inference via `predict_ranker()`.
- `core/ml_evaluation.py` har redan `per_date_ic`, `decile_spread`, `ic_significance`,
  `evaluate_model`, `compare_models` med deploy-gate.
- `marketscan` har redan `prediction_outcomes`-tabellen (migration 024),
  `outcome_filler.log_predictions()` + `fill_outcomes()`.

**Problemet:** Både `_walk_forward_validate` (ml_ranker.py rad ~336) och `evaluate_model`
(ml_evaluation.py rad ~213) delar träning/test med:
```python
train_df = df[df["date_dt"] < train_end]
test_df  = df[(df["date_dt"] >= train_end) & (df["date_dt"] < test_end)]
```
Det finns **ingen embargo**. Eftersom target är `forward_return_30d`, överlappar de sista
träningsradernas 30-dagars-fönster in i testperioden → **label-läckage** → uppblåst IC.
Det är roten till att IC ser OK ut i backtest men är 0.027 live.

---

## 1. Delsteg A — Bygg `core/ml_validation.py` (NY fil, idé #4)

Skapa en återanvändbar modul för purged walk-forward. Detta är delsystemet som #15
också använder.

**Fil:** `stock-scanner-fix/core/ml_validation.py` (ny)

```python
"""
ml_validation.py — Läckagefri tidsserievalidering för MarketScan ML.

Purged Walk-Forward CV (Lopez de Prado): när target är forward_return_Nd
överlappar de sista träningssamplernas label-fönster testperioden. Vi PURGE:ar
(tar bort) träningssamples vars label-fönster når in i embargo-zonen, och lägger
en EMBARGO-gap mellan train-slut och test-start.

Används av:
  - core/ml_ranker.py (_walk_forward_validate)
  - core/ml_evaluation.py (evaluate_model)
  - core/regime_ensemble.py (#15)
"""
from __future__ import annotations
import logging
from dataclasses import dataclass
import pandas as pd

logger = logging.getLogger(__name__)

# Forward-return-horisonten i kalenderdagar. MÅSTE matcha target-kolumnen
# (forward_return_30d). Embargo = horisont + säkerhetsmarginal.
FORWARD_HORIZON_DAYS: int = 30
EMBARGO_DAYS: int = 35  # 30d horisont + 5 handelsdagars marginal


@dataclass
class WalkForwardFold:
    train_start: pd.Timestamp
    train_end: pd.Timestamp      # exklusiv; sista tillåtna label-datum < train_end - embargo
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    train_idx: pd.Index
    test_idx: pd.Index


def purged_walk_forward_folds(
    df: pd.DataFrame,
    date_col: str = "date",
    initial_months: int = 24,
    test_months: int = 6,
    step_months: int = 6,
    embargo_days: int = EMBARGO_DAYS,
    min_train_rows: int = 200,
    min_test_rows: int = 50,
) -> list[WalkForwardFold]:
    """Generera läckagefria walk-forward-folds.

    PURGE: träningsrad med datum d tas med ENDAST om d + embargo < test_start,
    dvs dess 30-dagars-label hinner realiseras innan testperioden börjar.
    Det innebär i praktiken: train_end_effektiv = test_start - embargo.
    """
    d = df.copy()
    d["_dt"] = pd.to_datetime(d[date_col])
    d = d.sort_values("_dt")
    min_date, max_date = d["_dt"].min(), d["_dt"].max()

    folds: list[WalkForwardFold] = []
    test_start = min_date + pd.DateOffset(months=initial_months)

    while test_start + pd.DateOffset(months=test_months) <= max_date + pd.DateOffset(days=1):
        test_end = test_start + pd.DateOffset(months=test_months)
        # Embargo: träna bara på rader vars label realiserats före test_start
        train_cutoff = test_start - pd.Timedelta(days=embargo_days)

        train_mask = d["_dt"] < train_cutoff
        test_mask = (d["_dt"] >= test_start) & (d["_dt"] < test_end)

        train_idx = d.index[train_mask]
        test_idx = d.index[test_mask]

        if len(train_idx) >= min_train_rows and len(test_idx) >= min_test_rows:
            folds.append(WalkForwardFold(
                train_start=min_date,
                train_end=train_cutoff,
                test_start=test_start,
                test_end=test_end,
                train_idx=train_idx,
                test_idx=test_idx,
            ))
            logger.info("Fold: train<%s | test %s→%s (n_train=%d, n_test=%d)",
                        train_cutoff.date(), test_start.date(), test_end.date(),
                        len(train_idx), len(test_idx))
        test_start += pd.DateOffset(months=step_months)

    return folds
```

**Acceptanstest A** (`tests/test_ml_validation.py`, ny):
- Skapa syntetisk df med datum jämnt fördelade över 4 år, 20 tickers/dag.
- Anropa `purged_walk_forward_folds`. Verifiera för varje fold:
  `fold.train_end == fold.test_start - timedelta(days=35)` och
  `max(train_dates) < fold.test_start - timedelta(days=35)`.
- Verifiera att INGEN träningsrad har datum i `[test_start - 35d, test_start)`.

---

## 2. Delsteg B — Koppla purged folds i ml_ranker + ml_evaluation

### B1. `core/ml_ranker.py`
Ersätt loopen i `_walk_forward_validate` (rad ~348–416) så att train/test hämtas från
`purged_walk_forward_folds()` istället för den nuvarande oembargerade splitten. Behåll
all befintlig metrik-beräkning (IC, decil-spread, hit-rate) oförändrad — byt BARA hur
`train_df`/`test_df` väljs:

```python
from core.ml_validation import purged_walk_forward_folds

def _walk_forward_validate(df, feature_cols, initial_months=24, test_months=6, step_months=6):
    df = df.copy()
    results = []
    folds = purged_walk_forward_folds(
        df, date_col="date",
        initial_months=initial_months, test_months=test_months, step_months=step_months,
    )
    for fold in folds:
        train_df = df.loc[fold.train_idx].copy()
        test_df  = df.loc[fold.test_idx].copy()
        # … (oförändrad: filtrera testgrupper < MIN_GROUP_SIZE, _fit_model,
        #     predict, _per_date_ic, _decile_spread, hit_rate) …
        results.append({...})
    return results
```

### B2. `core/ml_evaluation.py`
Samma ändring i `evaluate_model` (rad ~213–243): byt den manuella `while train_end`-loopen
mot `purged_walk_forward_folds()`. Allt annat (per_date_ic, decile_returns, decile_spread,
ic_significance) oförändrat.

**Acceptanstest B:** Kör `python -m scripts.eval_model` på befintlig träningsdata FÖRE och
EFTER ändringen. IC EFTER ska vara LÄGRE eller lika (läckaget borttaget = ärligare siffra).
Detta är förväntat och korrekt — dokumentera båda siffrorna i `models/eval_report.json`.

---

## 3. Delsteg C — Uppgradera objektivet mot Rank IC (LambdaRankIC)

Nuvarande `_fit_model` använder `objective="lambdarank", metric="ndcg"`. Forskning
(arXiv:2605.00501) visar att direkt optimering mot Rank IC slår NDCG-LambdaRank. Lägg
till ett **valbart** IC-objektiv UTAN att ta bort det fungerande NDCG-spåret.

**Fil:** `core/ml_ranker.py`, i `_fit_model`. Lägg till en parameter `objective_mode`
(default `"lambdarank_ndcg"`, alternativ `"rank_ic"`). För `"rank_ic"`: behåll LightGBM
men byt etikettering från quintiler till **kontinuerlig cross-sectional rank** av
`forward_return_30d` (per datum, 0–1), och använd `objective="lambdarank"` med
`label_gain` linjär — eller, enklare och robustare första version: träna en
LightGBM-regressor mot **per-datum-rankad** target (`groupby('date').rank(pct=True)`),
vilket approximerar IC-optimering utan custom C-kod.

```python
# objective_mode == "rank_ic":
df["label_rank"] = df.groupby("date")["forward_return_30d"].rank(pct=True)
# träna regressor mot label_rank (0..1); IC mäts på samma skala
```

> **Gate:** Kör `compare_models()` mellan `lambdarank_ndcg` och `rank_ic`. Deploya det
> objektiv som ger högst OOS walk-forward IC + decil-spread. Lämna det andra kvar som
> valbart. Skriv vinnaren i `models/ml_ranker_universe_metrics.json`.

**Acceptanstest C:** `python -m scripts.eval_model --compare-objectives` skriver en
jämförelsetabell (ndcg vs rank_ic) med IC, IR, decil-spread, p-value per objektiv.

---

## 4. Delsteg D — Omträning på faktiska utfall ("lär av fel")

Loopen finns redan: `prediction_outcomes` fylls nattligt med `realized_return_30d`.
Nu ska den ackumulerade utfallstabellen bli VÄXANDE träningsdata.

### D1. Exportera realiserade utfall som träningsrader
**Fil:** `marketscan/backend_worker/ml_trainer.py` (utöka; läs den först — 65 rader).
Lägg funktion som drar `prediction_outcomes WHERE realized_return_30d IS NOT NULL`,
joinar mot historiska feature-värden. **OBS:** `prediction_outcomes` lagrar inte
features, bara `score_total`, `ml_rank`, `predicted_return`, `price_at`. För omträning
behövs feature-snapshot. Två vägar (välj A, fallback B):
- **A (rekommenderas):** Pipeline skriver redan `scored_universe.parquet` per dag och
  `score_history` finns. Bygg träningsdata genom att joina `score_history`
  (faktor-delscorer per ticker+datum) med realiserade 30d-returns beräknade ur
  `score_history.price` / prisdata. Detta ger (date, ticker, score_*, forward_return_30d).
- **B:** Lägg till en nattlig parquet-dump av features i pipeline (`models/feature_log/
  YYYY-MM-DD.parquet`) och bygg dataset av dem över tid.

> Skriv i specen vilken väg som valdes. Verifiera vilka kolumner `score_history` har
> (läs migration som skapar den + `backend_worker/score_tracker.py`).

### D2. Veckovis omträning (GitHub Actions)
**Fil:** `.github/workflows/ml_retrain.yml` (ny, i marketscan).
- Schemalägg veckovis (t.ex. söndag 04:00 UTC).
- Steg: checka ut BÅDA repon → bygg dataset (D1) → `python -m scripts.train_ranker`
  → `python -m scripts.eval_model` (gate) → om ny modell vinner: committa `.pkl` till
  stock-scanner-fix `models/` (eller ladda upp via befintlig `r2_uploader.py` om modeller
  lagras i R2 — verifiera hur pipeline laddar modellen idag).
- Registrera workflow i `apps/api/routers/admin.py` `_WORKFLOW_INPUTS` + admin-panelen.

**Acceptanstest D:** Kör `ml_retrain` manuellt (workflow_dispatch). Verifiera att en ny
`models/ml_ranker_universe.pkl` + `_metrics.json` skapas och att gaten loggar
"deploy_ranker: true/false". Modellversionen i `log_predictions` höjs (`ranker_v2`) så
gamla och nya prediktioner kan jämföras i `prediction_outcomes`.

---

## 5. Filer som rörs (sammanfattning)

| Repo | Fil | Åtgärd |
|---|---|---|
| stock-scanner-fix | `core/ml_validation.py` | NY — purged walk-forward |
| stock-scanner-fix | `core/ml_ranker.py` | Ändra `_walk_forward_validate` + `_fit_model` (rank_ic) |
| stock-scanner-fix | `core/ml_evaluation.py` | Ändra `evaluate_model` (purged folds) |
| stock-scanner-fix | `scripts/eval_model.py` | Lägg `--compare-objectives`-flagga |
| stock-scanner-fix | `tests/test_ml_validation.py` | NY — acceptanstest A |
| marketscan | `backend_worker/ml_trainer.py` | Utöka — dataset från realiserade utfall |
| marketscan | `.github/workflows/ml_retrain.yml` | NY — veckovis omträning |
| marketscan | `apps/api/routers/admin.py` | Registrera nytt workflow |
| marketscan | `apps/web/components/admin/AdminSections.tsx` | Lägg workflow i panel |

## 6. Deploy
1. Inga nya DB-migrationer (prediction_outcomes finns).
2. Pinna `lightgbm`, `scipy` i stock-scanner-fix `requirements.txt` om ej redan.
3. Kör eval före/efter embargo, spara båda IC-siffrorna.
4. Höj `model_version` till `ranker_v2` i `outcome_filler.log_predictions` när nya
   modellen deployas (så A/B blir mätbart).

## 7. Definition of Done
- [ ] `core/ml_validation.py` finns, test A grönt.
- [ ] Ranker + evaluation använder purged folds (ingen rad i embargo-zonen).
- [ ] `--compare-objectives` visar ndcg vs rank_ic; vinnaren deployad via gate.
- [ ] Veckovis omträning kör och respekterar deploy-gaten.
- [ ] OOS walk-forward IC dokumenterat (ärlig siffra). Mål > 0.05; om < 0.05 efter
      embargo → RAPPORTERA (det är ett ärligt utfall, inte ett fel) och föreslå
      nästa steg (fler features från #5/#3, eller batch 2-faktorer).
- [ ] `docs/SYSTEM_AI.md` uppdaterad.
