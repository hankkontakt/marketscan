# Segment-Specific Factor Scoring: Small Caps vs Large/Mid Caps — Evidence Review

**Date:** 2026-09-01
**Prepared for:** MarketScan stock-ranking system (0–100 multi-factor score: quality 25%, value 15%, momentum 15%, analyst 15%, insider 10%, catalyst 10%, payout 5%, growth 5%; segments large/mid/small/micro; Nordic + global large caps)
**Decision under review:** Should the score use segment-specific factor weights, segment×sector normalization, liquidity adjustments, and coverage-scaled analyst handling — instead of today's identical weights with only tier thresholds differing (small T1=62 vs large T1=75)?

---

## 1. Task Report — direct answer

**Yes to three of the four proposed changes; no to wholesale segment-specific factor weights.**

1. **Segment×sector normalization: YES — this is the single highest-value change.** Every major institutional provider (MSCI, FTSE Russell, JP Morgan, S&P DJI, RAFI) normalizes factor scores *within* peer groups (sector, industry, country, or size segment) rather than globally, precisely because raw cross-sectional scores are dominated by size/sector composition effects. MSCI's factor indexes use sector-relative z-scores for value and quality; MSCI's style indexes standardize *within each market-cap index*; RAFI constructs factor indices within 12 region×size groups; JP Morgan ranks within ICB industry. Your current global normalization almost certainly lets large-cap sector composition leak into every segment's scores.
2. **Liquidity adjustments: YES — as screens and weight caps, not as a return signal.** Amihud illiquidity is priced, but trading-friction anomalies mostly fail to replicate once microcaps are down-weighted (Hou-Xue-Zhang 2020), and small-cap trades cost ~2× large-cap (Frazzini-Israel-Moskowitz 2018). Institutional practice: liquidity screens (Fidelity, Russell RAFI) + liquidity-constrained weights (JP Morgan, RAFI) + float screens. A 0–100 rank that ignores liquidity will systematically over-rank illiquid microcaps whose scores are noise.
3. **Coverage-scaled analyst handling: YES.** Analyst coverage is strongly correlated with size (Hong-Lim-Stein 2000), dispersion effects are strongest in small stocks (Diether-Malloy-Scherbina 2002), and providers shrink missing/noisy analyst data toward neutral (JP Morgan neutral score 50.5; MSCI missing factor → 0 z-score). An unscaled 15% analyst weight in micro caps is mostly noise.
4. **Segment-specific factor weights: NO as a blanket change — with two evidence-based exceptions.** The institutional norm is *identical factor definitions and weights across size segments*, with differentiation in normalization, liquidity, and implementation (MSCI, FTSE Russell, S&P DJI, JP Morgan, AQR, Dimensional). The evidence supports only two segment-specific weight adjustments: (a) **value is stronger in small caps** (Israel-Moskowitz 2013; Fama-French 2012) — a modest value-weight increase in small/micro is defensible; (b) **quality acts as a junk-filter gate in small/micro** (Asness-Frazzini-Israel-Moskowitz-Pedersen 2018) — the size premium only exists quality-controlled, so in small/micro quality should *gate* (exclude junk) rather than merely carry a weight. Momentum shows no reliable size relation (Israel-Moskowitz 2013), so momentum weight should stay flat.

---

## 2. Evidence by question

### Q1. Do practitioners use separate factor weights or normalization per size bucket?

**Finding: identical factor definitions/weights across size segments; differentiation via normalization, liquidity, weighting constraints, and separate universes.**

