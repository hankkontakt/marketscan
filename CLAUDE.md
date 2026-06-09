# MarketScan

> 🧭 **AI/Claude: läs `docs/AI_GUIDE.md` FÖRST.** Det är den operativa manualen —
> hur du ska tänka, hela arkitekturen, alla verktyg (diagnostik, smoke-test,
> db-helpers, router-mall), buggmönster och steg-för-steg för vanliga uppgifter.
> `docs/SYSTEM_AI.md` är referens-uppslagsverket. `docs/CONTRIBUTING.md` är
> konventioner + checklistor.

## Prime directives
1. **Felsök, gissa inte.** Kör verktygen i §3 av `AI_GUIDE.md` innan du teoretiserar.
2. **Anta inget — verifiera mot live/kod.** Proba med `curl`, kör smoke-testet.
3. **Felet du ser är sällan rotorsaken.** Följ kedjan till botten.
4. **Bevara säkerhet + datakorrekthet.** RLS, GRANTs, auth-dependencies är inte valfria.
5. **Håll `SYSTEM_AI.md` (changelog) + `AI_GUIDE.md` uppdaterade.**

## Snabbreferens
| Vad | Var |
|---|---|
| Operativ AI-manual | `docs/AI_GUIDE.md` |
| Referensdok | `docs/SYSTEM_AI.md` |
| Konventioner/checklista | `docs/CONTRIBUTING.md` |
| API-ingång | `apps/api/main.py` |
| Tre Supabase-klienter | `apps/api/dependencies.py` |
| DB-felhantering | `apps/api/core/db.py` |
| Router-mall (nya features) | `apps/api/routers/_TEMPLATE.py` |
| Djupdiagnostik | `GET /api/admin/diagnostics/deep` · `apps/api/core/diagnostics.py` |
| Smoke-test | `python scripts/smoke_test.py` |
| Frontend API-klient | `apps/web/lib/api.ts` |
| Migrationer (körs manuellt) | `supabase/migrations/` |

## Verifiera före commit
```bash
PYTHONPATH=. python -c "from apps.api.main import app; print(len(app.routes))"
python scripts/smoke_test.py
cd apps/web && npx tsc --noEmit
```

## Mest kritiska gotchas
- **`42501 permission denied`** → kör `supabase/migrations/023_grant_table_privileges.sql`.
- **"Nätverksfel"** → CORS-löst serverfel (global handler fixar) eller fel `API_BASE`.
- **`def` inte `async def`** för synkrona Supabase-handlers (annars blockeras event-loopen).
- **service_role** (`get_supabase_admin`) endast bakom `require_admin`.
