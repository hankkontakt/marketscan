# Spec 07 — #10 Executive Dashboard (vidareutveckla Hem)

> **Repo:** marketscan (frontend endast). **Insats:** S. **Inget nytt backend.**
> **Skriven för:** DeepSeek v4-flash. Läs `docs/plan/00_MASTER_PLAN.md §6` först (konventioner:
> CSS-variabler, `npx tsc --noEmit` grönt, React Query-hooks). Avvik inte.

## DEL 0 — Designprincip (gäller hela bygget): undvik "score-blur"
Slå INTE ihop alla system till en siffra. Varje system är en egen lins:
- **Totalbetyg** (0–100) = kvalitet → kvalitetsmärke/tröskel.
- **ml_rank** (percentil 0–100) = sannolikhet slå index → **sortera/diskriminera på denna**.
- **MEWS** = mångdubblar-special (flaggar få). **Insiderkluster/memo** = diskreta badges.
- **Regim** = kontext.
→ I dashboarden: sortera topplistor på `ml_rank`, visa Totalbetyg som märke, övriga som strips/badges.

## Mål
Gör startsidan (`daglig-briefing`) till ett personligt nav: lägg till watchlist-signaler,
topp-MEWS, riskmätare och regim-gauge ovanpå befintlig hero + stat-chips.

## Återanvänd (exakt)
- Sida: `apps/web/app/(app)/daglig-briefing/DagligBriefingView.tsx` (befintlig hero + stat-chips + grid; behåll dem).
- Hooks: `useWatchlist()`, `useMangdubblare()` (mews_*-fält), `useRiskProfile()` (`profile`, `target_volatility`), `useRiskAnalytics()` (årlig vol), `useMacroRegime()` (`regime`, `label`, `color`), `useScoreMovers(days,direction,limit)`.
- Komponenter: `components/charts/ScoreSparkline.tsx`, `components/ui/MetricCard.tsx`, `components/ui/InfoTooltip.tsx`. MEWS-faktorstaplar finns i `app/(app)/mangdubblare/MangdubblareView.tsx` (återanvänd mönstret).
- Färger via `var(--color-...)` (aldrig hex).

## Steg
1. **`apps/web/components/widgets/RegimeGauge.tsx` (NY)** — halvcirkel-gauge.
   - Props: `{ regime: string; label: string; color: string }`. Data via `useMacroRegime()` i en wrapper, eller ta props.
   - SVG-halvcirkel; nålvinkel: `BJÖRN=−60°`, `NEUTRAL=0°`, `TJUR=+60°` (default 0 vid okänt).
   - Bågfärg: `green→var(--color-up)`, `red→var(--color-down)`, annars `var(--color-text-muted)`.
2. **`apps/web/components/widgets/RiskGauge.tsx` (NY)** — portföljvol vs målvol.
   - Props: `{ currentVol: number|null; targetVol: number|null; profileLabel: string|null }`.
   - Data: `useRiskAnalytics()` (current annual vol) + `useRiskProfile()` (`target_volatility`, `profile`).
   - Visa stapel med markör vid `targetVol`; text t.ex. "Din vol 14% vs mål 12% (Balanserad)".
   - Om `currentVol` eller `targetVol` är null → visa "Gör risktestet" + länk `/installningar`.
3. **`apps/web/components/widgets/WatchlistStrip.tsx` (NY)** — bevakade aktier.
   - Data: `useWatchlist()` + `useScoreMovers(7, "up", 50)` (för att hitta rörelser).
   - Rad per ticker: ticker, namn, signal-badge, Totalbetyg (märke), `ScoreSparkline`, ml_rank-indikator.
   - **Sortera fallande på `ml_rank`** (DEL 0). Lyft de med ny STARK / score-rörelse via liten "NY"-badge.
   - Länk `/aktie/{ticker}`. Tom watchlist → hjälptext "Bevaka aktier för att se signaler här".
4. **`apps/web/components/widgets/MewsStrip.tsx` (NY)** — mångdubblar-kandidater.
   - Data: `useMangdubblare()`, ta topp 3–5 efter `mews_score` där `mews_flag === true`.
   - Per kort: ticker, `mews_score`, mini-staplar för de 6 mews-faktorerna (`mews_fcf_yield`, `mews_small_size`, `mews_low_ps`, `mews_operating_leverage`, `mews_revenue_accel`, `mews_clean_accruals`). Länk `/mangdubblare`.
5. **Uppdatera `DagligBriefingView.tsx`** — montera widgetarna under hero/stat-chips:
   - Rad 1 (ny): `WatchlistStrip` (vänster, ~3/5) + kolumn med `RegimeGauge` ovanpå `RiskGauge` (höger, ~2/5).
   - Rad 2 (ny): `MewsStrip` (full bredd).
   - Behåll befintliga sektioner (Toppaktier/Insider/Sektorer); ändra deras topplistor till att sortera på `ml_rank` om fältet finns i datan.

## Acceptanstest
- `cd apps/web && npx tsc --noEmit` → inga fel.
- Hem visar alla 4 widgetar med riktig data. Tom portfölj/watchlist → graciös fallback (ingen krasch, hjälptext).
- Watchlist-strip och topplistor sorteras på `ml_rank` (ordningen skiljer sig synligt från Totalbetyg-sortering).

## Definition of Done
- [ ] 4 widget-filer skapade och monterade i `DagligBriefingView.tsx`.
- [ ] `npx tsc --noEmit` grönt. [ ] Fallbacks för tom data. [ ] Sortering på ml_rank.
- [ ] `docs/SYSTEM_AI.md` uppdaterad.
