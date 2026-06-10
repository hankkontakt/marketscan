# Spec 14 — M1 Nybörjarläge: Omdömeskort + Erfarenhetsnivåer

> **Skrivet: 2026-06-10. Beräknad insats: M–L (8–12h).**
> **Skrivet för:** DeepSeek v4-flash. **Läs HELA detta dokument + spec 13** innan du rör kod.
> **Bygger på:** `ExperienceProvider`, `StockView`, `VerdictHeader`, `ScanRow`-typen,
> `lib/format.ts`, `lib/labels.ts`, `InfoTooltip`.

---

## 0. Designdoktrin — läs detta noga

**Produkten har 3 erfarenhetsnivåer** — inte 2:

| Nivå | Vad användaren ser |
|---|---|
| **Nybörjare** (0–30 dagar) | Bara omdömeskortet. Inga siffror, inga tabs. En stor "Förstå"-knapp leder till AI-förklararen. Meny: Hem, Upptäck, Bevakningar, Guide, Inställningar. |
| **Van** (30+ dagar, eller självvalt) | Omdömeskortet + "visa siffrorna"-expand. Förenklade tabs (Oversikt, Rapporter). AI-flik finns. Meny: Hem, Upptäck, Portfölj, Bevakningar, Kalender, Inställningar. |
| **Erfaren** (självvalt) | Dagens fulla StockView med alla tabs. Full meny inkl. Verktyg. AI-kommitté, Strategi Lab — allt. |

**Designprinciper:**
1. **Nybörjare ska ALDRIG se ett rått nyckeltal först.** De ser en svensk mening. Siffror kommer efter klick.
2. **Varje omdöme är deterministiskt** — lookup-tabeller och enkel logik, inte AI. AI är bara för "förklara varför".
3. **Toggle mellan nivåer är instant** — inga API-anrop, inga page reloads. `ExpertOnly`/`BeginnerOnly` wrappers.
4. **Använd CSS-variabler** (`var(--color-...)`) — aldrig hårdkodade färger.
5. **Alla strängar på svenska** — inga engelska labels i UI:t.

---

## 1. Delsteg A — Utöka ExperienceProvider till 3 nivåer

**Fil:** `apps/web/components/providers/ExperienceProvider.tsx`

Ändra typen:
```tsx
export type ExperienceLevel = "beginner" | "intermediate" | "expert";
```

Ändra context — lägg till:
```tsx
interface ExperienceContextValue {
  level: ExperienceLevel;
  setLevel: (level: ExperienceLevel) => void;
  loading: boolean;
  onboardingCompleted: boolean;
  completeOnboarding: () => void;
  // NY: Hjälpfunktioner
  isAtLeast: (level: ExperienceLevel) => boolean;
}
```

Lägg till komponenter:
```tsx
// Visas ENDAST för nybörjare
export function BeginnerOnly({ children }: { children: React.ReactNode }) {
  const { level } = useExperience();
  if (level !== "beginner") return null;
  return <>{children}</>;
}

// Visas för nybörjare + van (döljs för experter)
export function NonExpertOnly({ children }: { children: React.ReactNode }) {
  const { level } = useExperience();
  if (level === "expert") return null;
  return <>{children}</>;
}

// Visas ENDAST för experter (ersätter gamla ExpertOnly — men behåll bakåtkompatibilitet)
export function ExpertOnly({ children }: { children: React.ReactNode }) {
  const { level } = useExperience();
  if (level !== "expert") return null;
  return <>{children}</>;
}

// Minst en viss nivå
export function AtLeast({ level: minLevel, children }: { level: ExperienceLevel; children: React.ReactNode }) {
  const { isAtLeast } = useExperience();
  if (!isAtLeast(minLevel)) return null;
  return <>{children}</>;
}
```

