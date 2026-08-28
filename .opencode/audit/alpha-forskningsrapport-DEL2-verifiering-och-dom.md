# Alpha-forskning DEL 2 — Verifieringsrunda, Devil's Advocate & Ärlig Dom

> **2026-08-28 (andra omgången).** Kompletterar `alpha-nordisk-smabolag-research-2026-08-28.md`.
> Innehåll: (1) osäkerheter jag sa jag skulle verifiera — vad som BLEV verifierat och vad som
> fortfarande är öppet, (2) ny evidens som kom fram, (3) devil's advocate mot hela idén,
> (4) ärlig dom: ÄR DET VÄRT DET?

---

## 1. Verifieringsresultat — osäkerheterna från del 1

### ✅ VERIFIERAT / NY EVIDENS

**1.1 Bolagsverket — gratis, officiell fundamenta-källa (STOR UPPTÄCKT)**
- **"API för värdefulla datamängder"** är **avgiftsfritt, inget avtal krävs**
  (bolagsverket.se/apierochoppnadata/hamtaforetagsinformation/vardefulladatamangder,
  uppdaterad 2026-06-30):
  - **Digitalt inlämnade årsredovisningar** (K2, K3, koncern-redovisning K3,
    **ESEF/xHTML** för noterade bolag) som ZIP-dokument per dokument-ID.
  - SNI-koder, företagsdata. REST/JSON, HTTPS, OAuth 2.
- **Fullt API "Företagsinformation" v4.7 (mars 2026):** ny endpoint för
  **finansiella rapporter** per organisationsnummer → årsredovisnings-status,
  ankomstdatum, registreringsdatum, typ (är PUNKT-I-TID-giltig metadata!).
- **v4.8 (april 2026):** detaljerad status (avregistrerad/avveckling/fusion)
  → detta ger **avlistnings-/dödsfalls-signaler** (kritisk för äkta
  survivorship-bias-fria backtests!) + **"Notifieringar om förändringar"**.
- **Vinstutdelning (v4.7):** beslutad utdelning per datum/valuta/belopp
  → payout-datapunkten, gratis, officiell.
- **Konsekvens:** fundamenta-gapet för svenska noterade bolag är **löst utan
  Börsdata och utan egen PDF-parsning** för ÅRS-data: ESEF xHTML =
  maskinläsbara rapporter (siffror = taggade, ingen OCR). Årlig lag (reports
  registreras vår/vinter) matchar en **årlig kvalitetsledviktning** perfekt
  (Arcada 2020 använde bara senaste års ROIC och fick signifikant alpha).
- **Kvarstående gap:** kvartalsvisa interimssiffror finns INTE i
  Bolagsverket-registret (delårsrapporter lämnas till börsen/bolagen, inte
  registret) → kvartalsvisa faktorer (PEAD, momentum-ökad quality-timing)
  kräver egen Q-rapport-extraktion (planerad pipeline) — eller yfinance.

**1.2 Tidigare QMJ-"endast en masteruppsats" → NU FYRA OBEROENDE STUDIER**
- **Heggli & Haugland (NTNU 2025):** A-uppsats som **VANN NTNU:s
  masteruppsatspris 2025** (jury: prof. Torvik & Lindset). Ej peer-reviewed
  tidskrift, men juryns nobelbedömning: "svært god kvalitet... bidrar til den
  vitenskapelige litteraturen på en god måte."
- **Andersen & Haugen (NTNU 2022):** QMJ ger abnormala avkastningar i alla
  nordiska länder, "quality puzzle confirmed in the Nordics."
- **Leira & Lerøen (NHH 2020, Oslo Børs 1998–2018):** högkvalitetsportfölj ger
  signifikant positiv meravkastning; QMJ-faktorn riskjusterad positiv.
- **Bashilov (Arcada 2020, Norden 2014–2019):** ROIC-top-10 % → signifikant
  alpha (CAPM + FF3), **LÄGRE volatilitet & högre Sharpe än marknaden**,
  **ÅRLIG rebalansering 1 juni** (retail-replikerbar), och "vi använder
  senaste års ROIC — 3-årspersistens-filtret gav inte mer". Direkt
  implementeringsmall.
