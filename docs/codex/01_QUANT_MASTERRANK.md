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

För att förhindra att aktier med fantastisk historisk kvalitet men extremt överhettad kurs rankas i topp tillämpas Anti-Bubbla-filtret med progressiv dämpning:

- **Progressiv Dämpning (RSI 70–75):** När en aktie uppvisar extrem värdering ($PEG > 2.5 \lor PE > PE_{p90}$) och RSI närmar sig överköpt (RSI > 70) dämpas ranken mjukt och proportionellt mot överhettningen:
  $$Dämpning = \min(10.0, 1.5 \cdot (RSI - 70))$$
- **Bubbla-Triage Cap (RSI > 75):** Om aktien bekräftas överköpt ($RSI > 75$) cappas ranken strikt till max $60.0$ (Tier 3) med flaggan `bubble_triage`.
- **Cyklisk & Noll-Tillväxt Guard:** Vid negativ eller nära-noll tillväxt ($\le 0.5\%$) är PEG matematiskt odefinierat och ignoreras helt. Grinden förlitar sig då uteslutande på historisk percentil ($PE_{p90}$) och sektorpeers så att cykliska bolag inte slinker förbi.

### Regler för Datatäthet (Thin Data), Analytikerspridning och PIT
- **T1-Krav:** Kräver giltiga värden för **minst 6 av 8 block**. Aktier med glesa data begränsas automatiskt till max Tier 3 med flaggan `thin_data`.
- **Analytiker-Tak & Spridning (Dispersion):** Analytikerblocket skalas ned om antalet analytiker är $< 3$. Dessutom appliceras ett avdrag på upp till 35% om riktkursspridningen ($IQR/Median > 0.4$) är hög, så att extrem oenighet mellan banker straffar konfidensen.
- **Segment-Normalisering (`master_rank_pctl`):** Vid sidan av rå MasterRank beräknas en segment-relativ percentil (0–100) för att möjliggöra rättvis jämförelse mellan småbolag ($T1 \ge 62$) och storbolag ($T1 \ge 75$).
- **PIT Soft-Block:** Bolag med fördröjd bokslutsdata (PENDING) tillåts delta på tekniska/analytiska signaler men kan aldrig uppnå Tier 1 förrän bokslutet verifierats.

---

## 5. Alpha Discovery & Forensiska Skyddsmotorer

Specialiserade signal- och skyddsmoduler som körs i `backend_worker/alpha_discovery/` och `backend_worker/`:

| Modul | Fil | Strategi |
|---|---|---|
| **Makroregim & EMA-tröghet** | `backend_worker/macro_regime.py` | 60-dagars EMA-utjämning (`compute_smoothed_regime_weights`) för flimmerfri regimstyrning |
| **Forensisk Sköld & Tillväxt-Sloan** | `backend_worker/forensic_shield.py` | Tillväxtjusterad Sloan Accrual $\Delta \text{Accruals} / \Delta \text{Sales}$ + utspädningsskydd |
| **Warrant Detector (TO-Radar)** | `backend_worker/alpha_discovery/warrant_detector.py` | Identifierar teckningsoptioner (TO1-TO9), utspädningsandel och lösenfönster |
| **Offentliga Upphandlingar** | `backend_worker/alpha_discovery/tenders_tracker.py` | Spårar offentliga ramavtal (TED/Doffin) för IT- och försvarskonsulter (`score_public_tenders`) |
| **Smart Money & Free Float** | `backend_worker/smart_money.py` | Opportunistiska insiderkluster vs optionslösen samt `compute_free_float_quality` |
| **Wyckoff Divergence** | `backend_worker/alpha_discovery/wyckoff_divergence.py` | Upptäcker ackumulations- och distributionsfaser baserat på volym/pris-divergenser |
| **FCF Inflection** | `backend_worker/alpha_discovery/fcf_inflection_scanner.py` | Hittar bolag där fritt kassaflöde svänger från negativt till kraftigt positivt |
| **Fund Shadowing** | `backend_worker/alpha_discovery/fund_shadowing.py` | Spårar toppfondernas ökade ägarandelar i nordiska aktier |
| **Analyst Credibility** | `backend_worker/alpha_discovery/analyst_credibility.py` | Vikter analytiker baserat på deras historiska träffsäkerhet |

---

## 6. Källkodskarta & Kodankare

| Komponent | Fil | Kärnmetoder |
|---|---|---|
| MasterRank Beräkning | `backend_worker/master_rank.py` | `fuse()`, `tier_of()`, `master_rank_run()`, `compute_peg()`, `load_weights()` |
| Forensisk Revision | `backend_worker/forensic_shield.py` | `audit_company_forensics()`, `SLOAN_ACCRUAL_THRESHOLD` |
| Makro & Faktorregimer | `backend_worker/macro_regime.py` | `classify_macro_regime()`, `compute_smoothed_regime_weights()`, `derive_regime_from_scan()` |
| QMJ & Kvalitet | `backend_worker/qmj_scores.py` | `extract_metrics()`, `composite()`, `compute_sector_value()`, `stratum_of()` |
| Smart Money & Float | `backend_worker/smart_money.py` | `analyze_insider_transactions()`, `compute_free_float_quality()` |
| Upphandlingar | `backend_worker/alpha_discovery/tenders_tracker.py` | `score_public_tenders()` |
| Teknisk Snapshot | `backend_worker/technical_snapshot.py` | `compute_technical()`, `snapshot_technicals()`, `rsi_14()` |

---

## 7. Recept för Ändringar & Felsökning

### Justera en faktorvikt:
1. Redigera `backend_worker/resources/weights.json`.
2. Kör historisk validering: `python backend_worker/backtest_runner.py`.
3. Verifiera ranking-distributionen: `python scripts/ranking_sanity_gate.py`.
4. Uppdatera vikttabellen i sektion 3 ovan *in-place*.

---

## 8. Småbolag & Kända Begränsningar

1. **Segment-relativ kalibrering & Percentiler:** Småbolag (`small_cap`, `micro_cap`) har glesare data och lägre analytikertäckning. MasterRank anpassar tier-trösklarna (T1 $\ge 62.0$, T2 $\ge 50.0$, T3 $\ge 38.0$) och beräknar `master_rank_pctl` inom segmentet.
2. **Smallcap Runway & Nyemissions-sköld:** Olönsamma småbolag med kort kassa ($< 12$ månader) och svagt kassaflöde/kvalitet ($< 60$) cappas till max $48.0$ (Tier 4 / EJ_AKTUELL).
3. **Compounder & MEWS-synergi:** Kapitaleffektiva småbolag ($Quality \ge 75$) med insiderköp eller stark MEWS-accelerering erhåller nisch-vallgravsbonus (Harvia, ATOSS, Bouvet).
4. **Vinstvolatilitet & Leasing-rabatt:** Finansiella aktörer med hög intäktsvolatilitet eller engångsavgifter (t.ex. FPG 7148.T) cappas vid max 58.0 för att inte förväxlas med stabila compounders.
5. **Datatäthet & Thin-Data Tak:** Vid färre än 3 giltiga kärnblock begränsas ranken automatiskt (`thin_cap = 61.999` för småbolag resp $64.999$ för stora bolag).
6. **Likviditetsflagga (`low_liquidity`):** Graderas av extern scanner baserat på omsättning; visas med varningstriangel i UI.
7. **ROE Kontrakt (Rå vs Residual):** UI och screener-filter använder uteslutande `roe_raw`. Den neutraliserade sektorresidualen `roe` är strikt intern för faktorberäkning.
