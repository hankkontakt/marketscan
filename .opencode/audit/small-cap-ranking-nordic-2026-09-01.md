# Small/Micro Cap Ranking Best Practices — Nordic Focus (First North, NGM, Spotlight)

**Date:** 2026-09-01
**Purpose:** Evidence base for a Nordic multi-factor ranker (0–100) covering small_cap and micro_cap segments: liquidity risk, momentum behavior, dilution/emission risk, data quality, point-in-time pitfalls, and segment-relative presentation.
**Language:** English (Swedish terms kept where domain-specific).

---

## 1. Task Report — direct answers

### Q1. Liquidity screens: what thresholds do screeners use, and when is a stock "uninvestable"?

**Answer:** Public screeners use a mix of (a) market-cap buckets, (b) average share volume, (c) average dollar volume, and (d) spread filters. There is no single "uninvestable" line; the practical rule for private investors is **position size ≤ ~10% of average daily turnover** and **bid-ask spread ≤ ~1–2%** — beyond that, execution costs destroy the edge.

Concrete thresholds found:

| Screener / source | Threshold | Context |
|---|---|---|
| Zacks "10 Winning Strategies" | **Avg dollar volume ≥ $500,000** ("bare minimum"); **20-day avg volume ≥ 50,000 shares** | Small-Cap Growth screen; "It has to be tradable" |
| Finviz | Market-cap buckets: Small $300M–$2B, Micro $50M–$300M, Nano <$50M; **Avg Volume "Over 500K"** is the commonly recommended liquidity gate | Screener filter presets; third-party guides |
| Stockopedia | Size groups: Micro <£50m, Small <£350m, Mid <£2.5bn, Large >£2.5bn; momentum screen uses **Market Cap >£25m floor** ("smallest companies tend to be illiquid and poorly understood"); volume metrics: 10d avg vol (null if <10 active trading days in 20), 3m avg vol, %10d-vs-3m trend | Glossary + published screens |
| Stockopedia (5 easy rules) | Small-cap range **£25m–£750m** | "small enough to multibag, reasonably well established" |
| Day-trading guides (Finviz-adjacent) | **ADV ≥ 300,000–500,000 shares** baseline; **dollar volume ≥ $5M** for intraday; spread >1–2% = significant cost | DayTradingToolkit, TradeWink, Alpha Learning |
| StocksToTrade | **Min 100,000 shares/day**; **position <10% of daily turnover** | Rule of thumb for retail |
| Nasdaq First North rulebook | Admission: **≥10% of shares in public hands, ≥300 qualified shareholders**; ongoing: quoted spread above INET threshold → moved to Auction segment unless a Liquidity Provider is engaged | Regulatory floor, not an investor rule |
| First North market data | Whole-market avg daily turnover **€41.1M across ~450 companies** (≈€90K/company/day average); avg trade size **€896** | Nasdaq facts & figures Q1 2024 |
| ScreenerHero (First North) | Companies **<€50M mcap typically trade €5,000–€50,000/day**; spreads **0.5–2%** for active names; institutions with >€1M positions find **<€30M mcap uninvestable** in practice | Nordic microcap guide |

**"Uninvestable" synthesis for private investors:** a stock is effectively uninvestable when a realistic position (say SEK 25–100K) exceeds ~10% of daily turnover, or when the spread exceeds ~2% — both are common below ~€30–50M market cap on First North. Screeners handle this either by hard-excluding (Zacks $500K dollar volume) or by flagging (Stockopedia nulls volume metrics when trading is too sparse).

### Q2. Momentum in small caps: relative strength, crash risk, seasonality, rebalancing

**Answer:** Momentum is *stronger gross* in small caps than large caps, but *net of costs and crash risk it is much weaker* — one 2026 study puts the breakeven market cap at ~$480M below which 12-1 momentum profit is consumed by transaction costs. Two structural risks dominate: **momentum crashes** (Daniel & Moskowitz 2016) and the **January effect** (momentum changes sign in January; losers rebound).

