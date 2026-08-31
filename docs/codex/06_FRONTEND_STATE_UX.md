# 🎨 Kapitel 6: Frontend Architecture, State & UX Engine

> **Domän:** Next.js 15.5 frontend, React 18.3, TanStack React Query v5, Tailwind CSS v4 och designsystem.  
> **Status:** Aktiv produktion.

---

## 1. Executive Summary & TL;DR

Frontend (`apps/web/`) är en modern Next.js App Router-applikation byggd för snabb finansiell överblick och aktiescreening. Designfilosofin kombinerar "Lysa-lugn" visuell renhet med "Avanza-handlingsbar" funktionalitet. All state och asynkron datahantering sköts med TanStack React Query v5.

---

## 2. Arkitektur & Komponenthierarki

```
  Next.js 15 App Router (`apps/web/app/`)
  ├── (marketing)/                <-- Publika landningssidor
  ├── (auth)/                     <-- Inloggning, registrering, återställ lösenord
  └── (app)/                      <-- Autentiserad huvudapplikation
      ├── oversikt/               <-- Dashboard med dagens marknad & portföljsammanfattning
      ├── screener/               <-- Flerfaktorscreener med MasterRank & filter
      ├── aktie/[ticker]/         <-- Detaljerad aktieanalys, diagram, insider & AI-kommitté
      ├── portfolj/               <-- Innehav, Avanza CSV-import, transaktioner & risk
      ├── strategi-lab/           <-- Backtesting av anpassade investeringsstrategier
      ├── insider-radar/          <-- Klusterköp och insynsaktivitet från FI
      └── kontrollpanel/          <-- Admin-verktyg, systemhälsa och diagnostik
```

---

## 3. Datahämtning & State Management (React Query)

Klienten använder `apps/web/lib/api.ts` för alla API-anrop med automatisk JWT-injicering från Supabase Auth:

| Hook / Hook-fil | API Endpoint | Caching-strategi (staleTime) |
|---|---|---|
| `useStock(ticker)` | `/api/stocks/{ticker}` | 60 sekunder |
| `useScreener(params)` | `/api/scan` | 30 sekunder |
| `usePortfolio()` | `/api/portfolio` | Invalideras direkt vid mutationer |
| `useInsiderRadar()` | `/api/insider/radar` | 5 minuter |
| `useSmartAlerts()` | `/api/smart-alerts` | 60 sekunder |

---

## 4. Designsystem & UI-Regler

1. **Inga Emojis i UI:** Alla visuella symboler MÅSTE vara linjeikoner från `lucide-react`. Emojis är strikt förbjudna i användargränssnittet.
2. **InfoTooltip på ALLA Finansiella Värden:**
   - Varje nyckeltal (P/E, MasterRank, ROE, RSI, Volatilitet etc.) måste renderas med en `<InfoTooltip>` som förklarar måttet och hur det tolkas.
3. **Typografi & Font-stack:**
   - Brödtext & UI: `Inter` (sans-serif).
   - Finansiella priser & ticker-koder: `Geist Mono` (monospace) för stabil sifferjustering.
4. **Diagram-motorer:**
   - **Recharts:** Används för fördelningsdiagram (Donut, Pie), radar-diagram (`MultiFactorRadar.tsx`) och tidsserier.
   - **Lightweight Charts:** Används för högpresterande candlestick-kursdiagram.

---

## 5. Källkodskarta & Filankare

| Område | Mapp / Fil | Ansvar |
|---|---|---|
| API Klient | `apps/web/lib/api.ts` | Central fetcher med fallback och auth-headers |
| Global Layout | `apps/web/app/(app)/layout.tsx` | Navigationsramverk, TopBar och Command Palette |
| Aktievyn | `apps/web/app/(app)/aktie/[ticker]/page.tsx` | Huvudsida för aktiedetaljer |
| Portföljvy | `apps/web/app/(app)/portfolj/page.tsx` | Portföljöversikt och innehavshantering |
| Avanza Import | `apps/web/components/portfolio/ImportModal.tsx` | CSV-uppladdning och parsning |
| Design Tokens | `apps/web/app/globals.css` | CSS-variabler för Tailwind v4 tema |

---

## 6. Kritiska Gotchas

- **React 18.3 Låsning:** Uppgradera inte `react` eller `react-dom` till v19. Radix UI bryts av React 19.
- **Next.js 15 Async Params:** I Next.js 15 är route-parametrar asynkrona promises:
  ```typescript
  export default async function Page({ params }: { params: Promise<{ ticker: string }> }) {
    const { ticker } = await params;
  }
  ```
- **API URL Fallback:** Använd alltid `NEXT_PUBLIC_API_URL || "https://marketscan-api.vercel.app"` för att förhindra att tomma strängar leder till CORS-kollisioner mot samma origin.