| Provider | Practice | Source |
|---|---|---|
| **MSCI** | Factor indexes: Alpha score = winsorized (±3) z-score of weighted factor combination; Value and Quality are **sector-relative z-scores**; Momentum = Barra momentum + analyst sentiment. **Size-segment-specific weight caps**: large cap max weight = parent weight +2% or 10×; mid/small cap = +1% or 5×. Non-target style exposures restricted to ±0.1 std dev; sector weights ±5%. | MSCI Core Multiple-Factor Indexes Methodology |
| **MSCI** | Style (value/growth) indexes: all eight variables **standardized within each individual market-cap index** ("The same style segmentation process is applied independently and consistently across all market capitalization indexes"). | MSCI US Equity Indexes Methodology |
| **MSCI** | FaCS/Barra GEMLT: fundamental descriptors standardized with **country-specific mean but global standard deviation** — explicitly because "using country-specific standard deviations can result in undesirable and unintended instability in the descriptor values, particularly for countries with small numbers of stocks." | MSCI FaCS Methodology |
| **FTSE Russell** | Factor scores: raw value → outlier removal → **z-score → mapped to 0–1 via cumulative normal distribution**. Value uses country-relative sales-to-price; leverage normalized to **regional industry (ICB) median**; "In case there are fewer than three securities in this region and industry no median normalisation is applied." | FTSE Global Factor Index Series Ground Rules + Methodology Overview |
| **JP Morgan** | Factor ranks are **percentile ranks within ICB 5 industry** of the eligible universe; ties broken by liquidity then size. Missing data → **neutral score of 50.5** (volatility needs ≥400 daily observations, momentum ≥200). Liquidity = median daily trading value over 22 days; **liquidity-constrained weights**. | JP Morgan US Single Factor Index Series Ground Rules |
| **RAFI** | Factor indices constructed **within each of 12 region and size groups** (Table 2 of rulebook); value = top 25% by cumulative fundamental weight within group, min 15 stocks; multi-factor = equal 20% sleeves (value/low-vol/quality/momentum/size; EM excludes size, 25% each); **liquidity ratio cap of 4×**. | RAFI Multi-Factor Index Series Rulebook |
| **Dimensional** | Same three premiums (size/value/profitability) in all strategies, but **implementation differs by size segment**: "In large caps, we target the premiums through both exclusions as well as over- and underweights. In small caps, where deviations from market-cap weights would be more costly to implement, we apply only exclusions." | Dimensional, "All Day, Every Day, Multifactor All the Way" (2022) |
| **AQR** | Separate size universes with the same factor definition: AQR Momentum Index (top 1,000 US stocks, top-third momentum) vs AQR Small Cap Momentum Index (ranks 1,001–3,000, top-third momentum); separate small-cap funds (Small Cap Momentum / Small Cap Multi-Style = value+momentum+quality within Russell 2000 range). | AQR Momentum Index Methodology; AQR Small Cap Momentum Style Fund prospectus (SEC) |
| **Morningstar** | Factor Profile: stock-level factor scores **standardized within asset class and region** ("stocks are compared with local peers"); fund-level scores ranked 1–100. Size uses log market cap (Style Box raw size score). | Morningstar Factor Profile Methodology (2019) |
| **S&P DJI** | Quality/Value: z-scores computed **within each index universe** (winsorized, ±4 cap on average z-score); Fidelity Global Quality Value variant: z-scores **within country+sector groups**, capped at 3 std devs, missing metric → 0. Optimized factor indices: sector weights constrained to 75–125% of underlying. | S&P Quality Indices Methodology; Fidelity Global Quality Value Index Methodology; S&P Optimized Factor Indices FAQ |

**Bottom line for Q1:** No major provider runs different *factor weights* per size bucket in index products. They run the same factor definitions with (a) peer-group normalization, (b) size-segment-specific weighting constraints, (c) liquidity screens/caps, and (d) separate universes/funds per size segment. Dimensional is the clearest example of size-segment-specific *implementation*.

### Q2. Does factor efficacy differ by company size? (2015–2026 evidence)

| Factor | Evidence by size | Sources |
|---|---|---|
| **Value** | **Stronger in small caps; weak/insignificant among the largest stocks.** "The value premium decreases with firm size and is weak among the largest stocks" (86 yrs US + 4 international markets). Fama-French (2012): value premia exist in all size groups, stronger as size decreases. | Israel & Moskowitz (2013, JFE); Fama & French (2012) as cited therein |
| **Quality / profitability** | **Stronger in small caps, and quality is the key interaction with size.** Small stocks are disproportionately "junk"; controlling for quality resurrects a monotonic size premium (alpha 5.9%/yr, t=4.89, vs 1.68%, t=1.23 without QMJ). Dimensional: value and profitability premiums among small caps exceed their large-cap counterparts. Verdad (Schatz, via Swedroe 2025): profitability premium loudest in small caps, fades in mega caps. | Asness, Frazzini, Israel, Moskowitz, Pedersen (2018, JFE); Dimensional (2022); Swedroe/Alpha Architect (2025) |
| **Momentum** | **No reliable relation with size** over 86 years (Israel-Moskowitz 2013). Hong-Lim-Stein (2000) found momentum stronger in small/low-coverage stocks, but Israel-Moskowitz show that result is sample-specific (1980–1996). Momentum works in all size groups (Fama-French 2012). Momentum is the most persistent factor in small caps post-1981 (Informed Momentum 2025). | Israel & Moskowitz (2013); Hong, Lim, Stein (2000); Informed Momentum (2025) |
| **Investment** | Conservative-investment (CMA) benefits among small caps; small-cap factor gains from momentum/profitability/investment exposures (Bridgeway 2026). | Bridgeway (2026) |
| **Trading frictions / liquidity anomalies** | **Mostly fail to replicate** once microcaps are mitigated: 65% of 452 anomalies (96% of trading-frictions category) insignificant with NYSE breakpoints + value-weighted returns. Microcaps = 3% of market cap but ~60% of stock count, with the highest cross-sectional dispersion in returns and anomaly variables. | Hou, Xue, Zhang (2020, RFS) |
| **Earnings volatility** | **Sign reverses across size**: small caps with volatile earnings underperform; large caps with volatile earnings show positive excess returns (Verdad, 10,000 global stocks, cap deciles). | Swedroe/Alpha Architect (2025) |

