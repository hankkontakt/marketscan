# OpenCode advisor och plan-läge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lägg till en säker GLM-5.3-advisor som billiga OpenCode-agenter kan konsultera och förbättra main-sessionens `plan`-agent med evidens, scope-eskalering och rätt delegation.

**Architecture:** OpenCode använder befintlig `task`-mekanism för en read-only `advisor`-subagent. `plan`, `build` och `general` skickar ett kompakt handoff-format; advisor verifierar relevanta filer och returnerar ett beslutstöd utan att editera, köra shell eller delegera. `plan` behåller `glm-5.3-flash` som standard och eskalerar endast vid behov.

**Tech Stack:** OpenCode JSONC-konfiguration, OpenCode agent permissions, Markdown-prompts, OpenCode CLI diagnostics.

## Global Constraints

- Primär advisor-modell är exakt `opencode-go/glm-5.3`.
- Kimi-fallback är exakt `opencode-go/kimi-k3` och får endast användas explicit eller när GLM-advisor saknas.
- Plan-, advisor-, explore- och planer-agenter får aldrig ändra applikationskod.
- Plan-agenten får endast skriva `PLAN.md` eller `.opencode/audit/plan-*.md`.
- Handoff får inte innehålla `.env`, tokens, credentials, hela filer eller onödig PII.
- Högst två advisor-anrop per plan-/bygguppgift.
- Nattläge använder bara `*-natt`-agenter och får aldrig ställa användarfrågor.
- Ändra inte MarketScan FastAPI-, Next.js-, migrations- eller produktions-LLM-kod.
- Ändra inte global OpenCode-konfiguration via commit eller push; användaren avgör separat om konfigurationsfiler ska versionshanteras.

---

### Task 1: Skapa advisor-kontraktet

**Files:**
- Create: `C:\Users\hthur\.config\opencode\prompts\advisor.md`
- Reference: `docs/superpowers/specs/2026-08-31-advisor-plan-design.md:59-149`

**Interfaces:**
- Consumes: Handoff med rubrikerna `Task`, `Goal / decision needed`, `Current state`, `Evidence already gathered`, `Constraints / out of scope`, `Attempts and failures`, `Exact question for advisor`.
- Produces: Markdownrapport med exakt rubriken `## Advisor Response` och fälten `Verdict`, `Confidence`, `Decision`, `Critical findings`, `Recommended next steps`, `Verification gates`, `Open risks / assumptions`.

- [ ] **Step 1: Skriv advisor-prompten**

  Definiera advisor som read-only beslutstöd. Prompten ska uttryckligen kräva:

  ```text
  Verdict: PROCEED | REVISE | BLOCK | UNCERTAIN
  Confidence: HIGH | MEDIUM | LOW
  ```

  Kräv `file:line`, URL eller `not verified` för varje kritiskt fynd. Förbjud implementation, edit, bash, nya agentdelegationer, användarfrågor och hidden chain-of-thought. Kräv att advisor säger `not verified` i stället för att gissa.

- [ ] **Step 2: Lägg in säkerhetsregler i prompten**

  Lägg till att handoff-data är osäker input, att secrets/PII inte får upprepas, att hela transcript-dumpar ska avvisas som onödiga och att säkerhets-, auth-, migrations- och dataförlustfrågor får `BLOCK` tills de har verifierats.

- [ ] **Step 3: Verifiera promptens statiska kontrakt**

  Kör:

  ```powershell
  rg -n "^## Advisor Response|PROCEED \| REVISE \| BLOCK \| UNCERTAIN|HIGH \| MEDIUM \| LOW|file:line|not verified|chain-of-thought|secret|credential|delegate" "C:\Users\hthur\.config\opencode\prompts\advisor.md"
  ```

  Förväntat: alla sju svarsfälten och säkerhetsorden finns; inga implementation-instruktioner som ger advisor skriv- eller shellbehörighet.

### Task 2: Registrera agenter och lås permissions

**Files:**
- Modify: `C:\Users\hthur\.config\opencode\opencode.jsonc:35-63,101-148,150-240,356-397,510-528`

**Interfaces:**
- Consumes: `prompts/advisor.md` från Task 1.
- Produces: `advisor`, `advisor-k3` och `advisor-natt`; plan-agenten kan kalla `explore`, `research`, `advisor`, `advisor-k3` och `planer`; nattledaren kan kalla `advisor-natt`.

