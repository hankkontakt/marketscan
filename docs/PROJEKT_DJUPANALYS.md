# MarketScan — Djupanalys av nästa stora projekt

> Rimlighetsbedömning + arkitektur + kostnad för de projekt som valts för
> aktiv utvärdering. Ärliga verdikter — vad som är klokt att bygga och inte.
> Underlag: marknadsresearch juni 2026 (se källor sist).
>
> **TL;DR-verdikt:**
> | # | Projekt | Rimligt? | Kostnad | Notis |
> |---|---|---|---|---|
> | 5 | ML-scoring för 10k aktier | ✅✅ Ja, gör detta | ~gratis compute, data är kostnaden | Använd ML, INTE LLM |
> | 2 | Auto-årsredovisningar + RAG | ✅ Ja | Nästan gratis (pgvector finns) | MFN.se + Börsdata |
> | 9 | Daglig briefing | ✅✅ Ja, enkelt | ~0 kr (gratis-tier räcker) | Mest mall, lite LLM |
> | 1 | Analytiker-agenten | ✅ Ja, on-demand | Några öre/rapport | Cacha hårt |
> | 4 | Broker-integration | ⚠️ Delvis / ❌ ej produkt | — | Läs möjligt, handel avråds |

---

## 🥇 #5 — Nästa-gen scoringmotor för 10 000 aktier (BILLIGT)

### Den avgörande insikten
**Du ska INTE använda en LLM (DeepSeek o.dyl.) för att betygsätta 10 000 aktier.**
Det skulle kosta en förmögenhet och vara långsamt. Branschstandarden — det
kvant-fonder faktiskt gör — är **klassisk maskininlärning** (gradient-boostade
träd, t.ex. LightGBM med "learning-to-rank"). Den modellen räknar ut ett betyg
för 10 000 aktier på **minuter, på en vanlig CPU, för ~0 kr**.

Tänk så här om de två "hjärnorna":
| | **Scoring-hjärnan (siffror)** | **Analys-hjärnan (text)** |
|---|---|---|
| Verktyg | LightGBM / ML | LLM (DeepSeek/Gemini) |
| Körs på | ALLA 10 000 aktier, varje natt | bara aktien användaren klickar på |
| Kostnad | ~gratis (CPU i pipelinen) | några öre per analys |
| Vad den gör | rankar/betygsätter | förklarar, sammanfattar, resonerar |

Det är därför 10 000 aktier är gratis: **LLM rör aldrig hela universumet.**

### Arkitektur
```
Datakällor (fundamenta + pris)
   │   Börsdata API (Norden) · SEC/yfinance (US) · Finnhub
   ▼
Feature-engineering  (~100–200 tvärsnittsfaktorer/aktie/dag)
   │   värde, kvalitet, momentum, tillväxt, lönsamhet, risk, likviditet …
   │   (ren pandas — det du redan gör i pipelinen, fast mycket bredare)
   ▼
LightGBM LambdaRank-modell   (tränad på faktor → framtida avkastning)
   │   walk-forward-backtestad · ensemble möjlig (LGBM + liten NN)
   ▼
SHAP-förklaringar  ("betyg 56: +momentum 40%, −värdering 30% …")
   ▼
scan_results (nattlig precompute — samma som nu, mycket bättre hjärna)
```

### Var passar en "LM" in? (din fråga)
Det du egentligen vill ha är en **extremt bra betygsättningsmodell** — och den
ska vara ML, inte en språkmodell. MEN en billig språkmodell kan **mata in extra
signaler** som faktorer i ML-modellen:
- Kör en **gratis/billig** LLM (Groq Llama, 14 000 req/dygn gratis) över nyheter
  / rapport-ton → ett sentiment-tal per aktie → blir en faktor bland de andra.
- Det är hybriden: ML rankar, en billig LLM berikar med text-härledda faktorer.

### Kostnad — krossar myten
- **Compute:** ~0 kr. LightGBM tränar och scorar 10k aktier i GitHub Actions
  (du har redan pipelinen). Inferens är millisekunder.
- **Den verkliga kostnaden är DATA**, inte modellen:
  - Norden: **Börsdata PRO API** (~hundratals kr/mån) — fundamenta för i princip
    alla nordiska bolag.
  - US: SEC EDGAR (gratis) + yfinance (gratis).
  - Europa brett: kan kräva en betald leverantör senare (steg 3).
- Jämför: en LLM-baserad scoring av 10k aktier/dag = tiotusentals API-anrop =
  hundratals–tusentals kr/mån. ML-vägen = nära 0.

### Faser
1. **Bygg ML-ramverket på dagens ~558 aktier.** Inför LightGBM-ranker bredvid
   nuvarande heuristiska score, walk-forward-backtesta, jämför. Inför SHAP.
2. **Bredda data till hela Norden** via Börsdata API → ~2 000–3 000 aktier.
3. **US-universum** via SEC/yfinance → +5 000 aktier.
4. **Europa** (betald datakälla vid behov) → 10 000+.
5. **Text-faktorer** (billig LLM-sentiment) som extra features.

