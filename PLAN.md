# [Usage Reduction] — Implementeringsplan: AI token/cost (opencode · Claude Code · Antigravity)

**Goal:** Sänka AI token/cost genom att mäta först, sedan köra ETT cache-buster-fönster med prefix-diet + modellrouting, och etablera per-harness-disciplin — utan att tappa Ground Truth eller bryta superpowers-planflödet.

**Scope/boundaries:**
- Görs EJ: kodrefaktoreringar (inga fil-splittar av StockView.tsx m.fl. — inte den verkliga cost-drivern).
- Görs EJ: teckna/avsluta prenumerationer — planen ger endast rekommendationer, kräver ditt beslut.
- Görs EJ: ändra innehåll i `docs/codex/**` (Ground Truth) — endast läspolicy för omkringliggande docs.
- Budgetapp + alla config-mappar utanför workspace: `not verified` tills access ges (Task 2).
- Antigravity: endast policy/beteende (ingen lokal config verifierad).

**Assumptions:**
1. marketscan-sessioner tvingas ladda ~170KB docs via "läs FÖRST"-kedjan: `CLAUDE.md:3` → `SYSTEM_INDEX.md`, `SYSTEM_AI.md:7` ("Läs ALLTID HANDOFF.md först", 1150 rader), `docs/SYSTEM_AI.md:3`, `docs/AI_GUIDE.md:9`, `DEBUGGING.md:4`, `docs/plan/00_MASTER_PLAN.md:7`; HANDOFF.md 595 rader, SETUP.md 349 (explore A + egen read — verifierade).
2. ~82-skills-manifest injiceras varje session (~10–15KB; exakt storlek `not verified` — mäts i Task 1).
3. opencode usage-data i SQLite `~/.local/share/opencode/opencode.db` (bekräfta med `opencode db path`; research, `not verified` lokalt).
4. Claude auto-cache invalideras av CLAUDE.md-edits/modellbyte (research, `not verified` live).
5. Claude: `/usage`(/cost)+`/context`; Pro $20 / Max $100–$200, 5h+weekly-windows delade mellan chat och Code; cancel-only (EEA/UK 14-dagars undantag). Antigravity: rider på Google AI Pro $19.99/Ultra $100–$200, 5h-fönster + weekly cap, AI-credits endast overage, auto-compact ~135k, Gemini implicit-cache 90 % rabatt. Research-baserat, `not verified` live.
6. Budgetapp på `C:\Users\hthur\Budgetapp` existerar (användarens besked) men är permission-nekat → recept i Task 2.
7. `scratch/test_ai_token_comparison.py` existerar (glob-bevis) — print-only-budgetkalkyl: används som målreferens, internt ej som parser.

**Dependencies (task-ordning):**
- Task 1 (baseline-data) → Task 3/4/5. **Task 3 → 4 → 5 = ETT cache-buster-fönster: körs samma dag, i den ordningen** (annars betalas full cache-pris per edit).
- Task 2 oberoende — körs när du ger access (öppna Budgetapp som workspace eller tillåt externa mappar).

**Downstream consumers (måste sweepas):**
- Skills-manifest/AGENTS.md → superpowers-plugin + `docs/superpowers/plans/2026-08-31-advisor-plan-mode.md:3` kräver `superpowers:subagent-driven-development` eller `superpowers:executing-plans` (grep-verifierat) → whitelista före arkivering.
- marketscan-docs → `scripts/verify_codex.py`-gate (SYSTEM_INDEX.md:59) måste vara grön efter Task 4.
- MCP context7: behåll själva tools (används), flytta ENDAST instructions-blocket (`~/.local/share`-block i marketscan CLAUDE.md) till on-demand-dok; gör `/mcp`-pruning i Claude endast om `/context` visar MCP-schemas som betydande post.
- Claude `/usage`-attribution per skill/subagent/MCP — används som evidens i Task 3/5.
- Inga kodtester berörs av doc-läspolicy-ändringarna; smoke_test/verify_codex oförändrade.