`isAtLeast`-implementation:
```tsx
const LEVEL_ORDER: Record<ExperienceLevel, number> = { beginner: 0, intermediate: 1, expert: 2 };

function isAtLeast(minLevel: ExperienceLevel): boolean {
  return LEVEL_ORDER[level] >= LEVEL_ORDER[minLevel];
}
```

Uppdatera `setLevel` att spara i API (PUT profile):
```tsx
api("/api/profile", {
  method: "PUT",
  body: JSON.stringify({ experience_level: newLevel }),
}).catch(() => {});
```

---

## 2. Delsteg B — Plain-language translationslager

**Fil:** `apps/web/lib/plainLanguage.ts` — kopiera EXAKT:

```ts
/**
 * Plain-language translationslager för MarketScan.
 * 
 * Översätter råa faktorscores → svenska meningar en nybörjare förstår.
 * ALL logik här är deterministisk — lookup-tabeller och enkla trösklar.
 * AI används ENDAST för fria förklaringar (spec 15).
 */

import type { ScanRow } from "@/types/scan";
import { FACTOR_LABELS } from "@/lib/labels";

// ── Typer ─────────────────────────────────────────────────────────────

export interface VerdictReason {
  icon: "check" | "warning" | "info";    // Vilken ikon
  title: string;                           // Kort rubrik
  detail: string;                          // En mening förklaring  
  scoreKey?: string;                       // Vilken score_*-faktor det gäller
}

export interface StockVerdict {
  qualityLabel: "exceptionell" | "stark" | "bra" | "okej" | "svag";
  qualitySentence: string;                 // "En stark kandidat — höga betyg på flera fronter."
  reasons: VerdictReason[];                // 3 skäl
  risk: VerdictReason;                     // 1 risk
  overallScore: number;                    // 0-100
}

// ── Hjälp — kategorisera score_total ─────────────────────────────────

function categorizeScore(score: number | null | undefined): StockVerdict["qualityLabel"] {
  const s = score ?? 0;
  if (s >= 85) return "exceptionell";
  if (s >= 70) return "stark";
  if (s >= 55) return "bra";
  if (s >= 40) return "okej";
  return "svag";
}

const QUALITY_SENTENCES: Record<StockVerdict["qualityLabel"], string> = {
  exceptionell: "En ovanligt stark kandidat — höga betyg på i stort sett alla fronter.",
  stark: "En stark kandidat med flera styrkor.",
  bra: "En helt okej kandidat — men det finns saker att hålla koll på.",
  okej: "En blandad bild — vissa saker ser bra ut, andra mindre bra.",
  svag: "Siffrorna är svaga just nu — det kan finnas bättre kandidater.",
};

// ── Huvudfunktion ──────────────────────────────────────────────────────

export function buildVerdict(stock: ScanRow): StockVerdict {
  const reasons: VerdictReason[] = [];
  const risks: VerdictReason[] = [];

  // Samla alla score_*-faktorer med sina värden
  const factors = [
    { key: "score_value", value: stock.score_value, weight: 3 },
    { key: "score_quality", value: stock.score_quality, weight: 3 },
    { key: "score_momentum", value: stock.score_momentum, weight: 2 },
    { key: "score_growth", value: stock.score_growth, weight: 2 },
    { key: "score_risk", value: stock.score_risk, weight: 2 },
    { key: "score_dividend", value: stock.score_dividend, weight: 1 },
    { key: "score_sentiment", value: stock.score_sentiment, weight: 1 },
    { key: "score_size", value: stock.score_size, weight: 1 },
  ].filter((f) => f.value != null);

  // Sortera: starkaste först
  const sorted = [...factors].sort((a, b) => (b.value ?? 0) - (a.value ?? 0));

  // Topp 3 som skäl
  for (const f of sorted.slice(0, 3)) {
    const label = FACTOR_LABELS[f.key] || f.key;
    const v = f.value ?? 50;
    if (v >= 70) {
      reasons.push({
        icon: "check",
        title: `Stark ${label.toLowerCase()}`,
        detail: factorPositiveDetail(f.key, v),
        scoreKey: f.key,
      });
    } else if (v >= 50) {
      reasons.push({
        icon: "info",
        title: `Okej ${label.toLowerCase()}`,
        detail: factorNeutralDetail(f.key, v),
        scoreKey: f.key,
      });
    } else {
      reasons.push({
        icon: "warning",
        title: `Svag ${label.toLowerCase()}`,
        detail: factorNegativeDetail(f.key, v),
        scoreKey: f.key,
      });
    }
  }

  // Sämsta som risk — den svagaste faktorn ELLER explicita risker
  const worst = sorted[sorted.length - 1];
  if (worst && (worst.value ?? 100) < 60) {
    risks.push({
      icon: "warning",
      title: `Svag ${FACTOR_LABELS[worst.key]?.toLowerCase() || worst.key}`,
      detail: factorNegativeDetail(worst.key, worst.value ?? 50),
      scoreKey: worst.key,
    });
  }
  // Ytterligare risker från fundamenta
  if ((stock.debt_to_equity ?? 0) > 2) {
    risks.push({
      icon: "warning",
      title: "Hög skuldsättning",
      detail: "Bolaget har mycket lån jämfört med eget kapital. Det ökar risken i sämre tider.",
    });
  }
  if (stock.low_liquidity) {
    risks.push({
      icon: "warning",
      title: "Låg likviditet",
      detail: "Aktien handlas sällan. Det kan vara svårt att sälja snabbt om du behöver.",
    });
  }
  if ((stock.beta ?? 1) > 1.5) {
    risks.push({
      icon: "warning",
      title: "Högre svängningar",
      detail: `Beta ${(stock.beta ?? 0).toFixed(1)} — aktien rör sig mer än börsen i stort.`,
    });
  }

  // Använd första risken, eller skapa en generisk
  const primaryRisk = risks[0] || {
    icon: "info" as const,
    title: "Ingen uppenbar risk",
    detail: "Ingen enskild faktor sticker ut som en varningssignal.",
  };

  return {
    qualityLabel: categorizeScore(stock.score_total),
    qualitySentence: QUALITY_SENTENCES[categorizeScore(stock.score_total)],
    reasons: reasons.slice(0, 3),
    risk: primaryRisk,
    overallScore: stock.score_total ?? 0,
  };
}

// ── Detaljgeneratorer per faktor ────────────────────────────────────

function factorPositiveDetail(key: string, value: number): string {
  const map: Record<string, string> = {
    score_value: `Aktien ser billig ut jämfört med liknande bolag (${Math.round(value)}/100).`,
    score_quality: `Bolaget har hög lönsamhet och stark balansräkning (${Math.round(value)}/100).`,
    score_momentum: `Kursen har gått starkt på sistone — medvind just nu (${Math.round(value)}/100).`,
    score_growth: `Både intäkter och vinster växer (${Math.round(value)}/100).`,
    score_risk: `Bolaget har relativt stabil kurs och låg skuldsättning (${Math.round(value)}/100).`,
    score_dividend: `Bolaget delar ut pengar till aktieägarna (${Math.round(value)}/100).`,
    score_sentiment: `Marknaden är positiv till aktien just nu (${Math.round(value)}/100).`,
    score_size: `Bolaget är tillräckligt stort för att vara stabilt men kan fortfarande växa (${Math.round(value)}/100).`,
  };
  return map[key] || `Högt betyg (${Math.round(value)}/100).`;
}

function factorNeutralDetail(key: string, value: number): string {
  const map: Record<string, string> = {
    score_value: `Varken särskilt billig eller dyr (${Math.round(value)}/100).`,
    score_quality: `Godkänd lönsamhet — varken bäst eller sämst (${Math.round(value)}/100).`,
    score_momentum: `Kursen är stabil, ingen tydlig riktning (${Math.round(value)}/100).`,
    score_growth: `Tillväxten är måttlig (${Math.round(value)}/100).`,
    score_risk: `Normal risknivå (${Math.round(value)}/100).`,
    score_dividend: `Liten eller ingen utdelning (${Math.round(value)}/100).`,
    score_sentiment: `Neutralt sentiment (${Math.round(value)}/100).`,
    score_size: `Medelstort bolag (${Math.round(value)}/100).`,
  };
  return map[key] || `Medel (${Math.round(value)}/100).`;
}

function factorNegativeDetail(key: string, value: number): string {
  const map: Record<string, string> = {
    score_value: `Aktien ser dyr ut — hög värdering jämfört med liknande bolag (${Math.round(value)}/100).`,
    score_quality: `Bolaget har låg lönsamhet — det drar ner betyget (${Math.round(value)}/100).`,
    score_momentum: `Kursen har gått svagt — motvind (${Math.round(value)}/100).`,
    score_growth: `Intäkter eller vinster minskar — ingen tillväxt (${Math.round(value)}/100).`,
    score_risk: `Högre risk — kursen svänger mycket eller bolaget har hög skuld (${Math.round(value)}/100).`,
    score_dividend: `Ingen utdelning alls (${Math.round(value)}/100).`,
    score_sentiment: `Marknaden är negativ till aktien just nu (${Math.round(value)}/100).`,
    score_size: `Mycket litet bolag — högre risk (${Math.round(value)}/100).`,
  };
  return map[key] || `Svagt betyg (${Math.round(value)}/100).`;
}
```