**Bottom line for Q2:** Value and quality/profitability are the factors whose efficacy differs most by size (both stronger in small caps). Momentum is size-neutral. Liquidity/friction signals are largely microcap artifacts. This supports: keep momentum weight flat; modestly raise value weight in small/micro; use quality as a gate in small/micro.

### Q3. Size premium today (SMB evidence, quality-filtered size, current views)

- **Quality-filtered size premium (AQR):** "Size Matters, If You Control Your Junk" (2018, JFE): the size premium's challenges (weak record, January concentration, microcap concentration, weak internationally) "disappear when controlling for the quality, or its inverse junk, of a firm." Quality-controlled size alpha 5.9%/yr (t=4.89) vs 1.68% (t=1.23) uncontrolled; restores a monotonic size-return relation; not concentrated in microcaps; not subsumed by illiquidity. Confirmed by Alquist, Israel, Moskowitz (2018), "Fact, Fiction, and the Size Effect."
- **Skeptical view (Research Affiliates):** Kalesnik & Beck, "Busting the Myth About Size": US size premium 3.4%/yr (1926–2014) driven by 1930s outliers and delisting bias; not statistically significant internationally; no risk-adjusted advantage. But: "The major anomalies are, in fact, stronger in the small-cap sector. Small stocks are more attractive as an alpha pool… exploited by rules-based value and momentum strategies." Hsu & Kalesnik, "Finding Smart Beta in the Factor Zoo": small-cap factor insignificant; value/low-vol/momentum significant.
- **Recent data (Damodaran, Jan 2025):** 1927–2024 small-cap premium = 2.07%/yr value-weighted, 6.69% equal-weighted; **drops to zero for any sample starting 1970**; last 20 years show a large-cap premium of ~4–4.5%/yr. "The small cap premium is not coming back… picking a company based on market cap will be, at best, a neutral strategy."
- **Monetary-policy dependence (Simpson & Grossmann 2024):** size premium present only during monetary easing (0.41%/mo, significant), absent during tightening — with or without quality control.
- **Takeover explanation (Easterwood, Netter, Paye, Stegemoller, JFQA 2024):** M&A news explains virtually all of the US size premium; takeover factor dominates size factor; small-cap quintile ~2.3× more likely to be acquired.
- **Definition matters (Bridgeway 2026):** requiring stocks to have *been* small (1–3 yr lookback) raises SMB from 17bp/mo (insignificant) to 21–28bp/mo (significant); removing fallen-large-caps and IPOs.
- **Current market state (OLZ 2025):** size factor flipped negative ~2018–2024 (Magnificent Seven concentration; 32% of MSCI USA); possible rotation/rebirth beginning late 2024.

**Bottom line for Q3:** The raw size premium is weak-to-dead in recent decades; the *quality-filtered* size premium is alive. For a ranking system this means: do not add a size premium to scores; do use quality to filter junk in small/micro segments; expect size-segment return differences to be regime-dependent (monetary policy, concentration).

### Q4. Cross-sectional normalization: rank vs z-score within size×sector groups; minimum group size

- **z-score is the institutional default** for factor scores: MSCI (winsorized ±3 z-scores, sector-relative for value/quality), S&P DJI (z-scores within index universe, capped ±3/±4), FTSE Russell (z-scores → cumulative-normal 0–1 mapping), JP Morgan (percentile ranks within ICB industry).
- **Rank/percentile is used where robustness to outliers matters**: FTSE Russell maps z-scores through the cumulative normal to a 0–1 score (a percentile transform); JP Morgan uses percentile ranks within industry; Morningstar ranks fund-level scores 1–100. Percentile transforms are more robust than raw z-scores in small, skewed groups.
- **Peer group = sector/industry (and country), not global**: MSCI value/quality sector-relative; JP Morgan ICB-industry percentile ranks; S&P DJI Fidelity variant country+sector groups; FTSE Russell regional-industry medians; RAFI region×size groups.
- **Minimum group size / fallback (published examples):**
  - FTSE Russell: "In case there are fewer than three securities in this region and industry no median normalisation is applied" (leverage ratio).
  - MSCI FaCS/Barra: country-specific *mean* but *global* standard deviation — explicitly to avoid instability for small countries; equal-weighted std dev so large caps don't dominate scale.
  - JP Morgan: missing/insufficient data → neutral score 50.5 (volatility <400 daily obs, momentum <200 obs).
  - MSCI Core MF: missing factor score → 0 (neutral z-score); minimum one factor score required for Alpha.
  - S&P DJI Fidelity variant: missing metric → z-score 0; winsorize to 96th percentile before z-scoring.