Evidence:
- **Gross vs net:** Jegadeesh–Titman 12-1 momentum on CRSP 1990–2023: small caps (<$500M) gross +1.34%/mo (t=4.7) but **−0.12%/mo net of costs** (turnover 1.8× higher, spreads 4.2× wider than large caps); breakeven ≈$480M. *(Preprint — treat as indicative, cross-checked below.)*
- **Crash risk:** Daniel & Moskowitz (2016) — momentum crashes cluster in high-volatility, post-bear-market rebounds (1932, 2009: long-short momentum lost >70% in months). Small-cap momentum concentrates in exactly the stocks that crash hardest when momentum reverses; a 15-name small-cap book had **99.2% bootstrap risk of ruin** at practical sizing (2026 practitioner autopsy; survivorship correction only cost 1.6pp of CAGR, so the ruin is structural, not a data artifact).
- **January/turn-of-year:** the January effect persists for small caps (Haug & Hirschey 2006, 1802–2004 data); **momentum returns are negative in January** and short-term reversal strengthens at the turn of the year, especially after recessions (Kozlowski & Lytle; Yao 2011 — long-term contrarian is "entirely attributable to the January size effect").
- **Mitigations with evidence:** volatility scaling (Barroso & Santa-Clara 2015) improves momentum Sharpe ~50%; risk-adjusted ranking (return/vol) tilts away from fragile high-beta names; regime gates (IWM 12m < 0 → halve exposure) per Cooper et al. 2004.
- **Rebalancing:** monthly rebalance is standard; decile momentum turnover ≈53.6%/mo one-way (S&P 500 sample) — for small caps expect higher; quarterly rebalancing for micro caps is the pragmatic choice.

### Q3. Dilution & emission risk: how screeners model it

**Answer:** The three standard building blocks are **(1) share-count growth (issuance velocity), (2) warrant/convertible overhang (fully diluted vs basic shares), and (3) cash runway for loss-makers.** Concrete rules exist from Simply Wall St and DilutionWatch.

- **Simply Wall St:** YoY increase in shares outstanding **>30% = "major risk" flag**; **<1 year cash runway = risk flag**; for loss-making companies the debt checks are replaced by two cash-runway checks (stable burn and trend burn, each scoring 1 point if cash covers >1 year).
- **DilutionWatch DilutionScore (0–100, higher = worse):**
  - Cash runway (30% weight): >18 months = 0 pts; 12–18 = 15; 6–12 = 40; 3–6 = 70; **<3 months = 100**.
  - Warrant & convert overhang (25%): <10% = 0–15; 10–25% = 15–40; 25–50% = 40–70; 50–100% = 70–90; **>100% = 90–100**.
  - Share issuance velocity (20%): <10% YoY = 0–10; 10–25% = 10–30; 25–50% = 30–60; 50–100% = 60–80; **>100% = 80–100**.
- **Fully diluted discipline (Curved):** use fully diluted share count as the valuation denominator; a 20% raise requires 25% earnings growth just to stand still per share; stock comp alone runs 3–8%/yr in young companies.
- **Swedish First North specifics:** units = share + teckningsoption (TO); dilution is disclosed in prospectuses and is frequently large — e.g., north net connect: max dilution **49.5%** of share capital incl. warrants; eEducation Albert: 5.6–6.3%; Nordic Paper LTIP: 1.39%. A ranker should treat outstanding TO series (TO1, TO2…) as pending dilution and announced rights issues (nyemission) as near-certain dilution.

### Q4. Point-in-time & survivorship pitfalls

**Answer:** These biases are *largest in small/micro caps* because delisting rates are highest there. Quantified magnitudes:

