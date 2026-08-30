# MarketScan — Hur poängsättningen fungerar (före och efter ROND 8)

> Dokument skapat 2026-08-30. Förklarar hur systemet rankar alla aktier,
> vad som byggts om i ROND 8 (MasterRank) och vad som fortfarande är ofullständigt.
> Skrivet för någon som aldrig sett projektet.

---

## 1. Kort version (TL;DR)

**Innan ROND 8:** varje aktie fick ett betyg (0–100) från två *separata* motorer som
inte pratade med varandra. En motor (score_total) gav ett generellt kvalitetsbetyg,
en annan (QMJ) rankade kvalitet/momentum/insider/värde. Ingen av dem kunde svara på
den viktigaste frågan: *"är det här en bra aktie, eller har priset redan sprungit
ikapp nyheterna?"* Aktier med ofullständig data kunde dessutom toppa listan felaktigt.

**Efter ROND 8:** en enda auktoritativ motor (**MasterRank**) som fuserar båda
plus fyra helt nya signaler — värdering mot egen historik, analytikeruppsida,
teknisk position (RSI/MA/52v-hög) och katalysatorfönster (nästa rapport).
En **anti-bubbla-grind** fångar "bra bolag, dåligt pris" (dyr värdering + tekniskt
överköpt → rank kapas). Vikterna är inte längre gissningar: systemet mäter
kontinuerligt om varje block faktiskt förutsäger utfall och justerar sig självt.

---

## 2. Vad som fanns innan — och varför det inte räckte

### 2.1 Två motorer, en vägg emellan

| Motor | Byggs i | Vad den gör | Vem använder den |
|---|---|---|---|
| `score_total` (11 faktorer) | externt repo (stock-scanner) | viktat kvalitetsbetyg 0–100 | Aktier-vyn (/scan) |
| `alpha_rank` (QMJ-komposit) | detta repo | kvalitet 40% / momentum 25% / insider 15% / värde 10% / utdelning 10% | Kandidatradarn |

Båda var okej var för sig, men ingen använde den andra — så en aktie kunde ha
högt betyg i ena motorn och saknas helt i den andra.

### 2.2 Problem 1 — "tunna data" toppade listan

score_total väger in 11 faktorer (värde 21%, kvalitet 17%, momentum 17%,
tillväxt 13%, risk 9%, sentiment 8%, storlek 5%, utdelning 5%, short interest 3%,
options flow 2%, + Piotroski justering ±8).

Saknades data för en faktor, **omviktades de kvarvarande upp till 3×**. En
amerikansk biotech med bara kvalitet + momentum fick därför ~87 poäng och låg
topp — fast man i praktiken bara tittade på 2 av 11 signaler. Det är därför
topplistan kunde se "konstig" ut: bäst rankade var ofta bolag med *minst* data.

### 2.3 Problem 2 — fyra helt saknade dimensioner

Ingen motor visste något om:

1. **Värdering vs aktiens egen historik** — är P/E 40x högt för just den här aktien, jämfört med dess egna senaste 5 år?
2. **Analytikeruppsida** — vad säger målpriserna jämfört med dagens kurs? (Din Advantest/Palantir-rapport visade precis att detta betyder allt: "rikthakturs ≈ spot = uppsidan inprisad".)
3. **Teknisk position** — RSI, MA200, avstånd till 52-v/hög beräknades *bara inne i LLM-prompter* och lagrades aldrig.
4. **Katalysatorer** — nästa rapportdatum, det som faktiskt flyttar kurser på kort sikt (China Life-interimrapporten).

### 2.4 Problem 3 — nordiskt vs globalt

QMJ (den kvalitativa motorn) kördes **bara för nordiska tickers**
(`.ST`, `.OL`, `.HE`, `.CO`). Alla globala aktier — NVDA, PLTR, 2628.HK (China Life),
Advantest 6857.T — fick **aldrig** QMJ-pelare. Så insider- och utdelningsblocken
var alltid tomma för hälften av universumet.

### 2.5 Problem 4 — hårdkodade magiska tal

