# 📈 Kapitel 1: Kvant, MasterRank & Alpha Engine

> **Domän:** Poängsättning av aktier, flerfaktormodeller, Anti-Bubbla-grind och Alpha Discovery.  
> **Status:** Aktiv produktion (Rond 8 / MasterRank).

---

## 1. Executive Summary & TL;DR

MasterRank är MarketScans auktoritativa poängsättningsmotor (0–100) som ersätter tidigare separata modeller. Den förenar fundamental kvalitet, historisk värdering, tekniskt momentum, analytikerkonsensus, insynsaktivitet, katalysatorer, utdelning och tillväxt i 8 vägda block, skyddad av en automatisk anti-bubbla-grind och datatäthetsregler.

---

## 2. Arkitektur & Dataflöde

```
  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
  │ QMJ Kvalitet   │ │ Värdering vs   │ │ 12-1 Momentum  │ │ Analytiker-    │
  │ & Piotroski    │ │ egen historik  │ │ & RSI/MA200    │ │ konsensus      │
  └───────┬────────┘ └───────┬────────┘ └───────┬────────┘ └───────┬────────┘
          │                  │                  │                  │
          └──────────────┐   │   ┌──────────────┘                  │
                         ▼   ▼   ▼                                 ▼
                   ┌─────────────────────────────────────────────────────┐
                   │          backend_worker/master_rank.py              │
                   │               (8 Vägda Block)                       │
                   └──────────────────────┬──────────────────────────────┘
                                          │
                   ┌──────────────────────┴──────────────────────────────┐
                   │  1. Thin Data Check (≥6/8 block för Tier 1)         │
                   │  2. Anti-Bubbla-Grind (PEG/PE_p90 + RSI > 75)       │
                   │  3. Tier-klassificering (T1 ≥75, T2 60-74, T3 <60)  │
                   └──────────────────────┬──────────────────────────────┘
                                          │
                                          ▼
                               Supabase: `scan_results`
```

---

## 3. Matematisk Formulering & De 8 Blocken

Baspoängen beräknas som en linjär kombination av 8 normaliserade delblock ($Score_i \in [0, 100]$):

$$MasterRank_{raw} = \sum_{i=1}^{8} w_i \cdot Score_i$$

Vikterna definieras i `backend_worker/resources/weights.json`:

| Block | Vikt ($w_i$) | Innehåll & Kärnsignaler | Datakälla |
|---|---|---|---|
| **Kvalitet** | 25 % | ROE, ROA, bruttomarginal, vinststabilitet, Piotroski F-score | `backend_worker/qmj_scores.py` |
| **Värde** | 15 % | P/E vs egen 5-årshistorik, P/E vs sektorpeers, P/B, EV/EBIT, PEG | `backend_worker/db_loader.py` |
| **Momentum** | 15 % | 12-1 månaders momentum, RSI(14), avstånd till MA50/MA200 | `backend_worker/technical_snapshot.py` |
| **Analytiker** | 15 % | Uppskattad uppsida (Target Price vs Spot), skalad med analytikertäckning | yfinance konsensus |
| **Insider** | 10 % | FI klusterköp, nettoköp, insider sentiment | `backend_worker/insider_cluster.py` |
| **Katalysator** | 10 % | Nästa rapportdatum inom $\le 45$ dagar, estimat-revideringar | `backend_worker/earnings_surprise.py` |
| **Utdelning** | 5 % | Direktavkastning, utdelningsandel av vinst, 5-års tillväxt | `backend_worker/qmj_scores.py` |
| **Tillväxt** | 5 % | 3-års omsättningstillväxt, EBITDA-tillväxt | `backend_worker/fundamentals_fetcher.py` |

---

## 4. Anti-Bubbla-Grinden ("Bubbla-Triage")

För att förhindra att aktier med fantastisk historisk kvalitet men extremt överhettad kurs rankas i topp tillämpas Anti-Bubbla-filtret:

$$\text{Om } (PEG > 2.5 \lor PE > PE_{p90}) \land (RSI > 75) \implies \begin{cases} MasterRank = \min(MasterRank, 60) \\ Tier = T3 \\ \text{Flagga} = \text{"Bubbla-triage"} \end{cases}$$