---

## 3. Delsteg C — Omdömeskort-komponenten

**Fil:** `apps/web/components/stock/VerdictCard.tsx` — kopiera EXAKT:

```tsx
"use client";

import { useState } from "react";
import { TrendingUp, Shield, AlertTriangle, ChevronDown, ChevronUp, Eye, Star } from "lucide-react";
import { cn } from "@/lib/utils";
import { buildVerdict } from "@/lib/plainLanguage";
import { formatPrice, formatPctChange, changeClass } from "@/lib/format";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { FeedbackWidget } from "@/components/ui/FeedbackWidget";
import { useExperience } from "@/components/providers/ExperienceProvider";
import { trackEvent, EVENT } from "@/lib/tracking";
import type { ScanRow } from "@/types/scan";

// Färgmappning för kvalitetsnivåerna
const QUALITY_COLORS = {
  exceptionell: { bg: "#f0fdf4", border: "#86efac", text: "#166534", emoji: "🌟" },
  stark: { bg: "#f0fdf4", border: "#bbf7d0", text: "#166534", emoji: "✅" },
  bra: { bg: "#f8fafc", border: "#e2e8f0", text: "#334155", emoji: "👍" },
  okej: { bg: "#fffbeb", border: "#fde68a", text: "#92400e", emoji: "🤔" },
  svag: { bg: "#fef2f2", border: "#fecaca", text: "#991b1b", emoji: "⚠️" },
};

export function VerdictCard({ stock }: { stock: ScanRow }) {
  const [showNumbers, setShowNumbers] = useState(false);
  const { level } = useExperience();
  const verdict = buildVerdict(stock);
  const colors = QUALITY_COLORS[verdict.qualityLabel];

  function handleExpand() {
    trackEvent(EVENT.VERDICT_EXPAND, { ticker: stock.ticker });
    setShowNumbers(!showNumbers);
  }

  return (
    <div
      className="rounded-2xl p-6 border-2 space-y-4"
      style={{
        background: colors.bg,
        borderColor: colors.border,
      }}
    >
      {/* ── Prisrad (alltid synlig) ──────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
            {stock.name}
          </h1>
          <span className="text-sm text-[var(--color-text-muted)]">{stock.ticker}</span>
        </div>
        <div className="text-right">
          <div className="text-2xl font-semibold text-[var(--color-text-primary)]">
            {formatPrice(stock.price)}
          </div>
          <div className={cn("text-sm font-medium", changeClass(stock.change_pct))}>
            {formatPctChange(stock.change_pct)}
          </div>
        </div>
      </div>

      {/* ── Signal-badge ─────────────────────────────────────── */}
      {stock.entry_signal && (
        <div className="flex items-center gap-2">
          <SignalBadge signal={stock.entry_signal} />
          {stock.entry_signal === "STARK" && (
            <span className="text-sm text-[var(--color-text-secondary)]">
              — ett av de högst rankade köplägena just nu
            </span>
          )}
        </div>
      )}

      {/* ── Omdömet (detta är hjärtat) ────────────────────────── */}
      <div className="text-center py-3">
        <span className="text-5xl">{colors.emoji}</span>
        <p className="text-lg font-medium text-[var(--color-text-primary)] mt-2 leading-relaxed">
          {verdict.qualitySentence}
        </p>
      </div>

      {/* ── 3 skäl ────────────────────────────────────────────── */}
      <div className="space-y-2">
        {verdict.reasons.map((reason, i) => (
          <div key={i} className="flex items-start gap-3 p-3 rounded-xl bg-white/60">
            <span className="mt-0.5">
              {reason.icon === "check" && <Shield size={18} className="text-green-600" />}
              {reason.icon === "info" && <Eye size={18} className="text-blue-500" />}
              {reason.icon === "warning" && <AlertTriangle size={18} className="text-amber-500" />}
            </span>
            <div className="min-w-0">
              <div className="text-sm font-medium text-[var(--color-text-primary)]">
                {reason.title}
              </div>
              <div className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                {reason.detail}
              </div>
              {reason.scoreKey && (
                <InfoTooltip
                  text={`Detta baseras på faktorn "${reason.scoreKey}". Betyget är en sammanvägning av flera nyckeltal.`}
                />
              )}
            </div>
          </div>
        ))}
      </div>

      {/* ── 1 risk ────────────────────────────────────────────── */}
      <div className="flex items-start gap-3 p-3 rounded-xl bg-amber-50/50 border border-amber-100">
        <AlertTriangle size={18} className="text-amber-500 mt-0.5 shrink-0" />
        <div className="min-w-0">
          <div className="text-sm font-medium text-[var(--color-text-primary)]">
            {verdict.risk.title}
          </div>
          <div className="text-xs text-[var(--color-text-secondary)] mt-0.5">
            {verdict.risk.detail}
          </div>
        </div>
      </div>

      {/* ── "Visa siffrorna" — expanderar nyckeltalen ──────────── */}
      <button
        onClick={handleExpand}
        className="w-full flex items-center justify-center gap-1 py-2 text-xs font-medium
                   text-[var(--color-accent)] hover:bg-[var(--color-accent-soft)] rounded-lg transition-colors"
      >
        {showNumbers ? (
          <>
            <ChevronUp size={14} /> Dölj siffrorna
          </>
        ) : (
          <>
            <ChevronDown size={14} /> Visa siffrorna bakom omdömet
          </>
        )}
      </button>

      {showNumbers && (
        <div className="grid grid-cols-2 gap-3 pt-2 border-t border-[var(--color-border-subtle)]">
          <NumberCard label="Totalbetyg" value={stock.score_total} unit="/100" tooltip="Sammanvägt betyg 0-100 baserat på 8 faktorer" />
          <NumberCard label="P/E" value={stock.pe_trailing} unit="x" tooltip="Pris per krona vinst. Lägre = billigare." />
          <NumberCard label="ROE" value={(stock.roe ?? 0) * 100} unit="%" tooltip="Avkastning på eget kapital. Högre = mer lönsamt." />
          <NumberCard label="Beta" value={stock.beta} unit="" tooltip="Kursens känslighet mot börsen. 1 = följer index." />
          <NumberCard label="Skuldsättning" value={stock.debt_to_equity} unit="x" tooltip="Skulder / eget kapital. Lägre = mindre risk." />
          <NumberCard label="Direktavkastning" value={(stock.dividend_yield ?? 0) * 100} unit="%" tooltip="Årlig utdelning i procent av kursen." />
        </div>
      )}

      {/* ── Actions ────────────────────────────────────────────── */}
      <div className="flex items-center justify-between pt-2 border-t border-[var(--color-border-subtle)]">
        <WatchlistButton ticker={stock.ticker} />
        <FeedbackWidget component="verdict_card" context={stock.ticker} />
      </div>
    </div>
  );
}

// ── Hjälpkomponenter ──────────────────────────────────────────────

function SignalBadge({ signal }: { signal: string | null }) {
  const labels: Record<string, string> = {
    STARK: "Starkt köpläge",
    OK: "Bra läge",
    VÄNTA: "Avvakta",
    EJ_AKTUELL: "Ej aktuellt",
  };
  const colors: Record<string, string> = {
    STARK: "bg-green-100 text-green-800",
    OK: "bg-blue-100 text-blue-800",
    VÄNTA: "bg-amber-100 text-amber-800",
    EJ_AKTUELL: "bg-gray-100 text-gray-600",
  };
  if (!signal || !labels[signal]) return null;
  return (
    <span className={cn("inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium", colors[signal] || colors["EJ_AKTUELL"])}>
      {labels[signal]}
    </span>
  );
}

function NumberCard({ label, value, unit, tooltip }: { label: string; value: number | null | undefined; unit: string; tooltip: string }) {
  const display = value != null ? `${typeof value === "number" && value < 10 ? value.toFixed(1) : Math.round(value)}${unit}` : "—";
  return (
    <div className="p-2 rounded-lg bg-white/50">
      <div className="flex items-center gap-1">
        <span className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wide">{label}</span>
        <InfoTooltip text={tooltip} />
      </div>
      <div className="text-sm font-semibold text-[var(--color-text-primary)]">{display}</div>
    </div>
  );
}

function WatchlistButton({ ticker }: { ticker: string }) {
  const { useWatchlist } = require("@/hooks/usePortfolio");
  // Förenklad — återanvänd logiken från VerdictHeader
  // TODO: Extrahera till shared hook
  return (
    <button className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium
                       border border-[var(--color-border)] text-[var(--color-text-secondary)]
                       hover:bg-[var(--color-bg-elevated)] transition-colors">
      <Star size={14} /> Bevaka
    </button>
  );
}
```

