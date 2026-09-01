# ⚖️ Kapitel 7: Portfolio, Risk Models & Strategy Lab

> **Domän:** Portföljkonstruktion, HRP, Equal Risk Contribution, VaR, CVaR, simulering och backtester.  
> **Status:** Aktiv produktion.

---

## 1. Executive Summary & TL;DR

Risk- och portföljmotorn i MarketScan erbjuder institutionella analysverktyg anpassade för privatsparare. Den stödjer automatisk import från Avanza CSV, beräkning av avancerade riskmått (VaR, CVaR, Max Drawdown) i ren Python utan externa tunga bibliotek i API:et, samt portföljoptimering via Hierarchical Risk Parity (HRP) och Black-Litterman.

---

## 2. Arkitektur & Beräkningsflöde

```
  ┌─────────────────────────────────────────────────────────────┐
  │                 Avanza CSV Export / Innehav                 │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │               apps/api/core/avanza_import.py                │
  │  • Parsar transaktioner & positioner (ISIN/kortnamn)        │
  │  • Rekoncilierar inköpskurser och valutor                   │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                 apps/api/core/prices.py                     │
  │  • Hämtar Yahoo v8 tidsserier via snabb httpx (ren Python)  │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
         ┌───────────────────────┴───────────────────────┐
         ▼                                               ▼
  ┌──────────────────────────────┐        ┌──────────────────────────────┐
  │   apps/api/core/risk_calc.py │        │portfolio_construction.py     │
  │  • Daglig VaR & CVaR (95%)   │        │  • HRP Trädklustring         │
  │  • Sharpe & Sortino Ratios   │        │  • Equal Risk Contribution   │
  │  • Max Drawdown & Beta       │        │  • Black-Litterman vyer      │
  └──────────────────────────────┘        └──────────────────────────────┘
```

---

## 3. Riskmodeller & Formler

### Value at Risk (VaR 95%) & Conditional VaR (CVaR)
Historisk och parametrisk beräkning på portföljens dagsavkastning $R_p$:

$$VaR_{0.95} = -\text{Percentil}(R_p, 0.05)$$

$$CVaR_{0.95} = -E[R_p \mid R_p \le -VaR_{0.95}]$$

### Sharpe & Sortino Ratio
Riskjusterad avkastning relativt riskfri ränta ($R_f$):

$$Sharpe = \frac{E[R_p - R_f]}{\sigma_p}, \quad Sortino = \frac{E[R_p - R_f]}{\sigma_{downside}}$$

där $\sigma_{downside}$ enbart mäter variansen för negativa avkastningsdagar.

---

## 4. Portföljkonstruktion & Optimering

1. **Hierarchical Risk Parity (HRP):**
   - Bygger en korrelationsmatris över innehaven, klustrar dem med trädstruktur (quasi-diagonalisering) och fördelar vikter baserat på invers volatilitet inom varje kluster.
   - Förhindrar att en enstaka volatil sektor dominerar portföljens totalrisk.
2. **Equal Risk Contribution (ERC):**
   - Beräknar marginellt riskbidrag per tillgång så att varje aktie bidrar med exakt lika stor del till portföljens totala varians.
3. **Black-Litterman:**
   - Fuserar marknadens jämviktsavkastning med användarens egna subjektiva vyer eller MasterRank-signaler.

---

## 5. Källkodskarta & Kodankare

| Komponent | Fil | Kärnmetoder |
|---|---|---|
| Riskanalys (API) | `apps/api/core/risk_calc.py` | `compute_live_risk()`, `_returns()` |
| Portföljkonstruktion | `apps/api/core/portfolio_construction.py` | `equal_risk_contribution()`, `black_litterman()`, `portfolio_stats()` |
| Avanza Import | `apps/api/core/avanza_import.py` | `parse_positioner_csv()`, `parse_inkopskurser_csv()` |
| Risk Router | `apps/api/routers/risk.py` | `/api/risk/analyze`, `/api/risk/stress-test` |
| Strategy Backtester | `backend_worker/strategy_backtester.py` | `run_backtest()`, `evaluate_performance()` |
| Paper Trading | `backend_worker/paper_trading.py` | `execute_paper_order()`, `track_virtual_pnl()` |

---

## 6. Felsöknings- och Körningsrecept

### Köra ett historiskt strategitest:
```bash
python backend_worker/strategy_backtester.py --strategy momentum_quality --start 2024-01-01
```

### Validera portföljberäkningar isolerat:
```bash
PYTHONPATH=. python -c "from apps.api.core.risk_calc import compute_live_risk; print('Risk module OK')"
```
