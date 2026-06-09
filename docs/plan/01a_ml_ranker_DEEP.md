# Spec 01a (DJUP) — #1: ML-ranker som scoring-hjärna

> **Detta är den utvecklade, fördjupade planen för det högst prioriterade projektet.**
> Den ersätter inte `01_ml_ranker_lambdarank.md` utan **fördjupar** den: mer teori (VARFÖR),
> mer exakt nulägesbild, och en fasindelad implementation med gater.
>
> **Repo:** primärt `stock-scanner-fix` (ML-hjärnan), loopen i `marketscan/backend_worker`.
> **Författare av koden:** DeepSeek v4-flash/pro — följ faserna i ordning, hoppa inte.
> **Läs först:** `00_MASTER_PLAN.md`. Läs sedan dessa filer HELT innan kod:
> `core/ml_predictor.py` (särskilt rad 60–195, 505–567, 668–712, 1568–1790),
> `core/ml_ranker.py`, `core/ml_evaluation.py`, `core/ml_validation.py` (skapas här),
> `marketscan/backend_worker/outcome_filler.py`, `core/macro_regime.py`,
> `scripts/train_ranker.py`, `scripts/build_ml_dataset.py`.

---

## 1. Varför detta är det viktigaste projektet

Varje rekommendation användaren ser (`STARK/OK/AVVAKTA`, sortering i screenern,
"Toppaktier idag", `predicted_return`, `ml_rank`) flödar genom scoring-hjärnan. Om
rankningen är nära slumpen är HELA produkten nära slumpen — oavsett hur fin frontend är.