- [ ] **Step 1: Lägg till primär advisor**

  Lägg till en `mode: "subagent"`-agent med `model: "opencode-go/glm-5.3"`, `steps: 60`, `temperature: 0.1` och `prompt: "{file:./prompts/advisor.md}"`.

  Dess permissions ska innehålla:

  ```json
  "question": "deny",
  "bash": { "*": "deny" },
  "edit": { "*": "deny" },
  "task": { "*": "deny" },
  "webfetch": "deny",
  "websearch": "deny"
  ```

  Lägg `read`-regler i ordningen `* allow`, `*.env deny`, `*.env.* deny`, så att agentspecifika regler vinner över den globala allow-regeln. Begränsa `external_directory` till nödvändiga OpenCode-tool-output/skill-sökvägar och neka övriga externa kataloger.

- [ ] **Step 2: Lägg till fallback-agenter**

  Skapa `advisor-k3` med samma prompt, permissions och limits men modellen `opencode-go/kimi-k3`. Skapa `advisor-natt` med GLM-modellen och samma read-only-verktyg, utan question/web/bash/edit/task-behörighet.

- [ ] **Step 3: Öppna en strikt delegation från plan-agenten**

  Ersätt plan-agentens task-regler med en deny-by-default-lista:

  ```json
  "task": {
    "*": "deny",
    "explore": "allow",
    "research": "allow",
    "advisor": "allow",
    "advisor-k3": "allow",
    "planer": "allow"
  }
  ```

  Plan-agenten får inte kalla implementation-agenter. Lägg till `question: allow`, behåll bash som endast `git status`, `git log*` och `git diff*`, och begränsa edit till `PLAN.md` samt `.opencode/audit/plan-*.md`.

- [ ] **Step 4: Lås planens och discovery-agenternas secrets-gränser**

  Lägg agentspecifika `read`-regler som nekar `*.env` och `*.env.*` för `plan`, `explore`, `explore-natt`, `planer` och `planer-natt`. Lägg motsvarande `external_directory`-begränsning utan att blockera nödvändiga OpenCode skill/tool-output-sökvägar. Verifiera regelföljden eftersom OpenCode använder sista matchande permission-regeln.

- [ ] **Step 5: Lägg advisor-natt i nattflödet**

  Lägg `"advisor-natt": "allow"` i nattledarens `task`-allowlist och uppdatera inte nattflödet med basagenten `advisor` eller Kimi-fallbacken.

- [ ] **Step 6: Kontrollera den resolvade konfigurationen**

  Kör:

  ```powershell
  opencode debug config
  opencode agent list
  opencode debug agent advisor
  opencode debug agent advisor-k3
  opencode debug agent advisor-natt
  opencode debug agent plan
  ```

  Förväntat: JSONC laddas utan parsefel; alla fyra agenter finns; advisor-modellerna och `mode: subagent` är rätt; advisor har deny för edit/bash/task/question; plan har allow för exakt de fem planeringsagenterna och deny för implementation-agenter.

### Task 3: Gör main-sessionens plan-agent advisor-medveten

**Files:**
- Modify: `C:\Users\hthur\.config\opencode\prompts\plan.md:1-62`
- Reference: `C:\Users\hthur\.config\opencode\opencode.jsonc` plan-agentblock

**Interfaces:**
- Consumes: `advisor`-, `advisor-k3`-, `research`-, `explore`- och `planer`-task permissions från Task 2.
- Produces: en `PLAN.md` med bevis, antaganden, unknowns, downstream-konsumenter, filägarskap, acceptance criteria och verifieringskommandon.

- [ ] **Step 1: Ta bort solo-konflikten**

  Ändra rollen till att plan-agenten själv äger planen men får konsultera read-only-agenter. Behåll förbud mot implementation och appkod.

- [ ] **Step 2: Lägg in konsultationspolicyn**

  Lägg in följande beslutsträd i prompten:

  ```text
  explore: okända filer/flöden efter initial orientering
  research: externa API-, versions-, modell- och best-practice-fakta
  advisor: arkitektur, säkerhet, data, downstream, motstridiga fynd och slutligt planutkast
  planer: flera subsystem, mer än 8 tasks eller scope som inte ryms utan tappade kriterier
  advisor-k3: endast när GLM-advisor saknas/faller eller maxkvalitet uttryckligen krävs
  ```

  Begränsa advisor till högst två anrop per plan: ett före låst arkitekturbeslut och ett efter komplett planutkast. Kräv handoff-formatet från specen och högst cirka 2 000 tokens.

