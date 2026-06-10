# Spec 13 — M0 Analytics + Feedback

> **Skrivet: 2026-06-10. Beräknad insats: S–M (4–6h).**
> **Skrivet för:** DeepSeek v4-flash. Läs ALLTID detta dokument HELT innan kod rörs.
> **Bygger på:** `docs/plan/00_MASTER_PLAN.md §6` + befintliga mönster i kodbasen.

---

## 0. Vad och varför

Just nu finns **noll mätning** i produkten. Du kan inte veta:
- Hur många slutför onboarding
- Vilka sidor besöks mest
- Om nybörjare stannar eller lämnar

**Mål:** Bygg ett **abstraherat tracking-lager** (lätt att byta provider) +
ett **in-app feedback-system** (admin kan granska utan att skriva till AI).
Allt ska funka gratis — Umami self-hosted på Vercel + Supabase.

---

## 1. Tracking-abstraktionslager

**Fil:** `apps/web/lib/tracking.ts` — kopiera EXAKT:

```tsx
/**
 * Tracking-abstraktion. Just nu Umami self-hosted.
 * Byta provider = byt implementering, behåll interface.
 *
 * Använd ALLTID EVENT-konstanterna, aldrig hårdkodade strängar.
 */
type EventProps = Record<string, string | number | boolean>;

declare global {
  interface Window {
    umami?: { track: (event: string, data?: EventProps) => void };
  }
}

export function trackEvent(name: string, props?: EventProps): void {
  if (typeof window !== "undefined" && window.umami) {
    window.umami.track(name, props);
  }
}

export function trackPageView(url?: string): void {
  if (typeof window !== "undefined" && window.umami) {
    window.umami.track("pageview", {
      url: url || window.location.pathname,
    });
  }
}

export const EVENT = {
  ONBOARDING_COMPLETED: "onboarding_completed",
  BEGINNER_TOGGLE: "beginner_toggle",
  STOCK_PAGE_VIEW: "stock_page_view",
  EXPLAIN_CLICK: "explain_click",
  EXPLAIN_FOLLOWUP: "explain_followup",
  FEEDBACK_SUBMITTED: "feedback_submitted",
  THEME_CLICK: "theme_click",
  THEME_STOCK_CLICK: "theme_stock_click",
  WATCHLIST_ADD: "watchlist_add",
  VERDICT_EXPAND: "verdict_expand_numbers",
} as const;
```

---

## 2. Umami — setup (manuellt steg av användaren)

### Steg 1: Skapa Supabase-schema

Kör i Supabase SQL Editor:
```sql
CREATE SCHEMA IF NOT EXISTS umami;
```

### Steg 2: Deploya Umami

1. `git clone https://github.com/umami-software/umami.git /tmp/umami`
2. `cd /tmp/umami && npm install`
3. Skapa `.env`:
```
DATABASE_URL=postgresql://postgres:[DITT-LÖSENORD]@[DIN-SUPABASE-HOST]:6543/postgres?options=-c%20search_path%3Dumami
HASH_SALT=$(openssl rand -hex 32)
APP_SECRET=$(openssl rand -hex 32)
TRACKER_SCRIPT_NAME=umami
```
4. Kör migrering: `npm run build` → kolla att den startar.
5. Deploya till Vercel: `cd /tmp/umami && vercel --prod`
6. Få URL: t.ex. `https://marketscan-umami.vercel.app`
7. Gå till URL:en, skapa admin-konto, lägg till "MarketScan" som website.
   Kopiera **Website ID** (UUID).

### Steg 3: Sätt miljövariabler i MarketScan

I Vercel (marketscan-web), lägg till:
```
NEXT_PUBLIC_UMAMI_URL=https://marketscan-umami.vercel.app
NEXT_PUBLIC_UMAMI_WEBSITE_ID=<ditt-website-id>
NEXT_PUBLIC_APP_DOMAIN=web-...-hankkontakts-projects.vercel.app
```

---

## 3. TrackingProvider

**Fil:** `apps/web/components/providers/TrackingProvider.tsx` — kopiera EXAKT:

