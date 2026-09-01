# OpenCode advisor och robustare plan-läge — designspec

## Idé

Ge OpenCodes billiga arbets- och planagenter en säker, read-only väg till
`opencode-go/glm-5.3` för svåra beslut, och gör plan-agenten bättre på evidens,
scope, downstream-konsekvenser och sekretess utan att den får ändra appkod.

## Mål och success criteria

- `plan` i main session kan kalla `explore`, `research`, `advisor` och vid stor
  scope `planer`, men ingen av dessa kan ändra applikationskod via planens
  delegation.
- `advisor` använder `opencode-go/glm-5.3`, är read-only och returnerar ett
  kompakt, stabilt råd med verdict, confidence, evidens, rekommenderad åtgärd
  och verifieringssteg.
- `build`, `general` och super-deepseek-flöden vet när och hur de ska fråga
  advisor utan att konsultera den för triviala ändringar.
- Handoff får inte innehålla `.env`, tokens, credentials eller onödig PII.
- Planer redovisar bevis/antaganden, downstream-konsumenter, unknowns och
  exakta verifieringskommandon.
- Advisor-anrop är begränsade till högst två per plan-/bygguppgift; Kimi K3 är
  en explicit fallback och används inte på varje fråga.
- Ingen MarketScan-applikationskod, API-route eller UI ändras i denna leverans.

## Antaganden

1. OpenCode-konfigurationen under `C:\Users\hthur\.config\opencode` är den
   aktiva globala konfigurationen och ska uppdateras för användning i flera
   projekt.
2. `task` är den stabila integrationspunkten; ingen egen provider-plugin ska
   byggas i första versionen.
3. `plan` ska fortsätta vara read-only mot appkoden och endast få skriva
   `PLAN.md` eller en avgränsad planrapport.
4. `glm-5.3-flash` behålls som standardmodell för planering; fulla GLM-5.3
   används via advisor och Kimi K3 bara vid explicit högkvalitetsbehov/fallback.

## Alternativ och valt angreppssätt

### A — OpenCode-native subagent via `task` (valt)

En read-only `advisor`-agent med explicit handoff-/svarskontrakt anropas av
plan- och build-agenter. Billig, portabel och använder befintlig OpenCode-
pipeline utan skör plugin-kod.

### B — Eget `consult_advisor`-plugin

Mer likt Anthropic server-side advisor, men skapar provider-/pluginberoende,
ny felhantering och mer svårtestad looplogik. Sparas som eventuell senare
optimering om task-handoffs visar sig för långsamma.

### C — Återanvänd befintlig `reviewer`

Minsta diff men saknar advisor-kontrakt, konsultationsregler och separat
fallback. Avvisat eftersom plan-agenten då fortfarande saknar rätt verktyg.

## Design

### 1. Agentroller och flöde

```text
plan/build/general (billig executor)
  ├─ explore             → okänd kod/struktur
  ├─ research            → aktuell extern fakta
  ├─ advisor             → arkitektur, risk, downstream och beslut
  ├─ advisor-k3          → explicit kvalitetsfallback
  └─ planer              → helapp eller >8 tasks
```

`advisor` och `advisor-k3` får läsa/globba/greppa men inte editera, köra shell,
ställa användarfrågor, använda webbsökning eller delegera vidare. `advisor-natt`
är samma GLM-agent utan fråga/stop-beteende för nattflödet.

### 2. Handoff-kontrakt

Varje konsultation skickas med följande rubriker och högst cirka 2 000 tokens:

```text
## Task
## Goal / decision needed
## Current state
## Evidence already gathered (file:line or URL)
## Constraints / out of scope
## Attempts and failures
## Exact question for advisor
```

Handoff ska vara en sammanfattning, inte en transcript-dump. Secrets, tokens,
`.env`-innehåll, hela filer och onödig persondata ska redigeras bort.

### 3. Advisor-svar