- **Survivorship bias:** ~0.9%/yr for mutual funds (Elton et al. 1996); 2–4%/yr hedge funds; **1–2%/yr for equities, worse in small/micro caps** (Foxholm; Susan Potter). One practitioner found ~8% of historical small-cap tickers missing from a "survivorship-free" vendor dataset — correcting it **removed ~40% of apparent momentum alpha**. Strasmore measured: of 7,063 US names trading in 2015, only **52.5% still traded in 2026**; median survivor return beat the full cohort by **3.81pp in 2017** (positive gap in all 10 years).
- **Look-ahead bias:** using fiscal-period-end instead of filing date hands the backtest data months early — average filing lag measured at **43.4 days** (Tradevo sample). Look-ahead benchmark bias alone can inflate results **up to 8%/yr** (Daniel, Sornette & Wöhrmann, arXiv 0810.1922).
- **Detection:** the **shift test** (lag every signal one period; a real edge decays gently, a leak collapses); rebuild the universe as-of each date including delisted names closed at final print; use as-reported (not restated) fundamentals with first-filed timestamps.
- **Nordic note:** First North delistings/transfers are frequent (5+ companies/yr graduate to the main market; many more delist), so point-in-time universe construction is mandatory for any Nordic small-cap backtest.

### Q5. Nordic small-cap data reality