---

## 4. Delsteg D — Modifiera StockView för nivåer

**Fil:** `apps/web/app/(app)/aktie/[ticker]/StockView.tsx`

### För nybörjare (beginner):

Byt ut HELA sidan. Rendera ENDAST:
```tsx
if (level === "beginner") {
  return (
    <div className="max-w-2xl mx-auto py-6 px-4 space-y-6">
      <VerdictCard stock={stock} />
      
      {/* AI-förklararen (byggs i spec 15 — här en placeholder) */}
      <ExplainSection ticker={stock.ticker} stock={stock} />
      
      {/* Bevaknings-CTA */}
      <BeginnerCTA ticker={stock.ticker} />
    </div>
  );
}
```

### För van (intermediate):

Omdömeskort som hero, sedan förenklade tabs:
```tsx
if (level === "intermediate") {
  return (
    <div className="max-w-4xl mx-auto py-4 px-4 space-y-4">
      <VerdictCard stock={stock} />
      
      <Tabs.Root defaultValue="oversikt">
        <Tabs.List>
          <Tabs.Trigger value="oversikt">Översikt</Tabs.Trigger>
          <Tabs.Trigger value="rapporter">Rapporter</Tabs.Trigger>
          <Tabs.Trigger value="ai">AI-analys</Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="oversikt"><OverviewTab stock={stock} /></Tabs.Content>
        <Tabs.Content value="rapporter"><RapporterTab ticker={stock.ticker} stock={stock} /></Tabs.Content>
        <Tabs.Content value="ai"><ExplainSection ticker={stock.ticker} stock={stock} /></Tabs.Content>
      </Tabs.Root>
    </div>
  );
}
```