**Risks/fallback:**
- Cache-buster-dagen misslyckas halvvägs → avbryt, noll edits till nästa dag (billigare än fortsättning mid-session).
- Skills-arkivering bryter plan-docs → whitelist via `docs/superpowers/plans/*.md`-grep; arkivera (flytta till `skills-archive/`), radera ALDRIG.
- Doc-diet utan pekare → agenter tappar kontinuitet och bränner MER tokens → ersätt varje fullread med 30–50-radig index-pekare (SYSTEM_INDEX stärks, inte tas bort).
- opencode DB-schema kan variera över versioner → fallback `opencode stats --days N` + CSV-export.
- Antigravity-siffror research-baserade → endast rekommendationer; `not verified` märkning kvarstår.
- Subagent-fanout ≈7× tokens i plan-mode = tredjepartsestimat (hypotes) → bekräftas/förnekas av Task 1-data, görs inte förrän data visar det.

**Consultations:** explore ×3 (marketscan-docs, systemkärna, budgetapp — budgetapp fullt nekat), research ×1 (opencode stats/db, Claude /usage+limits, Antigravity plans, prompt-caching, bevisade lever), advisor ×1 (GLM-5.3: REVISE → batch-fönster, superpowers-whitelist, `/context`-attribution, manifest-tak; dess påstående att `scratch/test_ai_token_comparison.py` saknas motbevisades av egen glob — Code vinner över boken). Egna verifikationer: glob scratch + grep `superpowers:`.

---

### Task 1: Usage & attribution-baseline (3–5 dagar)