**Answer:** **yfinance does NOT reliably cover Nordic small caps.** Documented issues: missing days on Stockholm (.ST) tickers (SAAB-B.ST, ERIC-B.ST, ABB.ST — issue #2608); "very small stocks on the Stockholm exchange sometimes shows no history at all" (issue #76, FEEL.ST); the yfinance price-repair docs state "Only US market data appears perfect"; currency mixups (£/pence-style) occur. A 2025 audit vs XETRA found deviations up to 11% and "suspicious days" (identical OHLC) on up to 10% of days even for DAX-40 names. **Verdict: usable for main-market prices with `repair=True` and validation gates; not trustworthy for First North/NGM/Spotlight fundamentals or micro-cap history.**

Better Nordic sources:
- **Börsdata:** 1,700+ Nordic companies "cover all the smaller market lists"; data collected directly from company interim/annual reports (not resold); 20 years of history; API available to PRO/PRO+ members; global (16,000+) via Refinitiv for Pro+.
- **Millistream:** MWS API — real-time Nordic quotes, fundamentals, corporate actions, earnings/dividend calendar, insiders; commercial.
- **Analyst coverage reality:** coverage "thins out below €200M market cap rapidly" — an estimated 300–500 quality Nordic companies have **no Bloomberg consensus and no sell-side coverage**; hundreds of listed small Nordic companies have no coverage at all (HedgeNordic). One analyst vs none cuts bid-ask spreads ~14% (Aalto thesis, 2014–2021, 1,017 firms). Swedish small-cap research is largely **commission-based** (Redeye, Erik Penser, Carlsquare, Analyst Group, Introduce) — a conflict-of-interest caveat. First North has lighter disclosure (IFRS not required), so earnings-date availability is poor; use company IR calendars.

### Q6. Presentation: segment-relative grades/percentiles

**Answer:** The Stockopedia pattern is the industry reference: **every rank is a percentile (0–100, 100 = best) computed against a defined peer set — the Market and/or the Industry/Sector Group (TRBC)** — and displayed as color-coded quintile bands (top 20% green → bottom 20% red). Key practices:
- Rank against **both** the whole market and the sector peer group; the sector set is restricted to the same market area (e.g., UK subscribers rank Vodafone vs UK telecoms only).
- Composite ranks (Quality/Value/Momentum → StockRank) are equal-weighted sub-ranks, re-ranked as percentiles.
- **Use medians, not means**, for peer comparisons — Stockopedia winsorizes means at 3% but states medians are "more appropriate for many of the mid cap and small cap stocks that many private investors prefer to hunt in."
- Show a **size-group label** (Micro/Small/Mid/Large) and a **Mkt Cap Rank** (position vs universe) so users never compare a micro cap's raw ratio against a large cap's.
- For a Nordic ranker: compute percentiles **within segment (small_cap vs micro_cap) × sector**, and additionally show a liquidity grade and dilution flag as separate, non-composite badges so a high fundamental score in an illiquid, dilutive stock is not misleading.

---

## 2. Concrete thresholds/rules for a Nordic small-cap ranker (synthesis)

**Segments** (align with Nasdaq Nordic official bands + First North reality):
- `small_cap`: **€150M–€1B** (Nasdaq Stockholm Small Cap band; ≈SEK 1.6B–11B)
- `micro_cap`: **€30M–€150M** (below the official Small Cap band; First North territory)
- Below €30M: rank only in a "speculative/nano" view with heavy flags, or exclude from the headline ranking universe (institutional exclusion zone per ScreenerHero).

**Liquidity gates (20-day medians):**
- Hard "investable" floor for ranking: **median daily turnover ≥ SEK 500K (~€45K)** for micro_cap; **≥ SEK 2M (~€180K)** for small_cap. (Rationale: private position SEK 25–50K ≤ 10% of daily turnover; First North <€50M names trade €5–50K/day, so this floor deliberately excludes the thinnest tail from the headline rank.)
- **Spread flag:** bid-ask spread >2% → liquidity grade D/F (First North active names run 0.5–2%; >2% = significant cost).
- **Price floor:** ≥ SEK 1 (penny-stock manipulation zone; Finviz/day-trading baselines use $1–5).
- **Free float ≥ 10%** and ≥300 shareholders where data allows (First North admission norms).
- Volume metrics: null out 10d/20d averages when <10 active trading days in the lookback (Stockopedia pattern) — a stock that doesn't trade daily cannot have a meaningful liquidity score.

**Momentum:**
- Primary signal: **12-1 momentum** (skip last month); supplement with 3–6 month return for micro caps where 12-1 is noisy.
- **Risk-adjust** momentum (return/12m vol) rather than raw return — tilts away from crash-prone high-beta names (Daniel & Moskowitz mitigation).
- **January handling:** expect momentum to underperform and short-term reversal to dominate in January; avoid full momentum weight at turn-of-year rebalances; consider a January-neutral variant.
- **Rebalance:** monthly for small_cap, quarterly for micro_cap (turnover cost); cap micro-cap momentum score contribution given the ~$480M breakeven finding.

**Dilution/emission:**
- **Share-count growth YoY:** >10% flag; >25% penalty; >50% severe penalty (DilutionWatch bands).
- **Warrant/convert overhang** (fully diluted ÷ basic − 1): <10% OK; 10–25% flag; >25% penalty; >100% critical.
- **Cash runway** (cash + ST investments ÷ trailing FCF burn, 3-mo avg) for loss-makers: <12 months flag (Simply Wall St); <6 months severe penalty (DilutionWatch 70–100 pts).
- **First North:** track outstanding TO series and announced nyemission as pending dilution; use fully diluted share count for per-share metrics.
- Per-share metrics must be recomputed on the **fully diluted** count (Curved).

**Point-in-time discipline:**
- Key fundamentals to **filing date + conservative lag (≥45–60 days)** for Nordic small caps (43-day average US lag; Nordic small caps report slower).
- Backtests: point-in-time universe incl. delisted/transferred names closed at final print; expect 1–2%/yr survivorship inflation, worse in micro caps; run the **shift test** before trusting any backtest.

**Data sourcing:**
- Prices: yfinance acceptable for main-market Nordic names with `repair=True` + validation gates; **do not trust** for First North/NGM/Spotlight micro caps or for fundamentals.
- Fundamentals: **Börsdata** (1,700+ Nordic, all smaller lists, API for PRO+) or **Millistream** (commercial, real-time + calendar + corporate actions).
- Analyst data: treat "no coverage" as neutral for micro caps (not a penalty); never require consensus estimates below €200M mcap.

**Presentation:**
- Percentile 0–100 (100 = best) computed **within segment × sector peer group**, plus a "vs whole market" percentile; quintile color bands.
- Use **medians** for peer comparisons.
- Separate badges: **Liquidity grade (A–F)**, **Dilution flag**, **Cash-runway flag** — never folded silently into the composite.

---

## 3. Verification Receipts

All URLs accessed 2026-09-01.

**Liquidity**
- Zacks "Top 10 Stock Screening Strategies" (Small-Cap Growth: avg dollar volume ≥$500K; 20-day volume ≥50K): http://www.zacksrw.com/manuals/10winning_strategies.pdf and http://woas.zacks.com/adv/10winning_strategies.pdf — backs Q1 thresholds.
- Finviz screener filter definitions (market-cap buckets incl. Small $300M–2B, Micro $50–300M, Nano <$50M; Average Volume = 3-month average): https://finviz.com/screener and https://finviz.com/help/screener — backs Q1.
- Finviz small-cap guides (Avg Volume Over 500K; price floors): https://prodigytradingteam.com/blogs/trading-blog/finviz-screener-settings-trading-strategies-small-mid-large-caps , https://tradingtoolshub.com/blog/how-to-use-finviz-for-stock-screening-step-by-step-guide/ , https://www.nwcast.com/article/guide-how-to-screen-stocks-with-finviz-for-free-20260707 — backs Q1.
- Stockopedia Screenable Glossary (size groups Micro <£50m / Small <£350m / Mid <£2.5bn; volume metrics incl. 10d avg vol null rule): https://www.stockopedia.com/ratio/printable/screenable/ and https://www.stockopedia.com/ratio/printable/ — backs Q1, Q6.
- Stockopedia momentum screen (Market Cap >£25m floor; NAPS-style spread filter discussion): https://www.stockopedia.com/content/riding-the-rally-screening-for-momentum-winners-1035582/ — backs Q1, Q2.
- Stockopedia "5 easy rules" (£25m–£750m): https://www.stockopedia.com/content/5-easy-rules-to-find-good-small-cap-stocks-983391/ — backs Q1.
- StocksToTrade (100K shares/day min; position <10% of daily turnover): https://stockstotrade.com/what-is-stock-liquidity/ — backs Q1.
- DayTradingToolkit (ADV 300–500K baseline; spread >1–2% significant): https://daytradingtoolkit.com/beginners-guide/stock-screener-filters-day-trading — backs Q1.
- TradeWink (dollar volume $5M): https://www.tradewink.com/learn/how-to-build-a-stock-screener — backs Q1.
- Nasdaq First North Growth Market Rulebook (10% public hands, 300 shareholders, spread→auction segment): https://bergssecurities.se/wp-content/uploads/2025/05/nasdaqfirstnorthgrowthmarketrulebook1april2025.pdf — backs Q1.
- Nasdaq First North facts & figures Q1 2024 (€41.1M daily turnover, €896 avg trade): https://www.nasdaq.com/docs/2024/05/08/First%20North%20Facts%20and%20Figures%20-%20Q1%20-%202024.pdf — backs Q1.
- ScreenerHero First North guide (<€50M mcap → €5–50K/day; spreads 0.5–2%; <€30M uninvestable for institutions): https://www.screenerhero.com/blog/sweden-first-north-guide — backs Q1, Q5.

**Momentum & seasonality**
- Haug & Hirschey, "The January Effect", Financial Analysts Journal 62(5) 2006 (persistent small-cap January effect): https://www.tandfonline.com/doi/abs/10.2469/faj.v62.n5.4284 and SSRN version https://papers.ssrn.com/sol3/papers.cfm?abstract_id=831985 — backs Q2 (double-sourced).
- Kozlowski & Lytle, "The January Anomaly and Anomalies in January" (momentum changes sign in January; reversal strengthens at turn of year; stronger after recessions): https://ojs.aut.ac.nz/applied-finance-letters/article/download/615/164 — backs Q2.
- Yao, "Momentum, contrarian, and the January seasonality", J. Banking & Finance 2011 (contrarian = January size effect; momentum January seasonality): https://www.sciencedirect.com/science/article/abs/pii/S0378426611003499 — backs Q2.
- Momentum crashes (Daniel & Moskowitz 2016 summary; 1932/2009 >70% losses; vol-scaling mitigation; Barroso & Santa-Clara 2015): https://signalstrike.trade/blog/momentum-crashes and https://github.laiyagushi.com/Starkl7/DeepMomentum — backs Q2 (double-sourced).
- Small-cap momentum gross vs net (CRSP 1990–2023; breakeven ~$480M) — preprint, treat as indicative: https://clawrxiv.io/abs/2604.00809 — backs Q2.
- Small-cap momentum ruin risk + survivorship correction (20.4→18.7% CAGR; 99.2% ruin): https://medium.com/gradient-growth/the-strategy-with-real-returns-and-a-99-risk-of-ruin-4d0b890b646f — backs Q2, Q4.
- S&P 500 12-1 momentum (53.6% monthly turnover; long leg +7.9% vs short leg −9.1%; crash episodes): https://www.scribd.com/document/1039583830/ssrn-5367656 — backs Q2.

**Dilution**
- Simply Wall St Company Analysis Model (cash runway checks for loss-makers): https://github.com/SimplyWallSt/Company-Analysis-Model/blob/master/MODEL.markdown and https://support.simplywall.st/hc/en-us/articles/9812782597135-Understanding-The-Financial-Health-Section — backs Q3.
- Simply Wall St dilution flags (>30% YoY share increase = major risk; <1yr runway): https://simplywall.st/stocks/us/software/nasdaq-mstr/strategy and https://simplywall.st/stocks/us/energy/nasdaq-prop/prairie-operating — backs Q3.
- DilutionWatch DilutionScore methodology (runway 30% / overhang 25% / velocity 20% with full band tables): https://dilutionwatch.com/articles/dilution-score-methodology.html — backs Q3.
- Curved dilution guide (fully diluted denominator; 20% raise → 25% earnings growth to stand still; stock comp 3–8%/yr): https://curvedtrading.com/articles/en/investing/dilution-analysis-guide/ — backs Q3.
- First North teckningsoptioner examples (north net connect 49.5% max dilution; eEducation Albert 5.6–6.3%; Nordic Paper 1.39%): https://nyemissioner.se/wp-content/uploads/rights-issues/2934/prospekt.pdf , https://www.datocms-assets.com/64385/1765459461-7-to2026-2029-a-eeducation-albert-ab.pdf , https://www.nordic-paper.com/sv/media/781/download?attachment= — backs Q3.

**Point-in-time / survivorship**
- Daniel, Sornette & Wöhrmann, "Look-Ahead Benchmark Bias" (up to 8%/yr): https://arxiv.org/html/0810.1922 — backs Q4.
- Susan Potter, "A Taxonomy of Backtest Lies" (0.9%/yr funds; 2–4%/yr HF; 1–2%/yr equities; 8% missing small-cap tickers → 40% alpha loss; shift test): https://www.susanpotter.net/quant/backtest-bias-taxonomy/ — backs Q4.
- Strasmore, "Look-Ahead Bias: The Backtest Killer" (52.5% of 2015 cohort alive in 2026; 3.81pp survivor gap 2017; 43-day filing-lag context; shift test): https://www.strasmore.com/blog/look-ahead-bias-in-backtesting — backs Q4.
- Tessera Alpha methodology (three biases; point-in-time universe; as-reported financials): https://tesseraalpha.com/methodology/backtesting-survivorship-lookahead — backs Q4.
- Foxholm, "Backtesting Pitfalls" (survivorship 1–2%/yr, most severe in small/micro caps; filing-date rule): https://foxholm.com/q/concepts/backtesting-pitfalls/ — backs Q4.
- Tradevo Data (43.4-day avg filing lag; fiscal-period-end vs first-filed join bug): https://dev.to/tradevodata/survivorship-bias-vs-lookahead-bias-the-two-silent-backtest-killers-pmm — backs Q4.

**Nordic data**
- yfinance issue #2608 (missing days on Stockholm .ST tickers): https://github.com/ranaroussi/yfinance/issues/2608 — backs Q5.
- yfinance issue #76 ("very small stocks on the Stockholm exchange sometimes shows no history at all"): https://github.com/ranaroussi/yfinance/issues/76 — backs Q5.
- yfinance price_repair docs ("Only US market data appears perfect"; currency mixups): https://github.com/ranaroussi/yfinance/blob/main/doc/source/advanced/price_repair.rst — backs Q5.
- Tobi Lux, "Data from yfinance — some Observations" (deviations up to 11% vs XETRA; suspicious days up to 10%): https://medium.com/@Tobi_Lux/data-from-yfinance-some-observations-41e99d768069 — backs Q5.
- Börsdata (1,700+ Nordic companies incl. smaller lists; API for PRO/PRO+; data from company reports): https://borsdata.se/en , https://borsdata.se/en/info/api/api_page , https://borsdata.se/en/about , https://github.com/Borsdata-Sweden/API — backs Q5.
- Millistream MWS docs (fundamentals, corporate actions, calendar, insiders): https://packages.millistream.com/documents/mws.pdf and https://millistreamtrader.com/index.php — backs Q5.
- Aalto thesis, "Effects of analyst coverage on market liquidity… Nasdaq Nordic 2014–2021" (1 analyst → 14% spread decline; 38% Amivest increase): https://aaltodoc.aalto.fi/handle/123456789/120129 — backs Q5.
- ScreenerHero Nordic microcap (coverage thins below €200M; 300–500 companies without Bloomberg consensus): https://www.screenerhero.com/blog/nordic-microcap-investing — backs Q5.
- HedgeNordic, "Mind the GARP in Nordic Stocks" (hundreds of small Nordic companies with no sell-side coverage): https://hedgenordic.com/2023/11/mind-the-garp-in-nordic-stocks/ — backs Q5.
- HHS thesis, "Initiations" (commission-based Swedish small-cap research: Redeye, Erik Penser, Carlsquare, Analyst Group, Introduce): http://arc.hhs.se/download.aspx?MediumId=4632 — backs Q5.
- Osuva thesis (First North lighter disclosure, IFRS not required): https://osuva.uwasa.fi/bitstreams/b00168ef-c320-4ca0-b069-b0536ddfcb71/download — backs Q5.

**Presentation**
- Stockopedia "Ranking data — percentiles and ordinals" (position + percentile ranks vs Market and/or Industry/Sector Group; TRBC): https://www.stockopedia.com/learn/our-data/ranking-data-percentiles-and-ordinals-462873/ — backs Q6.
- Stockopedia Traffic Lights (percentile vs industry and vs market; quintile color bands): https://www.stockopedia.com/learn/stockreports/traffic-lights-comparing-a-stock-vs-its-peers-463023/ — backs Q6.
- Stockopedia StockRanks (0–100 percentile composite; equal-weighted Q+V+M): https://www.stockopedia.com/stockranks/ and https://www.stockopedia.com/ratios/stockrank-5378/ — backs Q6.
- Stockopedia advanced screening rules (winsorize means at 3%; prefer medians for small caps): https://www.stockopedia.com/learn/screener/building-advanced-screening-rules-463278/ — backs Q6.
- Stockopedia Stock Report Guide (size groups; Mkt Cap Rank; quintile bands): https://www.stockopedia.com/courses/stock-report-guide/ — backs Q6.

---

## 4. Blockers / Inte gjort

- **clawRxiv preprint (breakeven ~$480M for small-cap momentum)** is a non-peer-reviewed preprint on a non-standard server; the *direction* of the finding (small-cap momentum gross ≫ net) is corroborated by the Medium practitioner autopsy and the SSRN S&P 500 study, but the exact $480M figure should be treated as indicative, not established.
- **ScreenerHero First North liquidity figures (€5–50K/day below €50M mcap)** are from a commercial blog, not an exchange publication; they are consistent with Nasdaq's own whole-market averages (€41.1M/day ÷ ~450 companies ≈ €90K/company/day mean, so the smallest names being far below the mean is plausible), but no independent per-company turnover distribution was found.
- **No authoritative public source was found for a single "uninvestable" liquidity threshold** — the literature converges on the *position-size-relative* rule (≤10% of daily turnover) and spread rules (≤1–2%) rather than an absolute number; the SEK 500K/2M floors in §2 are a synthesis, not a quoted standard.
- **Nordic-specific January-effect evidence** (Swedish tax-year-end is calendar-year, so December tax-loss selling applies) was not found in the searches; the cited January-effect literature is US-based. The mechanism (tax-loss selling + window dressing at calendar year-end) transfers to Sweden, but this is inference, not a cited fact.
- **Earnings-date availability for First North** was only indirectly evidenced (lighter disclosure, no IFRS requirement); no quantitative study of First North earnings-date data coverage was found.
- No application code was written (research-only task, per instructions).