Nuvarande tillstånd enligt projektets egen dokumentation: **Rank IC 0.027, hit-rate 52.3 %,
DSR 0.0**. Det betyder i praktiken *ingen statistiskt säkerställd edge*. Att lyfta detta är
den enskilt största hävstången i hela systemet — och allt annat (regimensemble #15, insider
#5, MEWS #3, riskprofil #19) blir mer värt när motorn under dem faktiskt rankar rätt.

**Mål:** ärlig, läckagefri **Rank IC > 0.05** (helst 0.08+), med **decil-spread > 0** och
**DSR > 0.5**, samt en modell som förbättras över tid genom att lära av faktiska utfall.

---

## 2. Teori — vad som är fel och varför (läs detta noga)

### 2.1 Vad Rank IC är, och varför 0.027 är illa
**Information Coefficient (IC)** = Spearman-rangkorrelation mellan modellens prediktion och
den faktiska framtida avkastningen, beräknad **per datum** (tvärsnitt av alla aktier samma
dag) och sedan medelvärdesbildad över alla datum.

- IC = 0 → modellen rankar som slump.
- IC ≈ 0.02–0.03 → knappt urskiljbart från brus (dagens läge).
- IC ≈ 0.05 → svag men reell edge (industriell baslinje för aktie-ML).
- IC ≈ 0.08–0.12 → stark edge (LambdaRankIC-papret når 0.115 på 21k aktier).

Lika viktigt som IC:s nivå är dess **stabilitet**: `ICIR = mean(IC) / std(IC)` (information
ratio på IC-serien). Hög IC som svänger vilt mellan +0.2 och −0.2 är inte handlingsbar. Vi
optimerar för IC **och** ICIR.

### 2.2 Läckagemekanismen (varför backtest ljuger)
Target är `forward_return_30d` = avkastningen de kommande 30 kalenderdagarna. En träningsrad
daterad **1 juni** har en etikett som beror på priser ända till **1 juli**.

Om valideringen delar train/test så här (nuvarande `ml_ranker._walk_forward_validate`):
```
train = allt med datum < 1 juni
test  = datum i [1 juni, 1 juli]
```
…så innehåller de SISTA träningsraderna (sent i maj) etiketter som sträcker sig in i juni —
**samma period som testet**. Modellen har då indirekt "sett framtiden". Resultat: backtest-IC
ser bra ut, live-IC kollapsar till 0.027. Detta är den klassiska *label-överlappnings­läckan*.

**Fix (Lopez de Prado, "purging" + "embargo"):** ta bort träningsrader vars etikett-fönster
överlappar testperioden, och lägg en lucka (embargo) ≥ targethorisonten:
```
train = datum < (test_start − 35 dagar)     # 30d horisont + 5 handelsdagars marginal
test  = datum i [test_start, test_end]
```
Då har varje träningsrads 30-dagars-etikett hunnit realiseras *före* testet börjar. IC blir
lägre men **ärlig** — och ärlig IC är det enda som överlever live.

> **Nyckelinsikt om nuläget:** Den GAMLA XGBoost-vägen (`ml_predictor.train_with_cpcv`,
> rad 712) har **redan** purge via `_cpcv_split` (rad 668, `purge_start = max(0, test_start
> - 30)`) **och** Deflated Sharpe Ratio (`_deflated_sharpe_ratio`, rad 60). Den NYA
> ranker-vägen (`ml_ranker.py`) saknar det. Projektet handlar därför till stor del om att
> **porta och förena** den befintliga rigoröra apparaten till ranker-vägen — inte uppfinna ny.

### 2.3 Varför ranking slår regression (objektiv-mismatch)
XGBoost-regressorn minimerar MSE mot avkastningens *nivå*. Men vi bryr oss bara om *ordningen*
(vilken aktie slår vilken). Att exakt träffa att A gav +2.1 % och B +1.8 % är irrelevant —
det enda som spelar roll är att A rankas över B. När modellen lägger kapacitet på att
förutsäga nivåer (som domineras av marknadsbrus) blir rankningen sämre.

`ml_ranker.py` adresserar redan detta med LightGBM **LambdaRank** (objective=`lambdarank`,
metric=`ndcg`). Forskning (arXiv:2605.00501, LambdaRankIC) visar att man kan gå längre och
optimera **direkt mot Rank IC** istället för NDCG, vilket gav 0.115 vs 0.042–0.047 för
regression. Vi inför det som ett valbart objektiv och låter en gate avgöra vinnaren.

### 2.4 "Lär av sina fel" — omträningsflywheel
Statiska modeller förfaller (alpha-decay). Systemet har redan grunden: varje natt loggas
prediktioner till `prediction_outcomes`, och `outcome_filler` fyller i `realized_return_30d`
efter 30 dagar. Det som saknas är att **stänga loopen**: låt den växande utfallstabellen bli
träningsdata och träna om walk-forward varje vecka. Då lär modellen sig av sina faktiska
träffar och missar, och vi kan *visa* IC-trenden över tid.

---

## 3. Lösningsarkitektur (helhet)

```
                ┌─────────────────────────────────────────────┐
                │  core/ml_validation.py (NY)                 │
                │  • purged_walk_forward_folds (embargo)      │
                │  • dsr() (portad från ml_predictor)         │
                │  • EN sanning för läckagefri validering     │
                └───────────────┬─────────────────────────────┘
                                │ används av
        ┌───────────────────────┼───────────────────────────┐
        ▼                       ▼                            ▼
core/ml_ranker.py        core/ml_evaluation.py       core/regime_ensemble.py (#15)
(LambdaRank +            (compare_models +            (bygger ovanpå, senare)
 rank_ic-objektiv)        DSR + per-regim-gate)

        │ predict_ranker()  (parquet → scan_results via marketscan db_loader)
        ▼
   prediction_outcomes (loggas nattligt)  ──30d──►  realized_return_30d (outcome_filler)
        │                                                   │
        └──────────────► VECKOVIS OMTRÄNING ◄───────────────┘
                         (.github/workflows/ml_retrain.yml)
                         dataset av realiserade utfall → train_ranker → gate → deploy
```

---

## 4. Implementation i faser (följ ordningen)

### FAS 0 — Ärlig baslinje (gör FÖRST, ingen kodändring i modellen)
Syfte: etablera den sanna, läckagefria IC:n för nuvarande ranker INNAN något ändras, så vi
kan mäta förbättring.

1. Skapa `scripts/audit_baseline.py` som kör nuvarande `ml_evaluation.compare_models()` på
   befintlig träningsdata och skriver `models/baseline_report.json` med: ranker-IC,
   xgboost-IC, decil-spread, antal datum, datumspann, antal unika tickers, andel rader med
   `forward_return_30d`-NaN.
2. **Dokumentera** dessa siffror i rapporten — de är "före"-värdena. Förvänta dig att
   ranker-IC här fortfarande är optimistisk (läckage ej fixat ännu).

**Gate FAS 0:** rapport finns och är incheckad. Inget annat.

---

### FAS 1 — Förena läckagefri validering (#4 inviks)
**Fil:** `core/ml_validation.py` (NY). Innehåll enligt `01_ml_ranker_lambdarank.md §1`
(purged_walk_forward_folds) PLUS porta in DSR:

```python
# Porta (kopiera, behåll signaturen) _deflated_sharpe_ratio från ml_predictor.py rad 60.
def deflated_sharpe_ratio(observed_sharpe, num_trials, T, skewness, kurtosis) -> float: ...
```

Konstanter:
```python
FORWARD_HORIZON_DAYS = 30
EMBARGO_DAYS = 35          # horisont + marginal
```

**Ändra två anropare** att hämta folds från `purged_walk_forward_folds`:
- `core/ml_ranker.py::_walk_forward_validate` (rad ~336–417).
- `core/ml_evaluation.py::evaluate_model` (rad ~213–243).
Behåll all metrik-kod (IC, decil-spread, hit-rate) oförändrad — byt BARA fold-genereringen.

**Edge cases att hantera (skriv tester):**
- Datumspann kortare än `initial_months + embargo + test_months` → 0 folds → returnera tom
  lista + logga varning (krascha inte).
- Datum med < `MIN_GROUP_SIZE` aktier filtreras i test (redan idag).
- Embargo får inte göra träningsmängden tom → om `len(train_idx) < min_train_rows`, hoppa
  folden.

**Gate FAS 1:**
- `tests/test_ml_validation.py` grönt: ingen träningsrad inom `[test_start−35d, test_start)`.
- Kör `audit_baseline.py` igen → ranker-IC EFTER embargo loggas som "ärlig baslinje".
  Denna siffra är referensen allt framöver jämförs mot. (Förvänta: lägre än FAS 0, korrekt.)

---

### FAS 2 — LambdaRankIC-objektiv (valbart, gate avgör)
**Fil:** `core/ml_ranker.py::_fit_model`. Lägg parameter `objective_mode` med tre lägen:

| Läge | Beskrivning |
|---|---|
| `lambdarank_ndcg` (nuvarande) | LightGBM LambdaRank, quintile-labels, metric NDCG |
| `rank_ic` (NY) | Träna mot per-datum-rankad target (`groupby('date').rank(pct=True)`), regressivt — approximation av direkt IC-optimering, robust och enkel |
| `xgboost_cs` (fallback) | Befintlig XGBoost-regressor mot `target_cs` |

`rank_ic`-implementation (robust första version utan custom C-loss):
```python
df["label_rank"] = df.groupby("date")["forward_return_30d"].rank(pct=True)  # 0..1
# LightGBM-regressor mot label_rank, samma tidsviktning som idag.
```
> Motivering: en full custom LambdaRankIC-loss (papret) kräver gradient-hack i LightGBM.
> Per-datum-rankad regressionstarget ger 80 % av effekten till 20 % av komplexiteten och är
> svår att göra fel. Lämna en `# NOTE`-kommentar om att custom-loss kan testas i batch 2.

**Gate FAS 2:** `scripts/eval_model.py --compare-objectives` kör alla tre lägena genom
`evaluate_model` (purged) och skriver en tabell med **IC, ICIR, decil-spread, DSR, p-value**
per läge. Deploya det läge som vinner på IC **och** decil-spread **och** har DSR > 0.5.
Skriv vinnaren i `models/ml_ranker_universe_metrics.json` (fältet `objective_mode`).

---

### FAS 3 — Feature-expansion (koppla #5, #3, regim)
Rankern använder idag 26 tekniska + 8 faktor-scores + 1 regim = 35 features. Lägg till
redan-existerande men outnyttjade signaler (om de finns i datasetet):

| Feature | Källa | Status |
|---|---|---|
| `insider_cluster` | #5 (FI-kluster) | **Finns redan** som FUNDA_FEATURE (ml_predictor rad 163) — säkerställ att den hamnar i träningsdatasetet |
| `insider_signal` | #5 | Finns (rad 162) |
| `mews_score` + 6 delfaktorer | #3 (MEWS) | NY — lägg till när #3 byggts |
| `regime_score` | macro_regime / HMM (#15) | Finns (rad 74 i ml_ranker) |
| `fcf_yield_rank`, `piotroski_score` | fundamenta | Finns (rad 160–161) |

**Viktigt (point-in-time):** FUNDA_FEATURES är bara point-in-time-säkra i live-inference,
INTE i historisk backtest (ml_predictor rad 154–158 varnar för detta). I
träning/backtest: använd dem ENDAST om datasetet har historiskt korrekta (laggade)
fundamentavärden. Annars håll dem till inference. Skriv tydligt i koden vilka features som är
backtest-säkra. Detta undviker en andra, subtilare läcka (lookahead i fundamenta).

**Gate FAS 3:** kör feature-permutation-importance (`feature_permutation_importance` finns,
ml_predictor rad 1434) på OOS-folds. Behåll bara features med icke-negativt bidrag; logga
vilka som droppades. IC ska inte sjunka när brusiga features tas bort.

---

### FAS 4 — Omträningsflywheel (stäng loopen)
Detaljer i `01_ml_ranker_lambdarank.md §4`. Fördjupning här:

**Datasetbygge (D1)** — välj väg A (rekommenderad):
- Bygg träningsrader ur `score_history` (faktor-delscorer per ticker+datum) + realiserade
  30d-returns. Verifiera `score_history`-schemat (läs migrationen som skapar den +
  `backend_worker/score_tracker.py`).
- För varje (ticker, scan_date): features = faktor-scores (+ ev. cachen tech-features om de
  finns), target = `forward_return_30d` = (pris 30d senare − pris) / pris. Priser från
  `prediction_outcomes` (`price_at`, `price_30d`) där de finns — det är redan realiserade,
  läckagefria utfall.

**Survivorship (KRITISKT):** om avlistade/konkursade bolag saknas i historiken blir IC
optimistisk (överlevnadsbias). Åtgärd:
- Inkludera tickers som FANNS vid scan-datumet även om de senare avlistats. `prediction_outcomes`
  loggade dem vid prediktionstillfället → de finns kvar i tabellen → använd den som
  survivorship-korrekt sanningskälla för träning. Dokumentera kända luckor.

**Veckovis omträning (D2):** `.github/workflows/ml_retrain.yml` (marketscan):
1. Checka ut båda repon, `PYTHONPATH` satt.
2. Bygg dataset (D1) från Supabase (`DATABASE_URL`).
3. `python -m scripts.train_ranker` → ny `.pkl`.
4. `python -m scripts.eval_model --gate` → jämför ny modell mot **deployad** modells
   `_metrics.json`. Deploya BARA om: ny IC > gammal IC, ny decil-spread > gammal, ny DSR > 0.5.
5. Om deploy: höj `model_version` (`ranker_v2` → `v3`…) och spara modellen där pipelinen
   laddar den (verifiera: lokalt `models/` eller R2 via `r2_uploader.py`).
6. Registrera workflow i `admin.py _WORKFLOW_INPUTS` + admin-panelen.

**A/B-mätbarhet:** eftersom `prediction_outcomes` har `model_version` kan du i AI-prestanda
jämföra realiserad IC per modellversion → bevisa att v3 faktiskt slår v2 *live*, inte bara i
backtest. Detta är den slutgiltiga sanningen.

**Gate FAS 4:** workflow kör manuellt (dispatch); en ny modell skapas; gaten loggar
deploy-beslut; `model_version` höjs vid deploy.

---

### FAS 5 — Live-övervakning & alpha-decay-larm
**Fil:** `backend_worker/ml_monitor.py` (NY, marketscan) eller utöka `ml_performance.py`-routern.
- Beräkna rullande 30-dagars **realiserad** Rank IC ur `prediction_outcomes` (WHERE
  realized_return_30d IS NOT NULL), per `model_version`.
- Om realiserad IC < 0.02 i 3 månader i rad → skriv larm (notistabell / e-post via befintlig
  `digest_mailer`) "modellens edge har förfallit, omträning rekommenderas".
- Exponera i AI-prestanda-sidan: IC-trend-graf per modellversion + nuvarande regim.

**Gate FAS 5:** AI-prestanda visar live realiserad IC-trend; larm triggar i ett syntetiskt
test där IC sänks artificiellt.

---

## 5. Utvärderingsprotokoll (definition av "bättre")

En modell är BÄTTRE och får deployas endast om ALLA gäller på **OOS purged walk-forward**:
1. **Rank IC** (medel) högre än nuvarande deployade modell.
2. **Decil-spread** (topp-20 % − botten-20 % avkastning) högre och > 0.
3. **DSR > 0.5** (deflated Sharpe — skyddar mot multiple-testing/överoptimering).
4. **ICIR** inte sämre (stabilitet).
5. (För #15 senare) per-regim-IC visar var modellen hjälper.

Alla siffror skrivs till `models/*_metrics.json` och visas i AI-prestanda. **Ingen modell
deployas på in-sample-siffror.**

---

## 6. Riskregister (specifikt för #1)

| Risk | Sannolikhet | Mitigering |
|---|---|---|
| Ärlig IC < 0.05 efter embargo | Medel | Det är ett ÄRLIGT utfall, inte ett fel. Rapportera, lägg till features (#5/#3), testa rank_ic-objektiv. Bygg inte vidare på en falsk 0.15. |
| Survivorship-bias i träningsdata | Hög om ej hanterad | Använd `prediction_outcomes` (loggat vid tillfället) som sanningskälla; dokumentera luckor |
| Fundamenta-lookahead (andra läckan) | Medel | FUNDA_FEATURES bara om historiskt laggade; annars endast inference |
| LightGBM saknas i Actions-miljön | Låg | Fallback till XGBoost finns redan; pinna `lightgbm` i requirements |
| Overfitting via många trials | Medel | DSR-gate straffar multiple testing; logga antal trials |
| Omträning deployar sämre modell | Låg | Hård gate (IC+spread+DSR) mot deployad modell; aldrig auto-deploy utan gate |
| Modell-pickle-tampering | Låg | SHA256-verifiering finns redan i `save_ranker`/`load_ranker` |

---

## 7. Filer som rörs (komplett)

| Repo | Fil | Åtgärd |
|---|---|---|
| stock-scanner-fix | `core/ml_validation.py` | NY — purged folds + DSR (portad) |
| stock-scanner-fix | `core/ml_ranker.py` | `_walk_forward_validate` (purged) + `_fit_model` (objective_mode) |
| stock-scanner-fix | `core/ml_evaluation.py` | `evaluate_model` (purged) + DSR i compare |
| stock-scanner-fix | `scripts/audit_baseline.py` | NY — FAS 0 |
| stock-scanner-fix | `scripts/eval_model.py` | `--compare-objectives`, `--gate` |
| stock-scanner-fix | `tests/test_ml_validation.py` | NY |
| stock-scanner-fix | `requirements.txt` | pinna lightgbm, scipy |
| marketscan | `backend_worker/ml_trainer.py` | dataset från realiserade utfall (survivorship-säkert) |
| marketscan | `backend_worker/ml_monitor.py` | NY — live IC-decay-larm |
| marketscan | `.github/workflows/ml_retrain.yml` | NY — veckovis omträning + gate |
| marketscan | `backend_worker/outcome_filler.py` | höj `model_version` vid deploy |
| marketscan | `apps/api/routers/ml_performance.py` | live realiserad IC per version |
| marketscan | `apps/api/routers/admin.py` | registrera retrain-workflow |
| marketscan | `apps/web/app/(app)/ai-prestanda/` | IC-trend per version + regim |

---

## 8. Öppna beslut att ta med användaren (innan FAS 4)
1. **Modell-lagring:** laddar pipelinen modellen från lokala `models/` (committad) eller
   från R2 (`r2_uploader.py`)? Det avgör hur `ml_retrain.yml` deployar. → verifiera, fråga om oklart.
2. **Omträningsfrekvens:** veckovis föreslås. Vill användaren ha tätare under rapportsäsong?
3. **Minsta datamängd för flywheel:** flywheel ger effekt först när ~3+ månaders utfall
   ackumulerats. Tills dess tränas på `score_history`-härledd data. Bekräfta att det är OK
   att börja med historiken och låta utfallen ackumulera parallellt.

---

## 9. Definition of Done (hela #1)
- [ ] FAS 0: ärlig baslinje dokumenterad (`models/baseline_report.json`).
- [ ] FAS 1: `core/ml_validation.py` + tester; ranker & evaluation använder purged folds.
- [ ] FAS 2: tre objektiv jämförda; vinnaren deployad via gate (IC+spread+DSR).
- [ ] FAS 3: feature-set rensat via OOS-permutation; #5:s `insider_cluster` med.
- [ ] FAS 4: veckovis omträning med hård deploy-gate; survivorship hanterat; `model_version` höjs.
- [ ] FAS 5: live realiserad IC-trend + alpha-decay-larm i AI-prestanda.
- [ ] Slutmål: ärlig OOS Rank IC > 0.05 (rapportera ärligt om ej nått + nästa steg).
- [ ] `docs/SYSTEM_AI.md` uppdaterad.