- **Slutsats:** riktningen (kvalitet ger positiv riskjusterad meravkastning i
  Norden) är nu dokumenterad av 4 studier på 3 universitet, 2020–2025, +
  AQR globalt (peer-reviewed, 23/24 länder). **Magnituden är osäker**
  (se devil's advocate — gross vs netto-reallitet).

**1.3 Verkligheten för aktiva nordiska förvaltare (NETTO-testet)**
- **Wasa-studien 2025** (Osuva, aktiv förvaltning i Norden, 62 fonder,
  DEC 2016–2024, **döda fonder INKLUDERADE** — survivorship-bias-fritt):
  hög Active Share-fonder genererade **1,5–2,4 %/år brutto**, och
  **1,13–1,15 %/år NETTO** efter avgifter och transaktionskostnader
  (mot riktiga indexfonder som benchmark).
- **BNP Paribas Nordic Small Cap** (sept 2025): 3-års annualiserad 13,93 %
  mot Carnegie Small Cap Nordic-benchmark 12,29 % → **~+1,6 %/år brutto**
  (före fondens egna avgifter ~1,5–2 % → ungefär noll till +0,1 % netto).
- **Budskap:** även professionella förvaltare med fullständig data, kapacitet
  och låga kostnader fångar i praktiken **~1–3 %/år brutto** i nordiska
  småbolag — INTE 9–10 %/år (som de akademiska siffrorna antyder brutto med
  helt bakåtblickande perfekta portföljer och ej exekvera-bara villkor).
- **Ärligt acceptansintervall för vår produktion:** **+1–3 %/år netto över
  index för en disciplinerad, lågomsättnings-användare**; optimistiskt
  +3–5 %/år för en årlig årsredovisnings-QMJ-screen. Negativt möjligt.

**1.4 Insider-data i NO/DK/FI (MAR-artikel 19) — bekräftat:**
- **Finland:** FIN-FSA mottar; börsmeddelanden publicerar; **tröskel höjd till
  EUR 20 000 från 4 dec 2024** (var 5 000) → färre småtransaktioner måste
  rapporteras = signalen blir glesare men välinformerad.
- **Norge:** MAR från 1 mars 2021; primärinsiders rapporterar till
  Finanstilsynet; **emittenten publicerar** via Oslo Børs/NewsPoint.
- **Danmark:** börsmeddelanden (Copenhagen), samma struktur.
- **Sverige: unikt.** FI:s marknadssök är ett CENTRALT register (det FI
  publicerar), inte bara "emittenten publicerar". Därför: Sverige kärnan nu;
  NO/DK/FI via börsmeddelande-parsning (news-pipeline, fas 2b) — BYGG BARA
  OM Sverige-signalen valideras.

**1.5 Plattformens existerande valideringsmaskineri (läst kod)**
- `signal_analytics.py`: beräknar REDAN forward returns (5/10/20/60 d) per
  signaltransition, durationer, win-rates, sektor-uppdelning →
  `signal_persistence_cache`. **Fas 0 är billigare än jag trodde.**
- **GLAPP som måste täckas:** ingen per-faktor-IC/decil-spread (Rank-IC per
  kvalitet/momentum-faktor), och horisonterna (max 60 d) är för korta för
  kvalitetsalpha (6–12 mån). Utöka horisonter + släpp per-faktor-scores i
  `prediction_outcomes`/`score_history` NU.

### ⚠️ KVARSTÅENDE OSÄKERHET (ärligt märkta)

1. **FI:s Excel-länkar för blankningar:** statisk HTML ger inga .xlsx-hrefs
   (sidan renderar dem via JS/app). Jag VERIFIERADE att register-sivans
   **HTML-tabell är scrapbar** (live-data 2026-08-28 med LEI + total short %),
   men Excel-export-URL:en måste identifieras i DevTools vid byggtillfället.
   Fallback: scrapa HTML-tabellen + "Historic positions"-vyn. Ej blockerare.
2. **NTNU 2025:s exakta mekanik** (rebalansfrekvens, kostnader, universe):
   fulltexten ligger bakom JS — abstrakten är verifierade. MSCI-UCITS-konstruktion
   antyder kapattad månads-/kvartalsrebalansering, förmodligen GROSS.
   Jag behandlar 80–90 bps/mån som **övre gräns i rent backtest-laboratorium**.
3. **Börsdata REST-API-nivå:** officiella sidor motsäger varandra
   (api_page säger "Pro för Nordic"; changes2025 säger "Pro+ från 1 feb 2025").
   **Verifiera med dem INNAN köp** (25 € vs 59 € = stor skillnad). OBS:
   Bolagsverket-fyndet gör Börsdata-övervägandet lägre prio nu.

---

## 2. DEVIL'S ADVOCATE — argumenten MOT

**D1. "Du mäter fel sak i fel tidsram."** Evidensen handlar om 6–36 månaders
premier. Plattformens valideringsloop mäter 5–60 dagars signalpersistens.
Ett år av "vi testar nu" kan visa INGET eller fel och få dig att tappa
förtroende. → Kräver förlängda horisonter INNAN någon slutsats.

**D2. "Nettto-alfan är liten — och din användare äter spredditen."**
Fondverklighet: 1–3 %/år bruttopremie för proffs med full data och
institutionell exekvering. Din användare betalar ~1 % per sida
(84–100 bps spread + courtage). Om användaren rebalanserar månadsvis:
kostnad 12 %/år → alla premier utplånade, säkert minus. **Produkten kan inte
rädda en högomsättande användare.** Enda fungerande versionen: årlig/
kvartalsvis ledviktning och långa fönster. Detta MÅSTE kommuniceras tydligt
i UI:t (förväntningsstyrning) — annars bygger du en bull-market-figur som
kollapsar vid första omsättningsruschen.

**D3. "Övertro på akademiska grova siffror."** 80–90 bps/mån ~ 9–10 %/år
gross är ett idealiserat resultat: fullständig börslistan (inkl. micro),
perfekt revisornjord data, prisindex med kapad vikt, inga kostnader.
Verkligheten (Wasa/BNP) säger ~1–2 %/år brutto. Att sälja säger "upp till 10 %"
vore oärligt och skulle användas av användare att handla ofta = skada.

**D4. "Crowding + tillräckligt utbud."** Sveriges ~80 småbolagsfonder har
jagat kvalitet i 20+ år. Kvalitetspremien i main-list småbolag är
sannolikt delvis prissatt. Överlevnadskvarteret är micro/small bortom
fondernas kapacitet och de mest illikvida namnen — exakt där spredditen
dödar din användare. **Kvarstående edge är smal och svåråtkomlig.**

**D5. "Tid > pengar."** Hela stacken (QMJ + PIT-fundamenta + shorts + PEAD +
validering) ≈ 4–8 veckor utveckling. Sannolikheten att plattformen har
viktigare hål just nu (stabilitet, UX, datakvalitet — se alla migrations och
fixar i AI_GUIDE) är hög. En alpha-motor på en instabil grund = bästa
marknadsföringen för dina konkurrenter.

**D6. "Regulatorisk/etik."** Om produktens marknadsföring implicit lovar
avkastning → risk för "unfair commercial practices"-problem + förtroendeskada
när resultaten blir tröga. Enda säkra ramen: "evidensbaserade signaler,
mätbar track record, ej rådgivning" — som produktposition är det mindre
klibbigt än "AI som ger dig alpha".

**D7. "Det finns ingen garanti — bara sannolikheter."** AQR själva skriver om
QMJ: "returns must be either an anomaly, data mining, or a still-to-be
identified risk factor." Om Asness inte vet, vet vi inte.

---

## 3. ARGUMENTEN FÖR (vad som faktiskt är kvar när röken lagt sig)

**F1. Datan är unikt bra och UNIKT BILLIG:** FI:s centrala insiderregister,
FI:s blankningsregister, Bolagsverkets ESEF/årsredovisningar + notifieringar
(avlistningar!) — alla gratis, officiella, punkt-i-tid-enliga. Ingen av era
konkurrenter (Avanza-, Nordnet-verktyg, betalde sajter) integrerar dessa
sammantaget. Det är **differentiering som kostar 0 kr kontant**.

**F2. Mätbar track record = äkta förtroende-varumärke:** plattformen kan bli
den enda svenska sajten som VISAR sin egen signalhistorik och utfall
(prediction_outcomes + score_history från dag 1). Ingen annan kan kopiera
det snabbt — det bygger på dagliga arkiv.

**F3. Skyddsfunktioner är värde i sig:** likviditetsfilter + short-avvikare +
kvalitetsgolv dämpar retail-användarnas klassiska blunders (köp av kassa
micro-caps med -80 %). Harm-reduction + tydlighet = kundbehållning.

**F4. Fyra oberoende studier (2020–2025) + AQR peer-reviewed:** riktningen är
så väldokumenterad som retrospektiva faktorstudier kan bli. Det är inte
spådom — det är den bästa grupperade evidensen som finns för den här
marknaden.

**F5. Låg kontant kostnad:** vägen är 0 kr/mån (exkl. kanske 50–150 kr
DeepSeek vid LLM-extraktion). Det enda som kostar är din tid.

---

## 4. ÄRLIG DOM — ÄR DET VÄRT DET?

**Kort svar: JA — men smalt inramat, med låg förväntning och i rätt ordning.
Det är värt ~2–4 veckors utveckling, inte 8. Och det är värt som
"trovärdighet + bättre beslutsunderlag + skyddsfilter", INTE som "en maskin
som ger dig alpha".**

**Verkligt förväntningsintervall (ärligt):**
- **Optimistiskt (evidensstödjt, om allt klickar och du rebalanserar årligen):**
  +2–5 %/år netto över index, med lägre volatilitet än marknaden.
- **Realistiskt (fondverklighet):** +1–3 %/år netto, om ens det.
- **Nedåt-scenario:** 0 %/+ eller minus efter dina egna kostnader, särskilt
  om du omsätter ofta.
- **Det "häftiga" du ser (9–10 %/år) är en labbsiffra. Lita aldrig på den.**

**VÄRT att göra nu (ordning):**
1. **Fas 0 (2–3 dagar):** förläng utfallshorisonterna (90/180/365 d), lägg
   per-faktor-Rank-IC/decil-tabeller. Utan detta kan du inte ens börja prata
   om alpha. Idag mäter ni 5–60 d signaler — fel tidsram.
2. **Fas 1a (3–5 dagar):** FI blanknings-worker (0 kr, unik gratisdata) som
   riskfilter + ny-disclosure-varning. Omedelbar produkt-/differensvinst.
3. **Fas 1b (4–6 dagar):** insider-säljkluster-varning + kvalitetskomposit
   (QMJ-z-score, **årlig ledviktning**, 4–6 nyckeltal ur ESEF + yfinance).
   Bygg på existerande Piotroski/FCF-modeller.
4. **Fas 2 (senare, efter validering):** PEAD/bredare faktortuning — ENDAST
   om Fas 0-data visar att signalerna bär.

**INTE värt nu:** Börsdata 59 €/mån (Bolagsverket löser årsdata), PEAD
innan Fas 0, månadsrebalansering, Europa-expansion, och framför allt:
ALLA "alpha"-claims i produkt/marknad. UI:t ska Visa: "Evidensgrundad
kvalitetsscreening; vi mäter vår egen träffsäkerhet här (länk); historisk
avkastning är ingen garanti; handla sällan, småbolagsspredden ~1 %/sida."

**Vad som skulle ändra min dom:**
- Om plattformen har öppna stabilitets-/databugg-idag → fixa först (kolla
  STATUS.md/TODO).
- Om din egen sannolikhet att använda verktyget/hålla ut med en
  årslång-forward-validering är låg → gör bara Fas 1a (shorts) och sluta där.
- Om du planerar att omsätta > 2–3 ggr/år i småbolag → pausa (spredden äter
  allt); bygg i stället förståelse för att verktyget kräver tålamod.

---

## 5. Referenstillägg (del 2)

- Bolagsverket: apierochoppnadata/hamtaforetagsinformation/vardefulladatamangder
  (uppd. 2026-06-30, avgiftsfritt); v4.7-nyheter (2026-03-24, finansiella
  rapporter), v4.8-nyheter (2026-04-23, detaljerad status).
- NTNU 2025: nva.sikt.no/registration/0198ef9185e0-... (prisvinnare 2025).
- Andersen & Haugen (2022): hdl.handle.net/11250/3060369 (NTNU, QMJ Norden).
- Leira & Lerøen (2020): openaccess.nhh.no hdl 11250/2734785 (Oslo Børs).
- Bashilov (2020): theseus.fi 10024/337854 (ROIC Norden, årlig rebalans).
- Wasa 2025: osuva.uwasa.fi/bitstreams/be0627fd-... (Active-funds Norden,
  2016–2024, döda fonder inkluderade; 1,13–1,15 %/år netto).
- BNP Paribas Nordic Small Cap factsheet (2025-09-30): ~+1,6 %/år brutto vs
  Carnegie Small Cap Nordic.
- Nasdaq Helsinki regulatory notice (2024-12-03): Art. 19-tröskel EUR 20 000.
- Euronext/Oslo MAR-letter (2021-01-11): primärinsider-rapportering →
  Finanstilsynet + emittentpublicering, tröskel EUR 5 000.
- signal_analytics.py (marketscan/backend_worker): existerande forward
  returns 5–60 d, signalpersistens, win-rates.
