# Spec 10 — #12: Portfolio Coach (proaktiv, daglig)

> **Repo:** marketscan (API + frontend). **Insats:** S–M.
> **Skriven för:** DeepSeek v4-flash. Läs `docs/plan/00_MASTER_PLAN.md §6` (särskilt §6.6:
> ALDRIG orderläggning/finansiell rådgivning) först.

## Mål
Daglig personlig briefing: "Du är 62 % övervikt tech, Tesla 18 % (över din maxgräns 12 %),
vol 16 % vs mål 12 %. 3 förslag…". **Alla siffror beräknas i Python; LLM:en får bara dem
(grounding) — den hittar aldrig på tal och föreslår aldrig att lägga order.**

## Finding (viktigt)
`POST /ai/portfolio-coach` finns REDAN (reaktiv chatt) i `apps/api/routers/ai.py`. Detta är en
NY, **proaktiv + cachad** variant — duplicera inte chatten, lägg en separat GET-endpoint.

## Återanvänd (exakt)
- `apps/api/routers/ai.py`: cache-helpers `from apps.api.core.ai_cache import get_cached, set_cache`
  (`get_cached(key, sb_admin)` / `set_cache(key, resp, sb_admin)`); DeepSeek-helper
  `_call_ai(system_prompt, user_message, max_tokens=500)` (async).
- `apps/api/core/portfolio_construction.py` (sektorallokering/koncentration om helpers finns).
- Riskprofil: `user_risk_profiles` (migration 032): `profile`, `max_position_pct`, `target_volatility`.
- Portföljvol: befintlig `/api/portfolio/analytics`-logik (Sharpe/vol).
- Regim: `/api/markets/regime`.

## Steg

### 1. API `apps/api/routers/ai.py` — `GET /api/ai/daily-coach`
Kräver `user: User = Depends(get_current_user)`, `sb_admin = Depends(get_supabase_admin)`.
1. **Beräkna fakta i Python (ej LLM):**
   - Portfölj: hämta `holdings` + priser (befintlig enrichment), beräkna positionsvikter,
     `largest_position` (ticker + %), sektorvikter + största sektorövervikt, koncentration
     (t.ex. topp-3-vikt). Återanvänd `portfolio_construction`-helpers om de finns, annars inline.
   - Riskprofil-rad → `max_position_pct`, `target_volatility`, `profile`.
   - Portföljvol (årlig) från analytics-logiken.
   - Regim (`regime`, `label`).
   - Samla i dict `coach_facts` (alla tal, avrundade).
   - Flagga avvikelser i Python: `largest_position_pct > max_position_pct`, `vol > target_volatility`.
2. **Cache:** `cache_key = f"daily_coach:{user.id}:{date.today().isoformat()}"`.
   `cached = get_cached(cache_key, sb_admin)`; om finns → returnera.
3. **Prompt:**
   - system: "Du är en kvantitativ portföljrådgivare. Svara på svenska, max 250 ord. ANVÄND
     ENDAST de siffror du får — hitta inte på tal. Peka på övervikter/risker och ge 3
     konkreta, handlingsbara förslag. Föreslå ALDRIG att lägga order automatiskt."
   - user: `json.dumps(coach_facts, ensure_ascii=False)`.
   - `text = await _call_ai(system_prompt, user_message, max_tokens=600)`.
4. **Svar** `DailyCoachOut`:
   ```json
   { "briefing": "<text>", "facts": {...}, "date": "YYYY-MM-DD",
     "disclaimer": "Detta är inte finansiell rådgivning. Inga affärer läggs automatiskt." }
   ```
   `set_cache(cache_key, <hela svaret>, sb_admin)`. Tom portfölj → returnera
   `{briefing:"", facts:{}, empty:true, disclaimer:...}` (ingen LLM-körning).

### 2. Frontend
- Hook `apps/web/hooks/useDailyCoach.ts`: `GET /api/ai/daily-coach`, staleTime 6h.
- Kort "Din portföljcoach" överst på `app/(app)/portfolj/PortfoljView.tsx` OCH på
  Hem-dashboarden (spec 07). Visa `briefing` + alltid `disclaimer` (liten grå text).
  `empty` → "Lägg till innehav för en coach-briefing →" (länk `/portfolj`).

### 3. Kostnad
Cachat per user/dag → max 1 LLM-anrop/user/dag (DeepSeek via `_call_ai`; Gemini-fallback finns
i llm-lagret men `_call_ai` använder DeepSeek direkt — OK för enstaka användare).

## Acceptanstest
- `GET /api/ai/daily-coach` (inloggad, portfölj finns) → briefing som matchar `facts`
  (jämför manuellt mot portföljen — koncentration/övervikt/vol stämmer). Inga uppdiktade tal.
- Andra anropet samma dag → cache-hit (ingen LLM-körning; verifiera via logg/snabbhet).
- `disclaimer` alltid med; coachen föreslår aldrig automatisk orderläggning. `tsc` grönt.

## Definition of Done
- [ ] `GET /api/ai/daily-coach` med Python-beräknade fakta + grounding-prompt + cache + disclaimer.
- [ ] Hook + "Din portföljcoach"-kort på portföljsidan + Hem.
- [ ] Tom-portfölj-fallback.
- [ ] `docs/SYSTEM_AI.md` uppdaterad.