```text
## Advisor Response
Verdict: PROCEED | REVISE | BLOCK | UNCERTAIN
Confidence: HIGH | MEDIUM | LOW
Decision: ...
Critical findings:
- [P0-P3] finding — evidence: file:line or "not verified"
Recommended next steps:
1. ...
Verification gates:
- ...
Open risks / assumptions:
- ...
```

Advisorn ger råd, inte implementation, slutligt användarsvar eller hidden
chain-of-thought. Om handoff saknar fakta ska den säga det och inte gissa.

### 4. Plan-agentens konsultationspolicy

- `explore` efter initial orientering när filer/flöden är okända.
- `advisor` efter orientering före arkitektur-/API-/data-/säkerhetsbeslut,
  efter upprepade motstridiga fynd och en gång efter färdigt planutkast för
  read-only kvalitetspass.
- Högst två advisor-anrop per uppgift. Kalla `advisor-k3` endast om GLM-
  advisor saknas/faller eller användaren uttryckligen vill ha maxkvalitet.
- `research` endast för externa versions-, API-, modell- och
  best-practice-påståenden; handoff till research ska vara redigerad.
- `planer` när scope berör flera subsystem, blir större än åtta tasks eller
  annars inte ryms utan att acceptance criteria tappas.
- Plan-agenten får aldrig kalla implementation-agenter.

### 5. Planens output och säkerhet

Varje plan ska innehålla scope/boundaries, evidence/antaganden/unknowns,
downstream-konsumenter, filägarskap, acceptance criteria och exakta
verifieringskommandon. Plan-läget kör inte tester själv; build-agenten kör
dem senare och planens text ska märka kommandon som ej körda.

Konfigurationen ska neka plan/advisor/explore/planer läsning av `.env` och
externa kataloger och begränsa planens skrivning till planartefakter. Globala
allow-regler får inte oavsiktligt återöppna dessa rättigheter.

## Felhantering och gränser

- Tomt eller trasigt child-resultat behandlas som *ej verifierat*, aldrig som
  lyckad konsultation.
- Advisor timeout/rate-limit: plan/build fortsätter endast med ett explicit
  `advisor unavailable`-antagande; den får inte påstå att rådet erhållits.
- Extern research misslyckas: skriv källan som overifierad och blockera inte
  trivial planering, men blockera säkerhets-/migrationsbeslut som kräver den.
- Upprepade konsultationer och delegation-loopar stoppas vid två advisor-anrop;
  resten går till människan eller nästa verifieringsgate.
- Om planutkastet överstiger åtta tasks eskaleras det i stället för att
  trunkeras till åtta.
- Nattläge använder endast `*-natt`, utan frågor eller Kimi-fallback som kan
  kräva mänskligt beslut.

## Testning och verifiering

1. Validera OpenCode-konfigurationen med OpenCodes diagnostik/agentlista och
   kontrollera att `advisor`, `advisor-k3`, `advisor-natt` och `plan` laddas.
2. Kör ett manuellt plan-scenario för en liten ändring och verifiera att ingen
   advisor kallas i onödan.
3. Kör ett komplext arkitektur-scenario och verifiera task-kedjan:
   `plan → advisor → planutkast → advisor review`.
4. Kör ett scenario med okänd kod och kontrollera `plan → explore`.
5. Kör ett scenario med aktuell extern API-fakta och kontrollera `plan →
   research`; inga secrets får finnas i handoff.
6. Kör ett scope-scenario över åtta tasks och kontrollera eskalering till
   `planer`.
7. Verifiera negativt: advisor försöker editera, köra bash, fråga användaren
   eller delegera; samtliga ska nekas/inte vara tillgängliga.
8. Re-read ändrade prompts/config, `git diff` för repoartefakter och grep-svep
   alla nya agentnamn och promptreferenser.

## Out of scope

- MarketScan FastAPI/Next.js-integration.
- Egen OpenCode-plugin eller server-side `consult_advisor`-API.
- Automatisk token-/kostnadstelemetri utanför OpenCodes befintliga session.
- Ändring av modellvalet för befintlig produktions-AI i MarketScan.
