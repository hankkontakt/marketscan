# MarketScan — Batch 1: Master-plan

> **Syfte:** Detta dokument är översiktsplanen för 6 stora förbättringsprojekt.
> Varje projekt har ett eget detaljerat spec-dokument (01–06) som är skrivet så
> att en enklare AI (DeepSeek v4-flash/pro) kan implementera koden utan att gissa.
>
> **Läs ALLTID detta dokument först**, sedan relevant spec. Avvik inte från
> konventionerna i avsnitt 6 utan att flagga det.

---

## 0. Status & beslut (fastställda med användaren 2026-06-09)

| Beslut | Värde |
|---|---|
| Projekt i batch 1 | #1, #3, #5, #7+#12, #15, #19 |
| #4 (Purged CV) | Inviks som delsteg i #1 |
| #6 (HMM-regim) | Inviks som delsteg i #15 |
| #7 + #12 | Sammanslås till ETT system ("Svensk dokumentintelligens") |
| Leverans | Master-plan + en delplan per projekt (detta) |
| Budget (LLM/data) | Gemini free tier + DeepSeek v4-flash (betald), mål **< 200–300 kr/mån** |
| Kodförfattare | DeepSeek v4-flash / v4-pro följer dessa specs |

---

## 1. Projektöversikt

| # | Namn | Spec | Repo (huvudsak) | Storlek |
|---|---|---|---|---|
| **#1** | ML-ranker: LambdaRank + läckagefri validering | `01_ml_ranker_lambdarank.md` | stock-scanner-fix | Stor |
| **#3** | MEWS — Multi-Bagger Early Warning Score | `02_mews_multibagger.md` | stock-scanner-fix | Stor |
| **#5** | FI Insider Cluster (robust bulk-ingestion) | `03_fi_insider_cluster.md` | marketscan | Stor |
| **#7+#12** | Svensk dokumentintelligens (RAG + Q-rapport-NLP) | `04_swedish_doc_intelligence.md` | marketscan | Massiv |
| **#15** | Regimberoende ensemble (+HMM-regim) | `05_regime_ensemble.md` | stock-scanner-fix | Massiv |
| **#19** | Riskprofil + LLM-Black-Litterman portfölj | `06_black_litterman.md` | marketscan | Massiv |

---

## 2. Systemarkitektur — så hänger repona ihop

Det finns **två repon** på användarens dator:

```
C:/Users/hthur/OneDrive/Desktop/
├── stock-scanner-fix/      ← SCORING- & ML-HJÄRNAN (Python, körs i GitHub Actions)
│   ├── core/               ← scoring.py, ml_ranker.py, ml_predictor.py, macro_regime.py …
│   ├── smallcap/           ← småbolagsmodell (scoring.py, scanner.py, insider.py …)
│   ├── scripts/            ← train_ranker.py, eval_model.py, build_ml_dataset.py
│   ├── models/             ← tränade modeller (.pkl) + metrics (.json)
│   └── data/               ← parquet-cache, OHLCV-cache
│
└── marketscan/             ← PRODUKTEN (API + webb + DB + workers)
    ├── apps/api/           ← FastAPI-routrar (REST)
    ├── apps/web/           ← Next.js-frontend
    ├── backend_worker/     ← jobb som körs i GitHub Actions (pipeline, fetchers, ml_trainer)
    │   └── pipeline/entrypoint.py  ← BRYGGAN: kör stock-scanner-fix/core via PYTHONPATH
    └── supabase/migrations/← Postgres-schema (SQL, körs manuellt i Supabase)
```

**Dataflöde (dagligt):**
```
GitHub Actions (nattlig cron)
  → backend_worker/pipeline/entrypoint.py
     → importerar stock-scanner-fix/core/ (via PYTHONPATH=.:../stock-scanner-fix)
     → kör daily_pipeline → scoring.py (8 faktorer) → ml_ranker.predict_ranker()
     → skriver scored_universe.parquet
  → backend_worker/db_loader.py  → laddar parquet → Supabase scan_results
  → backend_worker/outcome_filler.log_predictions()  → prediction_outcomes
  → (nattligt) outcome_filler.fill_outcomes()  → fyller realized_return_30d efter 30d
  → apps/api läser scan_results → apps/web visar
```