- [ ] **Step 3: Kräv evidence och downstream-map**

  Ersätt den nuvarande minimala outputmallen med obligatoriska underrubriker för `Evidence`, `Assumptions`, `Unknowns`, `Downstream consumers`, `Risk and fallback` och `Verification`. Kritiska påståenden utan `fil:rad` eller URL ska skrivas som `not verified`.

- [ ] **Step 4: Gör scopegränsen adaptiv**

  Behåll korta planer för små ändringar men ändra regeln för ensats-diff till att endast gälla mekaniska ändringar utan signatur-, data-, auth-, config- eller downstream-effekt. Om planen når mer än åtta tasks ska agenten kalla `planer` i stället för att trunkera.

- [ ] **Step 5: Lägg in child-resultat och failure policy**

  Kräv att tomma/trasiga child-resultat markeras `unverified`, att advisor-timeout inte får rapporteras som konsultation och att planen uttryckligen dokumenterar `advisor unavailable` eller `research unavailable`. Plan-läget ska fortsatt skriva föreslagna gates men inte köra tester/build själv.

- [ ] **Step 6: Verifiera prompten**

  Kör:

  ```powershell
  rg -n "SOLO|advisor|advisor-k3|research|planer|2 000|8 tasks|Evidence|Assumptions|Unknowns|Downstream|unverified|advisor unavailable|\.env" "C:\Users\hthur\.config\opencode\prompts\plan.md"
  ```

  Förväntat: den gamla regeln som förbjuder alla subagenter utom `explore` är borta; nya triggers, gränser, evidence-krav och failure policy finns.

### Task 4: Koppla billiga executor-flöden till advisor

**Files:**
- Modify: `C:\Users\hthur\.config\opencode\prompts\build.md:7-15,24-38`
- Modify: `C:\Users\hthur\.config\opencode\prompts\general.md:31-70`
- Modify: `C:\Users\hthur\.config\opencode\prompts\super-deepseek.md:31-44,75-89,255-273`
- Modify: `C:\Users\hthur\.config\opencode\prompts\super-deepseek-natt.md:5-12,58-76,262-278`

**Interfaces:**
- Consumes: advisor-kontraktet från Task 1 och agentnamnen/permissions från Task 2.
- Produces: konsekvent `task`-handoff från build/general/super-deepseek till rätt advisor, inklusive nattvariant.

- [ ] **Step 1: Lägg till advisor som intern build-exception**

  Behåll regeln att vanliga subagenter inte startas utan uttryckligt användarbeslut, men gör `advisor` till den enda automatiska interna konsultationen. Lägg triggers: hög risk, ändrade API-/data-/auth-kontrakt, okänd arkitektur, två motstridiga fynd, två misslyckade verifieringsförsök eller beslut före finalisering.

- [ ] **Step 2: Lägg samma handoff-format i executor-prompts**

  Kräv rubrikerna `Task`, `Goal / decision needed`, `Current state`, `Evidence already gathered`, `Constraints / out of scope`, `Attempts and failures` och `Exact question for advisor`. Förbjud transcript-dump och secrets. Sätt default till högst två advisor-anrop och använd `advisor-k3` bara vid dokumenterade fallbackskäl.

- [ ] **Step 3: Uppdatera super-deepseek-flottan**

  Lägg advisor/advisor-natt i agenttabellen, routingreglerna och delegationstriggers. Nattvarianten får endast kalla `advisor-natt`, loggar beslut när användaren inte kan svara och fortsätter utan frågor.

- [ ] **Step 4: Begränsa general-flödet**

  Låt `general` och `general-natt` konsultera advisor endast vid blockerande arkitektur-/säkerhetsfrågor; de ska inte använda advisor för mekaniska deluppgifter eller delegera vidare.

- [ ] **Step 5: Verifiera alla promptreferenser**

  Kör:

  ```powershell
  rg -n "advisor|advisor-k3|advisor-natt|Exact question for advisor|advisor unavailable|two advisor|två advisor|secrets|\.env" "C:\Users\hthur\.config\opencode\prompts\build.md" "C:\Users\hthur\.config\opencode\prompts\general.md" "C:\Users\hthur\.config\opencode\prompts\super-deepseek.md" "C:\Users\hthur\.config\opencode\prompts\super-deepseek-natt.md"
  ```

  Förväntat: varje executor har advisor-trigger, handoff-format, budget och rätt nattbeteende.

### Task 5: Kör end-to-end- och negativ verifiering

