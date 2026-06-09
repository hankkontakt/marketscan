# MarketScan — Framtida stora projekt (backlog)

> Idébank för stora/mega-projekt som sparats för senare. Ytlig nivå — när ett
> ska byggas görs en djupanalys (se `PROJEKT_DJUPANALYS.md` för mallen).
> Aktivt under utvärdering nu: #1, #2, #5, #9, #4 (i djupanalys-dokumentet).

---

## Sparade från första omgången

### #3 — Realtids nyhets- & sentimentmotor (svensk)
Streaming-NLP över svenska finanskällor (DI, Placera, Affärsvärlden,
Avanza/Nordnet-forum, Reddit, X) → sentiment per aktie i realtid + breaking-
events + personligt nyhetsflöde. *Lucka: svenska marknaden underbevakad av AI.*
Synergi: matar text-faktorer till #5 och källor till #1/#2.

### #6 — Visuell bolagsanalys ("Snowflake") + DCF-värdering
Interaktiv flerdimensionell bolagsprofil (värde/tillväxt/kvalitet/hälsa/
momentum/utdelning) + inbyggd DCF-modell med redigerbara antaganden och
scenarioanalys. *Likt Simply Wall St:s ikoniska "snowflake".* Kräver djupare
fundamenta (10 års räkenskaper) — bra att göra efter #5:s databredd.

### #7 — Mål- & livsplanering / robo-rådgivare (svensk skatt)
Målbaserad planering (FIRE, pension, kontantinsats), auto-allokering,
rebalansering, Monte Carlo-prognoser. Svensk-specifikt: **ISK vs KF vs depå**,
skatteoptimering, förlustkvittning, schablonskatt. *Breddar från verktyg till
livslång plattform.*

### #8 — Socialt lager + copy-signaler
Publika profiler, dela portföljer/screeners/teser, risk-justerade topplistor,
följ topp-presterare, diskussionstrådar, "copy-signaler" (notis när någon du
följer agerar). *Nätverkseffekter + retention + användargenererat innehåll.*

### #10 — Strategi-marknadsplats & no-code algo-byggare
Bygg screening/trading-strategier visuellt (no-code), backtesta (Strategy Lab
finns), publicera till marknadsplats, prenumerera på andras med alerts.
*Förvandlar Strategy Lab till en plattform/ekonomi (likt Composer.trade).*

---

## 5 nya idéer (i stilen du gillade — AI/data-intelligens, kostnadssnål)

### #11 — Insider- & ägarflödes-radar ("smart money")
Spåra insynshandel (FI:s insynsregister är publikt — du har redan
`insider_trades`) + institutionella ägarförändringar (Modular Finance Holdings-
data) → ML/regler flaggar ovanliga köp/sälj-mönster → alerts. *"Insiders köpte
stort i X förra veckan."* Billigt: mest data + regler, ingen tung LLM.

### #12 — Signalvalidering ("Är signalen verklig?")
Backtesta **automatiskt** varje köp-/säljsignal systemet ger, över historik →
visa varje signals historiska träffsäkerhet + snittavkastning. Då litar
användaren på signaler som **faktiskt fungerat**. *Gör signaler från åsikt →
bevis.* Bygger på Strategy Lab. Billigt (ren beräkning).

### #13 — Anomali- & event-detektor
Ett statistiskt/ML-lager som upptäcker ovanliga pris-/volym-/fundamenta-avvik i
realtid (volymspikar, gap, plötsliga betygsändringar, short-squeeze-setups) →
proaktiva notiser. *"Något händer med X."* Billigt: statistik/ML, ingen LLM.

### #14 — Peer- & substitut-motor ("Liknande aktier")
Givet en aktie, hitta dess verkliga peers via faktor-likhet + sektor +
affärsmodell (embeddings över bolagsbeskrivningar) → "gillar du X, kolla Y/Z" +
relativvärdering. *Driver jämförelse, diversifiering och idé-upptäckt.* Billigt:
embeddings (engång) + vektor-likhet.

### #15 — AI-tesisk bevakning ("Watch my thesis")
Användaren skriver en tes ("NCAB växer pga X") → systemet identifierar de
mätbara drivkrafterna och **bevakar** dem, larmar när bevisläget ändras (en KPI
vänder, en händelse inträffar). *Gör vag övertygelse → spårbar, falsifierbar
hypotes.* Liten LLM för att extrahera drivkrafter (engång), sen billig bevakning.

---

## Tvärsnitt: hur projekten hänger ihop
- **#5 (ML-scoring)** är navet — bredare data + bättre hjärna gynnar nästan allt.
- **#2 (RAG)** ger källor åt **#1 (agent)**, **#15 (tes)** och **#6 (DCF-antaganden)**.
- **#3 (sentiment)** matar text-faktorer till **#5** och larm till **#13**.
- **#11/#12/#13** är alla billiga "intelligens-lager" ovanpå data du redan har.
- **#9 (briefing)** är den dagliga leveranskanalen som kan yta allt ovanstående.

> När du vill aktivera något härifrån: säg till, så flyttar jag det till
> djupanalys med arkitektur, kostnad, faser och risker.