**Files:** Create `scripts/usage_report.py`, Create `.opencode/audit/usage-baseline.md`, Create snapshots i `C:\Users\hthur\AppData\Local\Temp\opencode\usage-baseline\`.

**Evidence:** `opencode stats --days --tools --models --project` + `opencode db path` (https://opencode.ai/docs/cli/); `scratch/test_ai_token_comparison.py` (print-only budgetkalkyl → målreferens, bygg parser från scratch); Claude `~/.claude/projects/**/*.jsonl` per-message-usage + `/usage` + `/context`.

**Interfaces:** Consumes: opencode SQLite/`opencode stats`, Claude JSONL, `/context`-snapshot (manuell rake 3–5 sessioner per harness). Produces: `usage_report.py` (per dag/modell/projekt/komponent: docs vs manifest vs MCP-tool-schemas vs system-prompt) + baseline-MD med datum + SEK-summa.

**Acceptance criteria:**
- Rapport med komponent-attribution per harness (ej bara kostnad — även orsak).
- Baseline-snapshot sparat med datum; `opencode db path` bekräftad.
- Parser fungerar på tomma/NULL-sessions (inga krascher).

**Verification:** `python scripts/usage_report.py` → CSV+MD; korscheck `opencode stats --days 7`. `not run` (plan-agent kör inte gates).

- [ ] Urläs opencode DB-schema → skriv SQLite-parser
- [ ] Claude `/context`-snapshot i ≥1 session per harness (rapport-checklista)
- [ ] Publicera baseline-MD + CSV (committad i marketscan)

---

### Task 2: Extern inventering + Budgetapp-recept (kräver åtkomst — ditt initiativ)

**Files:** Create `.opencode/audit/external-inventory.md`; (senare) `C:\Users\hthur\Budgetapp\scripts\usage_report.py` + `.opencode\audit\budgetapp-usage.md`.

**Evidence:** explore-resultat: alla externa sökvägar DENIED i plan-mode (`C:\Users\hthur\.config\opencode`, `.claude\`, `.antigravity\`, `C:\Users\hthur\Budgetapp`).

**Interfaces:** Consumes: när Budgetapp öppnas som workspace (eller `.claude\`/`.config\opencode\`/`.antigravity\` tillåts i permissions) körs samma scan-recept: instruktionsfiler+storlekar, "FÖRST"-citat, 10 största filer, `opencode.json`/`settings.json`/MCP-server-namn (INGA secrets). Produces: inventariefil per area med file:line + mappning "→ Task 3/4/5-item" eller "undantag".

**Acceptance criteria:**
- Varje extern area antingen evidens-citerad (file:line) eller explicit `not verified` + orsak.
- Budgetapp-fynd listar minst: auto-loadade docs + "läs FÖRST"-kedja + `.opencode`/`.claude`-status.

**Verification:** glob/grep på skapad fil; `not run` i plan-mode.

- [ ] Få bekräftelse på access från dig
- [ ] Skanna Budgetapp + system-config per recept ovan
- [ ] Publicera inventarie med prioriterade diet-items

---

### Task 3: System prefix-diet + skills-cap (cache-buster-dag, steg 1/3)

**Files:**
- Modify `C:\Users\hthur\.config\opencode\AGENTS.md` (slim ≤60 rader; bevara cache-/kostnads-/subagent-/encoding-regler + ny manifest-cap- och retirement-policy: max ~15 aktiva skills, nya skills kräver dokumenterat behov)
- Modify `C:\Users\hthur\OneDrive\Desktop\marketscan\CLAUDE.md` (flytta context7-instructions-blocket → `docs/ai/reference/README.md` + länk; ändra rad 3 till "läs index, sedan ENDAST relevant kapitel")
- Move `.agents\skills\` → `.agents\skills-archive\` (reversibelt): whitelista ALLA skills i `docs/superpowers/plans/*.md` + aktivt bruk enligt Task 1-data; superpowers-plugin-kärnor arkiveras ALDRIG.

**Evidence:** `docs/superpowers/plans/2026-08-31-advisor-plan-mode.md:3` (kräver `superpowers:subagent-driven-development`/`executing-plans` — verifierat); manifest ~82 skills (rättviselista i Task 1).

**Interfaces:** Consumes: Task 1-data (aktivt bruk per skill). Produces: slankare prefix + manifest.

**Acceptance criteria:**
- Ny session: available_skills ≤ ~15 poster; AGENTS.md ≤60 rader.
- Grep `superpowers:` i `docs/superpowers/plans/*.md` → alla refererade skills fortfarande aktiva.
- Inga skills raderade (alla i archive).

**Verification:** `opencode stats --days 1` efter ny session (context-input lägre än baseline); `/context`-snapshot jämförd med Task 1. `not run`.

- [ ] Slimma AGENTS.md + lägg manifest-policy (råder via redigering-verktyget, aldrig Set-Content — encoding-disciplin)
- [ ] Flytta context7-block → on-demand-dok + pekare i CLAUDE.md
- [ ] Whitelist-grep → arkivera icke-aktiva skills
- [ ] Starta ny session; verifiera manifest + prefix-storlek

---

### Task 4: Marketscan docs-diet (cache-buster-dag, steg 2/3)

**Files:**
- Modify `SYSTEM_INDEX.md` (stärk som index: "läs index + 1 relevant kapitel"; ta bort fullread-flöden; Gör EJ: ta bort roll-/routing-tabellerna)
- Modify `SYSTEM_AI.md` (1150 rader: aktiv ground truth behålls, historik/planer → `docs/archive/`; rad 7: "Läs ALLTID HANDOFF.md först" → 30–50-rads-pekare)
- Modify `docs/SYSTEM_AI.md` (469 rader → pekare på `docs/AI_GUIDE.md:9`), `HANDOFF.md` (595 → `docs/archive/` + kort pekare), `SETUP.md` (→ referens, ej auto-läst), `DEBUGGING.md:4`, `docs/plan/00_MASTER_PLAN.md:7` (pekare)
- Oförändrat: `docs/codex/**` (Ground Truth, alla kapitel <120 rader)

**Evidence:** explore A:s radantal/citat; SYSTEM_INDEX.md:54–59 (Living Documentation Directive, budget ≤500 rader/kapitel); `scripts/verify_codex.py` (gate).

**Interfaces:** Consumes: verify_codex-gate. Produces: session-start krävd läsning ≤ ~8KB (summa av tvingade docs, ej summan som görs tillgänglig).

**Acceptance criteria:**
- `python scripts/verify_codex.py` grön (alla kapitel ≤500 rader).
- Ingen tvingad fullread kvar: grep `Läs ALLTID|läs .*FÖRST|läs .*först` → alla träffar är pekare till index/kapitel, aldrig fulla docs.
- Varje pekare anger exakt fil + kapitel; lästid max ~5 min.

**Verification:** `python scripts/verify_codex.py` → `[OK]`-rader; manuellt: ny session utan "läs HANDOFF/SYSTEM_AI-fulltext". `not run`.

- [ ] Splitta SYSTEM_AI.md (ground truth vs arkiv) + ersätt rad 7 med pekare
- [ ] Pekare på docs/SYSTEM_AI, HANDOFF, SETUP, DEBUGGING, MASTER_PLAN
- [ ] Grep-sweep "FÖRST"-kedjan → inga fullreads kvar
- [ ] Kör verify_codex.py grön

---

### Task 5: Routing, subscription-karta & Claude/Antigravity-harness (cache-buster-dag, steg 3/3)

**Files:**
- Modify `C:\Users\hthur\.config\opencode\opencode.json` (default/small_model enligt Task 1-data; advisor-modell ENDAST för gate-beslut; högvariant endast vid behov)
- Modify `C:\Users\hthur\.claude\settings.json` (default-modell lägre klass för vardag; ställ in så att dyrare modeller kräver explicit val)
- Modify `C:\Users\hthur\.claude\CLAUDE.md`/init.md (trimma globalt referens-material)
- Modify `C:\Users\hthur\.claude\mcp.json` (disable servers som `/context`-data visar som top-poster)
- Create `C:\Users\hthur\.config\opencode\USAGE_POLICY.md`

**Evidence:** research: Claude Pro/Max-limits delas mellan chat+Code, 5h+weekly, cancel-only; Antigravity = Google AI Pro/Ultra (5h-window, credits overage-only, auto-compact ~135k); Gemini implicit-cache 90 %; subagent-fanout ≈7× i plan-mode (tredjepart — behandlas som hypotes); context7 CLI ≥ MCP (noll standing-context).

**Interfaces:** Consumes: Task 1-data (var kostnaden sitter). Produces: `USAGE_POLICY.md` med konkreta val per harness.

**Acceptance criteria:**
- USAGE_POLICY.md innehåller: harness→plan-karta (Claude Pro $20/Max $100 vs Google AI Pro $19.99/Ultra; vad som täcks var), kvartals-uppföljning, regler: ≤1–2 subagents i plan/felsökningsläge, `/compact` vid naturliga pauser (varm cache), aldrig återuppliva gamla sessioner, batch prefix-edits, all config-ändring i slutet av session.
- `/usage` efter 7 dagar visar modellfördelning enligt policy.
- Antigravity: dokumenterade rekommendationer (tier-fit, quota-fönster, compaction) — `not verified`-märkning kvarstår, inga filändringar mot ej verifierad config.

**Verification:** `/usage` + `opencode stats --models --days 7` jämfört mot Task 1-baseline. `not run`.

- [ ] Sätt default/small_model enligt Task 1-data (samma dag som 3–4)
- [ ] Claude settings + global CLAUDE.md-trim + MCP-pruning (endast top-poster per /context)
- [ ] Skriv USAGE_POLICY.md
- [ ] Verifiera efter 7 dagar mot baseline

---

## Verifiering och godkännande (gates — körs av build-agent efter din approbation)

1. `python scripts/usage_report.py` → baseline-snapshot sparat innan cache-buster-dag.
2. **En dags fönster:** Task 3 → 4 → 5 (i ordning, samma dag).
3. `python scripts/verify_codex.py` (marketscan) → `[OK]`.
4. `python scripts/smoke_test.py` → alla probes gröna (oförändrat beteende).
5. `opencode stats --days 7` + Claude `/usage` + `/context` → minskning mot baseline; modell/prefix-breakdown dokumenterad.
6. Grep-sweep `superpowers:` i `docs/superpowers/plans/` → alla sub-skills aktiva; grep "FÖRST"-kedjan → endast pekare kvar.
7. Rapportera FAKTISK utdata per kommando (aldrig påstå körda gates som inte körts).

## Confirm

- Presenterad PLAN.md (ersätter föregående smallcap-plan — den finns kvar i git: senast committad `4f27a53`); väntar på godkännande innan implementering.
- Task 2 kräver din åtgärd (access till Budgetapp/externa config-mappar) — säg till när det är dags.
