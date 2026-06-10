# Nybörjar-produkten — komplett plan & roadmap

> Hur bygger man något som Lysa (lugnt, enkelt, tryggt) men **manuellt** — ett
> hjälpmedel som hjälper folk *utan ekonomiutbildning* att hitta och **förstå** bra
> aktiekandidater, och lära sig medan de gör det.
>
> Research-grundad (Robinhood/Public/Simply Wall St-UX, fintech-onboarding-data,
> MiFID II/MAR-gränsen). Skriven 2026-06-10.

---

## 1. Vision & positionering

**Luckan:** Mellan **Lysa** (gör allt åt dig → noll förståelse, noll kontroll) och
**Börsdata** (all data → noll vägledning) finns nästan inget för nybörjaren som *vill*
välja aktier själv men inte förstår siffrorna.

**Positionering (en mening):**
> "Lär dig hitta bra aktier — förklarat på vanlig svenska, utan ekonomijargong."

**Vad det ÄR:** ett pedagogiskt upptäckts- och förståelseverktyg.
**Vad det INTE är:** inte robo-rådgivare, inte personlig rådgivning, inte mäklare, inte
"köp den här". (Regulatoriskt avgörande — se §10.)

**Edge:** inte mer data — utan **översättningen från siffror till begriplighet på svenska**.
Simply Wall St gör teman; ingen äger svensk nybörjarpedagogik + djup förklaring.

---

## 2. Målgrupp & "job to be done"

**Persona — "Nyfikna Nina", 25–45:**
- Har redan ett konto (Avanza/Nordnet), kanske köpt en fond, vill våga köpa enskilda aktier.
- Förstår inte P/E, ROE, Piotroski, RSI. Blir överväldigad av Börsdata.
- **Rädd att göra fel** — vill ha trygghet och förståelse, inte tips att jaga.

**Job to be done:**
> "Hjälp mig hitta och *förstå* några bra aktier jag känner mig trygg att börja med —
> och lär mig hur man tänker, medan jag gör det."

---

## 3. Designprinciper (från research)

1. **Vanlig svenska, noll jargong.** Varje siffra → en mening en 15-åring förstår.
2. **Progressive disclosure.** Omdöme + 3 skäl + 1 risk först; "visa siffrorna" expanderar.
3. **Kort-baserat, en sak per skärm, mobil-först** (Robinhood-mönstret).
4. **Lugn (Lysa-känsla):** mycket luft, mjuka färger, **ingen FOMO**, inga blinkande kurser.
5. **Lär-medan-du-gör:** kontextuell utbildning (tooltips, mikrolektioner).
6. **Upptäckt > screener:** teman/kollektioner istället för filter.
7. **Snabb "aha":** användaren ska *förstå en kandidat* inom minuter (retention dör annars —
   bara ~26 % återvänder dag 1, ~4,5 % dag 30).
8. **Risk-först & skyddsräcken:** spekulativt/illikvidt tydligt märkt.
9. **Trygghetston:** "Du behöver inte göra något idag."
10. **Regulatoriskt säker framing:** utbildning + generellt, aldrig personlig "köp till dig".

---

## 4. Kärnupplevelsen — fyra pelare

