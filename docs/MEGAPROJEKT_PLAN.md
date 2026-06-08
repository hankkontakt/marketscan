# MarketScan — 3 Megaprojekt (2026-06-08)

> Inga frågor ställs under genomförandet. Planen körs rakt igenom.

---

## Varför dessa tre?

Baserat på djupaudit av kodbasen:
- **Portfolio-sidan** är CRUD-komplett men saknar analytics helt — ingen riskberäkning, ingen optimering
- **Alert-systemet** är primitivt (bara pris) — ingen AI, inga sammansatta regler, ingen digest
- **Backtesting** finns som stub — ingen riktig motor, ingen signal-analytics

Alla tre bygger på data som redan finns i scan_results/transactions/holdings. Inget byggs i blindo.

---

## PROJEKT 1: Portfolio Risk Intelligence Engine

### Vad det är
En komplett risksanalysmotor kopplad till användarens portfölj.
Svarar på: *"Hur riskfylld är min portfölj? Vad driver mina avkastningar? Hur bör jag ombalansera?"*

### Vad som byggs

**DB (`019_risk_analytics.sql`):**
```
portfolio_risk_cache     — daglig snapshot av riskmetrik per portfölj
portfolio_factor_exposure — faktorexponering (value/momentum/quality/size)
rebalancing_targets       — sparade allokeringsmål
```

**Backend (`backend_worker/risk_analyzer.py`):**
- Sharpe ratio, Sortino ratio, Calmar ratio
- Max drawdown + recovery time
- Historical VaR (95%, 99%) och CVaR
- Beta mot OMXS30 (^OMX) och SPY
- Volatilitet (realized 20d, 60d, 90d)
- Korrelationsmatris mellan portföljens innehav
- Portfolio-optimering: Markowitz min-variance + HRP (återaktiverar hrp_optimizer-logiken korrekt)
- Driftavvikelse från målallokering + rebalanseringsförslag med transaktionskostnader

**API (`apps/api/routers/risk.py`):**
```
GET  /api/portfolio/risk              — komplett riskrapport (cachad 1 dag)
GET  /api/portfolio/risk/correlation  — korrelationsmatris N×N
GET  /api/portfolio/optimize          — optimala vikter (method=hrp|markowitz|equal)
GET  /api/portfolio/rebalance         — driftanalys + köp/säljlista för ombalansering
POST /api/portfolio/rebalance/targets — spara egna målallokeringar
GET  /api/portfolio/factor-exposure   — faktorexponering vs benchmark
```

**Frontend (`apps/web/app/(app)/portfolj/risk/page.tsx` + komponenter):**
- Risköversikt: gauge-kort för VaR, Sharpe, Max DD
- Korrelationsheatmap (alla holdings × holdings)
- Optimal vs aktuell allokering — bar chart med drift-indikator
- Ombalanseringstabel: "Köp X av AAPL, sälj Y av VOLV B"
- Faktorexponering: radar-chart (value/momentum/quality/growth/risk)

---

## PROJEKT 2: Smart Alerts & Digest Intelligence Hub

### Vad det är
Ny generation av bevakningssystemet. Ersätter enkla prisgränser med:
intelligenta sammansatta regler, score-spårning, och ett komplett e-postdigest-system.

### Vad som byggs

**DB (`020_smart_alerts.sql`):**
```
alert_rules          — sammansatta regler (multi-condition, NOT bara pris)
score_history        — daglig score-snapshots för alla tickers (tracking + backreference)
signal_transitions   — loggar varje gång entry_signal/trend_signal ändras per ticker
market_events        — ekonomisk kalender (Riksbank, ECB, Fed, earnings)
digest_log           — spår vilka digest-mejl som skickats
```

**Backend workers:**
- `backend_worker/score_tracker.py` — körs efter varje pipeline-körning, snapshots scores till score_history + detekterar transitions
- `backend_worker/smart_alert_engine.py` — utvärderar sammansatta alert-regler mot ny data, skapar notifications
- `backend_worker/digest_mailer.py` — veckodiges med: topp STARK-aktier, portföljsummary, kursrörelser, score-förändringar

**Sammansatta alert-regler (new concept):**
```json
{
  "conditions": [
    {"field": "score_total", "op": ">=", "value": 75},
    {"field": "entry_signal", "op": "=", "value": "STARK"},
    {"field": "piotroski_f", "op": ">=", "value": 7}
  ],
  "trigger": "any_match",   // eller "new_entry" (bara när aktie nyligen uppfyllde)
  "alert_type": "screen_match"
}
```

**Alert-typer (expanderade):**
- `price_cross` — prisgräns (finns)
- `score_change` — total-score ändras mer än N poäng
- `signal_change` — entry_signal byts (t.ex. VÄNTA→STARK)
- `screen_match` — aktie uppfyller sammansatt filter (ny)
- `insider_cluster` — ≥2 insiders köper samma bolag inom 14 dagar (ny)
- `volatility_spike` — vol_20d ökar >50% overnight (ny)

