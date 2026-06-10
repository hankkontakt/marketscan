# MarketScan — 50 Ideer + 10 Megaprojekt (2026-06-10)

> **Syfte:** Komplett idébank för MarketScans framtida utveckling. 50 ideer rankade på bang-for-buck (1-10) med fördelar/nackdelar. 10 megaprojekt med full analys.
>
> **Metod:** Fyra researchagenter har sökt igenom trender inom fintech (Koyfin, SimplyWallSt, TIKR, Robinhood), ML/kvantitativa tekniker (learning-to-rank, conformal prediction, meta-labeling), infrastruktur/monetisering/tillväxt, och den befintliga kodbasens luckor.
>
> **Kodbasstatus:** 232 TypeScript/Python-filer i marketscan, 231 Python-filer i stock-scanner-fix. 25 router endpoints, 17 GitHub Actions workflows, 32 DB-migrationer. 6 batch-1-projekt nyss implementerade.

---

## 0. Hur ideerna är strukturerade

Varje idé har:
- **#**: ID
- **Namn**: Kort beskrivning
- **Bang-for-buck (BFB)**: 1-10 (hur mycket värde per implementationstid)
- **Insats**: S (<1 dag), M (1-3 dagar), L (1-2 veckor), XL (2+ veckor)
- **Kategori**: Frontend, Backend, ML, Infra, Tillväxt, Monetisering, UX, Data, Risk
- **Fördelar / Nackdelar**
- **Konkret implementation**: Vad exakt man bygger

---

## 1. Idé #1–#50

### #1 — Smart Notifications Engine (Push + Email)
**BFB: 10 | Insats: L | Kategori: UX/Tillväxt**

*Bygg ett intelligent notifikationssystem som skickar push-notiser (Web Push API) + email baserat på användarens watchlist, portfölj och inställningar.*

**Triggers:**
- Insiderköp på bevakad aktie (inom 5 min från SEC/FI-filing)
- Score-förändring >15p (med sub-score breakdown)
- Inträde/lämnande av STARK/OK/VÄNTA-signal
- Kursgenombrott av MA50/MA200
- Ny rapport publicerad + AI-sammanfattning klar
- MEWS-flagga aktiveras för bevakad aktie

**Fördelar:** Driver DAU/MAU, mycket hög retention, låg kostnad per notis, utnyttjar befintlig data.
**Nackdelar:** Kräver Vercel/Edge-function för Web Push, användare kan stänga av notiser.

**Implementation:**
1. Backend: ny `backend_worker/notification_engine.py` — evaluera triggers mot användarinställningar
2. Frontend: `apps/web/lib/sw/` — Web Push API + Service Worker-uppdatering
3. DB: `notification_rules` tabell (per-user trigger preferences)
4. Infra: enkel notification dispatch worker i GH Actions (körs var 5:e minut via cron)

---

### #2 — Earnings Call AI Analyst (90-sekunders research memo)
**BFB: 10 | Insats: M | Kategori: ML/UX**

*Efter varje rapport publiceras, generera automatiskt ett strukturerat "analysmemo" med: (1) nyckeltal vs konsensus, (2) ledningens ton (positiv/negativ/defensiv), (3) 3 viktigaste citaten från VD/CFO, (4) implicit guidning, (5) jämförelse med peers.*

