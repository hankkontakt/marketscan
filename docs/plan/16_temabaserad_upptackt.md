# Spec 16 — M2 Temabaserad Upptäckt (Kuraterade kollektioner)

> **Skrivet: 2026-06-10. Beräknad insats: M (5–7h).**
> **Skrivet för:** DeepSeek v4-flash. **Läs HELA spec 14 + spec 13** innan du rör kod.
> **Bygger på:** `useScreener()`, `ScanParams`-typen, `ScanRow`-typen,
> `ResultTable`, `lib/format.ts`, spec 14 (FeedbackWidget).

---

## 0. Varför teman istället för screener?

En nybörjare kan inte bygga ett filter. Hon vet inte vad "P/E < 15" betyder.
Teman ersätter inte scannern — de är ett **alternativt ingångssätt** för den
som vill upptäcka aktier utan att förstå finansiella termer.

Teman är **förhandsgranskade, kuraterade** samlingar. Varje tema:
- Har ett mänskligt namn och en emoji
- Visar en enkel beskrivning på svenska
- Visar en risknivå (Låg / Medel / Högre)
- Visar 5 förhandsgranskade aktier med mini-omdömen
- Länkar vidare till aktiesidan (som nu har omdömeskort från spec 14)

**Dedikerad sida:** `/upptack` — en egen route, synlig i menyn för alla nivåer.

---

## 1. Delsteg A — Temadefinitioner

**Fil:** `apps/web/lib/themes.ts` — kopiera EXAKT:

```ts
import type { ScanParams } from "@/lib/api";

export interface ThemeDefinition {
  id: string;
  label: string;
  emoji: string;
  description: string;
  riskLabel: string;          // "Låg risk", "Medel risk", "Högre risk"
  riskExplanation: string;    // Förklarar VARFÖR risknivån
  params: ScanParams;
  limit: number;              // Hur många aktier att visa
  sortBy: string;             // t.ex. "score_total", "dividend_yield", "ml_rank"
}

/**
 * Kuraterade teman för nybörjarupptäckt.
 * Varje tema är ett ScanParams-objekt — återanvänder screener-API:t.
 * 
 * NÄR DU LÄGGER TILL ETT TEMA:
 * 1. Lägg objektet i arrayen nedan
 * 2. Kontrollera att params fungerar mot /api/scan (testa med curl)
 * 3. Uppdatera riskLabel/riskExplanation så de är ärliga
 */
export const THEMES: ThemeDefinition[] = [
  {
    id: "stable-large",
    label: "Stabila svenska storbolag",
    emoji: "🏰",
    description:
      "Stora, etablerade bolag med stark ekonomi. De svänger mindre än småbolag " +
      "och många har delat ut pengar i åratal. En lugn start.",
    riskLabel: "Låg risk",
    riskExplanation:
      "Storbolag är generellt stabilare — de har beprövade affärsmodeller, " +
      "spridda intäktskällor och klarar sämre tider bättre än småbolag. " +
      "Ingen aktie är riskfri, men dessa hör till de tryggare på börsen.",
    params: {
      segments: ["large_cap"],
      score_min: 55,
      piotroski_min: 5,
      sort_by: "score_total",
    },
    limit: 5,
    sortBy: "score_total",
  },
  {
    id: "dividend-reliable",
    label: "Företag som delar ut pengar varje år",
    emoji: "💎",
    description:
      "Bolag med en historia av att ge tillbaka pengar till aktieägarna " +
      "genom utdelning. Som att få ränta på pengarna — fast från aktier.",
    riskLabel: "Låg risk",
    riskExplanation:
      "Bolag som delar ut pengar är oftast mogna och lönsamma — de har " +
      "pengar över efter att ha investerat i verksamheten. Utdelningen " +
      "kan dock minskas eller ställas in om företaget går sämre.",
    params: {
      dividend_yield_min: 0.02,
      score_min: 50,
      piotroski_min: 5,
      sort_by: "dividend_yield",
    },
    limit: 5,
    sortBy: "dividend_yield",
  },
  {
    id: "value-quality",
    label: "Billiga & trygga — värdeinvestering",
    emoji: "🏷️",
    description:
      "Aktier som ser billiga ut jämfört med hur mycket de tjänar. " +
      "Klassisk värdeinvestering — köpa en krona för 70 öre.",
    riskLabel: "Medel risk",
    riskExplanation:
      '"Billiga" aktier kan vara billiga av en anledning — marknaden ' +
      'kanske ser risker som inte syns i siffrorna. Men historiskt har ' +
      "värdeinvestering varit en av de mest framgångsrika strategierna.",
    params: {
      pe_max: 15,
      piotroski_min: 6,
      score_min: 55,
      sort_by: "score_total",
    },
    limit: 5,
    sortBy: "score_total",
  },
  {
    id: "growth-small",
    label: "Växande småbolag — för den som kan ta högre risk",
    emoji: "🚀",
    description:
      "Mindre bolag som växer snabbt. Kan ge hög avkastning — men kan " +
      "också falla mycket om det går dåligt. Inget för den försiktige.",
    riskLabel: "Högre risk",
    riskExplanation:
      "Småbolag har större potential att växa — men också större risk " +
      "att krympa eller gå under. De svänger ofta mycket mer än storbolag. " +
      "Investera bara pengar du har råd att förlora.",
    params: {
      segments: ["small_cap", "micro_cap"],
      score_min: 50,
      sort_by: "ml_rank",
    },
    limit: 5,
    sortBy: "ml_rank",
  },
  {
    id: "starter-kit",
    label: "Nybörjarens startpaket — 5 att börja titta på",
    emoji: "🎓",
    description:
      "Fem stabila svenska bolag som är bra att börja med. Inte för att " +
      "du ska köpa — utan för att du ska lära dig vad som gör en aktie bra.",
    riskLabel: "Låg–Medel risk",
    riskExplanation:
      "Det här är en blandning av stora, stabila bolag med olika riskprofil. " +
      "Använd dem för att lära dig hur omdömeskortet och AI-förklararen fungerar.",
    params: {
      segments: ["large_cap", "mid_cap"],
      score_min: 60,
      sort_by: "score_total",
    },
    limit: 5,
    sortBy: "score_total",
  },
  {
    id: "insider-buying",
    label: "Där ledningen köper egna aktier",
    emoji: "🔍",
    description:
      "När VD och styrelse köper aktier i sitt eget bolag kan det vara " +
      "en signal om att de tror på framtiden. De har bättre insyn än någon annan.",
    riskLabel: "Varierande risk",
    riskExplanation:
      "Insiderköp är en positiv signal — men ingen garanti. Ledningen " +
      "kan ha fel, och det finns många skäl att köpa aktier som inte " +
      "har med framtidstro att göra. Kolla alltid omdömeskortet också.",
    params: {
      score_min: 45,
      sort_by: "score_total",
      // NOTE: insider-filter kräver att /api/scan stödjer insider-parametrar
      // Om inte: filtrera bort low_liquidity och visa toppscore
    },
    limit: 5,
    sortBy: "score_total",
  },
];
```

---

## 2. Delsteg B — ThemeCard-komponent

**Fil:** `apps/web/components/screener/ThemeCard.tsx` (NY)

