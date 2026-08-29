# Handoff — fortsättning nattrond 2026-08-29 (dag 2)

ÖPPNA PUNKTER (från HANDOFF_DATASYSTEM_2026-08-29.md):
1. **P1 qmj/rank visar 2 rader** medan radarn visar ~140 — utred rotorsak med direkt REST mot qmj_scores.
2. **Sektor + SUE-data**: GH-runnern Yahoo-blockerad → fyll via LOKAL körning med DATABASE_URL (hemma-IP fungerar: yf.Lookup + earnings_dates verifierade lokalt).
3. **Död smart-alert-UI** — bygg regelhantering i Bevakningar (backend finns: GET/POST/PUT/DELETE /api/alerts).
4. **Survivorship-bias** i signal_analytics (_forward_return_at droppar utträdda bolag) — terminal-pris-fallback.
5. **Dependabot-PR** checkout 4.2.2→7.0.1 — rebase/CI/merge.
6. **Deploy-verifiering**: Vercel web + API färska; visuell QA (inloggad) radar + portfölj.

VERKTG: `vercel env pull` ger SUPABASE_URL/ANON_KEY/DATABASE_URL (skrivs till gitignorad fil? se .gitignore — bekräfta!). Uppdatera HANDOFF när punkter stängs.
