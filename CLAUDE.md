# MarketScan

> 🧭 **AI/Claude: Läs `SYSTEM_INDEX.md` (index) först; läs sedan ENDAST relevant kapitel i `docs/codex/`. Fulla omläsningar av stora docs (SYSTEM_AI/HANDOFF/SETUP) är FÖRBJUDNA — använd pekare.**

> **Samarbetsstil:** Svara på svenska som en vanlig, insiktsfull AI-kollega.
> Börja med det användaren behöver veta. Förklara ändringar och verifiering i
> naturlig prosa när de är relevanta, utan mekaniska statusmallar,
> verktygsnarration eller tomma "nästa steg". Se även `AGENTS.md`.
> För operativ felsökning och buggmönster, se även `docs/AI_GUIDE.md` och `docs/CONTRIBUTING.md`. MCP/context7: se `docs/ai/reference/mcp-context7.md` vid behov.

## Prime directives
1. **Felsök, gissa inte.** Kör diagnostikverktygen innan du teoretiserar.
2. **Anta inget — verifiera mot live/kod.** Proba med `curl`, kör smoke-testet.
3. **Felet du ser är sällan rotorsaken.** Följ kedjan till botten.
4. **Bevara säkerhet + datakorrekthet.** RLS, GRANTs, auth-dependencies är inte valfria.
5. **Underhåll Living AI Codex in-place.** Ändra alltid berörda kapitel i `docs/codex/` direkt när du ändrar kod. Inga mikro-changelogs i dokumenten — dokumenten beskriver 100% aktiv mark sanning (Ground Truth).

## Snabbreferens
| Vad | Var |
|---|---|
| AI Master Index | `SYSTEM_INDEX.md` (och `llms.txt`) |
| System Codex (Alla domäner) | `docs/codex/` |
| Operativ AI-manual | `docs/AI_GUIDE.md` |
| Konventioner/checklista | `docs/CONTRIBUTING.md` |
| API-ingång | `apps/api/main.py` |
| Tre Supabase-klienter | `apps/api/dependencies.py` |
| DB-felhantering | `apps/api/core/db.py` |
| Router-mall (nya features) | `apps/api/routers/_TEMPLATE.py` |
| Djupdiagnostik | `GET /api/admin/diagnostics/deep` · `apps/api/core/diagnostics.py` |
| Smoke-test | `python scripts/smoke_test.py` |
| Codex-validerare | `python scripts/verify_codex.py` |
| Frontend API-klient | `apps/web/lib/api.ts` |
| Migrationer | `supabase/migrations/` (appliceras direkt med `supabase db push --linked`) |

## Verifiera före commit
```bash
python scripts/verify_codex.py
PYTHONPATH=. python -c "from apps.api.main import app; print(len(app.routes))"
python scripts/smoke_test.py
cd apps/web && npx tsc --noEmit
```

## Mest kritiska gotchas
- **`backend_worker/` i `apps/api/` är FÖRBJUDET** → Vercel 500MB gräns. Inget pandas/xgboost i API.
- **`42501 permission denied`** → kör `supabase/migrations/023_grant_table_privileges.sql`.
- **"Nätverksfel"** → CORS-löst serverfel (global handler fixar) eller fel `API_BASE`.
- **`def` inte `async def`** för synkrona Supabase-handlers (annars blockeras event-loopen).
- **service_role** (`get_supabase_admin`) endast bakom `require_admin`.