**API (`apps/api/routers/alerts.py` — fullständig omskrivning):**
```
GET    /api/alerts              — alla aktiva alert-regler (utökad)
POST   /api/alerts              — skapa ny regel (compound)
PUT    /api/alerts/{id}         — uppdatera regel
DELETE /api/alerts/{id}         — ta bort
GET    /api/alerts/triggered    — historik över triggade alerts (30 dagar)
GET    /api/score-history/{ticker} — historik för en aktie (för sparkline i UI)
GET    /api/score-history/movers   — aktier med störst score-förändring senaste 7d
```

**Frontend:**
- `/bevakningar` — komplett omdesign: alert-regler builder med dropdowns
- `/bevakningar/historia` — triggade alerts med sparklines
- `/oversikt` — lägg till "Score Movers" widget (toppers/bottoms senaste 7d)

---

## PROJEKT 3: Strategy Lab & Signal Analytics

### Vad det är
En komplett backtestningsmotor plus en "Strategy Lab" där man bygger, testar och jämför investeringsstrategier baserade på screener-filter.

### Vad det löser
Aktuell backtesting-stub returnerar aggregerade metrics utan kontext.
Ingen kan svara på: *"Om jag köpte alla STARK-aktier med Piotroski≥7 varje månad, vad hade hänt?"*

### Vad som byggs

**DB (`021_strategy_lab.sql`):**
```
strategies           — sparade strategier (filter_json + allokering + rebalansfrekvens)
strategy_runs        — körningar av en strategi (start/end datum, kapital)
strategy_positions   — alla positioner tagna under en körning
strategy_performance — daglig equity curve per körning
signal_persistence   — analyserade dataset: hur länge håller STARK-signal i snitt?
```

**Backend (`backend_worker/strategy_backtester.py`):**
Full backtesting-motor:
- Laddar `score_history` (byggs i Projekt 2) för historiska filtermatchningar
- Simulerar portföljkonstruktion: välj top-N aktier per filter-körning
- Position sizing: equal weight, score-proportionell, Kelly criterion
- Rebalansering: dagligen, veckovis, månadsvis, kvartalsvis
- Transaktionskostnader: konfigurerbart courtage (default: 0.05%)
- Metrics: total return, CAGR, Sharpe, Sortino, max drawdown, Calmar, win rate, avg hold time
- Monthly returns heatmap-data (år × månad)
- Equity curve som JSONB för visualisering

**Signal Analytics (`backend_worker/signal_analytics.py`):**
- Analyserar score_history: hur länge håller STARK/OK/VÄNTA-signaler i genomsnitt?
- Beräknar genomsnittlig avkastning 5/10/20/60 dagar efter signal-skifte
- Sektor-breakdown av signal persistence
- Conditional analysis: Piotroski≥7 STARK-signal vs allmän STARK → bättre?

**API (`apps/api/routers/strategy_lab.py`):**
```
GET    /api/strategies              — alla sparade strategier (user-owned)
POST   /api/strategies              — spapa ny strategi
PUT    /api/strategies/{id}         — uppdatera
DELETE /api/strategies/{id}         — ta bort
POST   /api/strategies/{id}/run     — kör backtest (async, sparas i strategy_runs)
GET    /api/strategies/{id}/results — senaste körning inkl equity curve + metrics
GET    /api/strategies/compare      — jämför 2-4 strategier (returns, Sharpe, DD)
GET    /api/signal-analytics        — signal persistence data (alla typer)
GET    /api/signal-analytics/{ticker} — signal-historik för specifik aktie
```

**Frontend (`apps/web/app/(app)/strategi-lab/`):**
- `/strategi-lab` — Strategi-lista + "Ny strategi"-knapp
- `/strategi-lab/[id]` — Strategi-detalj: filter-editor + backtest-konfiguration
- `/strategi-lab/[id]/resultat` — Equity curve, monthly returns heatmap, stats
- `/strategi-lab/jamfor` — Jämförelse av 2-4 strategier
- `/signal-analytics` — Ny analys-sida: hur länge håller signaler? Sektor-breakdown

---

## Genomförandeordning

```
1. Projekt 1: Migration 019 → risk_analyzer.py → risk.py router → Risk frontend page
2. Projekt 2: Migration 020 → score_tracker.py → smart_alert_engine.py → digest_mailer.py → alerts router → Frontend
3. Projekt 3: Migration 021 → strategy_backtester.py → signal_analytics.py → strategy_lab router → Frontend
4. GH Actions workflows: score_tracker + smart_alerts + digest triggers
5. SYSTEM_AI.md update
```

## Estimat

| Projekt | Filer | Åtgärder |
|---|---|---|
| P1 Risk Engine | 1 migration, 1 backend, 1 router, 4 frontend-komponenter | ~1800 LoC |
| P2 Smart Alerts | 1 migration, 3 backends, 1 router, 3 frontend | ~2200 LoC |
| P3 Strategy Lab | 1 migration, 2 backends, 1 router, 5 frontend-komponenter | ~2500 LoC |

**Total: ~6500 rader ny kod, 3 migrationer, 6 nya workers, 3 nya routers, 12+ nya frontend-sidor/komponenter**