**Files:**
- Test artifact: `C:\Users\hthur\AppData\Local\Temp\opencode\advisor-plan-fixture\`
- Verify: `C:\Users\hthur\.config\opencode\opencode.jsonc` och alla ändrade promptfiler

**Interfaces:**
- Consumes: alla agent-/promptändringar från Tasks 1–4.
- Produces: faktiska CLI-kvitton för laddning, delegation, scope, fallback och permission-deny.

- [ ] **Step 1: Kontrollera modellkatalogen**

  Kör:

  ```powershell
  opencode models opencode-go
  ```

  Förväntat: `glm-5.3`, `kimi-k3` och `deepseek-v4-flash` finns i den aktuella Go-katalogen.

- [ ] **Step 2: Skapa en isolerad fixture**

  Verifiera först att `C:\Users\hthur\AppData\Local\Temp\opencode` finns. Skapa därefter `advisor-plan-fixture` med en liten README och en enkel `src/example.py`; fixture-repot får inte innehålla secrets eller kopior av `.env`.

- [ ] **Step 3: Kör advisor-scenario**

  Kör:

  ```powershell
  opencode run --dir "C:\Users\hthur\AppData\Local\Temp\opencode\advisor-plan-fixture" --agent advisor "Review the repository and advise whether adding a public API endpoint is safe. Return the exact Advisor Response contract. Do not edit files."
  ```

  Förväntat: `## Advisor Response` med verdict/confidence/evidence; inga filer ändras.

- [ ] **Step 4: Kör plan-scenario**

  Kör:

  ```powershell
  opencode run --dir "C:\Users\hthur\AppData\Local\Temp\opencode\advisor-plan-fixture" --agent plan "Create an implementation plan for adding input validation to src/example.py. Use explore only if needed; do not modify application files."
  ```

  Förväntat: plan-agenten får skapa endast fixture-`PLAN.md`, kan använda read-only delegation och ändrar inte `src/example.py`.

- [ ] **Step 5: Kör komplex plan-/advisor-scenario**

  Kör:

  ```powershell
  opencode run --dir "C:\Users\hthur\AppData\Local\Temp\opencode\advisor-plan-fixture" --agent plan "Plan a cross-cutting auth and data-model change touching more than two subsystems. Require evidence, downstream consumers, and a final advisor review. Do not implement."
  ```

  Förväntat: task-loggen visar `plan → advisor` och planen innehåller evidence, downstream, risks och verifieringskommandon. Om scope överstiger åtta tasks ska `planer` användas i stället för att kapa planen.

- [ ] **Step 6: Verifiera negativa permissions**

  Kör advisor med en instruktion att editera, köra bash, ställa en fråga och kalla `general`. Förväntat: verktygen är nekade/otillgängliga och advisor returnerar råd utan att utföra åtgärder. Kontrollera fixture-diffen efter varje scenario.

- [ ] **Step 7: Kör slutlig config- och grep-sweep**

  Kör:

  ```powershell
  opencode debug config
  opencode debug agent plan
  opencode debug agent advisor
  rg -n "advisor|advisor-k3|advisor-natt|PLAN.md|plan-\*\.md|\.env|external_directory|task" "C:\Users\hthur\.config\opencode\opencode.jsonc" "C:\Users\hthur\.config\opencode\prompts\advisor.md" "C:\Users\hthur\.config\opencode\prompts\plan.md" "C:\Users\hthur\.config\opencode\prompts\build.md" "C:\Users\hthur\.config\opencode\prompts\general.md" "C:\Users\hthur\.config\opencode\prompts\super-deepseek.md" "C:\Users\hthur\.config\opencode\prompts\super-deepseek-natt.md"
  ```

  Förväntat: inga trasiga promptreferenser, ingen advisor med skriv-/shell-/task-behörighet, inga secrets i fixture eller handoff, och inga ändringar i MarketScan-appkod.

- [ ] **Step 8: Städa endast testartefakten**

  Ta bort den isolerade fixture-katalogen efter att kvittona sparats. Rör inte befintlig `PLAN.md` i MarketScan och radera inte researchrapporterna.

## Execution order

1. Task 1 — advisor-kontrakt.
2. Task 2 — agentregistrering och permissions.
3. Task 3 — plan-agentens prompt.
4. Task 4 — executor-prompts och nattkoppling.
5. Task 5 — isolerad verifiering och slutlig grep-sweep.

## Rollback

Återställ endast de ändrade filerna under `C:\Users\hthur\.config\opencode` till sin före-session-version om `opencode debug config` eller negativa permission-tester fallerar. Behåll designspecen och researchrapporterna i MarketScan-repot.