**A. Onboarding (≤3 min, "aha" direkt)**
En fråga per skärm: *Vad vill du? (växa pengar / utdelning / lära mig)* → *Hur mycket
svängning tål du?* → levererar **en kurerad lista** direkt ("Här är 5 stabila svenska bolag
att börja förstå"). Värde **före** registrering (progressive onboarding).

**B. Upptäck (teman/kollektioner)**
Spellistor i begripliga teman, t.ex.:
- "Stabila svenska storbolag"
- "Företag som delat ut pengar i 10+ år"
- "Billiga & trygga"
- "Växande småbolag (högre risk)" ← tydligt riskmärkt
- "Mycket insiderköp just nu"
Ett tryck → 3–5 förhandsgranskade kandidater + enkel förklaring. **Kurering slår fullständighet.**

**C. Förstå (omdömeskort + AI-förklarare)**
Per aktie: **plain-language-omdöme** ("Stark kandidat — billig, växande, låg skuld. Risk:
liten och svänger mer.") + knapp **"Förklara som om jag är 12"** → AI förklarar (förklarar,
ger ALDRIG köp/sälj). "Visa siffrorna" för den nyfikne.

**D. Följ & lär (bevakning-först)**
Nästa steg är **aldrig "köp nu"** utan *"Lägg i bevakning och följ i 30 dagar innan du
bestämmer dig."* Pedagogiskt + regulatoriskt tryggt. Visa hur kandidaten utvecklas + vad du
lärde dig.

---

## 5. Vad finns redan vs vad som byggs

| Pelare | Finns redan | Byggs nytt |
|---|---|---|
| Omdöme | Totalbetyg + 8 delscorer, AI-kommitté, scan_results | **Plain-language-lager** (siffra→mening) |
| Upptäckt | scan_results, entry_signal/segment/mews, insider-kluster | **Teman/kollektioner**-motor + vy |
| Förstå | llm_client, AI-kommitté | **AI-förklarare** ("som om jag är 12"), utbildnings-tooltips |
| Följ | watchlist, score-historik | **Bevakning-först-resa** + "vad hände/vad lärde du dig" |
| Profil | riskprofil-enkät, ExperienceProvider | **Nybörjarläge** (global toggle som förenklar hela appen) |
| Onboarding | OnboardingModal | **Kort, kurerad, "aha"-driven** onboarding |

→ Mycket är **förädling**, inte greenfield. Det mesta av motorn finns.

---

## 6. MVP — minsta som levererar värdet

**MVP = "Nybörjarläge" som förvandlar appen:**
1. **Nybörjarläge-toggle** (förenklar nav + döljer avancerat).
2. **Plain-language-omdömeskort** på aktiesidan (omdöme + 3 skäl + 1 risk, "visa siffror"-expand).
3. **4–5 teman** på en upptäckts-startsida.
4. **AI-förklarare** ("förklara enkelt") på aktiesidan.
5. **Bevakning-först-CTA** (inte "köp").
6. **Kort onboarding** som levererar en kurerad lista.

**INTE i MVP:** community, mobilapp-native, betalning, avancerad personalisering, facit-graf.
(Det kommer i senare faser.)

**MVP-mål:** en nybörjare ska gå från "jag fattar inget" → "jag förstår varför *den här*
aktien ser bra ut och vad risken är" på **under 5 minuter**.

---

## 7. Roadmap — från idé till färdig produkt

> Sekventiella faser. Varje fas levererar något testbart. Tidsuppskattningar antar en
> utvecklare (DeepSeek/du) i taget; justera fritt.

### Fas 0 — Fundament & beslut (1 vecka)
- Lås positionering, persona, **regulatorisk framing** (utbildning, ej rådgivning).
- Bestäm **datakälla-strategi** (yfinance funkar för bygge/test; **licensierad feed krävs
  innan kommersiell lansering** — se §10).
- Definiera **mätetal** (§8) + enkel analytics (Plausible/Umami, GDPR-vänlig).
- Skapa en plain-language **ordbok** (mappning: varje nyckeltal → svensk mening + tooltip).

### Fas 1 — Plain-language-lager + Nybörjarläge (MVP-kärna) (1–2 v)
- `lib/plainLanguage.ts`: funktioner som översätter delscorer/nyckeltal → meningar + risknivå.
- `Nybörjarläge`-toggle via `ExperienceProvider` (döljer jargong, förenklar nav).
- **Omdömeskort** på aktiesidan (omdöme + 3 skäl + 1 risk + "visa siffror").
- *Klart när:* en nybörjare förstår en akties omdöme utan att googla en enda term.

### Fas 2 — Temabaserad upptäckt (1 v)
- `themes`-definitioner (regler ovanpå scan_results, t.ex. "stabil utdelare" = utdelning >0
  i X år + låg vol + large_cap). Börja med 5 teman.
- Upptäckts-startsida: temakort → 3–5 kandidater med plain-language-rad.
- Riskmärkning på spekulativa teman.
- *Klart när:* en nybörjare hittar en relevant kandidat utan att bygga ett filter.

### Fas 3 — AI-förklarare + utbildning-i-kontext (1–2 v)
- `GET /api/ai/explain/{ticker}?level=beginner` — llm_client (Gemini gratis), grundad i
  bolagets faktiska score/skäl, **förklarar, rekommenderar aldrig**. Cachad per ticker/dag.
- "Förklara som om jag är 12"-knapp + inline mikrolektioner ("Vad är utdelning?").
- *Klart när:* användaren kan fråga "varför?" och få ett begripligt, grundat svar.

### Fas 4 — Onboarding + bevakning-först-resa + aktivering (1–2 v)
- Kort onboarding (en fråga/skärm) → kurerad startlista (värde före registrering).
- Bevakning-först-CTA + "följ i 30 dagar"-flöde + enkel "så här gick det"-återblick.
- Aktiverings-checklista (lägg till första bevakning, läs en förklaring).
- *Klart när:* time-to-first-"aha" < 5 min; D1-retention mätbar.

### Fas 5 — Förtroende + lugn design-polish (1 v)
- **Facit-transparens:** hur systemets signaler historiskt gått (inkl. missar) — bygger tillit.
- Lysa-känsla: typografi, luft, lugna färger, mjuka animationer, trygghetston genomgående.
- *Klart när:* appen känns lugn och trovärdig, inte en trading-terminal.

### Fas 6 — Produkt-redo (2–4 v, delvis parallellt)
- **Byt till licensierad datafeed** (Börsdata API / EOD / Polygon m.fl.) före betalning.
- **GDPR:** integritetspolicy, laglig grund, dataskydd, ev. biträdesavtal.
- **Villkor + MAR/-friskrivning + AI-transparens** (märk AI-genererat).
- **Prissättning + betalning** (Stripe; freemium — se §9).
- **Bolag/skatt** (AB, F-skatt, bokföring, moms).
- *Klart när:* lagligt och tekniskt redo att ta betalt.

### Fas 7 — Beta-lansering + iteration (löpande)
- Stängd beta med 20–50 riktiga nybörjare → mät §8, intervjua, iterera pedagogiken.
- Innehållsdistribution (förklara aktier enkelt på TikTok/YouTube/SEO) som tillväxtmotor.
- *Klart när:* aktiverings- och D7-retention slår fintech-snittet → skala.

---

## 8. Mätetal (vet du att det funkar)

| Kategori | Mätetal | Mål |
|---|---|---|
| **Aktivering** | % som når första "aha" (förstått en kandidat) inom 5 min | hög = allt |
| Retention | D1 / D7 / D30 | slå snitt (D1 ~26 %, D30 ~4,5 %) |
| Engagemang | teman öppnade, AI-förklaringar lästa, bevakningar tillagda | växande |
| **Förståelse** | enkät "förstod du varför?" (1-tap efter omdöme) | >70 % ja |
| Förtroende | NPS, "känner du dig tryggare med aktier nu?" | positivt |

---

## 9. Go-to-market (kort)

- **Distribution:** pedagogiskt innehåll ("förklara aktier enkelt på svenska") på TikTok/
  YouTube/Instagram + SEO på aktiesidor; svenska privatekonomi-communities.
- **Prissättning (freemium):** gratis = upptäckt + teman + grund-omdömen; **Pro** = obegränsad
  AI-förklarare, fler teman, facit-historik, fler bevakningar. Lågt pris (t.ex. 49–99 kr/mån)
  för nybörjarmålgruppen.
- **Ärlig konkurrensbild:** Simply Wall St/Avanza Aktieskola nuddar nischen; din vinst är
  **svensk pedagogik + djup, grundad förklaring** — inte fler funktioner.

---

## 10. Risker & ärlighet

| Risk | Sanning / mitigering |
|---|---|
| **Datalicens** | yfinance får ej användas kommersiellt → licensierad feed kostar pengar **innan** intäkter. Bygg/test på yfinance, byt före lansering. |
| **Plain-language är svårt** | Kvaliteten på översättning/AI-förklaring ÄR produkten. Lägg tid; testa på riktiga nybörjare. |
| **Retention brutal** | ~4,5 % dag 30 är normen. **Aktivering + snabb "aha" + utbildning** är enda försvaret. |
| **Regulatorisk linje** | Håll det **utbildning/generellt**, aldrig personlig "köp till dig". AI förklarar, råder ej. Prata med jurist + FI före betalning. |
| **Marknad/konkurrens** | Görbart men trångt. Edge = pedagogiken, inte data. |
| **Robo-advice-frestelse** | Frestande att göra portföljbyggaren personlig → hamnar i tillståndspliktig zon. Håll den generell/pedagogisk. |

---

## TL;DR
Bygg ett **Nybörjarläge** som översätter din befintliga motor till begriplig svenska, ger
**kurerade teman** istället för filter, en **AI som förklarar (inte råder)**, och en
**bevakning-först-resa** — allt i lugn Lysa-ton. MVP på ~4–6 veckor; färdig produkt kräver
även **licensierad data + GDPR/villkor + betalning**. Den verkliga vinsten är pedagogiken,
och den verkliga risken är aktivering — inte juridiken.
