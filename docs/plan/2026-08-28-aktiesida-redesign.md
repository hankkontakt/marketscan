# Aktiesida-redesign 2026-08-28

## Bakgrund

När användaren klickar på en aktie i "Upptäck" landar de på `/aktie/[ticker]`.
Sidan har tre vyvarianter baserat på erfarenhetsnivå (nybörjare/intermediate/expert).
Nybörjarvyn (default) visade bara: VerdictCard → AI-förklaring → CTA — ingen prishistorik,
inga synliga mätetal, ingen bolagsprofil, inga nyheter. Användaren upplever sidan som
"för svag på info utöver AI-grejerna" och "väldigt AI-gjord".

## Vad som finns idag (kartläggning 2026-08-28)

- `apps/web/app/(app)/aktie/[ticker]/StockView.tsx` — hela sidan, tre grep-nivåer:
  - `BeginnerOnly` (L68-74): VerdictCard + ExplainSection + BeginnerCTA
  - `NonExpertOnly` (L77-157): renderar ENDAST när `level === "intermediate"` (L79)
  - `ExpertOnly` (L160-242): VerdictHeader + 6 flikar
- `components/charts/PriceChart.tsx` — färdig ljusstake-chart (volym, MA50/MA200, 1M-3M-6M-1Å-MAX) — används i `OverviewTab`.
- `OverviewTab` (StockView L249-368): chart + nyckeltal (dl) + CompanyProfileCard — komplett Översikt.
- `RapporterTab` (L697-875): kvartalsrapporter, tillväxt, nyheter, nyckeltal.
- `AITab` (L879-889): ExplainSection + EarningsMemoCard + AnalysCommittee.
- `components/stock/VerdictCard.tsx`: emoji-betyg (🌟✅👍🤔⚠️ L29-35), hårdkodade
  färger (L18-27, 48-59, 266), `bg-white` reason-cards (L250) — bryter design-tokens.
- `components/stock/BeginnerCTA.tsx`: inline-hex `#f0fdf4`/`#bbf7d0` (L22-25) + 🎯.
- Design-tokens i `apps/web/app/globals.css`: `--color-bg-surface`, `--color-border`,
  `--color-accent`, `--color-up/-soft`, `--color-warn/-soft` etc. Mjuk känsla =
  `rounded-xl border bg-[var(--color-bg-surface)] border-[var(--color-border)]` +
  Inter + `--color-text-secondary`-rubriker.
- Nivåväxling finns bara i Inställningar (`components/providers/ExperienceProvider.tsx.setLevel`).

## AI-kostnad (fråga "vad kostar AI-förklaringen per klick")

- Modell: `deepseek-chat` (`apps/api/core/config.py` L23) → V4-Flash non-thinking.
- Per call: ~400 input / ~450-500 output tokens, max_tokens=500, temp 0.3
  (`ai.py` L636, `deepseek_client.py`).
- Pricing aug 2026 (V4-Flash): off-peak $0.22 in / $0.66 out; peak $0.44 / $1.32 per M.
  → **~$0.0004–0.0008 per call (~0,4–0,9 öre SEK)**.
- **Cache: `explain:{ticker}:beginner:{dagens datum}`** i Supabase `ai_cache` (24h).
  → 1 LLM-call per unik ticker per dag; alla efterföljande klick samma dag kostar ~0.
- Följdfrågor: inte cachade (~0,5 öre/fråga, 20/min limit).
- Micro-lektioner: statisk dict — 0 kr. Analyskommittén: 5 calls/ticker/dag (~$0.003, cachad).
- **Slutsats: försumbar kostnad (~1–3 USD/månad vid normal trafik). Cachen gör jobbet.**
- Risk att flagga: `deepseek-chat`-aliaset pensionshotades juli 2026 — byt till
  `deepseek-v4-flash` explicit i `config.py` (utanför sidans scope).

## Löst designbeslut (godkänt av användaren, alternativ A)

1. **Nivåväxlare direkt på sidan** — ny komponent `components/stock/LevelSwitcher.tsx`:
   pill-chips "Enkelt · Mellan · Avancerat" (mönster från `SegmentToggle`),
   använder `useExperience().setLevel`. Placerad i sidhuvudet på alla nivåer.
2. **Nybörjare får samma tab-struktur som mellanläget** (Översikt / Rapporter / AI):
   Översikt = PriceChart + synliga nyckeltal + CompanyProfileCard (+ BeginnerCTA sist
   endast för nybörjare); Rapporter = (mellanlägets befintliga innehåll); AI = VerdictCard
   + ExplainSection. Startvyn blir data, inte AI.
3. **VerdictCard restylas**: emoji → lucide-ikoner; hårdkodade färger → `--color-*`-tokens;
   signal-badge → `signalClass/signalLabel` (lib/format); reason-cards `bg-white` →
   `bg-[var(--color-bg-elevated)]`; risk-box → `--color-warn-soft`.
4. **BeginnerCTA restylas**: inline-hex → `bg-[var(--color-up-soft)]`-tokenkort; knapp accent.
5. **Expert-vyn orörd** (innehållsmässigt).

## Uppgifter

| # | Fil | Ändring |
|---|---|---|
| T1 | `components/stock/LevelSwitcher.tsx` | NY. Pill-switcher Enkelt/Mellan/Avancerat via `setLevel`. |
| T2 | `components/stock/VerdictCard.tsx` | Restyla till tokens; bort emoji/hårdkodade färger. |
| T3 | `components/stock/BeginnerCTA.tsx` | Restyla till tokens. |
| T4 | `app/(app)/aktie/[ticker]/StockView.tsx` | NonExpertOnly-bloocket renderar för BÅDE nybörjare och intermediate (ta bort L79-villkoret); BeginnerOnly-bloocket tas bort; LevelSwitcher i båda header-varianterna; BeginnerCTA sist i nybörjar-Översikt. |

## Acceptance criteria

- Nybörjare som landar på `/aktie/AAPL` ser: header (namn/kurs/förändring/signal-badge) +
  flikar Översikt/Rapporter/AI; Översikt visar chart + nyckeltal + (om tillgänglig) bolagsprofil.
- Inga emojis eller inline-hex-färger kvar i de tre berörda komponenterna.
- Mörkt läge: alla nya/restylade ytor använder tokens (inga `bg-white`, inga `#f0fdf4`).
- Nivåväxlaren fungerar: klick på "Avancerat" byter varv direkt (persistens via befintlig API).
- `npx tsc --noEmit` grönt i apps/web; befintliga tester gröna.

## Boundaries / ej göra

- Ej röra expert-vyns innehåll, ej röra api/backend, ej röra PriceChart-komponenten,
  ej ta bort AI-funktionaliteten (AI-tab finns kvar), ej röra cache/kostnad (redan OK).
- Notera i rapporten: `DEEPSEEK_MODEL`-bytesrekommendation (står utanför sidans scope).