```tsx
"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useScreener } from "@/hooks/useScreener";
import { formatPrice, formatPctChange, signalLabel } from "@/lib/format";
import { FeedbackWidget } from "@/components/ui/FeedbackWidget";
import { trackEvent, EVENT } from "@/lib/tracking";
import { cn } from "@/lib/utils";
import type { ThemeDefinition } from "@/lib/themes";
import type { ScanRow } from "@/types/scan";

const RISK_COLORS = {
  "Låg risk": { bg: "bg-green-50", text: "text-green-700", ring: "ring-green-200" },
  "Låg–Medel risk": { bg: "bg-green-50", text: "text-green-700", ring: "ring-green-200" },
  "Medel risk": { bg: "bg-amber-50", text: "text-amber-700", ring: "ring-amber-200" },
  "Varierande risk": { bg: "bg-amber-50", text: "text-amber-700", ring: "ring-amber-200" },
  "Högre risk": { bg: "bg-red-50", text: "text-red-700", ring: "ring-red-200" },
};

export function ThemeCard({ theme }: { theme: ThemeDefinition }) {
  const { data: stocks, isLoading } = useScreener({
    ...theme.params,
    limit: theme.limit,
  });

  const riskStyle = RISK_COLORS[theme.riskLabel] || RISK_COLORS["Medel risk"];

  function handleClick() {
    trackEvent(EVENT.THEME_CLICK, { theme_id: theme.id });
  }

  return (
    <div
      className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-bg-surface)]
                 p-5 space-y-4 hover:shadow-md transition-shadow"
    >
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-3xl">{theme.emoji}</span>
            <h3 className="text-base font-semibold text-[var(--color-text-primary)]">
              {theme.label}
            </h3>
          </div>
          <p className="text-sm text-[var(--color-text-secondary)] mt-2 leading-relaxed">
            {theme.description}
          </p>
        </div>
        <span
          className={cn(
            "inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium shrink-0 ml-2",
            riskStyle.bg,
            riskStyle.text,
          )}
        >
          {theme.riskLabel}
        </span>
      </div>

      {/* Riskförklaring */}
      <details className="text-xs text-[var(--color-text-muted)]">
        <summary className="cursor-pointer hover:text-[var(--color-text-secondary)]">
          Vad betyder "{theme.riskLabel}"?
        </summary>
        <p className="mt-1 leading-relaxed">{theme.riskExplanation}</p>
      </details>

      {/* Förhandsgranskade aktier */}
      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-12 bg-[var(--color-bg-elevated)] rounded-lg animate-pulse" />
          ))}
        </div>
      ) : stocks && stocks.length > 0 ? (
        <div className="space-y-2">
          {stocks.slice(0, theme.limit).map((stock, i) => (
            <ThemeStockRow key={stock.ticker} stock={stock} themeId={theme.id} position={i + 1} />
          ))}
        </div>
      ) : (
        <p className="text-xs text-[var(--color-text-muted)] py-2">
          Inga aktier matchar just nu — kom tillbaka senare.
        </p>
      )}

      {/* Se alla */}
      {stocks && stocks.length > 0 && (
        <Link
          href={`/screener?${new URLSearchParams(
            Object.entries({ ...theme.params, limit: String(theme.limit) }).reduce(
              (acc, [k, v]) => ({ ...acc, [k]: String(v) }),
              {},
            ),
          ).toString()}`}
          onClick={handleClick}
          className="inline-flex items-center gap-1 text-xs font-medium text-[var(--color-accent)]
                     hover:underline"
        >
          Se alla i {theme.label.toLowerCase()} <ArrowRight size={12} />
        </Link>
      )}

      {/* Feedback */}
      <div className="pt-2 border-t border-[var(--color-border-subtle)]">
        <FeedbackWidget component="theme_card" context={`theme:${theme.id}`} />
      </div>
    </div>
  );
}

/**
 * En rad i ett temakort — visar en aktie med mini-omdöme.
 */
function ThemeStockRow({ stock, themeId, position }: { stock: ScanRow; themeId: string; position: number }) {
  function handleClick() {
    trackEvent(EVENT.THEME_STOCK_CLICK, { theme_id: themeId, ticker: stock.ticker, position });
  }

  return (
    <Link
      href={`/aktie/${stock.ticker}`}
      onClick={handleClick}
      className="flex items-center gap-3 p-2 rounded-lg hover:bg-[var(--color-bg-elevated)]
                 transition-colors group"
    >
      <span className="text-xs font-mono text-[var(--color-text-muted)] w-4 text-right">
        {position}
      </span>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-[var(--color-text-primary)] group-hover:text-[var(--color-accent)] transition-colors">
          {stock.name || stock.ticker}
        </div>
        <div className="text-[10px] text-[var(--color-text-muted)]">
          {stock.ticker}
          {stock.sector && ` · ${stock.sector}`}
        </div>
      </div>
      <div className="text-right shrink-0">
        <div className="text-sm font-semibold text-[var(--color-text-primary)]">
          {formatPrice(stock.price)}
        </div>
        <div className={cn(
          "text-xs",
          (stock.change_pct ?? 0) > 0 ? "text-green-600" : (stock.change_pct ?? 0) < 0 ? "text-red-600" : "text-[var(--color-text-muted)]",
        )}>
          {formatPctChange(stock.change_pct)}
        </div>
      </div>
    </Link>
  );
}
```

---

## 3. Delsteg C — /upptack-sidan

**Fil:** `apps/web/app/(app)/upptack/page.tsx` — kopiera EXAKT:

