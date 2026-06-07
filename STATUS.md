# MarketScan 2.0 — Projektstatus

> **Senast uppdaterad:** 2026-06-07
> **Stack:** Next.js 15.5 + FastAPI 3.12 + Supabase + GitHub Actions
> **Frontend:** https://marketscan.vercel.app
> **API:** https://marketscan-api.vercel.app

## Status

Alla kärnfunktioner är byggda och deployade. Systemet är användbart men har tekniska skulder som måste lösas för att vara självgående.

### ✅ Klart

- **Alla sidor:** Översikt, Aktier (screener), Aktiekort (5 flikar), Portfölj, Bevakningar, Kalender, Jämför, Marknad, Guide, Kontrollpanel, Inställningar, Landing, Login, Register
- **Alla API-routes:** ~60+ endpoints — screener, stocks, portfolio, watchlist, alerts, AI, admin, markets, calendar, prediction, options, backtests, sector rotation, paper trading
- **AI-analys:** Analyskommittén (3 analytiker + ordförande) med DeepSeek, cachas i Supabase
- **Finnhub-integration:** Nyheter, earnings, prishistorik, insider, kalender — alla fungerar
- **Designsystem:** Ljust + mörkt tema, Inter + Geist Mono, InfoTooltips överallt
- **Auth:** Inloggning, registrering, lösenordsåterställning, JWT-validering
- **Säkerhet:** CSP, rate limiting, admin-auth, .gitignore, Finnhub key i header
- **Deployat:** Både frontend (marketscan.vercel.app) och API (marketscan-api.vercel.app)

### ⬜ Kvar att göra

#### Hög prioritet
1. **Koppla GitHub Actions pipeline** — workflow-filer finns, GitHub Secrets måste konfigureras
2. **Fixa DATABASE_URL pooler-port** — port 6543 svarar inte, krävs för pipeline
3. **Automatisk frontend-deploy** — frontend-projektet i Vercel deployas inte vid git push

#### Medel prioritet
4. **Cloudflare R2** — prishistorik, score-historik, parquet-lagring (betalningsproblem)
5. **E-postnotiser för prislarm** — checker finns, notiser saknas
6. **Pappershandel i UI** — backend finns, frontend saknas

#### Låg prioritet
7. **Tema sparas i Supabase**
8. **Mobil-PWA**
9. **Sektoröversikt heatmap**

### Kända problem

| Problem | Orsak |
|---|---|
| "Aktie hittades inte" när man klickar från vissa vyer | API_BASE kan peka på gammal deployment. Redeploya frontend. |
| AI-analys tar 10-15s | Tre parallella DeepSeek-anrop. Inget timeout i frontend. |
| Admin-panelen är öppen för alla | Använder `get_current_user` istället för `require_admin` |
| Pipeline kör inte automatiskt | GitHub Secrets saknas |

Detaljerad systemdokumentation: `SYSTEM_AI.md`
Användarens design-filosofi & historik: `HANDOFF.md`
