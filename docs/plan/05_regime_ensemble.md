# Spec 05 — #15: Regimberoende ensemble (+ #6 HMM-regim inviks)

> **Repo:** `stock-scanner-fix` (ML). Förutsätter att **Spec 01 (#1) är klar** —
> återanvänder `core/ml_validation.py` (purged folds) och `core/ml_ranker.py`.
> **Mål:** En ensemble av flera modeller där en regimdetektor (HMM) styr vikterna, plus
> en osäkerhetssignal när modellerna är oense. Robusthet mot alpha-decay vid regimskiften.
> **Evidensgrund:** "When Alpha Breaks" (arXiv:2603.13252) — alpha-decay drivs av
> regimskiften; two-level uncertainty + ensemble minskar nedsidan.
> **Läs först:** master §2, §3, §5, §6.1. Läs `core/macro_regime.py` (HELT — befintlig
> regimsignal), `core/ml_ranker.py`, `core/ml_validation.py` (från #1), `core/ml_evaluation.py`.

> ⚠️ Bygg INTE detta före #1. Det förutsätter purged validering och en fungerande ranker.

---

## 0. Bakgrund

- `core/macro_regime.py::detect_regime()` ger redan en kontinuerlig regim-composite
  (0.0 björn … 1.0 tjur) byggd på SPY/VIX/yieldkurva/kredit. Den matar redan
  `regime_score`-featuren i rankern.
- **Begränsning:** den är heuristisk och USA-centrerad. #6 inviks som en **HMM** som
  lär sig regimer datadrivet (inkl. svensk/europeisk input).

---

## A. #6 — HMM-regimdetektor

**Fil:** `stock-scanner-fix/core/regime_hmm.py` (ny). Beroende: `hmmlearn` (lägg i
requirements). Open source, körs i Actions.

```python
"""
regime_hmm.py — Datadriven marknadsregim via Gaussisk HMM.
3 tillstånd: 0=BJÖRN, 1=NEUTRAL, 2=TJUR (sorteras efter medelavkastning).
Features (dagliga): OMX30-avkastning(20d), realiserad vol-kvot(5d/60d),
  VIX-nivå (proxy; lägg till VSTOXX om tillgängligt), SPY vs MA200.
Tränas på historik, ger get_current_regime() + regim-sannolikheter.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class RegimeState:
    regime: str           # "BJÖRN"|"NEUTRAL"|"TJUR"
    regime_id: int        # 0|1|2
    probabilities: dict   # {"BJÖRN":p, "NEUTRAL":p, "TJUR":p}
    regime_score: float   # 0..1 (kontinuerlig, för ML-feature)

def train_regime_hmm(features_df) -> object: ...        # returnerar tränad GaussianHMM
def get_current_regime() -> RegimeState: ...            # cache 6h (som macro_regime)
def label_history(features_df) -> "pd.Series": ...      # regim-id per historiskt datum
```
- Datakällor via yfinance: `^OMX` (eller OMXS30-proxy), `^VIX`, `SPY`. Försök även VSTOXX
  (`^V2TX` om tillgängligt) — om ej, hoppa featuren (skriv `# TODO(fråga)` om osäker).
- Sortera HMM-tillstånd efter genomsnittlig OMX-avkastning så id 0=björn, 2=tjur (HMM-
  tillstånd är annars godtyckligt ordnade).
- Cache + atomisk modell-spar (mönster från `macro_regime.py` / `ml_ranker.save_ranker`).

**Acceptanstest A:** Träna på 5 år syntetisk/riktig data. Verifiera 3 tillstånd, att
`get_current_regime()` ger giltig `RegimeState`, och att björn-tillståndet har lägst
medelavkastning i `label_history`.

> `regime_hmm.regime_score` kan ERSÄTTA eller KOMPLETTERA `macro_regime`-composite som
> `regime_score`-feature i rankern. Behåll båda valbara; jämför vilken som höjer IC (#1:s gate).

---

## B. Ensemble-modell

**Fil:** `stock-scanner-fix/core/regime_ensemble.py` (ny)

Träna TVÅ modeller (återanvänd `core/ml_ranker._fit_model`):
- **Modell A** — LambdaRank på 5 års historik (långsam, stabil struktur).
- **Modell B** — regressor/ranker på 2 års historik (fångar senaste samband).

```python
def predict_ensemble(scored_df, universe="universe") -> pd.DataFrame:
    """Returnerar scored_df med:
       pred_a, pred_b (percentil-rank 0-100),
       ml_rank (regimviktad ensemble),
       ml_uncertainty (|rank_a - rank_b|, 0-100),
       ml_flag_uncertain (bool, > tröskel)."""
```
Regimvikt (från `get_current_regime`):
```
TJUR     → vikt A 0.4, B 0.6   (lita mer på senaste samband i stark marknad)
NEUTRAL  → vikt A 0.5, B 0.5
BJÖRN    → vikt A 0.7, B 0.3   (lita mer på lång historik i stress)
```
`ml_rank = wA*pred_a + wB*pred_b`. `ml_uncertainty = abs(pred_a - pred_b)`.
Om `ml_uncertainty > 20` (percentilenheter) → `ml_flag_uncertain=True` och sänk
aktiens visningsprioritet (markera "Osäker" i UI).

**Acceptanstest B:** På samma testdata ger ensemble ett `ml_rank` mellan pred_a/pred_b
enligt regimvikterna; uncertainty beräknas korrekt; höga-oenighet-aktier flaggas.

---

## C. Validering & gate (återanvänd #1)

Utvärdera ensemble med **samma purged walk-forward** (`core/ml_validation.py`) och
`core/ml_evaluation.compare_models`. Lägg ensemble som tredje kandidat:
- `scripts/eval_model.py --compare-all` → tabell: XGBoost vs LambdaRank vs Ensemble
  (IC, IR, decil-spread, p-value, per-regim-uppdelning).
- **Gate:** Ensemble deployas BARA om den slår bästa enkel-modellen på OOS IC + decil-spread.
  Per-regim-uppdelning (IC i björn/neutral/tjur separat) ska visa att ensemblen särskilt
  hjälper i björn/övergångsregim (annars är komplexiteten inte motiverad).

---

## D. Pipeline-integration

`core/daily_pipeline.py`: byt `predict_ranker()` mot `predict_ensemble()` BARA om gaten i C
godkänt. Annars behåll enkel ranker. Nya kolumner (`ml_uncertainty`, `ml_flag_uncertain`,
`regime` snapshot) flödar via parquet → `db_loader` → scan_results.

**Migration (marketscan):** `0NN_ml_uncertainty.sql` — lägg kolumner på scan_results:
`ml_uncertainty FLOAT`, `ml_flag_uncertain BOOLEAN`, `regime_at_scan TEXT`.

`outcome_filler.log_predictions`: höj `model_version` → `ensemble_v1` så utfall kan jämföras
mot `ranker_v2` i `prediction_outcomes`.

---

## E. Frontend

- Aktiekort: visa regim-snapshot ("Bedömt i: Tjurmarknad") + "Osäker prognos"-markering
  när `ml_flag_uncertain` (tooltip förklarar att modellerna är oense → lägre tillförlitlighet).
- AI-prestanda-sidan (admin): per-regim-IC-graf + ensemble vs enkel-modell över tid.

---

## Filer som rörs
| Repo | Fil | Åtgärd |
|---|---|---|
| stock-scanner-fix | `core/regime_hmm.py` | NY — HMM-regim (#6) |
| stock-scanner-fix | `core/regime_ensemble.py` | NY — ensemble |
| stock-scanner-fix | `scripts/eval_model.py` | `--compare-all` + per-regim |
| stock-scanner-fix | `core/daily_pipeline.py` | byt till ensemble (om gate OK) |
| stock-scanner-fix | `tests/test_regime_hmm.py`, `tests/test_ensemble.py` | NYA |
| stock-scanner-fix | `requirements.txt` | `hmmlearn` |
| marketscan | `supabase/migrations/0NN_ml_uncertainty.sql` | NY |
| marketscan | `backend_worker/db_loader.py` | mappa nya kolumner |
| marketscan | `backend_worker/outcome_filler.py` | `model_version=ensemble_v1` |
| marketscan | `apps/web/components/stock/…`, `ai-prestanda/` | regim + osäkerhet |

## Definition of Done
- [ ] HMM ger 3 ordnade regimer (björn lägst avkastning); test A grönt.
- [ ] Ensemble med regimvikter + osäkerhetssignal; test B grönt.
- [ ] Per-regim-IC visar var ensemblen hjälper; gate respekterad.
- [ ] Deploy bara om OOS-vinst; annars enkel ranker kvar (dokumentera beslutet).
- [ ] Frontend visar regim + osäkerhet.
- [ ] `docs/SYSTEM_AI.md` uppdaterad.