Vikterna (0.40/0.25/0.15...), RSI-band (35–68), pullback (5–18 %), boosts
(±8/+20/+30) — inget av det var någonsin backtestat mot egen data.

---

## 3. Hur MasterRank fungerar nu

### 3.1 En motor, 8 block

`master_rank` fuserar allt i **8 vägda block** (vikter i `backend_worker/resources/weights.json`):

| Block | Vikt | Innehåll | Källa |
|---|---|---|---|
| kvalitet | 25 % | ROE, marginaler, Piotroski m.m. | QMJ `quality_z` + score_quality |
| värde | 15 % | P/E vs egen historik + P/E vs sektor-peers + PEG + score_value | QMJ + scan_results |
| momentum | 15 % | 12-1 momentum + score_momentum + RSI/MA | QMJ + teknik |
| analytiker | 15 % | target-price vs spot (skalat av analytikertäckning) | yfinance `.info` |
| insider | 10 % | insiderkluster | QMJ (piotroski-proxy för globala) |
| katalysator | 10 % | nästa rapport ≤45 dagar → +5 boost | earnings_surprises |
| utdelning | 5 % | payout | QMJ (score_dividend-proxy) |
| tillväxt | 5 % | revenue growth | score_growth |

**Regler (viktiga för ärlighet):**

- **Datatäthet:** T1 (75+) kräver **minst 6 av 8 block** med riktig data. Mindre → capped till T3 med `thin_data`-flagga. Ett bolag med 2 signaler rankas aldrig högt igen.
- **Anti-bubbla-grind:** `EXTREME_OVERVAL` (PEG > 2.5 ELLER P/E i topp 10 % av egen historik) **+** `OVERBOUGHT` (RSI > 75) → rank kapas till **60 / T3** med flaggan **"Bubbla-triage"**. Detta är regeln som fångar "starkt bolag, priset har sprungit ikapp nyheterna".
- **Analytiker-capp:** analytikerblocket får aldrig dominera (>15 % av ranken) — småbolag har tunn analystäckning, en enda analytiker ger max 10 % vikt.
- **PIT soft-block:** nyare bolag där bokslutsdata väntar (PENDING) rankas ändå på teknik/analytiker/katalysator — men aldrig T1.

### 3.2 Tiers

| Tier | Poäng | Betydelse |
|---|---|---|
| T1 | 75+ | Kandidat (kräver ≥6/8 block + READY-data) |
| T2 | 65–74 | Värd att kolla |
| T3 | 50–64 | Neutral |
| T4 | <50 | Undvik |
| EXCLUDED | — | Hårda filter (short ≥8 %, ny-kolistad <90 d) |

### 3.3 Exempel från live-data (2026-08-30, efter fix)

| Aktie | Rank | Tier | Varför |
|---|---|---|---|
| PETR4.SA | 70.7 | T2 | Brasilianskt oljebolag: kvalitet 83, värde 92, pullback |
| NVDA | 67.0 | T2 | Kvalitet 96, **analytikeruppsida +48.7 % (58 analytiker)**, RSI 52 |
| 2628.HK (China Life) | 66.4 | T2 | **+19.75 % uppsida (15 analytiker)**, pullback |
| FTNT | 66.4 | T2 | Hög kvalitet men **EXTREME_OVERVAL-flagga** (dyr mot historik) |
| VEEV | 65.3 | T2 | Dyr (EXTREME_OVERVAL) → hämmas |

**Före fixen** var toppen HALO/EXEL/CPRX — biotech med 2/8 block (thin data).
Nu hämmas de korrekt och listan är globalt diversifierad (Brasilien, Japan,
USA, Taiwan, Hongkong) med analytiker-, teknik- och katalysatordata inblandade.

---

## 4. Evidensloopen — systemet som lär sig självt

Det här är MarketScans verkliga värde (och kärnan i ROND 8):

1. **Varje dag:** `master_rank` + alla block loggas till `score_history`.
2. **Varje vecka:** `signal_analytics` beräknar **Rank-IC** per block (90/180/365
   dagars avkastningshorisont) — korrelerar poängen mot faktisk framtida
   avkastning, minus 1 % per sida i transaktionskostnader. Data sparas i
   `factor_metrics`.
