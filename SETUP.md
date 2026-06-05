# MarketScan 2.0 — Uppstartsguide

> Följ stegen i ordning. Varje steg har en verifiering innan du går vidare.

---

## Del 1 — Externa tjänster (gör detta en gång)

### Steg 1: Supabase

1. Gå till **[supabase.com](https://supabase.com)** → "Start your project" → Logga in med GitHub
2. Klicka **New project**
   - Organization: din org (eller skapa ny)
   - Name: `marketscan`
   - Database Password: välj ett starkt lösenord (spara det!)
   - Region: **eu-north-1 (Stockholm)**
3. Vänta ~2 min tills projektet startar

4. I Supabase Dashboard: **Settings → API**
   - Kopiera `Project URL` → detta är `SUPABASE_URL`
   - Kopiera `anon public` → detta är `SUPABASE_ANON_KEY`
   - Kopiera `service_role` → detta är `SUPABASE_SERVICE_KEY`
   - Klicka på **"JWT Settings"** (längre ner) → kopiera `JWT Secret` → detta är `SUPABASE_JWT_SECRET`

5. Kör SQL-migrationen:
   - Gå till **SQL Editor** i Supabase Dashboard
   - Öppna filen `supabase/migrations/001_initial_schema.sql` (i din repo)
   - Klistra in hela innehållet → klicka **Run**
   - Du ska se: "Success. No rows returned"

6. Kör seed-data (valfritt, för att testa UI direkt):
   - Öppna `supabase/seed.sql`
   - Klistra in i SQL Editor → Run
   - Du ska se: "Success. 8 rows affected"

7. Hämta `DATABASE_URL` (för pipeline):
   - Settings → Database → **Connection string** → URI-format
   - Se ut som: `postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres`

**Verifiera:** Gå till Table Editor → scan_results → du ska se 8 rader (om du kört seed)

---

### Steg 2: Cloudflare R2 (för historikdata)

> R2 är gratis för de första 10 GB lagring och 10 miljoner läsningar/månad.

1. Gå till **[dash.cloudflare.com](https://dash.cloudflare.com)** → Logga in (skapa gratis konto om du inte har)
2. Vänster meny → **R2 Object Storage** → **Create bucket**
   - Bucket name: `marketscan-data`
   - Location: välj `WEUR (Western Europe)` eller `Auto`
3. Gå till **R2 → Manage R2 API Tokens** (längst upp till höger)
   - Create API Token
   - Permissions: `Object Read & Write`
   - Specify bucket: `marketscan-data`
   - Create Token
   - Kopiera **Access Key ID** → `R2_KEY_ID`
   - Kopiera **Secret Access Key** → `R2_SECRET`
4. R2-endpoint:
   - Format: `https://[ACCOUNT_ID].r2.cloudflarestorage.com`
   - Hitta ACCOUNT_ID i Cloudflare URL (t.ex. `https://dash.cloudflare.com/[ACCOUNT_ID]/r2`)

**Verifiera:** Du har nu: R2_KEY_ID, R2_SECRET, R2_ENDPOINT, R2_BUCKET=marketscan-data

---

### Steg 3: Vercel-projekt

1. Gå till **[vercel.com](https://vercel.com)** → Logga in med GitHub
2. **New Project** → "Import Git Repository"
   - Välj repot `marketscan` (du behöver pusha till GitHub först — se steg 5 nedan)
3. Framework: **Next.js** (väljs automatiskt)
4. Root Directory: `apps/web`
5. Klicka **Deploy** — första deplyen kan misslyckas, det är OK (vi sätter env-vars efteråt)

---

## Del 2 — Lokal miljö

### Steg 4: Fyll i .env

```bash
# I marketscan/-mappen, kopiera exemplet:
cp .env.example .env
```

Öppna `.env` och fyll i:

```env
# === Supabase (från steg 1) ===
SUPABASE_URL=https://[DITT-PROJEKT-ID].supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_KEY=eyJhbGc...
SUPABASE_JWT_SECRET=[JWT-SECRET]

# Postgres direct URL (för pipeline/backend_worker)
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres

# === Cloudflare R2 (från steg 2) ===
R2_KEY_ID=[din-key-id]
R2_SECRET=[din-secret]
R2_ENDPOINT=https://[account-id].r2.cloudflarestorage.com
R2_BUCKET=marketscan-data

# === AI providers (minst en krävs för AI-funktioner) ===
ANTHROPIC_API_KEY=sk-ant-...   # Claude — för Analyskommittén, NL-screener
# GEMINI_API_KEY=                # Alternativ AI
# DEEPSEEK_API_KEY=              # Alternativ AI

# === Next.js (kopiera samma Supabase-värden) ===
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://[DITT-PROJEKT-ID].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGc...
```

---

### Steg 5: Pusha till GitHub

```bash
cd C:\Users\hthur\OneDrive\Desktop\marketscan

# Skapa nytt GitHub-repo (gör detta på github.com → New repository → marketscan)
# Välj: Private, ingen README, ingen .gitignore

# Koppla och pusha:
git remote add origin https://github.com/[DITT-GITHUB-ANVÄNDARNAMN]/marketscan.git
git branch -M main
git push -u origin main
```

---

### Steg 6: Installera Node.js-paket

```bash
cd C:\Users\hthur\OneDrive\Desktop\marketscan\apps\web

npm install
```

> Tar 2–4 minuter. Installerar Next.js, React, TanStack Query, Supabase, TradingView, shadcn, Recharts m.m.

**Verifiera:** `npm run type-check` — ska returnera 0 fel (kan ha några TS-varningar vid första körning)

---

### Steg 7: Starta frontend (Next.js)

```bash
# Terminal 1: frontend
cd C:\Users\hthur\OneDrive\Desktop\marketscan\apps\web
npm run dev
# → Öppnas på http://localhost:3000
```

**Verifiera:** Öppna http://localhost:3000 — du ska se landningssidan med MarketScan-logon.
Klicka "Logga in" → du ska komma till /login.

---

### Steg 8: Starta FastAPI (backend)

```bash
# Terminal 2: API
cd C:\Users\hthur\OneDrive\Desktop\marketscan

# Installera Python-paket (API-lager, ej heavy pipeline):
pip install -r apps/api/requirements.txt

# Starta:
python -m uvicorn apps.api.main:app --reload --port 8000
```

**Verifiera:**
- http://localhost:8000/api/health → `{"status":"ok","version":"2.0.0"}`
- http://localhost:8000/api/scan → returnerar scan-data (om seed körts)
- http://localhost:8000/api/docs → Swagger UI (bara i development)

---

### Steg 9: Skapa första användaren

1. Gå till http://localhost:3000/register
2. Fyll i e-post + lösenord → "Skapa konto"
3. Bekräfta via e-post (Supabase skickar bekräftelsemejl)
   - OBS: I development kan du stänga av bekräftelse-krav i Supabase:
     Authentication → Settings → "Confirm email" → stäng av (för lokal testning)
4. Logga in på http://localhost:3000/login

**Verifiera:** Du ska komma till /oversikt. NavRail ska synas till vänster.

---

### Steg 10: Testa kärnfunktioner

```
[ ] /oversikt    — Laddas med "Marknadsöversikt", datum, möjligheter-lista
[ ] /screener    — Visar aktier från seed (VOLV-B, ERIC-B, etc.)
                   Prova segment-toggle: "Småbolag" / "Alla"
                   Prova filter: Köpläge = Starkt
                   Prova ⌘K (eller Ctrl+K) — öppnar Command Palette
[ ] /aktie/VOLV-B.ST
                   Sticky header med kurs + köpläge + totalbetyg
                   Tab: Översikt — nyckeltal
                   Tab: Faktorer — radar-chart
                   Tab: AI — Analyskommittén (klicka "Starta analys")
[ ] /portfolj    — Tom portfölj (lägg till innehav från aktiekort)
[ ] /bevakningar — Tom, testa lägg till t.ex. "VOLV-B.ST"
[ ] /kontrollpanel — Status-panel (kör som admin om role=admin i Supabase profiles)
```

---

## Del 3 — Pipeline (GitHub Actions)

### Steg 11: Konfigurera GitHub Secrets

På GitHub: ditt repo → **Settings → Secrets and variables → Actions → New repository secret**

Lägg till dessa:

| Secret | Värde |
|---|---|
| `DATABASE_URL` | Din Postgres connection string |
| `SUPABASE_URL` | https://[projekt].supabase.co |
| `SUPABASE_SERVICE_KEY` | Service role key |
| `SUPABASE_ANON_KEY` | Anon key |
| `R2_KEY_ID` | Cloudflare R2 Key ID |
| `R2_SECRET` | Cloudflare R2 Secret |
| `R2_ENDPOINT` | https://[account].r2.cloudflarestorage.com |
| `R2_BUCKET` | marketscan-data |
| `ANTHROPIC_API_KEY` | Claude API-nyckel |
| `FINNHUB_API_KEY` | Finnhub (earnings data) |

### Steg 12: Koppla befintlig core/-logik

Pipeline-workflown i `.github/workflows/pipeline.yml` förväntar sig att `core/`-modulen (från `stock-scanner-fix`) är tillgänglig.

**Alternativ A (rekommenderat för nu):** Kör pipeline från `stock-scanner-fix`-repot som vanligt, men lägg till ett steg som kallar `db_loader.py`:

Öppna `stock-scanner-fix/.github/workflows/pipeline.yml` och lägg till i slutet av main-steget:

```yaml
- name: Load to Supabase Postgres
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
    R2_KEY_ID: ${{ secrets.R2_KEY_ID }}
    R2_SECRET: ${{ secrets.R2_SECRET }}
    R2_ENDPOINT: ${{ secrets.R2_ENDPOINT }}
    R2_BUCKET: ${{ secrets.R2_BUCKET }}
  run: |
    pip install psycopg2-binary boto3
    python - <<'EOF'
    import sys, os
    sys.path.insert(0, 'C:/Users/hthur/OneDrive/Desktop/marketscan')
    from backend_worker.db_loader import load_scan
    from backend_worker.r2_uploader import upload_score_snapshot
    import pandas as pd
    # Läs senaste scan-resultat
    df = pd.read_parquet('data/scan_results.parquet')  # justera sökväg
    load_scan(df, os.environ['DATABASE_URL'])
    upload_score_snapshot(df)
    print(f"Loaded {len(df)} rows to Postgres + R2")
    EOF
```

**Alternativ B:** Flytta alla `core/`-filer till `marketscan/backend_worker/pipeline/` och kör allt från det nya repot. (Mer arbete, men renare separation.)

---

## Del 4 — Vercel-deploy (produktion)

### Steg 13: Miljövariabler i Vercel

Gå till Vercel → ditt projekt → **Settings → Environment Variables**

Lägg till ALLA variabler från `.env` (fast med produktionsvärden). Viktigt:
- `NEXT_PUBLIC_API_URL` ska vara `https://marketscan.vercel.app` (eller din domän)
- `SUPABASE_URL`, `SUPABASE_ANON_KEY` — samma som lokalt

### Steg 14: Första produktion-deploy

```bash
# Pusha main → Vercel bygger automatiskt
git push origin main
```

**Verifiera:** Öppna `https://marketscan.vercel.app` → landningssida ska synas

### Steg 15: Domän (valfritt)

Vercel → Settings → Domains → Add domain → följ instruktioner för DNS

---

## Del 5 — Felsökning

### Problem: "Module not found: apps.api.core"
```bash
# Säkerställ att du kör från repo-roten:
cd C:\Users\hthur\OneDrive\Desktop\marketscan
python -m uvicorn apps.api.main:app --reload --port 8000
# INTE från apps/api/
```

### Problem: "TypeError: Cannot read properties of undefined" i Next.js
```bash
# TypeScript-check:
cd apps/web
npm run type-check
# Fixa alla röda fel, kör sen om
```

### Problem: Supabase "JWT expired"
- JWT_SECRET måste matcha exakt det som Supabase visar under Authentication → JWT Settings
- Kontrollera att SUPABASE_JWT_SECRET i .env är rätt

### Problem: scan-resultat saknas i screener
```bash
# Kontrollera att seed körts:
# Supabase → SQL Editor:
SELECT count(*) FROM scan_results;
-- Ska returnera > 0
```

### Problem: "CORS error" i webbläsaren
- Kontrollera `CORS_ORIGINS` i `apps/api/core/config.py`
- Lägg till `http://localhost:3000` om det saknas

### Problem: Vercel build failure "bundle too large"
- Kör `grep -r "pandas\|yfinance\|xgboost" apps/api/` — ska ge NOLL träffar
- Om du hittar imports: ta bort dem omedelbart

---

## Sammanfattning: vad varje repo/mapp gör

```
marketscan/                    ← DETTA REPOT (ny 2.0-plattform)
  apps/web/                    ← Next.js, kör lokalt med: npm run dev
  apps/api/                    ← FastAPI, kör lokalt med: uvicorn apps.api.main:app
  backend_worker/              ← KÖRS ALDRIG lokalt, bara i GitHub Actions
  supabase/                    ← SQL migrations, kör en gång i Supabase Dashboard

stock-scanner-fix/             ← GAMMALT REPO (Streamlit, kör fortfarande)
  core/                        ← Scoring-motor, återanvänds av backend_worker
  web/                         ← Gammal Streamlit-app (kan avvecklas gradvis)
```