```tsx
"use client";

import Script from "next/script";
import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { trackPageView } from "@/lib/tracking";

const UMAMI_URL = process.env.NEXT_PUBLIC_UMAMI_URL || "";
const WEBSITE_ID = process.env.NEXT_PUBLIC_UMAMI_WEBSITE_ID || "";

export function TrackingProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  // Track client-side navigations
  useEffect(() => {
    trackPageView(pathname);
  }, [pathname]);

  // Om ingen URL/ID konfigurerats, rendera bara children (ingen krasch)
  if (!UMAMI_URL || !WEBSITE_ID) {
    return <>{children}</>;
  }

  return (
    <>
      <Script
        src={`${UMAMI_URL}/umami.js`}
        data-website-id={WEBSITE_ID}
        data-domains={process.env.NEXT_PUBLIC_APP_DOMAIN}
        strategy="afterInteractive"
        defer
      />
      {children}
    </>
  );
}
```

**Registrera i** `apps/web/app/(app)/layout.tsx`:
```tsx
import { TrackingProvider } from "@/components/providers/TrackingProvider";
```
Och wrappa children:
```tsx
<ExperienceProvider>
  <TrackingProvider>
    <div className="app-layout">
      ...
    </div>
  </TrackingProvider>
</ExperienceProvider>
```

---

## 4. Instrumentera events

### 4a. OnboardingModal.tsx

Lägg i imports:
```tsx
import { trackEvent, EVENT } from "@/lib/tracking";
```

I `handleContinue()` när sista steget nås:
```tsx
function handleContinue() {
  if (step < steps.length - 1) {
    setStep(step + 1);
  } else {
    trackEvent(EVENT.ONBOARDING_COMPLETED, { level });  // <-- NY
    completeOnboarding();
    setOpen(false);
  }
}
```

I `handleSkip()` (så vi ser hur många som hoppar över):
```tsx
function handleSkip() {
  trackEvent(EVENT.ONBOARDING_COMPLETED, { level, skipped: true });  // <-- NY
  if (step < 1) {
    setLevel("beginner");
  }
  completeOnboarding();
  setOpen(false);
}
```

### 4b. ExperienceProvider.tsx

Lägg i imports:
```tsx
import { trackEvent, EVENT } from "@/lib/tracking";
```

I `setLevel`:
```tsx
const setLevel = useCallback((newLevel: ExperienceLevel) => {
  trackEvent(EVENT.BEGINNER_TOGGLE, { from: level, to: newLevel });  // <-- NY
  setLevelState(newLevel);
  api("/api/profile", { method: "PUT", body: JSON.stringify({ experience_level: newLevel }) }).catch(() => {});
}, [level]);
```

### 4c. StockView.tsx

Lägg i imports:
```tsx
import { trackEvent, EVENT } from "@/lib/tracking";
```

I StockView-komponenten, efter `useStock(ticker)`:
```tsx
const { data: stock, isLoading, error } = useStock(ticker);

useEffect(() => {
  if (stock?.ticker) {
    trackEvent(EVENT.STOCK_PAGE_VIEW, { ticker: stock.ticker });
  }
}, [stock?.ticker]);
```

---

## 5. Feedback-system

### 5a. Migration `035_user_feedback.sql`

```sql
CREATE TABLE IF NOT EXISTS user_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  component TEXT NOT NULL,
  context TEXT,
  rating INTEGER NOT NULL CHECK (rating IN (1, 0, -1)),
  comment TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_component ON user_feedback (component);
CREATE INDEX IF NOT EXISTS idx_feedback_created ON user_feedback (created_at DESC);

ALTER TABLE user_feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "feedback_insert_own" ON user_feedback
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "feedback_select_own" ON user_feedback
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "feedback_admin_all" ON user_feedback
  FOR ALL USING (
    (SELECT COALESCE(raw_app_meta_data->>'role', 'authenticated') FROM auth.users WHERE id = auth.uid()) = 'admin'
  );

GRANT SELECT, INSERT ON user_feedback TO authenticated;

COMMENT ON TABLE user_feedback IS 'User feedback on UI components. Migration 035. Diagnostic marker: migration_035_user_feedback.';
```