```tsx
"use client";

import { THEMES } from "@/lib/themes";
import { ThemeCard } from "@/components/screener/ThemeCard";
import { useExperience } from "@/components/providers/ExperienceProvider";

export default function UpptackPage() {
  const { level } = useExperience();

  // Nybörjare ser teman i en enkelkolumn med mer luft
  const isBeginner = level === "beginner";

  return (
    <div className={isBeginner ? "max-w-xl mx-auto py-8 px-4" : "max-w-4xl mx-auto py-6 px-4"}>
      {/* Hero (bara för nybörjare) */}
      {isBeginner && (
        <div className="text-center mb-8 space-y-2">
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
            Upptäck aktier
          </h1>
          <p className="text-sm text-[var(--color-text-secondary)] max-w-md mx-auto leading-relaxed">
            Vi har plockat ut några samlingar för att du ska slippa bygga filter.
            Bläddra bland temana — klicka på en aktie för att förstå den bättre.
          </p>
        </div>
      )}

      {/* Titel för van/erfaren */}
      {!isBeginner && (
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">
            Upptäck aktier
          </h1>
        </div>
      )}

      {/* Temagrid */}
      <div className={isBeginner
        ? "space-y-6"
        : "grid grid-cols-1 md:grid-cols-2 gap-6"
      }>
        {THEMES.map((theme) => (
          <ThemeCard key={theme.id} theme={theme} />
        ))}
      </div>

      {/* Footer-not: Screener finns kvar för experter */}
      {isBeginner && (
        <p className="text-center text-[11px] text-[var(--color-text-muted)] mt-8">
          När du är redo för mer avancerad filtrering kan du byta till
          Erfaren-läget i Inställningar — då får du tillgång till scannern.
        </p>
      )}
    </div>
  );
}
```

---

## 4. Delsteg D — Navigering

### I TopBar.tsx — lägg till i alla nivåers menyer:

```tsx
// I NAV_BY_LEVEL (spec 14) — alla nivåer har /upptack:
{ href: "/upptack", label: "Upptäck" },
```

### I DRAWER_PRIMARY (mobil):

```tsx
{ href: "/upptack", label: "Upptäck", icon: Compass },
```

---

## 5. Delsteg E — API: Om /api/scan inte stödjer insider-filter

Temat `insider-buying` använder `sort_by: "score_total"` och filtrerar bara på
`score_min: 45`. Det är safe — scannern stödjer alla dessa parametrar redan.

Om du vill ha RIKTIG insider-filtrering (bara aktier med aktiva insiderkluster):
1. Lägg till `is_cluster: boolean` i ScanParams
2. Lägg till `mews_flag: boolean`-stöd i screener-endpointen
3. Uppdatera `/api/scan` router att filtrera på dessa fält

Men för MVP:n räcker score_min + segment-filter. Temat är ändå användbart.

---

## 6. Filer som rörs

| Fil | Åtgärd |
|---|---|
| `apps/web/lib/themes.ts` | NY — 6 temadefinitioner |
| `apps/web/components/screener/ThemeCard.tsx` | NY — temakort med aktierader |
| `apps/web/app/(app)/upptack/page.tsx` | NY — /upptack-sidan |
| `apps/web/components/layout/TopBar.tsx` | Lägg /upptack i alla menyer |
| `apps/web/components/providers/ExperienceProvider.tsx` | Se spec 14 |

---

## 7. Acceptanstest

- [ ] `/upptack` laddar 6 teman
- [ ] Varje tema visar rätt emoji, namn, beskrivning, risknivå
- [ ] Varje tema laddar 5 förhandsgranskade aktier från `/api/scan`
- [ ] Klick på aktie → `/aktie/{ticker}` med omdömeskort (spec 14)
- [ ] "Se alla" → `/screener?params` med rätt filter
- [ ] Riskförklaring expanderas vid klick på "Vad betyder X?"
- [ ] FeedbackWidget under varje temakort
- [ ] Nybörjare: enkelkolumn, hero-text
- [ ] Van/Erfaren: 2-kolumn-grid
- [ ] Teman syns i menyn för alla nivåer
- [ ] Inget tema kraschar om `/api/scan` returnerar 0 resultat
- [ ] `cd apps/web && npx tsc --noEmit` — 0 fel
- [ ] `docs/SYSTEM_AI.md` uppdaterad