**Fördelar:** Unikt — ingen svensk plattform gör detta. Använder befintligt LLM-lager (#7). Content marketing-magnet.
**Nackdelar:** Kräver transkript-API (EarningsCall lib, gratis tier). LLM-kostnad (men ~0.01$/rapport med Gemini Flash).

**Implementation:**
1. `backend_worker/earnings_analyst.py` — hämta transkript, kör LLM
2. Spara i `earnings_memos`-tabell
3. Visa på aktiesidan som "Rapportanalys"-kort (bredvid qualitative_signals från #7)
4. Frontend-hook: `useEarningsMemo(ticker)`

---

### #3 — Verified Investment Thesis Board
**BFB: 9 | Insats: L | Kategori: UX/Tillväxt**

*En strukturerad asynkron "thesis board" där användare publicerar investeringsteser (ticker, riktning, tidshorisont, katalysatorer, risker). Varje tes poängsätts mot efterföljande kursutveckling. Topp-författare syns på leaderboard.*

**Fördelar:** Skapar community-effekt utan chat-kaos. Strukturerat innehåll enklare att moderera. SEO-magnet — teser om specifika aktier rankar i Google.
**Nackdelar:** Kräver moderation. Måste undvika regleringsproblem (ingen finansiell rådgivning — tydlig disclaimer).

**Implementation:**
1. DB: `investment_theses` tabell (ticker, direction, horizon, catalysts, risks, score_created, score_realized)
2. API: `apps/api/routers/theses.py` — CRUD + leaderboard
3. Frontend: `/teser/` sida med leaderboard + per-aktie-flik i StockView
4. Scoring: jämför thesis med faktisk kursutveckling efter horizon

---

### #4 — Portfolio Stress Tester (Scenario Engine)
**BFB: 9 | Insats: M | Kategori: Risk/UX**

*Låt användaren definiera custom shock-scenarier: "AAPL -30%, räntor +200bps, olja $120". Systemet propagerar chocken genom korrelationsmatris och visar nytt portföljvärde, VaR, CVaR, och största positionsförlusten.*

**Fördelar:** Bloomberg-nivå-funktion för retail. Bygger på befintlig portfolio_construction.py (#19). Mycket visuellt imponerande.
**Nackdelar:** Korrelationsmatriser är bakåtblickande — bryts ner i kriser (måste dokumenteras).

**Implementation:**
1. `apps/api/core/stress_test.py` — portfölj-chock-propagation via kovariansmatris
2. API: `POST /api/portfolio/stress-test` — acceptera shock-definition, returnera nytt portföljvärde + riskmått
3. Frontend: interaktivt formulär + waterfall chart (Plotly) som visar position-by-position-impact
4. Återanvänd `apps/api/core/prices.fetch_price_history_batch()` för korrelationsmatris

---

### #5 — "Fantasy Stocks" Weekly Tournament
**BFB: 9 | Insats: M | Kategori: UX/Tillväxt**

*Användare bygger en virtuell $100K-portfölj som tävlar i veckoliga/månatliga/kvartalsvisa ligor. Använd end-of-day-priser. Temaveckor: "Dividend Week", "Volatility Week". Topplista med badges.*

**Fördelar:** Skyhögt engagemang (Robinhood/GameStock bevisat). Ingen regulatorisk risk (virtuella pengar). Recurring engagement loop.
**Nackdelar:** Kräver separat fantasy-portfolio state machine. Kan distrahera från seriös analys.

**Implementation:**
1. DB: `fantasy_portfolios`, `fantasy_holdings`, `fantasy_tournaments`, `fantasy_leaderboard`
2. Backend: `backend_worker/fantasy_engine.py` — daglig P&L-uppdatering
3. Frontend: `/fantasy/` — leaderboard + join/create tournament
4. Återanvänd befintlig paper trading-infrastruktur

---

### #6 — Search-as-You-Type Stock Search (Fuzzy + NLP)
**BFB: 9 | Insats: S | Kategori: UX**

*Ersätt den nuvarande enkla sökningen med fuzzy matchning + NLP: "svenska techbolag med hög tillväxt" → screener-filter. "visa aktier som gått ner mycket senaste månaden" → sorterat resultat. Använd befintliga AI-endpoints för NL-parsing.*

**Fördelar:** Liten insats, stor UX-förbättring. Bygger på befintligt `safe_search` + AI-infra. Konkurrenter saknar svensk NL-sökning.
**Nackdelar:** NL-parsing kan misslyckas — måste ha tydlig fallback. LLM-kostnad per sökning.

**Implementation:**
1. AI: anropa `POST /api/ai/parse-filter` (redan befintlig) från sökfältet
2. Frontend: ersätt search-input i TopBar.tsx med debounced fuzzy + NL-sökning
3. Visa resultat i dropdown medan användaren skriver
4. Cache:a NL-resultat i 24h för vanliga sökningar

---

### #7 — Stock Comparison Matrix (Head-to-Head++)
**BFB: 9 | Insats: S | Kategori: UX**

*Ta "/jamfor" till nästa nivå: visa en matris med upp till 6 bolag sida vid sida. Alla nyckeltal i kolumner. Färgkodning (grönt = bäst, rött = sämst). En klick för att lägga till/ta bort.*

**Fördelar:** Saknas i nästan alla svenska verktyg. Låg komplexitet — bara frontend + befintliga endpoints. Extremt användbart för investeringsbeslut.
**Nackdelar:** Kräver att alla tickers har komplett data (hantera saknade fält).

**Implementation:**
1. Frontend: `/jamfor/` → `ComparisonMatrix.tsx` — dynamisk kolumngenerering från valda tickers
2. Reuse: `useStock.ts` för data, `ScoreSparkline`, `TrendBadge` för visualisering
3. URL-baserad state: `?tickers=AAPL,GOOGL,MSFT...`

---

### #8 — Portfolio Rebalancing Calculator
**BFB: 9 | Insats: S | Kategori: UX**

*Visa drift från målallokering. Föreslå exakta köp/sälj-transaktioner för att återställa balansen. Minimera antal transaktioner. Hantera courtage.*

**Fördelar:** Praktiskt för användare med flera innehav. Mycket litet scope — enkel matematik. Kopplar till befintlig portföljinfrastruktur.
**Nackdelar:** Inga — ren nytta.

**Implementation:**
1. `apps/api/core/rebalance.py` — linjär optimering (minimera transaktioner givet målvikter)
2. API: `GET /api/portfolio/rebalance-plan` (utöka befintlig `/rebalance`)
3. Frontend: tabell med nuvarande vs målvikt + rekommenderade köp/sälj

---

### #9 — Live Price Ticker (WebSocket)
**BFB: 9 | Insats: L | Kategori: Backend/UX**

*Lägg till ett websocket-lager (FastAPI WebSocket eller serverless via Vercel Edge) som pushar live-priser till frontend. Ersätt polling-baserad refresh på portföljsidan och aktiesidan.*

**Fördelar:** Dramatisk UX-förbättring. Portfölj och aktiesidor känns "levande". Minskar API-belastning (färre poll-anrop).
**Nackdelar:** Vercel serverless WebSocket är begränsat (max 60s). Behöver dedicerad server eller använda Supabase Realtime.

**Implementation:**
1. Alternativ A: Supabase Realtime — prenumerera på `scan_results`-ändringar
2. Alternativ B: Lightweight WebSocket-server på Fly.io/Railway
3. Frontend: `useLivePrice(ticker)` hook med fallback till polling
4. Börja med enkel SSE (Server-Sent Events) som fungerar på Vercel

---

### #10 — "Executive Dashboard" Start Page (Morning Briefing 2.0)
**BFB: 8 | Insats: M | Kategori: UX**

*En personlig startsida som visar: dagens viktigaste händelser, hur min portfölj presterar, vilka av mina bevakningar som har signaler, topp-3 MEWS-kandidater denna vecka, veckans insiderkluster, och marknadssentiment i en blick. Som Bloomberg-terminalens "Launchpad" fast för retail.*

**Fördelar:** Gör Översikt-sidan till navet. Personalisering = retention. All data finns redan.
**Nackdelar:** Kräver auth för personalisering. Kan bli plottrigt — behöver bra design.

**Implementation:**
1. Frontend: `/oversikt/` → widget-baserad layout med draggable cards
2. Komponenter: `PortfolioSnapshot`, `WatchlistSignals`, `TopMEWS`, `InsiderRadarStrip`, `MarketRegimeGauge`
3. Backend: ny `GET /api/dashboard` endpoint som samlar allt i ett anrop

---

### #11 — Mobile PWA Push Notifications
**BFB: 8 | Insats: L | Kategori: UX/Tillväxt**

*Full PWA med offline-stöd + push-notiser via Web Push API. Gör att användare kan "installera" appen på sin hemskärm och få notiser även när de inte har appen öppen.*

**Fördelar:** Når mobilanvändare utan att bygga native-app ($50k+). Finans-appar har 96% push-opt-in (högst av alla kategorier).
**Nackdelar:** iOS Safari begränsar Web Push (måste vara "added to home screen"). Komplex service worker-hantering.

**Implementation:**
1. Uppgradera befintlig Serwist PWA-konfiguration (finns i next.config.ts + app/sw.ts)
2. Lägg till Web Push API i service worker
3. Backend: `/api/notifications/subscribe` + `/api/notifications/send`
4. UI: "Installera app" prompt + push-permission dialog

---

### #12 — AI Portfolio Coach (Daily Check-in)
**BFB: 8 | Insats: M | Kategori: ML/UX**

*En AI-agent som dagligen kollar användarens portfölj och ger en personlig briefing: "Du är överviktad mot tech med 62%. Tesla utgör 18% vilket är över din maxgräns. Här är 3 diversifieringsförslag..."*

**Fördelar:** Mycket hög upplevd nytta. Personaliserad AI. Bygger på #19 (riskprofil + portföljkonstruktion).
**Nackdelar:** LLM-kostnad om det körs för alla användare varje dag. Måste cache:a — körs bara när portföljen ändras.

**Implementation:**
1. `backend_worker/portfolio_coach.py` — daglig portföljanalys + AI-coach
2. Prompt: använd riskprofil, nuvarande allokering, portföljregler → konkreta förslag
3. Frontend: syns på portföljsidan som "Din portföljcoach säger..."

---

### #13 — "Guru Portfolio" Tracker (13F + Insider Mirroring)
**BFB: 8 | Insats: L | Kategori: Data/UX**

*Spåra kända investerares (Berkshire, Pershing Square, osv) 13F-filings automatiskt + svenska storinvesterare via FI-registret. Visa vad de köper/säljer, kvartalsförändringar, och "copycat-portfolio"-förslag.*

**Fördelar:** TIKR har detta som premium-funktion men ingen svensk plattform har det. SEO-magnet ("vad köper Warren Buffett?").
**Nackdelar:** 13F-data är 45 dagar försenad. Svenska insynsdata via FI är bättre. Kräver namnmatchning.

**Implementation:**
1. `backend_worker/guru_tracker.py` — hämta 13F från SEC EDGAR via Apify MCP ($0.045/query)
2. DB: `guru_portfolios`, `guru_trades`
3. API: `GET /api/gurus` + `GET /api/gurus/{name}/portfolio`
4. Frontend: `/gurus/` page med leaderboard över superinvesterare

---

### #14 — Dynamic Screener Presets (Community-driven)
**BFB: 8 | Insats: S | Kategori: UX**

*Låt användare spara och dela screener-konfigurationer. Tracka de mest använda och visa deras simulerade historiska prestanda. Andra kan forka och modifiera. "PEG < 1, ROE > 15%, insiderköp" blir en permalink.*

**Fördelar:** Nätverkseffekt kring verktyget. Låg implementeringstid. All infrastruktur finns (saved_screens).
**Nackdelar:** Kräver moderering av spam-screens. Simulerad historisk prestanda kan vara missvisande.

**Implementation:**
1. DB: uppgradera `saved_screens` med `is_public`, `fork_count`, `avg_return_simulated`
2. API: `GET /api/screens/public`, `POST /api/screens/{id}/fork`
3. Frontend: offentlig screener-galleri-sida + "Fork"-knapp

---

### #15 — Factor Research Lab
**BFB: 8 | Insats: L | Kategori: ML**

*Ett interaktivt gränssnitt där användare kan testa egna faktorer (t.ex. "gross_margin / enterprise_value", "3m momentum minus 12m momentum"). Systemet backtestar faktorn mot historisk data och visar IC, decil-spread, och faktoravkastning över tid.*

**Fördelar:** Differentierar plattformen dramatiskt. Inga retail-verktyg har detta. Använder befintlig backtesting-infrastruktur (strategy_lab).
**Nackdelar:** Komplext — behöver ett DSL eller visual formula builder. Datakvalitet avgörande för trovärdighet.

**Implementation:**
1. `stock-scanner-fix/core/factor_lab.py` — dynamisk faktor-utvärdering
2. Frontend: interactive formula builder + factor performance charts
3. Återanvänd `score_history` för historisk backtest-data

---

### #16 — Sector Rotation Heatmap
**BFB: 8 | Insats: S | Kategori: UX/Data**

*Visa en heatmap över sektorers relativa styrka över olika tidsramar (1v, 1m, 3m, 6m, 1y). Färgkoda grönt/rött. Klicka på en sektor för att se ingående aktier. Baserat på befintlig sector_momentum.py och rotation_engine.py.*

**Fördelar:** Låg kostnad — all data och logik finns redan i stock-scanner-fix. Bloomberg-nivå-visualisering. Mycket pedagogiskt.
**Nackdelar:** Passiv visualisering — ingen direkt action.

**Implementation:**
1. API: `GET /api/sectors/momentum` — returnera sektor-returns per tidsram
2. Frontend: heatmap som visar sektorer som rader, tidsperioder som kolumner
3. Återanvänd `core.sector_momentum` och `core.rotation_engine`

---

### #17 — One-Click Portfolio Export (Avanza/Nordnet CSV Import v2)
**BFB: 8 | Insats: S | Kategori: UX**

*Förbättra den befintliga Avanza-importen: stöd Nordnet-CSV, SAVR, Lysa. Auto-detektera format. Preview innan import. Hantera fonder, ISK, kapitalförsäkring. Matcha mot tickers i universumet.*

**Fördelar:** Låg barriär för nya användare. Befintlig infrastruktur finns (avanza_import.py).
**Nackdelar:** Många CSV-format att stödja. Namn-matchning mot tickers är skört.

**Implementation:**
1. `apps/api/core/avanza_import.py` → `apps/api/core/portfolio_import.py` — stöd Nordnet, SAVR, Lysa
2. UI: visa matchade och omatchade rader separat, låt användaren korrigera
3. Hantera fonder via ISIN-matchning mot `fund_holdings`-tabellen

---

### #18 — Automated Weekly Market Report (PDF/Email)
**BFB: 8 | Insats: S | Kategori: Tillväxt**

*Automatisera en snygg, svensk veckorapport som sammanfattar marknaden: vinnare/förlorare, sektorrotation, insideraktivitet, nya signaler, MEWS-uppdatering. Skicka som email-digest till prenumeranter varje fredag. PDF-export.*

**Fördelar:** Content marketing — delas vidare. Bygger på befintlig daglig briefing-infrastruktur. Låg ansträngning — AI-generera text.
**Nackdelar:** Måste vara tillräckligt bra för att inte kännas som spam.

**Implementation:**
1. `backend_worker/weekly_digest.py` — samla data, generera markdown, konvertera till HTML/PDF
2. Återanvänd `digest_mailer.py` och email/ templates
3. Frontend: `/veckobrev/` — arkiv med alla tidigare veckobrev
4. Prenumerationsformulär på startsidan

---

### #19 — "What If" DCF / Valuation Playground
**BFB: 7 | Insats: L | Kategori: UX**

*Ett interaktivt verktyg där användaren kan tweaka ett bolags siffror (revenue growth, margins, WACC, terminal growth) och se DCF-värderingen uppdateras i realtid. Visualisera Monte Carlo-simulering av värderingen med konfidensintervall.*

**Fördelar:** Bloomberg Terminal-liknande funktionalitet. Inget svenskt retail-verktyg har detta. Mycket pedagogiskt.
**Nackdelar:** DCF-modellering kräver många antaganden — risk att användare tar siffrorna för bokstavligt.

**Implementation:**
1. `apps/api/core/valuation.py` — DCF-modell (FCF-projektion, terminalvärde, diskontering)
2. Frontend: interaktiva sliders + waterfall chart + Monte Carlo-histogram
3. Pre-fylla med yfinance-data (nuvarande FCF, revenue, growth rates)
4. Spara användarens "scenarios" i DB

---

### #20 — Insider Trade Flash (Real-Time Alerts)
**BFB: 7 | Insats: M | Kategori: Data/UX**

*När FI-registret uppdateras (dagligen) eller SEC EDGAR (Form 4 i realtid), pusha en notis till alla som bevakar/har aktien: "VD för Volvo köper aktier för 2.3M kr — första köpet på 18 månader."*

**Fördelar:** Insider-signaler är den starkast bevisade retail-edgen. Real-tidskomponenten gör plattformen oumbärlig.
**Nackdelar:** FI-data är daglig, inte real-tid. SEC är snabbare men bara USA.

**Implementation:**
1. `backend_worker/insider_alerts.py` — jämför senaste pull med föregående, hitta nya trades
2. Kombinera med #1 (Smart Notifications) för push/email
3. Visa "Insider Flash" banner på översiktssidan

---

### #21 — Correlation Matrix Explorer
**BFB: 7 | Insats: M | Kategori: UX/Data**

*Interaktiv korrelationsmatris för alla aktier i en watchlist/portfölj/sektor. Hierarkisk clustering för att gruppera liknande aktier. Hover för exakta r-värden. Klicka för scatterplot. Standard i Bloomberg, saknas i retail.*

**Fördelar:** Kraftfull diversifieringsinsikt. Imponerande visualisering (Plotly). Använder befintlig prisdata.
**Nackdelar:** Kan bli långsam med många aktier (O(n²)-korrelationer).

**Implementation:**
1. API: `POST /api/portfolio/correlation-matrix` — ta emot ticker-lista, returnera matris
2. Frontend: interaktiv heatmap med `plotly.js` + `scipy.cluster.hierarchy`
3. Färgkoda: röd=0.8+, orange=0.5-0.8, grön=-0.5--0.8

---

### #22 — API-as-a-Service (External API Access)
**BFB: 7 | Insats: L | Kategori: Monetisering**

*Exponera MarketScans data och scoring som ett externt API. API-nycklar, rate limits, dokumentation (OpenAPI/Swagger). Gratis tier (100 req/dag), Pro ($29/mån), Enterprise.*

**Fördelar:** Direkt intäktsström. Låg marginalkostnad — samma infra, nytt gränssnitt. Efterfrågan från fintech-utvecklare.
**Nackdelar:** Kräver API key management, rate limiting, dokumentation, support. Dataleverantörers licenser kan begränsa vidarespridning (yfinance ToS-varning).

**Implementation:**
1. `apps/api/routers/api_keys.py` — CRUD för API-nycklar
2. `apps/api/core/api_auth.py` — API key middleware
3. Docs: OpenAPI/Swagger auto-generated + `/api/docs`
4. Stripe-integration för betalning

---

### #23 — Portfolio Backtesting (Walk-Forward)
**BFB: 7 | Insats: L | Kategori: ML/Risk**

*Låt användare backtesta sin portföljallokering mot historisk data: "Om jag hade ägt den här mixen i 3 år, hur hade den presterat?" Använd walk-forward för att undvika lookahead-bias. Visa drawdown, Sharpe, riskattribution.*

**Fördelar:** Kraftfullt beslutsunderlag. Bygger på strategi-lab-koden.
**Nackdelar:** Historisk avkastning ≠ framtida avkastning (måste disclaimas tydligt).

**Implementation:**
1. `backend_worker/portfolio_backtester.py` — walk-forward-simulering av en viktuppsättning
2. Återanvänd `strategy_backtester.py` men för portföljvikter istället för signaler
3. Frontend: equity curve + drawdown chart + risk metrics

---

### #24 — Price Alert 2.0 (Multi-Condition)
**BFB: 7 | Insats: S | Kategori: UX**

*Uppgradera den befintliga prisalert-funktionen: stöd för tekniska indikatorer (RSI < 30, MACD crossover, MA50 korsar MA200), volymspikar, och ATR-baserade stop-loss. Kombinera villkor med AND/OR.*

**Fördelar:** Bygger på befintlig `price_alerts`-tabell + `PriceAlertChecker`. Stort steg upp i funktionalitet.
**Nackdelar:** Komplext UI för att bygga multi-condition alerts.

**Implementation:**
1. DB: uppgradera `price_alerts` med `conditions JSONB` (stöd för tekniska triggers)
2. `backend_worker/technical_alert_checker.py` — evaluera RSI, MACD, MA-crossover
3. Frontend: alert-byggare med dropdown för indikator + operator + värde

---

### #25 — Podcast/News Sentiment Feed
**BFB: 7 | Insats: M | Kategori: Data**

*Skapa en svensk finansnyhetsaggregator med sentiment-analys. Hämta från Di, Affärsvärlden, Placera, Redeye, MFN. Kör FinBERT-sentiment på varje artikel. Visa "Sentiment Trend" per aktie — blir mer positiv/negativ i media?*

**Fördelar:** Unik svensk data — ingen konkurrent har bra sentiment. SEO-magnet för aktie-nyheter.
**Nackdelar:** RSS-scraping kan vara skört (siter ändrar struktur). Upphovsrätt för fulltext.

**Implementation:**
1. `backend_worker/news_sentiment_aggregator.py` — hämta RSS, kör sentiment
2. Återanvänd `core/news_fetcher.py` och `vaderSentiment`/`FinBERT`
3. DB: `news_sentiment` tabell (article_id, ticker, sentiment, source)
4. Frontend: Sentiment Trend-chart per aktie

---

### #26 — Automated A/B Testing Framework
**BFB: 7 | Insats: M | Kategori: Infra/UX**

*Bygg in A/B-testning i plattformen: experiment-flaggor som kan slås på/av per användargrupp, mät konvertering/engagement, statistisk signifikans-test. Möjliggör datadrivna produktbeslut.*

**Fördelar:** Grundläggande för professionell produktutveckling. Låg kostnad per experiment.
**Nackdelar:** Kräver tillräcklig trafik för signifikans. Ökar kodkomplexitet.

**Implementation:**
1. `apps/web/lib/experiments.ts` — experiment-flaggor + tracking
2. DB: `experiments`, `experiment_assignments`, `experiment_events`
3. Admin-panel: experimentöversikt + start/stop + resultat

---

### #27 — Automated Dependency Upgrades (Dependabot+)
**BFB: 7 | Insats: S | Kategori: Infra**

*Sätt upp automatisk dependency-uppgradering med CI-gate: Dependabot / Renovate öppnar PR, CI kör tester + typecheck, auto-merge vid grönt. Eliminerar manuell dep-hantering.*

**Fördelar:** Säkerhetshål patchas automatiskt. Noll manuellt arbete efter setup.
**Nackdelar:** Auto-merge kan introducera breaking changes om tester inte är heltäckande.

**Implementation:**
1. `.github/dependabot.yml` — konfigurera npm + pip uppdateringar
2. CI: lägg till auto-merge action vid grönt bygge + godkända tester

---

### #28 — Rate Limit Dashboard (Admin)
**BFB: 7 | Insats: S | Kategori: Infra/UX**

*Visualisera API-användning, rate limit-träffar, populäraste endpoints, långsammaste queries, och användaraggregat. Admin-only dashboard för att optimera prestanda.*

**Fördelar:** Snabbt byggt — slowapi + Supabase logs. Ger operativa insikter.
**Nackdelar:** Kräver logging-infrastruktur. Admin-only (få användare).

**Implementation:**
1. `apps/api/routers/admin.py` — lägg till `/admin/api-stats` med rate limit-data
2. Logga alla requests med duration till `api_request_log` (async, icke-blockerande)
3. Frontend: admin-tab med histograms, top lists, rate limit alerts

---

### #29 — Dividend Calendar++
**BFB: 7 | Insats: S | Kategori: UX**

*Ta befintlig utdelningskalender (core/dividend_calendar.py) och gör den interaktiv: filtrera på yield, sektor, utdelningshistorik, nästa X-dag. Visa total förväntad utdelning för min portfölj. "Dividend income stream" visualisering över året.*

**Fördelar:** Svenska investerare älskar utdelningar. Enkel — data finns redan. Låg komplexitet.
**Nackdelar:** Begränsat universum (mest large cap).

**Implementation:**
1. API: `GET /api/calendar/dividends` med filter-params
2. Frontend: updatera `/kalender` med utdelnings-tab + portfölj-income-stream
3. Återanvänd `core/dividend_calendar.py`

---

### #30 — Screener Prestanda Dashboard (Admin)
**BFB: 6 | Insats: S | Kategori: Infra**

*Visa screener-användning: vanligaste sökningarna, vilka filter som används mest, hur lång tid queries tar, vilka segment/scores som visas mest.*

**Fördelar:** Datadriven produktutveckling — se vad användare faktiskt gör. Enkel att bygga.
**Nackdelar:** Kräver query-loggning. Privacy concern — logga inte användar-specifika sökningar.

**Implementation:**
1. Logga sök-params (anonymiserat) till `screener_query_log`
2. Admin-dashboard: heatmap av filterkombinationer + populäraste sökningar
3. Anonymisera — inga user_id i loggen

---

### #31 — Error Boundary + Graceful Degradation
**BFB: 6 | Insats: S | Kategori: UX/Infra**

*Lägg till React Error Boundaries på alla sidor. Visa användbara felmeddelanden istället för blank vit sida. Fallback-UI för varje komponent: "Kunde inte ladda aktiedata — försök igen" med retry-knapp.*

**Fördelar:** Dramatisk UX-förbättring vid fel. Låg ansträngning. Reducerar "det funkar inte"-support.
**Nackdelar:** Kräver systematisk genomgång av alla komponenter.

**Implementation:**
1. `apps/web/components/ErrorBoundary.tsx` — generisk error boundary
2. Wrappa alla sidor i `app/(app)/` med ErrorBoundary
3. Visa `ErrorBlock` (finns redan) för API-fel

---

### #32 — SEO Optimization (Programmatic Stock Pages)
**BFB: 6 | Insats: M | Kategori: Tillväxt**

*Generera statiska/metadata-rika sidor för alla aktier i universumet: title="Volvo B (VOLV-B.ST) — Analys, Betyg & Nyckeltal", meta description med AI-genererad sammanfattning. Sitemap. Schema.org structured data (FinancialProduct).*

**Fördelar:** Gratis organisk trafik. Långsiktig tillväxtmotor. Varje aktiesida blir en landningssida.
**Nackdelar:** SEO-resultat tar månader. Kräver Next.js generateStaticParams + ISR.

**Implementation:**
1. `apps/web/app/aktie/[ticker]/` → generateMetadata() med dynamisk title/description
2. Generera sitemap.xml dynamiskt från scan_results
3. Lägg till JSON-LD structured data (schema.org/FinancialProduct)

---

### #33 — Dark Mode Polish
**BFB: 6 | Insats: S | Kategori: UX**

*Komplett dark mode-genomgång: verifiera alla komponenter, fixa hårdkodade färger, testa alla sidor. Mörkt tema är nu standard för fintech.*

**Fördelar:** Många användare förväntar sig dark mode. Plattformen har redan CSS-variabler — nästan där.
**Nackdelar:** Tidskrävande att hitta alla hårdkodade färger.

**Implementation:**
1. Audit: sök efter hårdkodade hex-färger i TSX-filer
2. Ersätt med CSS-variabler (`var(--color-...)`)
3. Lägg till auto-detection av system-preference

---

### #34 — Keyboard Shortcuts / Power User Mode
**BFB: 6 | Insats: S | Kategori: UX**

*Tangentbordsgenvägar för vanliga operationer: / för sök, Ctrl+K för kommandopalett (som Notion/Superhuman), Ctrl+B för tillbaka till översikt, p för portfölj, s för screener.*

**Fördelar:** Power users älskar det. Nästan ingen konkurrent har det.
**Nackdelar:** Discovery-problem — användare måste veta att shortcutsen finns.

**Implementation:**
1. `apps/web/hooks/useKeyboardShortcuts.ts` — global keydown-lyssnare
2. Kommandopalett: modal med sökning (Ctrl+K) — alla sidor/actions
3. Visa tillgängliga shortcuts med ?-tangenten

---

### #35 — Supabase Row-Level Security Audit
**BFB: 6 | Insats: S | Kategori: Säkerhet**

*Systematisk genomgång av ALLA tabellers RLS-policies och GRANTs. Verifiera att inga användare kan läsa andras data. Testa med olika roller (anon, authenticated, service_role).*

**Fördelar:** Kritisk för säkerhet och GDPR. Hittar dolda buggar.
**Nackdelar:** Manuellt arbete. Inga synliga features.

**Implementation:**
1. Script: `scripts/rls_audit.py` — testa varje tabell med varje roll
2. Proba: försök läsa andra användares portfolios, alerts, settings
3. Dokumentera alla fynd + fixa eventuella brister

---

### #36 — Automated Smoke Test after Every Deploy
**BFB: 6 | Insats: S | Kategori: Infra**

*Lägg till `scripts/smoke_test.py` i CI som körs efter varje deploy (inte bara PR). Om smoke-test failar → auto-rollback eller Slack-notis.*

**Fördelar:** Fångar deploy-regressioner direkt. Redan byggt — bara konfigurera.
**Nackdelar:** Kräver Vercel deploy hook / GitHub Actions integration.

**Implementation:**
1. `.github/workflows/post-deploy.yml` — triggas av Vercel deploy webhook
2. Kör `python scripts/smoke_test.py` mot prod-URL
3. Slack-notis vid fail (webhook)

---

### #37 — User Onboarding Flow (Walkthrough)
**BFB: 6 | Insats: M | Kategori: UX/Tillväxt**

*En guidad onboarding för nya användare: "Lägg till din första aktie i watchlist", "Kör din första screener", "Gör risktestet", "Se din första AI-analys". Progress bar. Tooltips.*

**Fördelar:** Ökar conversion från registrering till aktiv användare. Minskar "jag förstår inte hur man använder detta".
**Nackdelar:** Kan irritera avancerade användare — måste gå att skippa.

**Implementation:**
1. Använd befintligt `OnboardingModal.tsx` + `ExperienceProvider.tsx`
2. Steg-för-steg-guide med 5-6 steg
3. Markera UI-element med tooltips (driver.js eller custom)
4. Completion → "Du är redo!" + första rekommendationen

---

### #38 — Social Share Cards (Open Graph)
**BFB: 6 | Insats: S | Kategori: Tillväxt**

*Generera dynamiska Open Graph-bilder för varje aktiesida: visar ticker, current price, score, trend, och sparkline. När någon delar en aktielänk på Twitter/LinkedIn/Discord ser det professionellt ut.*

**Fördelar:** Ökar delningar dramatiskt. Gratis marknadsföring.
**Nackdelar:** Kräver image generation (Satori/Vercel OG eller sharp).

**Implementation:**
1. `apps/web/app/aktie/[ticker]/opengraph-image.tsx` — Next.js OG Image generation
2. Visa: ticker, pris, score, sparkline, logotyp
3. Använd `@vercel/og` för rendering

---

### #39 — Performance Attribution (Brinson Model)
**BFB: 6 | Insats: M | Kategori: UX/Risk**

*Bryt ner portföljavkastning i: allokeringseffekt (sektorövervikt), selektionseffekt (bra aktieval inom sektor), och interaktionseffekt. Visualisera som waterfall chart.*

**Fördelar:** Bloomberg-nivå-analys. Inget retail-verktyg har detta.
**Nackdelar:** Kräver benchmark-data (OMX30/SPX för jämförelse). Komplext att förklara för användare.

**Implementation:**
1. `apps/api/core/attribution.py` — Brinson-Faugher attribution model
2. API: `GET /api/portfolio/attribution`
3. Frontend: waterfall chart + förklaringstext

---

### #40 — "Similar Stocks" Improvement (Multi-dimensional)
**BFB: 6 | Insats: S | Kategori: ML/UX**

*Uppgradera "Liknande aktier" från 8-feature cosine similarity till multi-dimensional embedding: kombinera fundamental, teknisk, sektor, och sentiment i en gemensam vektor. Använd dimensionality reduction (UMAP) för 2D-visualisering.*

**Fördelar:** Mer sofistikerat än någon konkurrent. Använder befintlig similar stocks-infrastruktur.
**Nackdelar:** UMAP-beräkning kan vara långsam på serversidan.

**Implementation:**
1. `core/ml_features.py` — compute multi-dimensional feature vector per stock
2. Browser-side UMAP via `umap-js` (WASM) för 2D-projektion
3. Frontend: interaktiv scatter plot av liknande aktier

---

### #41 — Localization (English + Other Languages)
**BFB: 5 | Insats: L | Kategori: Tillväxt**

*Full i18n av plattformen (Next.js i18n routing + i18next). Börja med engelska för att öppna internationell marknad. Återanvänd befintlig core/i18n/ i stock-scanner-fix.*

**Fördelar:** Öppnar global marknad. Plattformen har redan grunden (sv/en/de i core/i18n/).
**Nackdelar:** Stort scope — varje UI-sträng måste översättas. Löpande underhåll.

**Implementation:**
1. `apps/web/lib/i18n/` — i18next-konfiguration
2. Översätt alla hårdkodade svenska strängar → translation keys
3. Börja med TopBar, NavRail, FilterRail — mest synliga
4. Använd AI (DeepSeek/Gemini) för initial översättning

---

### #42 — Webhook System for External Integrations
**BFB: 5 | Insats: M | Kategori: Backend/Infra**

*Låt användare/webhooks konsumera events: "när en aktie får betyg STARK", "när insider köper X". Webhook-URL:er, retry-logik, signerade payloads (HMAC).*

**Fördelar:** Plattforms-effekt — tredjeparter kan bygga på MarketScan.
**Nackdelar:** Kräver delivery infrastructure (kö, retry, dead letter). Säkerhetsrisk med user-defined URLs.

**Implementation:**
1. `apps/api/routers/webhooks.py` — CRUD för webhook-prenumerationer
2. `backend_worker/webhook_dispatcher.py` — leverera events, retry 3x, dead-letter
3. Webhook secret verification (HMAC-SHA256)

---

### #43 — Economic Calendar Integration
**BFB: 5 | Insats: S | Kategori: Data**

*Lägg till en makroekonomisk kalender i `/kalender`-vyn: räntebesked, KPI, BNP-rapporter, arbetsmarknadssiffror. Hämta från gratis-API (t.ex. Investing.com scraping eller Trading Economics RSS).*

**Fördelar:** Kompletterar befintlig kalender. Viktigt för makro-medvetna investerare.
**Nackdelar:** Datakälla kan vara opålitlig (skrapning). Kräver underhåll.

**Implementation:**
1. `core/economic_calendar.py` — RSS/API-parsning
2. Frontend: lägg till makroflik i `/kalender`
3. Visa hur varje event förväntas påverka olika sektorer

---

### #44 — Usage Analytics (Plausible/Umami-style, Self-hosted)
**BFB: 5 | Insats: S | Kategori: Infra**

*Lägg till privacy-first webbanalys (Umami eller Plausible self-hosted) för att spåra sidvisningar, användarflöden, och konvertering utan att sälja användardata.*

**Fördelar:** Datadrivna beslut kräver analytics. Privacy-first (GDPR-compliant). Gratis self-hosted.
**Nackdelar:** Kräver extra infra (Supabase eller Vercel Postgres för Umami).

**Implementation:**
1. Installera Umami (open source, self-hosted, kan använda Supabase)
2. Lägg till tracking script i `apps/web/app/layout.tsx`
3. Dashboard: admin-only, visa användarflöden

---

### #45 — CI Speed Optimization
**BFB: 5 | Insats: S | Kategori: Infra**

*Optimera GitHub Actions CI: cache:a pip/npm dependencies, parallellisera tester, använd turborepo för affected-only builds, docker layer caching.*

**Fördelar:** Snabbare feedback-loop. Lägre Actions-minuter.
**Nackdelar:** Tar tid att finjustera caching.

**Implementation:**
1. `actions/cache@v4` för pip + npm
2. `turborepo` configuration (om monorepo-struktur införs)
3. Parallellisera pytest-körningar efter fil

---

### #46 — "Market Regime Gauge" Widget
**BFB: 5 | Insats: S | Kategori: UX**

*En enkel visuell widget på översiktssidan som visar aktuell marknadsregim: björn/neutral/tjur med sannolikheter från HMM-modellen. Färgkoda bakgrunden subtilt baserat på regim (röd/grå/grön).*

**Fördelar:** Utnyttjar den nya HMM-regimdetektorn (#15). Pedagogiskt och visuellt.
**Nackdelar:** Kan överdriva regimsignalens betydelse.

**Implementation:**
1. `apps/web/components/widgets/RegimeGauge.tsx` — halvcirkelformad gauge
2. `apps/web/hooks/useMacroRegime.ts` — hämta regime_state från API (redan befintlig?)
3. Visa på översiktssidan

---

### #47 — Price Fallback / Enhancement
**BFB: 5 | Insats: S | Kategori: Backend**

*Förbättra priskällorna: lägg till Polygon.io som primärkälla ($29/mån för real-time), fallback till yfinance. Caching-lager för att minimera API-kostnader.*

**Fördelar:** Mer pålitliga priser än gratis Yahoo. Bättre täckning för mindre bolag.
**Nackdelar:** Månadskostnad. Komplex caching vid flera providers.

**Implementation:**
1. `apps/api/core/prices.py` — Polygon.io-first med yfinance-fallback
2. Cache-priser i 15 minuter i minnet
3. Hantera rate limits graciöst

---

### #48 — Stock Universe Manager UI (Admin)
**BFB: 5 | Insats: S | Kategori: Backend**

*Bygg ett admin-gränssnitt för att hantera aktieuniversumet: lägg till/ta bort tickers, flagga inaktiva, visa statistik per ticker (senast hämtad, antal framgångsrika/ misslyckade fetches, data-kompletthet).*

**Fördelar:** Admin-verktyg som saknas idag. Gör det enkelt att underhålla universumet.
**Nackdelar:** Admin-only — få användare.

**Implementation:**
1. API: `GET/POST/DELETE /api/admin/universe`
2. Frontend: admin-tab "Universum" med sökning + statistik
3. Använd `UniverseManager` i `core/universe_manager.py`

---

### #49 — Options Flow Dashboard
**BFB: 4 | Insats: L | Kategori: Data/UX**

*Komplett optionsflödesanalys: ovanlig optionsaktivitet, put/call-ratio, max pain, gamma exposure. Visualisera options-kedjan med färgkodning. Riktar sig till avancerade traders.*

**Fördelar:** Differentierande — få svenska verktyg har optionsanalys. Hög-intresse för erfarna traders.
**Nackdelar:** Optionsdata är dyrt (Polygon Options $79/mån). Komplext. Nischat.

**Implementation:**
1. Återanvänd `core/options_flow.py`, `core/options_greeks.py`, `core/options_maxpain.py`
2. Polygon.io Options data feed
3. Frontend: options-kedja med highlight för ovanlig volym

---

### #50 — AI Code Review Bot for the Repo Itself
**BFB: 4 | Insats: M | Kategori: Infra/ML**

*Sätt upp automatisk AI-kodgranskning på PR:er: kontrollera mot säkerhetsregler (§6.6 i master-plan), konventioner (CLAUDE.md), och vanliga buggmönster. Auto-kommentera på PR.*

**Fördelar:** Fångar misstag tidigt. Sparar manuell review-tid. Använder egen AI-infrastruktur.
**Nackdelar:** GitHub Actions kostnad per PR. AI:n kan ha false positives.

**Implementation:**
1. `.github/workflows/ai-review.yml` — triggas på PR
2. Anropa Anthropic API (eller DeepSeek) för kodgranskning
3. Posta resultat som PR-kommentar via GitHub API

---

## 2. TOPP 10 MEGAPROJEKT

Dessa är "batch 2"-klassade — 2+ veckors implementation vardera, transformerande för plattformen.

---

### MEGA #1 — Native Mobile App (React Native / Expo)
**BFB: 10 | Insats: XL (4-6 veckor) | Kategori: UX/Tillväxt/Monetisering**

*Bygg en React Native-app med Expo som omsluter kärnfunktionaliteten: screener, portfölj, aktiedetaljer, AI-analys, push-notiser. Code-sharing med Next.js (hooks, types, api client).*

**Arkitektur:**
```
apps/
  api/        (befintlig FastAPI)
  web/        (befintlig Next.js)
  mobile/     (NY — Expo/React Native)
    hooks/   → delade hooks med web/
    types/   → delade types med web/
    lib/     → delad api.ts med web/
```

**Fördelar:**
- Når den stora mobilanvändarbasen (70%+ av fintech-trafik är mobil)
- Push-notiser fungerar native (iOS + Android)
- Code-sharing reducerar utvecklingskostnad ~50%
- Premium-funktion kan vara app-only → driver conversion
- Biometrisk auth (FaceID/fingeravtryck) för snabb inloggning

**Nackdelar:**
- Största enskilda utvecklingsinsatsen i denna lista
- Måste hantera App Store/Google Play-godkännande
- Två plattformar att underhålla (web + mobile)
- Prestandautmaningar med tunga beräkningar på mobil

**Implementation:**
1. Initiera Expo-projekt i `apps/mobile/`
2. Dela types, hooks, api.ts via workspace-paket (`packages/shared/`)
3. Återskapa kärnsidor: Översikt, Screener, Portfölj, Aktie, AI-analys
4. Native push-notiser via Expo Push API
5. Biometrisk auth via expo-local-authentication
6. Offline-stöd med AsyncStorage/SQLite

**Framgångsmått:** 500+ app-installationer, 40%+ DAU, push-opt-in >60%

---

### MEGA #2 — Real-time Market Data Engine (WebSocket + Redis)
**BFB: 9 | Insats: XL (2-3 veckor) | Kategori: Backend/UX**

*Ersätt polling med riktig real-tidsdata: en separat WebSocket-server (FastAPI WebSocket eller dedicated) som streamar prisuppdateringar, signaländringar, och notifikationer. Redis pub/sub för skalning. Frontend prenumererar på tickers.*

**Arkitektur:**
```
Polygon.io WebSocket → Redis Pub/Sub → FastAPI WebSocket Server → Browser (useLivePrice)
                                                                    ↓
                                                              Vercel Edge (SSE fallback)
```

**Fördelar:**
- Dramatisk UX-förbättring — plattformen känns "levande"
- Minskar API-anrop (polling → push)
- Möjliggör intraday-funktioner (realtids-screener, live-portfölj)
- Grund för framtida funktioner (live-insider-alerts, real-tids-scoring)

**Nackdelar:**
- Kräver dedikerad server (ej serverless) — Fly.io/Railway $5-25/mån
- WebSocket state management är komplext
- Reconnection-logik + fallback till polling

**Implementation:**
1. `apps/ws/` — FastAPI WebSocket-server
2. Redis Cloud (gratis tier 30MB) för pub/sub
3. Frontend: `useRealtimePrice(ticker)` — WebSocket med SSE-fallback
4. Stream:a prisändringar, signalbyten, insider-event

**Framgångsmått:** <500ms latency för prisuppdateringar, 99.9% uptime

---

### MEGA #3 — Freemium Monetization (Stripe + Tiered Access)
**BFB: 9 | Insats: XL (3-4 veckor) | Kategori: Monetisering**

*Introducera en freemium-modell med Stripe: Free (basic screener, 1 watchlist, 1 portfolio), Pro ($9/mån — unlimited screening, AI-analys, MEWS, insider radar), Enterprise (API access, white-label).*

**Features per tier:**

| Feature | Free | Pro ($9/mån) | Enterprise ($99/mån) |
|---------|------|-------------|---------------------|
| Screener | Basic (5 filter) | Unlimited | Unlimited + export |
| AI-analys | 3/mån | Unlimited | Unlimited + custom |
| Portfölj | 1 portfölj | 5 portföljer | Unlimited |
| Watchlist | 1 lista, 20 aktier | 5 listor | Unlimited |
| Insider Radar | — | Ja | Ja + alerts |
| MEWS | — | Ja | Ja |
| Black-Litterman | — | Ja | Ja + custom |
| API access | — | — | 10k req/dag |
| Support | Community | Email | Dedicated |

**Fördelar:**
- Direkt intäktsström — estimerat $500-2000/mån vid 50-200 betalande
- Free tier driver adoption, Pro converterar power users
- Validerar produktens värde — om folk betalar, är produkten bra
- Stripe-integration är robust och låg risk

**Nackdelar:**
- Kräver auth + subscription management (Stripe Customer Portal)
- Feature-gating måste implementeras överallt (frontend + backend)
- Måste ha tillräckligt många användare för att vara värt det
- Support-börda ökar med betalande kunder

**Implementation:**
1. Stripe Integration: `apps/api/routers/billing.py` — checkout, webhooks, portal
2. DB: `subscriptions` tabell — tier, status, stripe_customer_id
3. Feature gating: `apps/api/core/features.py` — tier-baserad åtkomstkontroll
4. Frontend: uppgraderingsmodaler, "Pro"-badge, betalväggar
5. Admin: subscription-översikt + MRR-dashboard

**Framgångsmått:** 50+ betalande användare inom 3 mån, MRR >$500

---

### MEGA #4 — Automated Equity Research Agent (Deep Research AI)
**BFB: 8 | Insats: XL (3-4 veckor) | Kategori: ML/UX**

*En AI-agent som automatiskt producerar djupgående analysrapporter för alla aktier i universumet. Liknar ett "sell-side research report" fast genererat på begäran. Inkluderar: företagsbeskrivning, branschanalys, finansiell analys, värdering (DCF + peers), risker, och AI-kommitténs samlade omdöme.*

**Arkitektur:**
```
Användare begär rapport → Queue (Supabase) → Deep Research Agent
  → Hämta finansiell data (yfinance)
  → Hämta nyheter/rapporter (MFN, SEC)
  → Kör 3 analytiker-agenter (parallel) — fundamental, teknisk, sentiment
  → Syntetisera till en rapport (DeepSeek)
  → Spara + notifiera användaren
```

**Fördelar:**
- Differentierar plattformen från ALLA svenska konkurrenter
- Hög upplevd nytta — "min egen analysavdelning"
- Kan vara premium-funktion (#4 + #3 = naturlig kombination)
- Återanvänder AI-kommitté-arkitekturen från `core/ai_analysis.py`

**Nackdelar:**
- Hög LLM-kostnad per rapport ($0.05-0.50 beroende på modell)
- Måste cache:a aggressivt — regenerera bara vid ny data
- Risk att AI:n hallucinerar siffror — måste ha strict grounding i data

**Implementation:**
1. `backend_worker/deep_research_agent.py` — multi-step agent orchestration
2. Prompt engineering: tvinga alla siffror att citeras från data
3. Cache: rapporten är giltig tills ny kvartalsrapport/nyhet
4. Frontend: `/aktie/[ticker]/rapport` — elegant rapportvy med export (PDF)
5. Premium-gatad (del av Pro-tier)

**Framgångsmått:** >80% av rapporter korrekta (fact-checkade), <5% hallucination rate

---

### MEGA #5 — Broker Integration (Avanza/Nordnet API)
**BFB: 8 | Insats: XL (4-6 veckor) | Kategori: UX/Monetisering**

*Integrera med svenska mäklares API:er (Avanza, Nordnet) för att synka innehav, transaktioner, och watchlists automatiskt. Användaren loggar in med BankID → portföljen synkas i realtid. Ingen manuell CSV-import.*

**Arkitektur:**
```
Användare → BankID-auth → Broker API → Hämta innehav + transaktioner
  → Normalisera till MarketScan-format → Synka mot portfolios/holdings/transactions
  → Event-triggers: ny transaktion → uppdatera portföljanalys
```

**Fördelar:**
- Eliminerar största onboarding-friktionen (manuell CSV-import)
- Möjliggör automatisk portföljanalys (alltid up-to-date)
- Premium-funktion — hög betalningsvilja
- Differentierar från alla svenska konkurrenter

**Nackdelar:**
- Avanza/Nordnet har inga officiella öppna API:er — kräver omvänd engineering eller samarbete
- BankID-integration är komplext och kostsamt
- Regulatoriska utmaningar (KYC, dataskydd, PSD2)
- Högt underhåll — brokers ändrar sina system

**Implementation:**
1. Research-fas: undersök om Avanza/Nordnet har öppna API:er (sannolikt nej)
2. Alternativ: använd PSD2 (Open Banking) för kontoinformation
3. Alternativ 2: samarbeta med en av mäklarna för API-access
4. `apps/api/core/broker_sync.py` — normalisering + synkronisering
5. Premium-only feature

**Framgångsmått:** 100+ synkade portföljer, <5% sync errors

---

### MEGA #6 — Advanced Backtesting Engine (Walk-Forward + CPCV)
**BFB: 8 | Insats: XL (2-3 veckor) | Kategori: ML/Risk**

*Bygg en professionell backtestingmotor som stöder: walk-forward-optimering, combinatorial purged cross-validation, transaktionskostnader, slippage, survivorship-bias-korrigering, och deflated Sharpe ratio. Användare skapar strategier visuellt (signal A + filter B → portfölj C) och ser robusta backtest-resultat.*

**Arkitektur:**
```
Strategi-definition (JSON) → Walk-Forward Splitter → Per-fold:
  1. Träna modell på train (purged)
  2. Generera signaler på test
  3. Simulera portfölj (med kostnader)
  4. Mät OOS-prestanda
→ Aggregerade metrics + DSR + equity curves
```

**Fördelar:**
- Befintlig strategi-lab är basic — detta gör den professionell
- Använder precis den purged CV-infrastruktur vi byggde i #1
- Kan användas internt för att utveckla nya strategier
- Möjliggör "strategi-marknadsplats" där användare delar beprövade strategier

**Nackdelar:**
- Mycket komplext — kräver rigorös testning för att undvika falska resultat
- Användare kan misstolka backtest-resultat som garanti för framtida avkastning
- Hög beräkningskostnad per backtest (parallellisering krävs)

**Implementation:**
1. `stock-scanner-fix/core/walk_forward_backtester.py` — CPCV-backtesting engine
2. `stock-scanner-fix/core/backtest_metrics.py` — DSR, ICIR, max drawdown, CAGR, Calmar
3. GH Actions: tung beräkning async (användaren får notis när klar)
4. Frontend: visuell strategi-byggare + resultat-dashboard

**Framgångsmått:** Walk-forward backtests tar <5 min, <1% buggar i resultat

---

### MEGA #7 — Social/Community Platform ("Nordic Investors")
**BFB: 7 | Insats: XL (4-6 veckor) | Kategori: Tillväxt/Community**

*Bygg en community-del kring plattformen: användarprofiler, diskussionstrådar per aktie, "följ" andra investerare, se deras offentliga portföljer (opt-in), veckans bästa teser, "nordiska investerarkartan" (geografisk visualisering av användare).*

**Arkitektur:**
```
Community Layer:
  - User profiles (utökade) — bio, strategi, "investeringsstil"
  - Threads per ticker — diskutera analyser, nyheter, scenarier
  - Follow-system — följ intressanta analytiker
  - Public portfolio (opt-in) — visa allokering (ej belopp)
  - Thesis leaderboard — bäst track record
  - Badges/achievements — bidragit X antal analyser, högst rankad tes, etc.
```

**Fördelar:**
- Nätverkseffekt — plattformen blir mer värdefull ju fler användare
- SEO-magnet — community-content indexeras
- Retention — användare återvänder för communityt, inte bara verktyget
- Kan byggas inkrementellt (börja med thesis board, lägg till trådar, profiler)

**Nackdelar:**
- Moderering är en stor utmaning — spam, manipulation, regelefterlevnad
- "Ghost town"-risk — community utan användare är värre än inget community
- Kräver betydande användarbas för att fungera (>1000 MAU)

**Implementation:**
1. DB: `user_profiles_public`, `threads`, `posts`, `follows`, `likes`
2. API: `apps/api/routers/community.py` — threads, posts, follows
3. Frontend: `/community/`, `/aktie/[ticker]/diskussion`
4. Moderation: AI-baserad spam-detection + manuell reporting

**Framgångsmått:** 100+ aktiva trådar/vecka, <5% spam-rate

---

### MEGA #8 — Factor Zoo & Research Platform
**BFB: 7 | Insats: XL (3-4 veckor) | Kategori: ML**

*Bygg ett system för systematisk faktorforskning: hundratals faktorer (value, momentum, quality, growth, low-vol, ESG, technical, alternative), automatisk utvärdering med purged walk-forward, faktor timing (när fungerar vilken faktor?), och faktor-portföljkonstruktion.*

**Arkitektur:**
```
Factor Library (100+ faktorer) → Walk-Forward Evaluation → Factor Zoo Dashboard
  → Long-Short Factor Returns → Factor Correlation Matrix
  → Factor Timing (regim → bästa faktorn) → Dynamic Factor Allocation
```

**Fördelar:**
- Plattform för kvantitativa investerare — nischat och premium
- Bygger på all ML/valideringskod från #1 och #15
- Kan leda till bättre scoringmodeller internt (data-driven feature selection)
- Möjliggör "smart beta"-portföljer för användare

**Nackdelar:**
- Extremt komplext — kräver djup kvantitativ expertis
- Risk för data mining / overfitting om inte rigoröst kontrollerat
- Smal målgrupp (kvantitativa investerare)

**Implementation:**
1. `stock-scanner-fix/core/factor_library.py` — 100+ faktorer, varje med metadata
2. `stock-scanner-fix/core/factor_evaluator.py` — automatisk WF-utvärdering
3. `stock-scanner-fix/core/factor_timing.py` — regime-conditional factor performance
4. Frontend: Factor Zoo dashboard (faktoravkastning, IC heatmap, regime breakdown)

**Framgångsmått:** >50 faktorer med dokumenterad OOS IC

---

### MEGA #9 — Data Pipeline 2.0 (Airflow/Modal + Data Lake)
**BFB: 6 | Insats: XL (3-4 veckor) | Kategori: Infra**

*Migrera från GitHub Actions-baserad pipeline till en riktig data pipeline-plattform: Apache Airflow eller Modal för orkestrering, DuckDB/Parquet-data lake för lagring, dbt för transformationer, och Supabase som serving layer.*

**Arkitektur:**
```
Data Sources (yfinance, FI, MFN, SEC, Polygon, etc.)
  → Ingestion Layer (Modal/Airflow tasks)
  → Data Lake (S3/R2 — Parquet/DuckDB)
  → Transformation Layer (dbt — SQL-baserad)
  → Serving Layer (Supabase — API-facing)
  → ML Training (Modal GPU jobs)
  → Model Serving (pickle → Supabase/R2)
```

**Fördelar:**
- Skalbar — kan hantera 10x dagens datavolym
- Pålitlig — Airflow har retry, alerting, DAG-visualisering
- Testbar — dbt har tester för datakvalitet
- Framtidssäker — rätt arkitektur för tillväxt

**Nackdelar:**
- Massiv migration — alla befintliga GH Actions-workflows måste skrivas om
- Ökad infrastrukturkostnad (Airflow-instans, Modal GPU)
- Ökad komplexitet — fler rörliga delar
- Overkill för nuvarande datavolym (~1200 tickers)

**Implementation:**
1. Sätt upp Modal (Python-native, enklare än Airflow) för orkestrering
2. Migrera pipeline-steg ett i taget (börja med daglig scoring)
3. Behåll GH Actions för enkla cron-jobb under migrationen
4. dbt för datakvalitetstester och transformationer

**Framgångsmått:** Pipeline tar <15 min (idag ~30-90 min), 99.5% uptime

---

### MEGA #10 — AI Co-Pilot / "Swedish Warren"
**BFB: 6 | Insats: XL (3-4 veckor) | Kategori: ML/UX**

*En konverserande AI-co-pilot som kan hela plattformens data. Ställ frågor i naturligt språk: "Vilka småbolag har ökat sin FCF-yield mest senaste kvartalet och har insiderköp?" → returnerar filtrerad lista med analys. "Jämför Volvo och Scania på värdering och tillväxt" → sida vid sida med AI-sammanfattning. "Är min portfölj för risky?" → riskanalys med rekommendationer.*

**Arkitektur:**
```
Användarfråga i naturligt språk → AI Router:
  1. Klassificera frågan (screening, jämförelse, portföljanalys, kunskapsfråga)
  2. Generera strukturerad query (API-anrop till relevanta endpoints)
  3. Hämta data
  4. Syntetisera svar med kontext + källhänvisningar
→ Visa som chat-bubbla + strukturerat resultat
```

**Fördelar:**
- "Killer feature" — ingen svensk plattform har en AI-co-pilot
- Minskar inlärningskurvan för nya användare dramatiskt
- Kan ersätta mycket manuellt klickande i screener/compare
- Premium-feature med mycket hög betalningsvilja

**Nackdelar:**
- Hög LLM-kostnad per konversation (om inte aggressivt cachad)
- Hallucinationsrisk — måste vara grounded i faktisk data
- Komplext att bygga robust query-förståelse för alla domäner
- Kräver kontinuerlig prompt engineering och utvärdering

**Implementation:**
1. `apps/api/routers/copilot.py` — konversations-endpoint
2. AI Router: klassificera → API-anrop → syntetisera (använder llm_client.py)
3. Strict grounding: alla siffror måste citeras från API-data
4. Frontend: flytande chat-bubbla (liknande Intercom/ Crisp)
5. Context: ha tillgång till användarens portfölj, watchlist, riskprofil
6. Rate limiting: 10 frågor/dag för free, obegränsat för Pro

**Framgångsmått:** >70% av frågor besvaras korrekt (fact-check), <5% hallucination rate, NPS >50

---

## 3. SAMMANFATTANDE PRIORITERING

### Omedelbara vinster (S-insats, hög BFB):
1. #6 Search-as-you-type (BFB 9, S)
2. #7 Stock Comparison Matrix (BFB 9, S)
3. #8 Portfolio Rebalancing Calculator (BFB 9, S)
4. #16 Sector Rotation Heatmap (BFB 8, S)
5. #17 One-Click Portfolio Export v2 (BFB 8, S)
6. #14 Dynamic Screener Presets (BFB 8, S)
7. #24 Price Alert 2.0 (BFB 7, S)

### Snabba vinster (M-insats, hög BFB):
8. #2 Earnings Call AI Analyst (BFB 10, M)
9. #4 Portfolio Stress Tester (BFB 9, M)
10. #5 Fantasy Stocks Tournament (BFB 9, M)
11. #10 Executive Dashboard (BFB 8, M)
12. #12 AI Portfolio Coach (BFB 8, M)
13. #25 News Sentiment Feed (BFB 7, M)

### Strategiska investeringar (L/XL):
14. Mega #1 Native Mobile App (BFB 10)
15. Mega #3 Freemium Monetization (BFB 9)
16. Mega #2 Real-time Market Data (BFB 9)
17. Mega #4 Deep Research AI Agent (BFB 8)
18. Mega #5 Broker Integration (BFB 8)
19. #1 Smart Notifications Engine (BFB 10, L)
20. #9 Live Price Ticker (BFB 9, L)

---

*Dokument v1 — 2026-06-10. 50 ideer, 10 megaprojekt, 4 agenters research.*