3. **Var 60:e dag (eller `--reweight`):** motorn läser IC-värdena och skriver om
   `weights.json` — IC > 0.03 → uppvikt, IC < -0.02 → nedvikt, IC ≈ 0 → borttaget.
4. **T1-träffprocent** mäts över tid i `prediction_outcomes`.

Resultat: viktarna blir **bevis, inte gissningar**. Momentum har t.ex. 15 %
(pga blandad svensk evidens) i stället för QMJ:s gamla 25 % — och sänks
automatiskt om IC mäter negativt. Blocker som inte förutsäger utfall tas bort.

---

## 5. Hur varje aktie poängsätts steg-för-steg (receptet)

1. **Data hämtas:** bokslut (ytfinance), prishistorik 1 år (ytfinance), analytiker-
   målpriser/rekommendationer (`yfinance .info`), SUE/rapportdatum
   (`earnings_surprises`), insiderkluster (`insider_cluster_signals`).
2. **Per block beräknas ett 0–100-delbetyg** (percentil i universumet, eller
   absolut skala). Saknad data → blocket saknas (aldrig "50").
3. **Fusion:** viktad summa enligt `weights.json`. Saknade block hämmas till
   1.5× omviktning max (Rond-5-beslut), och kräver ≥6/8 block för T1.
4. **Justeringar:** katalysatorboosting (+5 ≤45 d), anti-bubbla-grind (cap 60),
   analytiker-capp (≤15 %).
5. **Tier bestäms** (T1–T4 / EXCLUDED) och skrivs till `master_rank`-tabellen.
6. **För varje ny dag:** samma recept körs fredags natt 04:30 UTC (workflow
   `master_rank.yml`), efter QMJ 04:15.

---

## 6. Vad som fortfarande är ofullständigt (ärligt)

- **`val_hist_z` är 0 för alla i dag** — värdering mot *egen 5-årshistorik* kräver
  historisk P/E-data, men `score_history` har bara 3 dagar (2026-08-28–30).
  Tills data ackumuleras används sektor-peers + score_value som vikarier.
- **`pit_status=STALE`** för de flesta globala aktier — betyder bara "QMJ har
  inte rankat den här aktien" (QMJ fokuserar nordiskt), inte att den är dålig.
- **T2/T3-spannet är brett** — skillnaden mellan 65 och 70 poäng är liten för
  ögonblicket; när 5-årsvärderingsdata byggs får anti-bubbla-grinden verklig kraft.
- **Finnhub analyst/katalysator-data är US-only** (verifierat live 2026-08-30) —
  därför går analytiker via yfinance `.info` och katalysatorer via
  earnings_surprises (yfinance `earnings_dates`). Det fungerar, men nordiska
  småbolag har ofta tunn analystäckning (därför analytiker-cappen).

---

## 7. Filkarta (om du vill gräva)

| Fil | Vad |
|---|---|
| `backend_worker/master_rank.py` | Motorn: fusion, tiers, anti-bubbla-grind, reweight |
| `backend_worker/resources/weights.json` | Läsvikter (skrivs om av --reweight) |
| `backend_worker/analyst_fetcher.py` | Analytiker (yfinance .info target/recs) |
| `backend_worker/catalyst_fetcher.py` | Katalysatorer (earnings_surprises + dividend) |
| `backend_worker/technical_snapshot.py` | RSI14/MA50/MA200/52v-hög |
| `backend_worker/signal_analytics.py` | Rank-IC per block (evidensmätningen) |
| `backend_worker/score_tracker.py` | Daglig snapshot (evidensloop) |
| `supabase/migrations/066-070` | Tabeller: analyst_estimates, catalyst_events, master_rank m.fl. |
| `apps/api/routers/market_intel.py` | `/market-intel/master/rank` + `/master/{ticker}` |
| `apps/web/app/(app)/topplistor/TopplistorView.tsx` | Topplistor-vyn |
| `apps/web/components/widgets/MasterRankStrip.tsx` | Top-5-widget på hemsidan |
| `.github/workflows/master_rank.yml` | Fredagsjobb 04:30 UTC |