### Regler för Datatäthet (Thin Data) och PIT (Point-in-Time)
- **T1-Krav:** Kräver giltiga värden för **minst 6 av 8 block**. Aktier med glesa data (t.ex. nynoterade globala bolag) begränsas automatiskt till max Tier 3 med flaggan `thin_data`.
- **Analytiker-Tak:** Analytikerblocket skalas ned om antalet analytiker är $< 3$, så att en enstaka överoptimistisk riktkurs inte kan driva ranken.
- **PIT Soft-Block:** Bolag med fördröjd bokslutsdata (PENDING) tillåts delta på tekniska/analytiska signaler men kan aldrig uppnå Tier 1 förrän bokslutet verifierats.

---

## 5. Alpha Discovery Engine

Specialiserade signalmoduler som körs i `backend_worker/alpha_discovery/`:

| Modul | Fil | Strategi |
|---|---|---|
| **Wyckoff Divergence** | `backend_worker/alpha_discovery/wyckoff_divergence.py` | Upptäcker ackumulations- och distributionsfaser baserat på volym/pris-divergenser |
| **FCF Inflection** | `backend_worker/alpha_discovery/fcf_inflection_scanner.py` | Hittar bolag där fritt kassaflöde svänger från negativt till kraftigt positivt |
| **Warrant Detector** | `backend_worker/alpha_discovery/warrant_detector.py` | Identifierar potentiell utspädning från teckningsoptioner i småbolag |
| **Fund Shadowing** | `backend_worker/alpha_discovery/fund_shadowing.py` | Spårar toppfondernas ökade ägarandelar i nordiska aktier |
| **Analyst Credibility** | `backend_worker/alpha_discovery/analyst_credibility.py` | Vikter analytiker baserat på deras historiska träffsäkerhet |

---

## 6. Källkodskarta & Kodankare

| Komponent | Fil | Kärnmetoder |
|---|---|---|
| MasterRank Beräkning | `backend_worker/master_rank.py` | `fuse()`, `tier_of()`, `master_rank_run()`, `compute_peg()` |
| QMJ & Kvalitet | `backend_worker/qmj_scores.py` | `extract_metrics()`, `composite()`, `compute_sector_value()`, `stratum_of()` |
| Faktorregimer | `backend_worker/factor_regime.py` | `compute_regime()`, `classify_regime()`, `compute_nordic_composite()` |
| Teknisk Snapshot | `backend_worker/technical_snapshot.py` | `compute_technical()`, `snapshot_technicals()`, `rsi_14()` |
| Insynskluster | `backend_worker/insider_cluster.py` | `calculate_clusters()`, `calculate_sell_clusters()`, `dedupe_trades()` |
| Earnings Surprises | `backend_worker/earnings_surprise.py` | `compute_sue()`, `process_earnings_frame()`, `fetch_earnings_dates()` |

---

## 7. Recept för Ändringar & Felsökning

### Justera en faktorvikt:
1. Redigera `backend_worker/resources/weights.json`.
2. Kör historisk validering: `python backend_worker/backtest_runner.py`.
3. Verifiera ranking-distributionen: `python scripts/ranking_sanity_gate.py`.
4. Uppdatera vikttabellen i sektion 3 ovan *in-place*.

---

## 8. Småbolag & Kända Begränsningar

1. **Segment-relativ kalibrering:** Småbolag (`small_cap`, `micro_cap`) har glesare data och lägre analytikertäckning. MasterRank anpassar tier-trösklarna (T1 $\ge 62.0$, T2 $\ge 50.0$, T3 $\ge 38.0$) så att köpvärda småbolag inte utestängs.
2. **Datatäthet & Thin-Data Tak:** Vid färre än 3 giltiga kärnblock begränsas ranken automatiskt (`thin_cap = 61.999` för småbolag resp $64.999$ för stora bolag).
3. **Koncentrationsrisk (NAV):** Modellen mäter ej portfölj-/NAV-koncentration i investmentbolag (t.ex. 3i Group / Action). Detta är en känd begränsning i universumet.
4. **Likviditetsflagga (`low_liquidity`):** Graderas av extern scanner baserat på omsättning; visas med varningstriangel i UI.
5. **ROE Kontrakt (Rå vs Residual):** UI och screener-filter använder uteslutande `roe_raw` (yfinance råvärde). Den neutraliserade sektorresidualen `roe` är strikt intern för faktorberäkning.