- **Size×sector vs size-only:** MSCI style indexes standardize within market-cap index (size segment) but not within sector; MSCI factor indexes standardize within sector (not size segment); RAFI uses region×size groups; JP Morgan uses industry (not size). **The combination (segment×sector) is the most defensible for a system that must be comparable across segments** — it removes both size-composition and sector-composition effects. Practical minimum: ~5–10 names per group before falling back to segment-level mean + global std dev (MSCI FaCS pattern).

### Q5. Liquidity: Amihud illiquidity, ADV screens, bid-ask adjustments, practical thresholds

- **Amihud ILLIQ (2002):** daily |return|/dollar-volume averaged; positive cross-sectional return–illiquidity relation; **effects stronger for small firms**; explains time-variation in the small-firm effect. Revisited (2019): illiquid-minus-liquid (IML) factor premium positive and significant over 63 years, lower but still significant post-2002.
- **Trading costs by size (Frazzini, Israel, Moskowitz 2018, RAPS):** live-trade data ($1.05T, 21 markets): average market impact ~10–11bp for large caps vs **~21bp for small caps** (~2×). Size/value/momentum survive costs at large capacity (break-even sizes $275B/$214B/$56B US); short-term reversal does not. Implication: small-cap factor signals with high turnover are disproportionately expensive.
- **Microcap caveat (Hou-Xue-Zhang 2020):** 96% of trading-friction anomalies fail with NYSE breakpoints + value-weighted returns; "anomalies in microcaps are more apparent than real" due to trading costs.
- **Practical screens/thresholds used by providers:**
  - **Fidelity Factor Indices:** exclude bottom quintile by "days to trade $10 million"; exclude <15% free float; minimum 6-month traded volume $25M; float-adjusted market cap >$75M (US) / >$100M (global).
  - **Russell RAFI:** liquidity screen captures 95% of FTSE All-World liquidity; cutoff = 2 std devs below the mean of the lognormal distribution of 12-month average daily dollar trading value (ADDTV); non-All-World names get half the cutoff.
  - **JP Morgan:** liquidity = median daily trading value over 22 days; maximum constituent weight and weight-change limits are functions of liquidity (in days); industry target weights capped by liquidity limits.
  - **RAFI:** liquidity ratio (fundamental weight / liquidity weight) capped at 4×; 30/90-day median daily traded value; <30 days history → fundamental value zero.
  - **AQR:** momentum index universes "screened using certain liquidity and other criteria"; float-adjusted market cap weighting underweights low-float names.
- **Bid-ask/spread:** Amihud & Mendelson (1986) quoted-spread premium (as reviewed in Amihud 2002); spread-based measures are data-hungry — Amihud ILLIQ was designed precisely as a daily-data proxy for price impact where microstructure data are unavailable (relevant for Nordic small caps).

**Bottom line for Q5:** Use liquidity as (a) an eligibility screen per segment (ADV/float/days-to-trade), (b) a weight or score cap (liquidity-constrained), and (c) a data-quality gate (insufficient trading history → neutral). Do not add illiquidity as a *return* factor in the score — its premium is concentrated in exactly the names you can't trade, and friction anomalies fail replication.

### Q6. Analyst coverage in small caps: coverage as signal, confidence scaling, dispersion

- **Coverage is strongly correlated with size** (Bhushan 1989, as cited in Hong-Lim-Stein 2000) — so raw analyst scores in small caps are systematically sparse and must be size-adjusted (HLS use *residual* coverage after regressing on size).
- **Coverage and momentum (Hong, Lim, Stein 2000, JF):** momentum profits ~60% greater in the lowest-coverage tercile than the highest; the coverage effect is **greatest among small stocks**; effect concentrated in past losers (bad news diffuses slowly). Israel-Moskowitz (2013) note this is sample-specific but the coverage-momentum interaction is a real, if second-order, effect.
- **Dispersion (Diether, Malloy, Scherbina 2002, JF):** high-dispersion quintile underperforms low-dispersion by **9.48%/yr**; effect **strongest in small stocks** (16.4%/yr in the smallest quintile) and in past losers; consistent with Miller (1977) differences-of-opinion (prices reflect optimism), not risk. Dispersion = std dev of forecasts / |mean forecast|; mean forecast zero → highest dispersion bucket.
- **Provider handling of sparse analyst data:**
  - **MSCI Core MF:** Momentum factor = average of Barra momentum and Analyst Sentiment; "If Analyst Sentiment score is missing, then the Momentum factor score is the Barra Momentum factor score and vice-versa." Missing factor score → 0 z-score.
  - **JP Morgan:** insufficient observations → neutral score 50.5 (not exclusion).
  - **S&P DJI:** missing metric → z-score 0.