**Registrera i diagnostics.py:** Lägg `"migration_035_user_feedback"` i `MIGRATION_MARKERS` och `"user_feedback"` i `USER_TABLES`.

### 5b. API: feedback.py

**Fil:** `apps/api/routers/feedback.py` — kopiera EXAKT:

```python
from __future__ import annotations
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from apps.api.core.security import get_current_user, User
from apps.api.dependencies import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["feedback"])

class FeedbackRequest(BaseModel):
    component: str
    context: str | None = None
    rating: int = Field(..., ge=-1, le=1)
    comment: str | None = None

@router.post("/feedback")
def submit_feedback(
    body: FeedbackRequest,
    user: User = Depends(get_current_user),
    sb = Depends(get_supabase),
):
    res = sb.table("user_feedback").insert({
        "user_id": user.id,
        "component": body.component,
        "context": body.context,
        "rating": body.rating,
        "comment": body.comment,
    }).execute()
    row = res.data[0] if res.data else {}
    return {"id": row.get("id"), "created_at": row.get("created_at")}
```

Registrera i `main.py`:
```python
from apps.api.routers import feedback as feedback_router
app.include_router(feedback_router.router)
```

### 5c. Admin API

I `apps/api/routers/admin.py`, lägg till:

```python
@router.get("/admin/feedback")
def admin_feedback(
    component: str | None = None,
    limit: int = 200,
    sb_admin = Depends(get_supabase_admin),
    user: User = Depends(require_admin),
):
    query = (
        sb_admin.table("user_feedback")
        .select("id, user_id, component, context, rating, comment, created_at")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if component:
        query = query.eq("component", component)
    res = query.execute()
    data = res.data or []
    # Aggregate stats
    positive = sum(1 for r in data if r.get("rating") == 1)
    negative = sum(1 for r in data if r.get("rating") == -1)
    neutral = sum(1 for r in data if r.get("rating") == 0)
    by_component = {}
    for r in data:
        c = r.get("component", "unknown")
        if c not in by_component:
            by_component[c] = {"total": 0, "positive": 0, "negative": 0, "neutral": 0}
        by_component[c]["total"] += 1
        rat = r.get("rating", 0)
        if rat == 1: by_component[c]["positive"] += 1
        elif rat == -1: by_component[c]["negative"] += 1
        else: by_component[c]["neutral"] += 1
    return {
        "feedback": data,
        "count": len(data),
        "stats": {"positive": positive, "negative": negative, "neutral": neutral},
        "by_component": by_component,
    }
```

### 5d. FeedbackWidget — frontend

**Fil:** `apps/web/components/ui/FeedbackWidget.tsx` — kopiera EXAKT:

```tsx
"use client";

import { useState } from "react";
import { ThumbsUp, ThumbsDown, X } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { trackEvent, EVENT } from "@/lib/tracking";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export function FeedbackWidget({
  component,
  context,
  className,
}: {
  component: string;
  context?: string;
  className?: string;
}) {
  const [rating, setRating] = useState<1 | 0 | -1 | null>(null);
  const [showComment, setShowComment] = useState(false);
  const [comment, setComment] = useState("");

  const mutation = useMutation({
    mutationFn: (body: { component: string; context?: string; rating: number; comment?: string }) =>
      api("/api/feedback", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => {
      trackEvent(EVENT.FEEDBACK_SUBMITTED, { component, rating: rating ?? 0 });
      toast.success("Tack!");
    },
    onError: () => {},
  });

  function handleRate(r: 1 | -1) {
    setRating(r);
    setShowComment(true);
    mutation.mutate({ component, context, rating: r, comment: "" });
  }

  function submitComment() {
    const c = comment.trim();
    mutation.mutate({ component, context, rating: rating ?? 0, comment: c || undefined });
    setShowComment(false);
    setComment("");
  }

  return (
    <div className={cn("inline-flex items-center gap-1", className)}>
      <span className="text-[10px] text-[var(--color-text-muted)] select-none">
        {rating === null ? "Hjälpsamt?" : rating === 1 ? "Tack!" : "Noterat"}
      </span>
      <button
        onClick={() => handleRate(1)}
        className={cn(
          "p-1 rounded-md transition-colors",
          rating === 1 ? "text-green-600 bg-green-50" : "text-[var(--color-text-muted)] hover:text-green-500",
        )}
      >
        <ThumbsUp size={14} strokeWidth={1.5} />
      </button>
      <button
        onClick={() => handleRate(-1)}
        className={cn(
          "p-1 rounded-md transition-colors",
          rating === -1 ? "text-red-600 bg-red-50" : "text-[var(--color-text-muted)] hover:text-red-500",
        )}
      >
        <ThumbsDown size={14} strokeWidth={1.5} />
      </button>
      {showComment && (
        <span className="flex items-center gap-1 ml-1">
          <input
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submitComment()}
            placeholder="Kort kommentar..."
            className="w-36 text-[11px] px-2 py-1 rounded border border-[var(--color-border)]
                       bg-[var(--color-bg-surface)] text-[var(--color-text-primary)]"
            autoFocus
          />
          <button onClick={submitComment}
            className="text-[10px] px-2 py-1 rounded bg-[var(--color-accent)] text-white">
            OK
          </button>
          <button onClick={() => setShowComment(false)}
            className="text-[var(--color-text-muted)]">
            <X size={12} />
          </button>
        </span>
      )}
    </div>
  );
}
```

### 5e. Admin feedback-sida

**Fil:** `apps/web/app/(app)/admin/feedback/page.tsx` — kopiera EXAKT:

```tsx
"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ThumbsUp, ThumbsDown, Minus, Download } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface FeedbackItem {
  id: string;
  user_id: string;
  component: string;
  context: string | null;
  rating: number;
  comment: string | null;
  created_at: string;
}

interface FeedbackData {
  feedback: FeedbackItem[];
  count: number;
  stats: { positive: number; negative: number; neutral: number };
  by_component: Record<string, { total: number; positive: number; negative: number; neutral: number }>;
}

const COMPONENTS = ["verdict_card", "explain_text", "theme_card", ""];

export default function AdminFeedbackPage() {
  const [filter, setFilter] = useState("");
  const { data, isLoading } = useQuery<FeedbackData>({
    queryKey: ["admin-feedback", filter],
    queryFn: () => {
      const params = new URLSearchParams({ limit: "200" });
      if (filter) params.set("component", filter);
      return api(`/api/admin/feedback?${params}`);
    },
    refetchInterval: 30_000,
  });

  function exportJSON() {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data.feedback, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `feedback-${new Date().toISOString().split("T")[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (isLoading) return <div className="p-8 text-sm text-[var(--color-text-muted)]">Laddar...</div>;

  const s = data?.stats ?? { positive: 0, negative: 0, neutral: 0 };
  const total = s.positive + s.negative + s.neutral;

  return (
    <div className="max-w-5xl mx-auto p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Feedback</h1>
        <button onClick={exportJSON}
          className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg border border-[var(--color-border)] hover:bg-[var(--color-bg-elevated)]">
          <Download size={14} /> Exportera JSON
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        <StatCard label="Totalt" value={total} />
        <StatCard label="Positiva" value={s.positive} color="text-green-600" />
        <StatCard label="Negativa" value={s.negative} color="text-red-600" />
        <StatCard label="Neutrala" value={s.neutral} color="text-[var(--color-text-muted)]" />
      </div>

      {/* Filter */}
      <div className="flex gap-1 flex-wrap">
        {COMPONENTS.map((c) => (
          <button key={c}
            onClick={() => setFilter(c)}
            className={cn(
              "text-xs px-3 py-1 rounded-full border transition-colors",
              filter === c
                ? "bg-[var(--color-accent)] text-white border-[var(--color-accent)]"
                : "border-[var(--color-border)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-elevated)]",
            )}>
            {c || "Alla"}
          </button>
        ))}
      </div>

      {/* Per-component breakdown */}
      {data?.by_component && Object.keys(data.by_component).length > 0 && (
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-[var(--color-text-muted)] border-b border-[var(--color-border)]">
              <th className="py-1 font-medium">Komponent</th>
              <th className="py-1 font-medium text-right">Totalt</th>
              <th className="py-1 font-medium text-right">👍</th>
              <th className="py-1 font-medium text-right">👎</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(data.by_component).map(([name, stats]) => (
              <tr key={name} className="border-b border-[var(--color-border-subtle)]">
                <td className="py-1.5">{name}</td>
                <td className="py-1.5 text-right">{stats.total}</td>
                <td className="py-1.5 text-right text-green-600">{stats.positive}</td>
                <td className="py-1.5 text-right text-red-600">{stats.negative}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Feedback list */}
      <div className="space-y-1">
        {data?.feedback.map((item) => (
          <div key={item.id} className="flex items-start gap-3 p-2 rounded-lg bg-[var(--color-bg-surface)] border border-[var(--color-border-subtle)]">
            <span className="mt-0.5">
              {item.rating === 1 ? <ThumbsUp size={14} className="text-green-600" /> :
               item.rating === -1 ? <ThumbsDown size={14} className="text-red-600" /> :
               <Minus size={14} className="text-[var(--color-text-muted)]" />}
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium">{item.component}</span>
                {item.context && <span className="text-[10px] text-[var(--color-text-muted)]">{item.context}</span>}
                <span className="text-[10px] text-[var(--color-text-muted)] ml-auto">
                  {new Date(item.created_at).toLocaleDateString("sv-SE")}
                </span>
              </div>
              {item.comment && (
                <p className="text-xs text-[var(--color-text-secondary)] mt-0.5 break-words">
                  {item.comment}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div className="p-3 rounded-xl bg-[var(--color-bg-surface)] border border-[var(--color-border-subtle)] text-center">
      <div className={cn("text-2xl font-semibold", color || "text-[var(--color-text-primary)]")}>{value}</div>
      <div className="text-[10px] text-[var(--color-text-muted)]">{label}</div>
    </div>
  );
}
```

Registrera i admin NavRail/TopBar — lägg till som admin-länk.

---

## 6. Sammanfattning filer

| Fil | Åtgärd | Radantal |
|---|---|---|
| `apps/web/lib/tracking.ts` | NY — abstraktionslager | ~50 |
| `apps/web/components/providers/TrackingProvider.tsx` | NY — Umami + SPA tracking | ~40 |
| `apps/web/app/(app)/layout.tsx` | Wrappa med TrackingProvider | +3 |
| `apps/web/components/ui/FeedbackWidget.tsx` | NY — tumme upp/ner komponent | ~80 |
| `apps/api/routers/feedback.py` | NY — POST /api/feedback | ~30 |
| `apps/api/main.py` | Registrera feedback-router | +2 |
| `apps/api/routers/admin.py` | GET /admin/feedback | +50 |
| `supabase/migrations/035_user_feedback.sql` | NY | ~25 |
| `apps/api/core/diagnostics.py` | Lägg 035 marker | +2 |
| `apps/web/app/(app)/admin/feedback/page.tsx` | NY — admin-vy | ~130 |
| `apps/web/components/onboarding/OnboardingModal.tsx` | +trackEvent | +3 |
| `apps/web/components/providers/ExperienceProvider.tsx` | +trackEvent i setLevel | +2 |
| `apps/web/app/(app)/aktie/[ticker]/StockView.tsx` | +trackEvent i mount | +5 |

---

## 7. Acceptanstest / Definition of Done

- [ ] `python scripts/smoke_test.py` — feedback-endpointen returnerar 401 utan token
- [ ] `cd apps/web && npx tsc --noEmit` — inga TypeScript-fel
- [ ] Umami deployad, script laddas i MarketScan, events syns i Umami-dashboard
- [ ] FeedbackWidget klickbar — tumme upp/ner skickar POST, toast visas
- [ ] Admin `/admin/feedback` visar feedback med filtrering
- [ ] Export-knapp laddar ner JSON
- [ ] Tracking fungerar utan Umami (graciös fallback)
- [ ] `docs/SYSTEM_AI.md` uppdaterad