### För experter:

Behåll dagens StockView HELT oförändrad.

---

## 5. Delsteg E — Nybörjar-CTA

**Fil:** `apps/web/components/stock/BeginnerCTA.tsx` (NY)

Ett grönt kort under omdömeskortet:
```
┌─────────────────────────────────────────┐
│  🎯  Vill du följa den här aktien?      │
│                                         │
│  Lägg den i din bevakningslista och     │
│  följ hur omdömet utvecklas under       │
│  de kommande 30 dagarna.                │
│                                         │
│  Inga köp, ingen risk — bara lärande.   │
│                                         │
│  [  ★  Lägg i bevakning  ]              │
└─────────────────────────────────────────┘
```

---

## 6. Delsteg F — Förenkla navigering per nivå

**Fil:** `apps/web/components/layout/TopBar.tsx`

### Nybörjar-meny:
```tsx
const NAV_BY_LEVEL: Record<ExperienceLevel, typeof PRIMARY_NAV> = {
  beginner: [
    { href: "/daglig-briefing", label: "Hem" },
    { href: "/upptack", label: "Upptäck" },       // NY (spec 16)
    { href: "/bevakningar", label: "Bevakningar" },
    { href: "/guide", label: "Guide" },
    { href: "/installningar", label: "Inställningar" },
  ],
  intermediate: [
    { href: "/daglig-briefing", label: "Hem" },
    { href: "/upptack", label: "Upptäck" },
    { href: "/portfolj", label: "Portfölj" },
    { href: "/bevakningar", label: "Bevakningar" },
    { href: "/kalender", label: "Kalender" },
    { href: "/installningar", label: "Inställningar" },
  ],
  expert: [
    // Dagens PRIMARY_NAV oförändrad
    ...PRIMARY_NAV,
  ],
};
```