### Rimlighet: ✅✅ **Mycket rimligt — detta bör byggas.**
Det svåra är inte kostnad eller compute, utan **datainsamling + ML-rigor**
(undvika overfitting, walk-forward-validering, survivorship bias). Det är ett
riktigt mega-projekt men på en beprövad väg (Microsofts **Qlib** + LightGBM är
open source och exakt denna stack).

### Risker
- **Overfitting / falsk alpha** — måste backtestas korrekt (walk-forward, out-of-sample).
- **Datakvalitet & survivorship bias** — avlistade bolag måste finnas i träningsdata.
- **Datakostnad/licens** för bred europeisk täckning.

---

## 🥈 #2 — Auto-hämta årsredovisningar + RAG ("Fråga bolaget")

### Vision
Systemet hämtar **automatiskt** varje bolags senaste årsredovisning + kvartals-
rapporter, och användaren kan ställa frågor som besvaras **grundat i rapporten,
med sidcitat** — ingen hallucination.

### Går det att auto-hämta svenska årsredovisningar? **Ja.**
- **MFN.se** (Modular Finance) streamar pressmeddelanden + rapporter för **alla**
  nordiska börsbolag, taggat per bolag — inkl. årsredovisningar. Förutsägbar
  struktur att hämta från.
- **Börsdata API** — strukturerad fundamenta + rapportlänkar (Norden).
- Fallback: bolagens IR-sidor, Nasdaq Nordic.

### Arkitektur (elegant — du har redan databasen)
```
Nattlig ingestion-job:
  för varje universum-ticker:
    hitta senaste rapport-PDF (MFN.se / IR)  →  ladda ner
    extrahera text (PDF-parser)  →  dela i chunks
    embed:a (billig/lokal embedding-modell)
    spara i  pgvector  (Postgres-tillägg i din Supabase — GRATIS)

Fråga-flöde:
  användarfråga → embed → hämta relevanta chunks → LLM svarar MED citat
```

### Kostnad: nästan gratis
- **Lagring:** `pgvector` i din befintliga Supabase = 0 kr extra.
- **Embeddings:** billiga (eller en lokal modell = gratis). En årsredovisning
  ~50–100 chunks → försumbart.
- **Per fråga:** en LLM-call (DeepSeek, några ören), grundad i hämtade chunks.

### Faser
1. Ingestion-pipeline för svenska large/mid cap (MFN.se).
2. pgvector + RAG-endpoint + "Fråga bolaget"-UI på aktiesidan.
3. Bredda till alla rapporter (Q1–Q4), earnings-call-transkript.
4. Proaktivt: AI-sammanfattning av varje ny rapport ("3 viktigaste sakerna").

### Rimlighet: ✅ **Rimligt.** Mest arbete i ingestion-pipelinen (PDF→text→chunks).
pgvector-i-Supabase gör infran nästan gratis. Fey gör detta för US 10-K/10-Q —
ingen gör det bra för svenska bolag = tydlig lucka.

---

## 🥉 #9 — Daglig briefing (billig, ingen ljud än)

### Vision
En personlig morgonrapport om DINA innehav + bevakningar + marknadsläge +
relevanta händelser. Som dina gamla dagliga mail i Streamlit-systemet, fast
bättre. (Ljud-podd sparas till senare — enligt önskemål.)

### Hur håller vi DeepSeek-användningen minimal?
**Insikten: 90 % av briefingen behöver ingen AI.** Den är **mall** fylld med
strukturerad data du redan har:
- portföljens dagsutveckling, top movers i din bevakning, betygsförändringar,
  kommande rapporter/utdelningar, marknadsregim.

