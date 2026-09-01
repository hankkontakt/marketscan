# MARKETSCAN — AI USAGE REDUCTION · ANTIGRAVITY-HANDOFF

> **Vem:** Google Antigravity (eller annan coding-agent). **Vad:** kör hela programmet nedan i ordning.
> **Var:** Windows, `C:\Users\hthur\`. Alla sökvägar absoluta. Kör från `C:\Users\hthur\OneDrive\Desktop\marketscan` som workspace-root.
> **Regel 0 — Code wins over book:** Om någon rad här inte stämmer med verkligheten (fil saknas, radnummer förskjutits, en gate fejar): verifiera själv, anpassa, dokumentera avvikelsen. Planen är ett recept, inte en religiös text.
> **Regel 1 — Kör aldrig gates du inte kört:** Rapportera FAKTISK kommandoutdata, aldrig "borde funka".
> **Regel 2 — Windows-encoding (kritisk):** PowerShell 5.1 `Set-Content`/`Get-Content`/`Out-File` dubbelkorrumperar svenska tecken (→ `â€"`). Skriv/editera ALLTID UTF-8-dokument via edit-verktyg eller .NET: `[System.IO.File]::WriteAllText($p, $t, (New-Object System.Text.UTF8Encoding($false)))`. Misstänkt korruption: `git grep -l "Ã¤\|â€\|Ã¶" -- .`
> **Regel 3 — Git:** Conventional commits (feat/chore/docs + scope), EN commit per avslutad våg. Ingen push utan uttryckt tillåtelse. Committa aldrig `.env`-värden/secrets eller PII.
> **Regel 4 — STOP för mänskliga beslut:** Prenumerationsbyten (Claude-plan, Google AI-plan) och access-byten utförs ALDRIG av agenten — endast rekommendationer i `USAGE_POLICY.md`. Om en permission-neck blockerar: skriv `DENIED: <sökväg>` och fortsätt; slutrapporten listar blockerarna.

---

## Bakgrund (varför programmet finns)

User betalar för AI-användning (opencode, Claude Code, Google Antigravity) och ser onödig tokenförbrukning. Tre verifierade cost-drivers:

1. **marketscan tvingar ~170KB docs-läsning vid sessionstart** via "läs FÖRST"-kedjan — `CLAUDE.md:3` → `SYSTEM_INDEX.md`; `SYSTEM_AI.md:7` "Läs ALLTID HANDOFF.md först" (SYSTEM_AI.md = 1150 rader); `docs/SYSTEM_AI.md:3` (469 rader); `docs/AI_GUIDE.md:9`; `DEBUGGING.md:4`; `docs/plan/00_MASTER_PLAN.md:7`; HANDOFF.md 595 rader; SETUP.md 349 rader. (+ `docs/codex/**`: 8 kapitel, 786 rader, alla <120 rader — små, ok, RÖR INTE innehållet.)
2. **~82 skills i `available_skills`-manifestet** (`C:\Users\hthur\.agents\skills\` + `.claude\skills\` + superpowers-plugin) injiceras varje session (~10–15KB uppskattat; mät i Wave 1).
3. **Cache-invalideringar:** Claude auto-cache betalar fullt pris när CLAUDE.md/AGENTS.md ändras eller modellen byts → alla prefix-editeringar MÅSTE samlas i ETT dagsfönster (Wave 2).

Bekräftade externa fakta (2026-09-01; källa i parentes):
- opencode: `opencode stats --days --tools --models --project`; SQLite `~/.local/share/opencode/opencode.db`; bekräfta med `opencode db path` (opencode.ai/docs/cli + GitHub issue 17765). Äldre install: `%APPDATA%\opencode`.
- Claude Code: `/usage` (alias `/cost`), `/context`; auto-cache invalideras av CLAUDE.md-edits/modellbyten (code.claude.com/docs/en/prompt-caching); subagent-grupper ≈7× tokens i plan-mode (tredjepartsestimat — behandla som hypotes).
- Anthropic-cache: manuell `cache_control`, skriv 1.25× (5 min) / 2× (1 h), läs 0.1× (platform.claude.com/docs).
- Gemini: implicit caching (standard på 2.5+), 90 % rabatt cachelagrade tokens (ai.google.dev/gemini-api/docs/caching).
- Antigravity: ingen fristående prenumeration — rider på Google AI Pro $19.99 / Ultra $100–$200; quota-cykel 5 h + weekly cap; AI-credits endast overage; auto-compact ~135k tokens (antigravity.google/docs/plans + blog). `not verified live` — märk om.

---

## DITT UPPDRAG (översikt)

| Wave | Innehåll | Filer som rörs | Gate |
|---|---|---|---|
| 1 | Instrumentering + baseline (ingen väntan) | `scripts/usage_report.py` + `.opencode/audit/usage/*` | script körs |
| 2 | **EN DAG** prefix-diet + marketscan docs-diet + routing/policy | `.config\opencode\AGENTS.md`, `marketscan\CLAUDE.md`, `.agents\skills\*`, marketscan-docs, `opencode.json`, `~\.claude\settings.json`, `~\.claude\CLAUDE.md`, `~\.claude\mcp.json` | verify_codex + smoke + tsc |
| 3 | (Villkorad) Budgetapp + extern config-inventering | `C:\Users\hthur\Budgetapp\*`, `~\.config\opencode\`, `~\.claude\`, `~\.antigravity\` | inventarie-fil |
| 4 | Slutgates + jämförelserapport | `.opencode/audit/usage/usage-after-*.md` | alla gates |

**Ordningsregel (viktig!):** Wave 2 = ett enda dagsfönster, delarna A→B→C i den ordningen. Avbryt hellre mitt i dagen än att fortsätta nästa dag — varje separat edit-dag kostar en full cache-write för ett ~170KB-prefix.

---

## WAVE 1 — Instrumentering & baseline (inget att vänta på; DB:n har historik)

### 1.1 Skapa `scripts/usage_report.py` (i marketscan-repot)

**Konsumerar:** (a) `opencode db path` → SQLite (tabeller för sessions/parts med token/cost; undersök schema först: `sqlite3 <db> .tables`), fallback `opencode stats --days 30 --project marketscan --tools --models`; (b) `C:\Users\hthur\.claude\projects\**\*.jsonl` — per-meddelande `usage` + `costUSD` (eller `cost`); (c) prefix-storlek: mät bytes av `C:\Users\hthur\.config\opencode\AGENTS.md` + antal skill-dirar i `.agents\skills\`, `.claude\skills\`, `.config\opencode\node_modules\superpowers\skills\` (uppskatta 30 tokens/skill-post).

**Producerar** (ingen pandas — ren stdlib sqlite3/json/csv):
- `.opencode/audit/usage/usage-baseline-<ISO-datum>.csv` — kolumner: datum | harness | modell | prompt_tokens | completion_tokens | cache_read | cache_write | cost_usd
- `.opencode/audit/usage/usage-baseline-<ISO-datum>.md` — sektioner: (1) totalsummor 30 d; (2) per modell; (3) per komponent: docs (markerad/uppskattad från prefix-mätning), manifest-skills, MCP-schemas (mät via `/context` i 3 Claude-sessioner, manuell logg i MD), system-prompt; (4) SEK-summa (USD×11).
- Fånga även: `opencode db path`-utdatat och `opencode stats --days 30`-utdatat oförändrat i MD:n.

**Gate 1:** `python scripts/usage_report.py` slutkörs utan fel; MD + CSV existerar och innehåller riktiga siffror (inte 0/None överallt — om DB är tom, korsvalidera med `opencode stats` och skriv "källa X").
**Vilken våg som helst: skriv ALDRIG secrets/API-nycklar; JSONL/DB kan innehålla prompts — sammanfatta, citera INTE rå prompttext.**

### 1.2 /context-sampling (3 sessioner, räcker)

I 3 Claude-Code-sessioner (marketscan): kör `/context` i början, logga breakdown-rad, till `.opencode/audit/usage/context-breakdown.md` (datum, summa system/Claude-läge, top-3-grupper). Detta blir underlaget för Wave 2:C:s MCP-pruningsbeslut.

---

## WAVE 2 — CACHE-BUSTER-DAG (A → B → C, samma dag)

### A. System prefix-diet + skills-cap

**2A-1. `C:\Users\hthur\.config\opencode\AGENTS.md`** — slimma till ≤60 rader. FÖRSLAG på vad som står kvar (inte raderat, sammanfattat): Verifiering-och-konto-regler; encoding-disciplin (utf8-bad); subagent-disciplin (korta briefs ≤2KB, verifiera artefakter); kostnadsregeln (deepseek-first, variant high/low, eskalera bara vid 2 failade gates); cache-disciplin (batcha prefix-edits till sessionens slut, byt aldrig modell/verktyg mitt i session); nya uppgifter = nya sessioner, /compact; self-suggestion (NY REGEL: max ~15 aktiva skills i `.agents\skills\` — nya kräver dokumenterat behov och godkännande; inaktiva flyttas till `skills-archive\`); git-hygien; nattkör-flagga.
**Felväg:** Inga regler får strykas tyst — om du måste ta bort en regel: flytta den till en kommentar/README-referens och nämn det i rapporten.

**2A-2. Skills-arkivering (reversibel — flytta, radera aldrig):**
- Skapa `C:\Users\hthur\.agents\skills-archive\` och flytta dit inaktiva skill-kataloger från `.agents\skills\`.
- **WHITELIST (får ej flyttas):** (1) alla skills refererade i `docs/superpowers/plans/*.md` — aktuellt: `superpowers:subagent-driven-development`, `superpowers:executing-plans` (verifiera med grep `superpowers:` och lägg till alla nya); (2) alla i `.config\opencode\node_modules\superpowers\skills\` (plugin-interna — rör inte plugin-mappen alls); (3) skills med aktiv användning enligt Wave 1-data; (4) kärnorna agenten pekar på i denna plan: `deep-think` (finns i BÅDE `.agents\skills\` och superpowers), `plan-mode`.
- **Gate A:** grep `superpowers:` i `docs/superpowers/plans/*.md` → alla referenser fortfarande aktiva. Manifest-storleken efter: räkna `Get-ChildItem .agents\skills`-kataloger — mål ≤15.

**2A-3. `C:\Users\hthur\OneDrive\Desktop\marketscan\CLAUDE.md`:**
- Flytta hela `<mcp_instructions>`-blocket (context7) → `docs\ai\reference\mcp-context7.md`; behåll EN rad i CLAUDE.md: "MCP/context7: se docs/ai/reference/mcp-context7.md vid behov."
- Rad 3: `AI/Claude: läs SYSTEM_INDEX.md FÖRST.` → `AI/Claude: Läs SYSTEM_INDEX.md (index) först; läs sedan ENDAST relevant kapitel i docs/codex/. Fulla omläsningar av stora docs (SYSTEM_AI/HANDOFF/SETUP) är FÖRBJUDNA — använd pekare.`
- Behåll: prime directives, snabbreferens-tabell, verifiera-före-commit, gotchas (alla redan korta och värdefulla).

### B. Marketscan docs-diet (ersätt fullreads med 30–50-rads-pekare)

| Fil | Åtgärd |
|---|---|
| `SYSTEM_AI.md` (1150 rader) | Splitta: aktiv ground truth (mål ≤200 rader) behålls; per-runda-historik/planer → `docs\archive\system-ai-2026-09-01.md`. Rad 7 "Läs ALLTID HANDOFF.md först" → "HANDOFF-arkiv: se docs/archive/ (kursivt: current state = git)." |
| `docs/SYSTEM_AI.md` (469 rader) | → 20-rads-pekare till `docs/codex/00-04` + `docs/AI_GUIDE.md`; original → `docs/archive/` |
| `HANDOFF.md` (595 rader) | → 25-rads-sammanfattning ("senaste: git log --oneline -20") + original → `docs/archive/HANDOFF-2026-09-01.md` |
| `SETUP.md` (349 rader) | → referens-dok (läs på begäran); ta bort ur alla "först"-kedjor (sök `SETUP` i CLAUDE.md/SYSTEM_INDEX) |
| `DEBUGGING.md:4` | "Läs detta FÖRST vid felrapportering" → "Vid fel: läs DEBUGGING.md + docs/codex/04 (pekare)" |
| `docs/plan/00_MASTER_PLAN.md:7` | "Läs ALLTID detta dokument först" → pekar-form; kvar som plan-arkiv |
| `SYSTEM_INDEX.md` | BEHÅLLS som index (det ÄR pekaren). Endast småpasta: tydligare "läs ENDAST relevant kapitel". |

**RÖR INTE:** `docs/codex/**` (Ground Truth), `scripts/verify_codex.py`, källkoden helt och hållet, `supabase/`, `apps/`, `backend_worker/`.
**Gate B:** `python scripts/verify_codex.py` → grönt (`[OK]`-rader för alla kapitel). Grep `Läs ALLTID|läs\s+.*FÖRST|läs\s+.*först` i `*.md` → inga fullreads kvar, bara pekare/antydningar.

### C. Routing, Claude/Antigravity-harness & policy

**2C-1. `C:\Users\hthur\.config\opencode\opencode.json`** (säkerhetskopiera original först): sätt/certifiera `small_model` (billigaste dagliga ops-modellen, t.ex. deepseek-flash low) och default-modell (deepseek-v4-flash, variant high för riktiga uppgifter, low för trivialt); advisor-modeller (GLM-5.3/K3) endast för gate-beslut (2 per uppgift max). Om filen saknas: skapa med ENDAST dessa nycklar + befintliga providers oförändrade.

**2C-2. `C:\Users\hthur\.claude\settings.json`** (säkerhetskopiera!): sätt lägre default-modell (t.ex. Sonnet) för vardag; dyrare modell endast explicit. **Rör inte:** auth/API-nycklar, account-IDs. Om settings saknas: hoppa över och dokumentera.

**2C-3. Global CLAUDE.md** (`~\.claude\CLAUDE.md` eller `init.md`): trimma referensmaterial till on-demand (max ~40 rader; använd pekare på filer i stället för fulltext). Märk: allt här påverkar Claude-prefix-cachen — görs i Wave 2, aldrig senare.

**2C-4. `~\.claude\mcp.json`:** disable ENDAST de servers som `/context`-data (Wave 1.2) visar i top-3 med stor yta OCH som inte används av repository-instruktioner. context7 får DISABLA endast om `/context` visar den dominerande posten — annars behåll funktionen och flytta bara instruktionsblocket (redan gjort i 2A-3). Notera varje disable + motivering.

**2C-5. Skapa `C:\Users\hthur\.config\opencode\USAGE_POLICY.md`** (RAPPORT — den agenten inte tillhandahåller; besluten stannar hos människan):
- Harness→plan-karta: Claude Pro $20 / Max $100 / Max $200 (5 h + weekly, delade mellan chat+Code, cancel-only, EEA/UK 14-dagars undantag) · Google AI Pro $19.99 / Ultra $100/$200 (5 h-cykel, weekly cap, credits overage-only; Antigravity rider på dessa, auto-compact ~135k) · opencode = per-token via opencode-go-provider (noll abonnemang).
- Regler: ≤1–2 subagents samtidigt i plan/felsökningsläge (fanout ≈7× tokens — hypotes tills Wave 1-data visar); `/compact` vid naturliga pauser (varm cache) — återuppliva ALDRIG gamla sessioner; batch prefix-edits till sessionsslut; byt aldrig modell/verktyg mitt i session; veckovis `opencode stats --days 7` + `/usage`-koll; kvartalsöversyn.
- Faktabaserade ALLTID med `not verified`-märkning där källan saknas.

---

## WAVE 3 — Budgetapp & extern inventering (VILLKORAD)

**Förutsättning:** access till `C:\Users\hthur\Budgetapp` (och ev. `.config\opencode\`, `.claude\`, `.antigravity\`). Antigravity startad från marketscan kan MÖTA permission-neck. Testa först: en listing av `C:\Users\hthur\Budgetapp`.
- **Om tillåtet:** kör samma recept som ovan: (1) instruktionsdok + storlekar; (2) "läs FÖRST"-kedja (citera file:line); (3) 10 största filer; (4) `.opencode\`/`.claude\`-status; (5) `git log --oneline -15`; (6) kör sedan Wave 1-motsvarighet + diet på samma prinsiper (sänn: fullreads→pekare; AGENTS/CLAUDE-smältning; routing per Wave 2:C). Skriv allt → `budgetapp\usage-report.md` + `budgetapp\PLAN-REMAINING.md` om något kvarstår.
- **Om nekad:** `.opencode/audit/external-inventory.md` med `DENIED: <varje sökväg>` + exakt vad som krävs (workspace-root eller permission-allow). Avsluta Wave 3; resten av uppdraget slutförs ändå.

---

## WAVE 4 — Slutgates & jämförelserapport

**Gates (alla `not run` förut — nu KÖR!):**
```powershell
# 1. Codex-ground truth
python scripts/verify_codex.py                # → alla [OK]
# 2. Inga imports-regler brutna
PYTHONPATH=. python -c "from apps.api.main import app; print(len(app.routes))"   # → tal >0, spara
# 3. Smoke (30 probes)
python scripts/smoke_test.py                  # → [OK]-rader, inga fel
# 4. Frontend-types
cd apps/web; npx tsc --noEmit                 # → 0 fel
# 5. Tester
cd ..; PYTHONPATH=. python -m pytest apps/api/tests backend_worker/tests -v      # → record resultat
# 6. Usage-jämförelse (efter ≥3 dagar, dvs. en UPPFÖLJNINGSKÖRNING)
opencode db path
opencode stats --days 7 --project marketscan
python scripts/usage_report.py
```
**Slutprodukt:** `.opencode/audit/usage/usage-after-<ISO-datum>.md` — tabell före/efter: prompt_tokens/dag, cache_read/dag, cost USD/dag per modell, prefix-storlek (AGENTS.md rader, manifest-storlek, krävd docs-stack KB). Delta per komponent; missförhållanden → `not verified` + förklaring. **Kom ihåg att skriva in FAKTISK utdata (kommandot + resultatet) i slutrapporten — aldrig påstå ett gate som inte körts.**

**Commit-plan (conventional, en per våg):**
- `chore(scripts): usage instrumentation + baseline`
- `chore(ai-cost): system prefix diet + skills cap + docs pointers (cache-buster wave)`
- `docs(ai-cost): USAGE_POLICY + external inventory` (om Wave 3 kördes)
- `docs(ai-cost): before/after usage report`

---

## STOPP-VILLKOR (kör aldrig förbi utan mänskligt beslut)

1. **Prenumerationsförändringar** (Claude-plan, Google AI-plan, provider-konto) — endast rekommenderas, aldrig aktiveras.
2. **Access-byten** (permission-policy, workspace-root) — be människan.
3. **Källkodsstörningar** utöver CLAUDE.md/AGENTS.md-config: `apps/`, `backend_worker/`, `supabase/migrations/`, `docs/codex/` — RÖRS INTE. Varje föreslagen `src`-ändring hamnar i rapporten, inte i koden.
4. **Radering av data/dokument:** Arkiv — flytta, aldrig ta bort (historik = dokumenterad).
5. **En gate misslyckas:** stoppa vågkedjan, ge exakt utdata, vänta på mänskligt beslut.

---

## CHECKLISTA (gå igenom i slutet)

- [ ] `scripts/usage_report.py` kör utan fel och producerade baseline-CSV+MD med riktiga siffror
- [ ] `opencode db path`-utdata fångat som bevis för datakälla
- [ ] AGENTS.md ≤60 rader; manifest ≤15 skills; `superpowers:`-grep mot `docs/superpowers/plans/*.md` → grönt
- [ ] CLAUDE.md:s context7-block bort ur prefixet; "läs FÖRST"-kedjan ersatt av pekare (SYSTEM_INDEX + codex-kapitlet)
- [ ] `verify_codex.py` grön; `smoke_test.py` grön; `tsc --noEmit` 0 fel; pytest-resultat inspelat
- [ ] USAGE_POLICY.md skapad (mänskliga beslut listade som öppna frågor, inget aktiverat)
- [ ] Wave 3: Budgetapp antingen dietad, alternativt `denied`-dokumenterad
- [ ] Uppföljningskörning (≥3 dagar senare): före/efter-rapport med FAKTISK utdata
- [ ] Inga secrets/PII i någon skapad fil (svep: `git grep -i "sk-|api[_-]?key|token" <nya filer>`)