- **Coverage as a signal in its own right:** low coverage = less efficient pricing = larger alpha pool (RAFI: "small stocks… receive considerably less attention from sell-side analysts. Consequently, small stocks are more likely to be mispriced"); but this argues for *stronger* value/momentum signals in small caps, not for trusting sparse analyst consensus numbers.

**Bottom line for Q6:** Scale the analyst factor by coverage confidence (shrink toward neutral below ~2–3 analysts), penalize high dispersion (it predicts low returns, especially in small caps), and treat analyst sentiment as a momentum *component* (MSCI pattern) rather than a standalone 15% pillar in micro caps where coverage is near zero.

---

## 3. Recommendations (concrete, for the 0–100 rank over large/mid/small/micro; Nordic + global large caps)

**R1. Keep factor definitions and base weights identical across segments** (institutional norm; avoids overfitting and keeps scores comparable). Only two evidence-based weight deltas:
- **Value: +2–3 pts in small/micro** (shift from growth or payout), because the value premium is concentrated in small caps (Israel-Moskowitz 2013; Fama-French 2012).
- **Quality: keep 25% but add a junk-gate in small/micro** — e.g., floor the quality sub-score at a minimum before a stock can reach T1 in small/micro (AQR 2018: the size premium only exists quality-controlled). This is a gate, not a weight change.
- Momentum weight flat (size-neutral evidence). Analyst weight flat in large/mid but *confidence-scaled* (R4) in small/micro.

**R2. Normalize within segment×sector (GICS sector or ICB industry), not globally.**
- Value, quality, growth, payout: winsorized z-score (cap ±3) within segment×sector; map to 0–100 via percentile (cumulative-normal or rank) for robustness in small groups (FTSE Russell / JP Morgan pattern).
- Momentum: normalize within segment only (price-based factors are standardized globally/size-segment in MSCI/Barra, not sector-relative).
- **Fallback rule:** if segment×sector group < ~5–10 names, use segment-level mean + global std dev (MSCI FaCS pattern: local mean, global scale); if < 3 names, skip sector adjustment entirely (FTSE Russell pattern).
- This directly fixes the current design's biggest weakness: global normalization lets large-cap sector composition distort small-cap scores.