LLM:en skriver bara den korta **berättande sammanfattningen** ("Din portfölj steg
1,2 % drivet av NCAB; två bevakade bolag fick höjt betyg…").

### Kostnadsminimering (flera lager)
1. **Mall först, AI sist** — bara 1–2 stycken text genereras per användare.
2. **Delad marknadssektion** — generera marknadsläget **en gång**, återanvänd för
   alla användare (inte per person).
3. **Gratis-tier räcker långt:** Gemini Flash-Lite (1 500 anrop/dygn gratis)
   eller Groq Llama (14 000/dygn gratis) → för en liten användarbas = **0 kr**.
4. **DeepSeek prompt-cache** ($0,028/M på cache-träffar) om du vill ha en modell.
5. **Batch** — allt i en nattlig körning.

→ Realistisk kostnad för personligt bruk / liten bas: **~0 kr/mån.**

### Leverans
- E-post (som förut på Streamlit) + in-app-vy. Schemalagt GitHub Actions-jobb
  (du har redan workflow-infran).

### Rimlighet: ✅✅ **Mycket rimligt och billigt.** Återanvänder mönstret från dina
gamla Streamlit-mail. Lågt risk, högt dagligt engagemangsvärde.

---

## #1 — Analytiker-agenten (autonom djupresearch)

### Vision
Användaren klickar "Djupanalys" på en aktie → en AI-agent kör flera steg
(hämtar fundamenta, pris, nyheter, rapport via #2, peers) → levererar ett
komplett, **källhänvisat** investeringsmemo (bull/bear/värdering/risker).

### Arkitektur
- **Verktygsanvändande agent** (function calling) med en billig modell
  (DeepSeek eller Gemini Flash). Verktygen = dina befintliga endpoints + #2-RAG.
- Output = strukturerat memo med citat (compliance-vänligt — branschen kräver
  audit trail + källhänvisning).

### Kostnad — nyckeln är att det är ON-DEMAND
- En agentisk körning = flera LLM-anrop (~20–50k tokens). Med DeepSeek
  ($0,14/$0,28 per M) ≈ **några ören–någon krona per rapport**.
- **Körs ALDRIG på alla 10k aktier** — bara när en användare ber om det.
- **Cacha hårt:** spara memot per aktie i t.ex. 1 dygn/vecka → många användare,
  en kostnad.

### Rimlighet: ✅ **Rimligt som on-demand-funktion med hård cache + budget per
användare.** Detta är frontier-trenden 2026 (multi-agent, investment memos).
Bygg efter #2 (RAG) så agenten kan citera rapporter.

### Risk
- Kostnad om det missbrukas → kräver per-användare-budget/rate-limit (du har
  redan rate-limiter + auth på AI-endpoints).
- Kvalitet/hallucination → grunda i #2 + verifieringssteg.

---

## #4 — Broker-integration (Avanza/Nordnet): går det?

### Ärligt svar: **delvis tekniskt möjligt, men avrådes som produkt.**

**Läsa innehav (synk):**
- Det finns ett **inofficiellt** Python-API för Avanza (`Qluxzz/avanza`,
  `avanza-api` på PyPI). Kan läsa innehav och t.o.m. lägga order.
- **MEN** det är uttryckligen *"proof of concept, inte för produktion, kan
  sluta fungera utan förvarning"*, kräver användarens **TOTP-2FA-hemlighet +
  inloggning**, och strider mot Avanzas villkor.
- Nordnet har ett halv-officiellt "External API" (nExt) — gated/instabilt.
- **Officiell väg:** PSD2/Open Banking via licensierad AISP (Tink, Enable
  Banking) ger kontoaggregering — men inte detaljerade innehav/handel, och
  kräver licens.

**Lägga order (handel):**
- **Bygg INTE detta.** Att lagra användares mäklar-credentials och utföra affärer
  åt dem = enorm säkerhets-, juridik- och ansvarsrisk. (Och MarketScans egna
  säkerhetsregler förbjuder att utföra trades åt användaren.)

### Realistisk medelväg
1. **Förbättra import** istället: smartare CSV-igenkänning, schemalagd
   påminnelse att re-importera, auto-mappning.
2. **Personligt bruk:** för DIG ensam kan du köra det inofficiella Avanza-API:t
   som ett privat script (egna credentials, egen risk) för att auto-synka — men
   inte exponera det för andra användare.
3. **Vänta på riktigt officiellt API / PSD2-investeringsdata** för en
   produktifierad multi-användarversion.

### Rimlighet: ⚠️ **Läs-synk: möjligt men skört + villkorsgrått → ej för
flera användare.** ❌ **Handel: bygg inte.** Bäst ROI: polera importflödet.

---

## Sammanfattande rekommendation (ordning att bygga)
1. **#5 ML-scoring** (störst hävstång, ~gratis, systemets hjärna) — börja på 558,
   bredda stegvis.
2. **#2 RAG** (pgvector i Supabase, nästan gratis) — ger även underlag åt #1.
3. **#9 Daglig briefing** (snabb vinst, ~0 kr, dagligt engagemang).
4. **#1 Analytiker-agenten** (on-demand, byggs ovanpå #2).
5. **#4 Broker** — polera import; bygg inte handel.

---

## Källor
- LLM-priser: [TLDL cheapest LLM API 2026](https://www.tldl.io/resources/cheapest-llm-api-2026), [TokenMix free LLM API](https://tokenmix.ai/blog/free-llm-api)
- ML-scoring: [Qlib + LightGBM quant workflow](https://vadim.blog/qlib-ai-quant-workflow-lightgbm), [Multi-factor LightGBM + Bayesian Opt (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S1877050922020130)
- Broker-API: [Qluxzz/avanza (GitHub)](https://github.com/Qluxzz/avanza), [avanza-api (PyPI)](https://pypi.org/project/avanza-api/)
- Svensk rapportdata: [MFN.se](https://mfn.se/), Börsdata API
- Agentic finance: [Agentic AI in Financial Services 2026](https://neurons-lab.com/articles/agentic-ai-in-financial-services-2026/)
