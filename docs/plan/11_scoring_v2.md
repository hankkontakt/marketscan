# Spec 11 — Scoring v2 (forskningsbaserade förbättringar av rankern)

> **Repo:** stock-scanner-fix (ML-hjärnan). **Insats:** M–L per punkt.
> **Skriven för:** DeepSeek v4-flash. Läs `docs/plan/00_MASTER_PLAN.md §6` + `01a_ml_ranker_DEEP.md`
> (FAS-strukturen, gate-kriterier) först.
> **Bygger på batch 1 #1:** `core/ml_ranker.py`, `core/ml_validation.py`
> (`purged_walk_forward_folds`, `deflated_sharpe_ratio`), `core/ml_evaluation.py`
> (`per_date_ic`, `decile_spread`, `ic_significance`, `compare_models`).
>
> **GEMENSAM GATE (alla punkter):** deploya en ändring BARA om den på OOS purged walk-forward
> slår nuvarande på **Rank IC OCH decil-spread** och har **DSR > 0.5**. Annars: rapportera
> ärligt, behåll gammalt. Bygg i ordning **S5 → S1 → S2 → S3 → (S4 valfri)**.

## S5 — Fler features in i rankern (billigast, gör FÖRST)
**Mål:** mata #5/#7/#3-signalerna in i rankern (de finns redan), så de skärper *rankningen*
(percentil-output) utan att grumla Totalbetyget (anti-blur, DEL 0).
**Bygg:**
- I `core/ml_ranker.py`: lägg i `RANKER_FEATURES` (eller en ny `EXTRA_SIGNAL_FEATURES`-lista som
  läggs till om kolumnerna finns i datasetet): `insider_cluster` (0/1), `cluster_score`,
  `qualitative_score`, `mews_score`.
- I dataset-bygget (marketscan `backend_worker/ml_trainer.py` / `scripts/build_ml_dataset.py`):
  joina in dessa per (ticker, datum) DÄR historiskt laggade värden finns.
- **Point-in-time (kritiskt, se 01a FAS 3):** dessa får bara användas i TRÄNING om historiskt
  korrekta (laggade) värden finns. Saknas historik → använd dem ENDAST i live-inference, inte i
  backtest. Markera i koden vilka kolumner som är backtest-säkra (kommentar + en lista
  `BACKTEST_SAFE_FEATURES`).
**Gate:** permutation-importance OOS (`feature_permutation_importance` finns i ml_predictor) —
behåll bara features med icke-negativt bidrag; logga vilka som droppades.

## S1 — Uniqueness-viktning (Lopez de Prado)
**Problem:** överlappande 30d-labels är ej IID; rankern viktar idag bara på tidsdecay
(`RANKER_HALFLIFE_YEARS`), inte uniqueness → samtidiga redundanta labels överrepresenteras.
**Bygg i `core/ml_validation.py`:**
```python
def label_uniqueness(dates: pd.Series, horizon_days: int = 30) -> pd.Series:
    """Andel av varje rads [date, date+horizon] som inte överlappar andra labels.
       1 = helt unik, ~0 = mycket samtidighet. Vikt ∝ uniqueness."""
    # Räkna samtidiga öppna labels per kalenderdag; varje rads vikt = mean(1/concurrency)
    # över sitt fönster. Effektiv implementation: sortera datum, glidande räkning.

def combine_weights(time_decay: pd.Series, uniqueness: pd.Series) -> pd.Series:
    w = time_decay * uniqueness
    return w / w.mean()
```
**Koppla i `core/ml_ranker.py::_fit_model`:** efter att `weights` (tidsdecay) beräknats,
`weights = combine_weights(weights, label_uniqueness(df["date"]))` bakom flagga
`use_uniqueness=True` (default True, men lätt att stänga av för A/B).
**Gate:** jämför med/utan i `eval_model`; behåll om OOS IC/ICIR ej försämras.

## S2 — Meta-labeling + triple-barrier (störst potential)
**Idé:** primärmodell = rankern (vilka ska upp). Sekundär "meta"-modell = P(signalen korrekt)
→ filtrera falska positiva, ge konfidens.
**Bygg `core/meta_labeling.py` (NY):**
```python
def triple_barrier_labels(prices: pd.DataFrame, tp=0.09, sl=0.09, max_days=29) -> pd.Series:
    """Per (ticker, datum): 1 om +tp nås före −sl och före max_days, annars 0.
       Parametrar = optimum från arXiv:2504.02249. Använd OHLCV-cache (data/cache)."""

def train_meta_model(primary_df: pd.DataFrame, features: list[str]) -> object:
    """LightGBM-binärklassificerare på rader där primären sa KÖP (topp-decil ml_rank),
       target = triple_barrier-träff. Walk-forward via purged_walk_forward_folds."""

def apply_meta(scored_df: pd.DataFrame, meta_model) -> pd.DataFrame:
    """Lägg kolumn meta_confidence (0–1). STARK prioriteras/filtreras på hög meta_confidence."""
```
**Användning:** efter `predict_ranker`, kör `apply_meta`; UI kan visa "STARK (hög tillförlitlighet)"
för hög `meta_confidence`. **Gate:** precision/hit-rate på topp-decil med vs utan meta-filter (OOS);
behåll om precision↑ utan att täckningen kollapsar.

## S3 — Conformal prediction (kalibrerad konfidens)
**Bygg `core/conformal.py` (NY):**
```python
def calibrate(residuals: np.ndarray, alpha: float = 0.1) -> float:
    """Split-conformal: returnera (1-alpha)-kvantil av |residualer| från kalibreringsset."""

def predict_interval(point_preds: np.ndarray, q: float) -> tuple[np.ndarray, np.ndarray]:
    """[point - q, point + q] → garanterad ~ (1-alpha) täckning."""
```
**Användning:** kalibrera på senaste OOS-fold; ge varje aktie ett band för `predicted_return`.
UI: "STARK (90 % konfidens)". Parar med #15:s `ml_uncertainty`. **Gate:** empirisk täckning
≈ nominell (90 %) på OOS; annars omkalibrera.

## S4 — Stacked heterogen ensemble (valfri, sist)
**Endast om S1–S3 inte räcker.** Bygg ovanpå `core/regime_ensemble.py`: stacka
LightGBM-ranker (A) + sekvensmodell LSTM/GRU (B, kräver `torch`/`keras`, kör i Actions) +
linjär (C) via en meta-learner (linjär stacking på OOS-prediktioner). Gate som vanligt.

## Filer
| Fil | Åtgärd |
|---|---|
| `core/ml_ranker.py` | S5 (features) + S1 (uniqueness-vikt i `_fit_model`) |
| `core/ml_validation.py` | S1 (`label_uniqueness`, `combine_weights`) |
| `core/meta_labeling.py` | S2 (NY) |
| `core/conformal.py` | S3 (NY) |
| `core/regime_ensemble.py` | S4 (valfri stacking) |
| marketscan `backend_worker/ml_trainer.py` | S5 (joina signaler i dataset, point-in-time-säkert) |
| `scripts/eval_model.py` | gates för varje punkt |
| `tests/test_meta_labeling.py`, `tests/test_conformal.py` | NYA |

## Definition of Done (per punkt)
- [ ] OOS-gate (Rank IC + decil-spread + DSR) bättre eller ej sämre än nuvarande.
- [ ] Deploya bara på OOS-vinst; annars rapportera + behåll gammalt.
- [ ] Point-in-time-säkerhet dokumenterad (S5).
- [ ] `docs/SYSTEM_AI.md` uppdaterad.