Samma mönster för DRAWER_PRIMARY och DRAWER_VERKTYG.

---

## 7. Sammanfattning filer

| Fil | Åtgärd |
|---|---|
| `apps/web/components/providers/ExperienceProvider.tsx` | Ändra: 3 nivåer, `BeginnerOnly`, `NonExpertOnly`, `isAtLeast` |
| `apps/web/lib/plainLanguage.ts` | NY — översätter ScanRow → svenska meningar |
| `apps/web/components/stock/VerdictCard.tsx` | NY — omdömeskortet |
| `apps/web/components/stock/BeginnerCTA.tsx` | NY — CTA-kort |
| `apps/web/app/(app)/aktie/[ticker]/StockView.tsx` | Ändra: nivå-baserad rendering |
| `apps/web/components/layout/TopBar.tsx` | Ändra: `NAV_BY_LEVEL` |
| `apps/web/app/(app)/layout.tsx` | Lägg `BeginnerOnly`/`NonExpertOnly` om nav ändras per layout |

---

## 8. Acceptanstest

- [ ] `cd apps/web && npx tsc --noEmit` — 0 fel
- [ ] Nybörjare: aktiesidan visar bara VerdictCard + ExplainSection + CTA
- [ ] Van: aktiesidan visar VerdictCard + förenklade tabs
- [ ] Erfaren: aktiesidan visar dagens fulla StockView oförändrad
- [ ] BuildVerdict för ett starkt bolag (score_total > 70) ger "stark" eller "exceptionell"
- [ ] BuildVerdict för ett svagt bolag (score_total < 40) ger "svag"
- [ ] 3 skäl + 1 risk räknas korrekt från faktorscores
- [ ] "Visa siffrorna" expand visar rätt nyckeltal
- [ ] FeedbackWidget fungerar (POST till /api/feedback)
- [ ] Meny ändras korrekt vid nivåbyte
- [ ] `docs/SYSTEM_AI.md` uppdaterad