**R3. Add liquidity as screen + cap, per segment.**
- **Eligibility screens (micro/small):** minimum float (≥15% free float), minimum 6-month traded value (Fidelity: $25M US-scale; scale down for Nordic micro), and exclude the bottom quintile by "days to trade $10M" (Fidelity) or an ADDTV cutoff (Russell RAFI: 2 std devs below lognormal mean of the segment's ADDTV distribution).
- **Score/weight cap:** cap the contribution of any name whose liquidity ratio (score weight / liquidity weight) exceeds ~4× (RAFI pattern) or cap position size by days-to-trade (JP Morgan pattern).
- **Do not** add Amihud ILLIQ as a return factor in the score (friction anomalies fail replication; premium concentrated in untradeable names — HXZ 2020; Amihud 2002).
- Expect small-cap implementation cost ~2× large-cap (FIM 2018) — prefer lower-turnover signals in small/micro.

**R4. Coverage-scaled analyst handling.**
- **Confidence scaling:** shrink the analyst sub-score toward neutral (50th percentile) as coverage falls below ~3 analysts; below 1 analyst, set analyst contribution to neutral (JP Morgan 50.5 / MSCI 0-z-score pattern). Never let a single analyst's estimate carry full 15% weight.
- **Dispersion penalty:** high forecast dispersion (std/|mean|) → cap or reduce the analyst sub-score (DMS 2002: high dispersion predicts 9.5%/yr underperformance, strongest in small caps).
- **Momentum integration:** blend analyst sentiment into the momentum factor (MSCI pattern) rather than keeping it a fully independent pillar in small/micro.
- **Coverage as a signal:** in small/micro, low coverage + positive momentum is a *stronger* signal (HLS 2000) — optionally add a small momentum boost for low-coverage names.

**R5. Keep segment-specific tier thresholds, and justify them by distribution, not efficacy.**
- Small T1=62 vs large T1=75 is consistent with the evidence that small-cap score distributions are noisier and more dispersed (HXZ 2020: microcaps have the highest cross-sectional dispersion in returns and anomaly variables). Document the thresholds as distributional (percentile-based) rather than efficacy-based.
- Consider a **micro-cap data-quality gate**: exclude names below liquidity/float/price thresholds from ranking entirely (HXZ: microcaps are 60% of names, 3% of market cap, anomalies "more apparent than real").

**R6. Missing-data policy (uniform across segments):** missing metric → neutral score (0 z-score / 50th percentile), never exclusion; require minimum history (e.g., ≥200 daily observations for momentum, ≥400 for volatility-type inputs — JP Morgan pattern); require ≥1 non-missing factor for a score (MSCI pattern).

---

## 4. Verification Receipts

All URLs accessed 2026-09-01.

| # | Source | URL | Backs claims |
|---|---|---|---|
| 1 | Asness, Frazzini, Israel, Moskowitz, Pedersen (2018), "Size Matters, If You Control Your Junk," JFE | https://www.sciencedirect.com/science/article/pii/S0304405X18301326 ; https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2553889 ; https://pdfs.semanticscholar.org/00c7/19c3a6c20bc17d945e7d1799566ac972b648.pdf | Q2 quality×size; Q3 quality-filtered size premium (5.9% vs 1.68% alpha); junk filter |
| 2 | Israel & Moskowitz (2013), "The role of shorting, firm size, and time on market anomalies," JFE 108(2) | https://www.sciencedirect.com/science/article/abs/pii/S0304405X12002401 ; https://www.aqr.com/Insights/Research/Journal-Article/The-Role-of-Shorting-Firm-Size-and-Time-on-Market-Anomalies | Q2 value weaker in large caps; momentum size-neutral; Fama-French 2012 cross-ref |
| 3 | Hou, Xue, Zhang (2020), "Replicating Anomalies," RFS 33(5) | https://ideas.repec.org/a/oup/rfinst/v33y2020i5p2019-2133..html ; https://www.nber.org/papers/w23394 | Q2 friction anomalies fail; Q3/Q5 microcaps 3%/60%; dispersion by size |
| 4 | Frazzini, Israel, Moskowitz (2018), "Trading Costs of Asset Pricing Anomalies," RAPS | https://pages.stern.nyu.edu/~afrazzin/pdf/Trading%20Cost%20of%20Asset%20Pricing%20Anomalies%20-%20Frazzini,%20Israel%20and%20Moskowitz.pdf ; https://www.aqr.com/Insights/Research/Working-Paper/Trading-Costs-of-Asset-Pricing-Anomalies | Q5 small-cap 21bp vs large 10–11bp impact; break-even capacities |
| 5 | Amihud (2002), "Illiquidity and stock returns," JFM 5(1) | https://www.cis.upenn.edu/~mkearns/finread/amihud.pdf ; https://ideas.repec.org/a/eee/finmar/v5y2002i1p31-56.html | Q5 ILLIQ definition; illiquidity premium stronger for small firms |
| 6 | Amihud (2019), "Illiquidity and Stock Returns: A Revisit" | https://doi.org/10.1561/104.00000073 | Q5 IML factor persists |
| 7 | Hong, Lim, Stein (2000), "Bad News Travels Slowly," JF 55(1) | https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00206 ; http://stat.wharton.upenn.edu/~steele/Courses/434/434Context/Momentum/BadNewsJF2000.pdf | Q6 coverage×momentum; coverage-size correlation; 60% momentum differential |
| 8 | Diether, Malloy, Scherbina (2002), "Differences of Opinion and the Cross Section of Stock Returns," JF 57(5) | https://diether.org/papers/dms.pdf ; https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00490 | Q6 dispersion 9.48%/yr; strongest in small stocks (16.4%) |
| 9 | MSCI Core Multiple-Factor Indexes Methodology | https://www.msci.com/documents/10199/ecc2cfae-0766-fa4f-8ce5-0fc3028272f3 | Q1/Q4 sector-relative z-scores ±3; analyst sentiment blend; missing→0; size-segment weight caps |
| 10 | MSCI US Equity Indexes Methodology (2023) | https://www.msci.com/indexes/documents/methodology/1_MSCI_US_Equity_Indexes_Methodology_20230511.pdf | Q1/Q4 standardization within each market-cap index |
| 11 | MSCI FaCS Methodology (Bonne, Roisenberg, Subramanian, Melas) | https://www.msci.com/downloads/web/msci-com/research-and-insights/blog-post/are-growth-and-value-indexes-still-in-style/MSCI-FaCS-Methodology.pdf | Q4 country mean + global std dev; small-country instability; equal-weighted std dev |
| 12 | MSCI, "Foundations of Factor Investing" (2013) | https://www.msci.com/documents/1296102/1336482/Foundations_of_Factor_Investing.pdf/004e02ad-6f98-4730-90e0-ea14515ff3dc | Q1 six-factor framework; factor indexes as building blocks |
| 13 | MSCI USA Small Cap Sector Neutral Quality Index | https://www.msci.com/indexes/index/763540/msci-usa-small-cap-sector-neutral-quality-index | Q1 small-cap sector-neutral factor index exists as product |
| 14 | FTSE Global Factor Index Series Ground Rules | https://www.lseg.com/content/dam/ftse-russell/en_us/documents/ground-rules/ftse-global-factor-index-series-ground-rules.pdf | Q4 regional-industry medians; <3 securities → no normalization; country-relative value; neutral z-score for negative assets |
| 15 | FTSE Global Factor Index Series Methodology Overview | https://www.lseg.com/content/dam/ftse-russell/en_us/documents/other/ftse-global-factor-index-series-methodology-overview.pdf | Q4 z-score → cumulative normal 0–1 mapping |
| 16 | JP Morgan US Single Factor Index Series Ground Rules | https://www.lseg.com/content/dam/ftse-russell/en_us/documents/ground-rules/jp-morgan-us-single-factor-index-series-ground-rules.pdf | Q4 ICB-industry percentile ranks; neutral 50.5; Q5 liquidity = 22-day median trading value; liquidity-constrained weights; Q6 min observations |
| 17 | Russell RAFI Index Series Ground Rules | https://www.lseg.com/content/dam/ftse-russell/en_us/documents/ground-rules/russell-rafi-index-series-construction-and-methodology.pdf | Q5 ADDTV lognormal cutoff; 95% liquidity capture |
| 18 | RAFI Multi-Factor Index Series Rulebook | https://www.rafi.com/content/dam/rafi/documents/index-documents/rulebooks/rulebook-rafi-multi-factor-index-series.pdf | Q1 12 region×size groups; min 15 stocks; equal 20% factor sleeves; Q5 liquidity ratio cap 4× |
| 19 | Kalesnik & Beck, "Busting the Myth About Size" (RAFI) | https://www.researchaffiliates.com/content/dam/ra/publications/pdf/284-busting-the-myth-about-size.pdf | Q3 skeptical size view; delisting bias; anomalies stronger in small caps |
| 20 | Hsu & Kalesnik, "Finding Smart Beta in the Factor Zoo" (RAFI) | https://www.researchaffiliates.com/content/dam/ra/publications/pdf/223-finding-smart-beta-in-the-factor-zoo.pdf | Q3 size insignificant; value/low-vol/momentum significant |
| 21 | Dimensional, "All Day, Every Day, Multifactor All the Way" (2022) | https://www.dimensional.com/be-en/insights/all-day-every-day-multifactor-all-the-way | Q1 size-segment implementation (exclusions only in small caps); Q2 premiums larger in small caps |
| 22 | Morningstar Factor Profile Methodology (2019) | https://assets.contentstack.io/v3/assets/blt4eb669caa7dc65b2/bltf09d73b4a44d9f14/61b8e525ad89d90d95a0a5c4/Factor_Profile_Methodology.pdf | Q1 standardization within asset class+region; 7 factors; 1–100 ranking |
| 23 | S&P DJI Quality Indices Methodology | https://www.spglobal.com/spdji/pt/documents/methodologies/methodology-sp-quality-indices.pdf | Q4 z-scores within index universe; ±4 winsorization; missing→average of remaining |
| 24 | S&P DJI, Fidelity Global Quality Value Index Methodology | https://www.spglobal.com/spdji/en/documents/methodologies/Fidelity%20Global%20Quality%20Value%20Index%20Methodology.pdf | Q4 country+sector z-scores, cap 3; missing→0; size-adjusted value score (60/40) |
| 25 | S&P Optimized Factor Indices FAQ | https://www.spglobal.com/spdji/en/documents/additional-material/faq-sp-optimized-factor-indices.pdf | Q1 sector constraints 75–125%; balanced active exposures ±2.5% |
| 26 | Fidelity Factor and Income Indices Methodology | https://institutional.fidelity.com/app/proxy/content?literatureURL=%2F9905790.PDF | Q5 days-to-trade-$10M bottom quintile; 15% float; $25M 6-month volume; $75M/$100M float cap |
| 27 | AQR Momentum Index Methodology | https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/AQR-Momentum-Index-Methodology.pdf | Q1 separate size universes (top 1,000 vs 1,001–3,000); liquidity screens |
| 28 | AQR Small Cap Momentum Style Fund prospectus (SEC 497k) | https://www.sec.gov/Archives/edgar/data/1444822/000119312526027547/d178309d497k.htm | Q1 small-cap fund = Russell 2000 range; float-adjusted weighting |
| 29 | AQR, "The Small Firm Effect Is Real and Its Spectacular" (Cliff's Perspective) | https://www.aqr.com/-/media/AQR/Documents/Insights/Perspectives/The-Small-Firm-Effect-Is-Real-and-Its-Spectacular.pdf | Q3 quality-controlled size premium narrative |
| 30 | Alquist, Israel, Moskowitz (2018), "Fact, Fiction, and the Size Effect" | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3177539 | Q3 size effect clarification |
| 31 | Swedroe (2025), "Where Factors Speak Loudest: Why Size Matters in Factor Investing," Alpha Architect | https://alphaarchitect.com/size-factor/ | Q2 Verdad size-decile factor analysis; earnings-volatility sign reversal; monetary-policy link |
| 32 | Simpson & Grossmann (2024), "The resurrected size effect still sleeps in the (monetary) winter" | https://www.sciencedirect.com/science/article/abs/pii/S1057521924000139 | Q3 size premium only in easing periods |
| 33 | Damodaran (2025), "Data Update 3 for 2025" | https://aswathdamodaran.substack.com/p/data-update-3-for-2025-the-times | Q3 1927–2024 premium 2.07% VW/6.69% EW; zero from 1970; large-cap premium last 20 yrs |
| 34 | Swedroe (2024), "What Happened to the Size Premium?", Morningstar | https://www.morningstar.com/alternative-investments/what-happened-size-premium | Q3 takeover factor (Easterwood et al., JFQA 2024) explains size premium |
| 35 | OLZ (2025), "Death (and Rebirth?) of the Size Factor in the USA" | https://olz.ch/en/insights/death-and-rebirth-of-the-size-factor-in-the-usa | Q3 size factor flipped ~2018; Mag-7 concentration |
| 36 | Bridgeway (2026), "I Know What You Did Last Summer" | https://bridgeway.com/perspectives/i-know-what-you-did-last-summer/ | Q3 persistent-small definition; SMB 17→21–28bp/mo; Q2 CMA/momentum in small caps |
| 37 | Informed Momentum (2025), "Dude, Where's My Small Cap Premium?" | https://www.informedmomentum.com/wp-content/uploads/2025/01/IMC-Dude-Wheres-My-Small-Cap-Premium.pdf | Q2/Q3 momentum overlay in small caps; post-1981 size effect negative |
| 38 | Russell Investments (2024), "Is small cap exposure still a good idea?" | https://russellinvestments.com/content/ri/us/en/insights/russell-research/2024/06/-is-small-cap-exposure-still-a-good-idea-asking-for-a-friend--.html | Q3 SMB/HML context |

**Double-sourced critical claims:**
- Value premium decreases with size / weak in largest stocks: Israel & Moskowitz (2013) + Fama & French (2012, cited therein) — receipts #2.
- Quality-filtered size premium: Asness et al. (2018, JFE) + Alquist-Israel-Moskowitz (2018) + AQR Cliff's Perspective — receipts #1, #29, #30.
- Microcaps inflate anomalies / friction anomalies fail: Hou-Xue-Zhang (2020) + Fama-French (2008, cited therein) — receipt #3.
- Small-cap trading costs ~2× large-cap: Frazzini-Israel-Moskowitz (2018) — receipt #4 (single primary source; corroborated by Alpha Architect summary of the same paper).
- Sector/industry-relative normalization is institutional standard: MSCI Core MF + JP Morgan ground rules + S&P DJI Fidelity variant — receipts #9, #16, #24.

---

## 5. Blockers / Inte gjort

- **Exact minimum group sizes** for segment×sector normalization are rarely published by providers. Only FTSE Russell publishes a hard number (<3 securities → no median normalization). MSCI's FaCS solution (local mean, global std dev) is the documented fallback pattern; the 5–10 name threshold in R2 is a recommendation, not a sourced standard.
- **FTSE Russell's detailed factor-index ground rules** were located (receipt #14) but the full z-score procedure (rule 5.2) could not be fully extracted from the search snippet; the overview PDF (receipt #15) confirms the z-score → cumulative-normal 0–1 pipeline. If exact FTSE z-score mechanics matter, fetch the full ground-rules PDF.
- **Nordic-specific evidence** (OMX small-cap factor efficacy, Nordic liquidity thresholds) was not searched — the evidence base is US/global. Nordic small caps are thinner than US small caps, so the liquidity thresholds in R3 should be calibrated locally, not copied from US providers.
- **Contradicting sources flagged:** Hong-Lim-Stein (2000) vs Israel-Moskowitz (2013) disagree on whether momentum is stronger in small caps (HLS: yes, sample 1980–1996; I&M: no reliable relation over 86 years). RAFI (Kalesnik & Beck) vs AQR (Asness et al.) disagree on whether a size premium exists at all (RAFI: delisting-bias artifact; AQR: real once quality-controlled). Both pairs are presented with their respective evidence; the recommendations are robust to either view (no size premium is added to scores; quality gating is recommended regardless).
- **Morningstar Factor Profile** community page returned empty; the official methodology PDF (receipt #22) was used instead.