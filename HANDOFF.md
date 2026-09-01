# MarketScan 2.0 — Handoff Summary

> **Syfte:** Koncis överlämning för agenter.
> **Aktuell historik:** git log --oneline -20
> **Fullständigt arkiv:** docs/archive/HANDOFF-2026-09-01.md

## Systemkärna
- **Frontend:** Next.js 15.5 + React 18.3 (ej 19) + Tailwind CSS v4 + Radix UI.
- **Backend:** FastAPI på Vercel (stateless, def-handlers för DB).
- **Databas:** Supabase Postgres (eu-north-1, Stockholm, port 6543 pooler).
- **Design:** Lysa-lugn bas, Avanza-handlingsbar touch, inga emojis (Lucide), InfoTooltips överallt.

## Kritiska Invarianter
1. `backend_worker/` importeras ALDRIG av `apps/api/` (Vercel 500MB gräns).
2. React 18.3 — uppgradera inte till React 19.
3. Koden vinner över gamla dokument — verifiera mot `docs/codex/` och kör `python scripts/verify_codex.py`.
4. Git äger ändringshistoriken.