**Konsekvens för planering:**
- ML/scoring-ändringar (#1, #3, delar av #15) görs i **stock-scanner-fix**.
- Datatabeller, API, frontend, workers (#5, #7, #19, delar av #15) görs i **marketscan**.
- Varje spec anger EXAKT vilket repo + filsökväg varje ändring gäller.

---

## 3. Nya delsystem som behöver byggas (delas av flera projekt)

| Delsystem | Byggs i | Används av | Spec |
|---|---|---|---|
| Purged Walk-Forward CV (embargo) | stock-scanner-fix `core/ml_validation.py` (ny) | #1, #15 | 01 |
| HMM-regimdetektor | stock-scanner-fix `core/regime_hmm.py` (ny) | #15 (matar #1-feature) | 05 |
| Svensk vektordatabas (pgvector) | marketscan migration + `backend_worker/rag/` | #7 | 04 |
| LLM-abstraktionslager (Gemini→DeepSeek-fallback) | marketscan `apps/api/core/llm_client.py` (ny) | #7, #19 | 04 |
| Riskprofil (questionnaire + DB) | marketscan migration + API | #19 | 06 |

> **VIKTIGT:** LLM-abstraktionslagret (04 §4) byggs FÖRST om både #7 och #19 ska
> köras, eftersom båda använder det. Bygg det en gång, återanvänd.

---

## 4. Kostnadsbudget (mål < 200–300 kr/mån)

| Tjänst | Användning | Kostnad |
|---|---|---|
| Gemini API (free tier) | Embeddings (10M tok/min gratis) + Flash-Lite extraktion (1000 req/dygn) | **0 kr** |
| DeepSeek v4-flash | Fallback när Gemini-kvot slut + komplex syntes | ~50–150 kr/mån vid måttlig volym |
| Supabase (befintlig) | pgvector-lagring (ingår i nuvarande plan) | 0 kr extra |
| FI insider-register | Gratis offentlig data | 0 kr |
| yfinance (fundamenta/pris) | Gratis | 0 kr |
| GitHub Actions | Befintliga workers + nya cron-jobb | 0 kr (inom free minutes) |
| LightGBM/hmmlearn/scipy | Open source, körs i Actions | 0 kr |

**Designprincip:** Allt som kan vara gratis SKA vara gratis. Betald LLM (DeepSeek)
används bara där kvalitet kräver det, alltid med hård cache (ai_cache-tabellen finns
redan) + budgettak. Varje spec som rör LLM har ett "Kostnadskontroll"-avsnitt.

> Om något projekt under implementation visar sig KRÄVA dyrare tjänst (t.ex. betald
> embeddings-modell för acceptabel svensk kvalitet) → **stanna och fråga användaren**,
> bygg inte vidare på en dyr lösning utan godkännande.

---

## 5. Beroenden & rekommenderad byggordning

```
Steg 1 (grund, blockerar andra):
  #1  ML-ranker + Purged CV  ─────┐  (etablerar läckagefri validering + modell-loop)
                                  │
Steg 2 (oberoende, kan parallellt):
  #3  MEWS                        │  (egen score, ingen ML-beroende)
  #5  FI Insider Cluster          │  (egen datapipeline + tabell)
                                  │
Steg 3 (bygger på steg 1):
  #15 Regimberoende ensemble  ◄───┘  (kräver #1:s ranker + ny HMM-regim)
                                     (#5:s insider-signal kan bli ML-feature)
Steg 4 (oberoende massiv):
  #7+#12  Svensk dokumentintelligens (greenfield; bygg LLM-lager först)
  #19     Riskprofil + Black-Litterman (kan använda #7:s LLM-lager + AI-committee)
```

**Motivering:**
- #1 först — den etablerar `core/ml_validation.py` (purged CV) som #15 återanvänder,
  och bevisar att modellen blivit bättre innan vi bygger ovanpå den.
- #3 och #5 är fristående datapipelines → kan byggas när som helst, bra "parallella spår".
- #15 sist av ML-spåren — den kombinerar #1:s ranker med regim + ev. #5:s insider-signal.
- #7 och #19 är produkt-/LLM-spår, oberoende av ML-spåret. Bygg LLM-lagret (delat) först.

---

## 6. Tvärgående konventioner (DeepSeek MÅSTE följa dessa)

### 6.1 Python (stock-scanner-fix + marketscan/backend_worker)
- Python 3.13. Använd `from __future__ import annotations` överst i nya moduler.
- Logging via `logging.getLogger(__name__)` — **aldrig** `print()` i bibliotekskod
  (CLI-entrypoints får använda `print()` för slutresultat).
- Nya beroenden läggs i RÄTT repos `requirements.txt` + nämns i spec.
- Alla nätverksanrop: timeout + try/except + rate-limit-delay (se befintliga mönster
  i `outcome_filler.py`, `fi_insider_fetcher.py`).
- Filskrivning av modeller/artefakter: atomisk (skriv `.tmp` → `os.replace`), se
  `ml_ranker.save_ranker()`.
- Aldrig hårdkoda hemligheter. Läs från `os.environ` (`DATABASE_URL`, `DEEPSEEK_API_KEY`,
  `GEMINI_API_KEY`, etc.).

### 6.2 Databas (marketscan/supabase/migrations)
- En migration per ny tabell/ändring, numrerad i sekvens (nästa lediga: **028**).
- Filnamn: `0NN_kort_beskrivning.sql`. Körs MANUELLT i Supabase SQL Editor (skriv det
  i spec:ens "Deploy"-avsnitt).
- Alla nya tabeller: `ENABLE ROW LEVEL SECURITY` + minst en RLS-policy.
- Publik aggregerad läsdata: `GRANT SELECT ... TO authenticated, anon`.
- Skrivning sker via service_role (kringgår RLS) från backend_worker.
- Idempotenta inserts: `ON CONFLICT ... DO NOTHING/UPDATE` + unik constraint.
- Lägg till `COMMENT ON TABLE ... IS '... Migration 0NN. Diagnostic marker: migration_0NN_namn.'`
  och registrera i `apps/api/.../diagnostics.py` USER_TABLES (mönstret finns i 024).

### 6.3 API (marketscan/apps/api)
- FastAPI-routrar i `apps/api/routers/`. Följ befintligt mönster:
  `router = APIRouter(prefix="/api/...", tags=[...])`.
- Auth: `Depends(get_current_user)` för user-data; `Depends(require_admin)` för admin-only.
- DB-access: `Depends(get_user_supabase)` (RLS-skyddad) eller `Depends(get_supabase_admin)`.
- Registrera nya routrar i `apps/api/main.py` (eller där routrar inkluderas — verifiera).
- Pydantic-scheman i `apps/api/schemas/`.

### 6.4 Frontend (marketscan/apps/web)
- Next.js App Router. Sidor i `apps/web/app/(app)/<namn>/`.
- Data-fetching via React Query-hooks i `apps/web/hooks/`, anropar `api()` från `lib/api`.
- Admin-only sidor: server-side JWT-admin-check (mönster i `kontrollpanel/page.tsx`),
  och länk i `components/layout/TopBar.tsx` bara om `isAdmin`.
- Färger/spacing via CSS-variabler (`var(--color-...)`). Aldrig hårdkodade hex.
- TypeScript måste passera `npx tsc --noEmit` innan commit.

### 6.5 GitHub Actions (nya cron-jobb)
- Workflow-filer i `.github/workflows/` (verifiera repo — workers ligger i marketscan).
- Varje nytt workflow med `workflow_dispatch`-inputs MÅSTE registreras i
  `apps/api/routers/admin.py` `_WORKFLOW_INPUTS`-dicten (annars 422 från GitHub).
- Lägg in workflow i admin-panelens lista (`components/admin/AdminSections.tsx`).
- Secrets: `DATABASE_URL`, `GEMINI_API_KEY`, `DEEPSEEK_API_KEY`, `GH_CHECKOUT_TOKEN`
  (befintliga). Nya secrets nämns explicit i spec.

### 6.6 Säkerhetsregler (ALDRIG bryt — från användarens stående direktiv)
- `GH_CHECKOUT_TOKEN` får ALDRIG nå frontend/bundle — endast backend-secret.
- `service_role`-nyckel endast i backend_worker/cron/admin-endpoints, aldrig frontend.
- Logga aldrig tokens, lösenord eller PII.
- `/api/debug/*`-endpoints MÅSTE vara admin-skyddade.
- Klient-felrapporterings-endpoint måste vara rate-limitad.
- Utför ALDRIG finansiella affärer / överför pengar åt användare (gäller även #19 —
  den ger FÖRSLAG på vikter, lägger ALDRIG order).

### 6.7 Dokumentationsplikt
- Efter varje implementerat projekt: uppdatera `docs/SYSTEM_AI.md` (marketscan) enligt
  dess "0. Underhållsprotokoll". Nya filer, funktioner, dataflöden, tabeller ska in.

---

## 7. Globala acceptanskriterier (gate per projekt)

Varje projekt anses KLART när:
1. All kod följer konventionerna i §6.
2. Projektets egna acceptanstester (i specen) passerar.
3. `cd apps/web && npx tsc --noEmit` är grönt (om frontend rörts).
4. `python scripts/smoke_test.py` (marketscan) passerar (om API rörts).
5. Inga hemligheter läckt; RLS aktivt på nya tabeller.
6. `docs/SYSTEM_AI.md` uppdaterad.
7. ML-projekt (#1, #15): ny modell deployas BARA om den slår nuvarande på
   walk-forward Rank IC **och** decil-spread (gate i `core/ml_evaluation.py`).

---

## 8. Risker (hela batchen)

| Risk | Mitigering |
|---|---|
| Overfitting / falsk alpha (#1, #15) | Purged walk-forward + decil-spread + DSR-gate; deploya bara OOS-vinst |
| LLM-kostnad skenar (#7, #19) | Gemini free tier först, hård cache, budgettak, fråga vid behov av dyrare |
| FI-register ändrar HTML/endpoint (#5) | Robust parser med JSON+HTML-fallback + larm vid 0 rader; daglig validering |
| Svensk embeddings-kvalitet otillräcklig (#7) | Testa Gemini-embeddings mot lokal KB-modell; fråga om betald krävs |
| Datakvalitet/survivorship i träningsdata (#1) | Säkerställ avlistade bolag finns; dokumentera kända luckor |
| Beroendekonflikt LightGBM/hmmlearn i Actions | Körs i stock-scanner-fix-miljön (ej API-bundeln); pin versioner |
| 30d-utfallsfönster (#1-loop) | Loopen finns redan (prediction_outcomes); börja logga modell v2 direkt |

---

## 9. Hur du (DeepSeek) ska arbeta

1. Läs detta master-dokument helt.
2. Öppna relevant spec (01–06). Läs den helt innan du rör kod.
3. Följ specens steg i ordning. Varje steg har: filsökväg, vad som ska göras,
   och (där relevant) komplett kodskelett eller signaturer.
4. Kör specens acceptanstester efter varje delsteg.
5. Bryt aldrig §6-konventionerna. Är något oklart i specen → IMPLEMENTERA INTE
   en gissning; lämna en `# TODO(fråga): ...`-kommentar och rapportera.
6. Uppdatera `docs/SYSTEM_AI.md` när projektet är klart.

---

*Master-plan v1 — 2026-06-09. Specs 01–06 detaljerar varje projekt.*
