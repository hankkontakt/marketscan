# Faktorer och AI: en evidensbaserad granskning för MarketScan (Nordic small cap-fokus)

*Datum: 2026-08-28. Uppdrag: webbresearch, inga kodändringar. Alla påståenden är citerade mot de källor som listas i slutet; inget har hämtats ur minnet utan verifiering via sökning + djupavläsning av källorna.*

---

## Sammanfattning (för den otålige ägaren)

1. **Small-cap-premien som sådan är död sedan ~1983** — men "småbolag" är ändå rätt universum, eftersom **alla** faktorer (värde, kvalitet, PEAD, insider, momentum) är starkare i småbolag. Fördelen är alltså faktor-exponering + illikviditetspremie, inte storleken i sig (Asness et al. 2018; van Dijk 2011).
2. **De faktorer som har verkligt stöd för nordiska småbolag**, i fallande styrka: **Piotroski F-Score** (~10 %/år internationellt, starkast i småbolag), **PEAD** (dokumenterad i Sverige/Norden, men modest och kostnadskänslig), **kvalitet (gross profitability/ROIC)** (likvärdig med value, korrelerar negativt med value → bra hedge), **momentum 12-1** (globalt starkast i småbolag men svensk småbolagsevident blandad — en 2024-studie finner *reversal*), **insiderköp PDMR** (signaleffekt vid annonsering, starkare i småbolag, men långsiktig drift ifrågasatt i senaste svensk forskning), **short interest** (stark US-evidens, svag tillgänglighet i Norden).
3. **Där LLM/AI mätbart tillför värde** (med evidens): **earnings-call-ton** (FinBERT, out-of-sample alpha; Q&A-delen mest informativ), **nyhetssentiment med moderna språkmodeller** (OPT/LLaMA-3 slår ordlistebaserade metoder med bred marginal; håller även efter transaktionskostnader), **LLM-baserad nyhetsförståelse för småbolag** (Lopez-Lira & Tang: prediktiv kraft *starkare i småbolag* och efter negativa nyheter).
4. **Där AI är hype**: LLM-prisprognoser (alpha försvinner under bias-korrigerad backtesting — FINSABER), "AI-score" utan grund i verifierbara data, headlinesentiment på illikvida småbolag (få nyheter, ingen täckning → signalen är brus), ML på ~700 aktier (överanpassning är norm, inte undantag), samt all form av backtesting med look-ahead/survivorship-läckage (LightGBM är *särskilt* känslig för exekveringsläckage — direkt relevant för MarketScan).
5. **Rekommendation**: stoppa ny "AI-featurism". Prioritera (a) korrekt punkt-i-tid-data + purged walk-forward-validering av befintlig LightGBM — det enda som skyddar mot falsk alpha; (b) PEAD- och F-Score-signaler (billiga, evidensbaserade); (c) earnings-call/rapport-NLP som *händelseextraktion* + ton; (d) insider-/PDMR-eventflöde; (e) RAG-Q&A enbart som verifierat beslutstöd (inte signal).

---

## 1. Rankingfaktorer med verkligt stöd för småbolag

### 1.1 Small-cap-premien: debatten (vad du faktiskt köper)

**Läget:** Den obetingade small-cap-premien (Banz 1981) försvann efter början av 1980-talet. van Dijk (2011) sammanfattar 30 år av forskning: effekten är svag efter upptäckten, koncentrerad till mikrobolag och till januari. Asness, Frazzini, Israel, Moskowitz & Pedersen (2018, *Size matters, if you control your junk*) visar att preemien **återuppstår när man kontrollerar för kvalitet ("junk")** — och att den då är stabil, inte koncentrerad till mikrobolag, och finns i 24 marknader. Deras tolkning: småbolagspremien är i hög grad en **illikviditetspremie** (storleksfaktorn laddar tungt på likviditetsriskfaktorer).

Nyare forskning nyanserar ytterligare: premien lever kvar **villkorat på konjunktur-fas** (signifikant positiv endast i konjunktur-bottnar — APJFS 2024) och **endast under perioder av penningpolitiskt lättande** (2024-års studie "The resurrected size effect still sleeps in the (monetary) winter"; QMJ förklarar inte bort den i 2000-talet). Horowitz-Loughran-Savin (2000): effekten försvinner när man tar bort aktier < $5M market cap.

**Slutsats för MarketScan:** Att fokusera på nordiska småbolag är inte fel — men motiveringen ska vara **faktorpremiernas styrka i småbolag** (se nedan), inte en tro på "size premium". Småbolag = högre friktion (spread, marknadsimpact, blankningssvårigheter) som både skapar utrymme för långsam prisanpassning *och* äter avkastning. Varje signal måste backas netto efter kostnader (se PEAD-avsnittet: netto-drift är högst i small-cap, inte micro-cap — Quant Decoded 2026).

### 1.2 Momentum (12-1)

- **Evidensstyrka: stark globalt; blandad i svenska småbolag.**
- Jegadeesh & Titman (1993) är grunden; Fama & French (2012) finner momentum i alla regioner utom Japan, och **starkare i småbolag** (globalt 0,82 %/mån för små vs 0,41 % för stora).
- Norden: Grobys (2018, *Applied Economics*): momentum starkt och signifikant i nordiska marknader **oavsett storlek**; värdepremien däremot bara när småbolag ingår.
- Sverige: Parmler & González (2006) fann signifikant momentum (men svagare i storlekssorterade portföljer); Gong et al. (2015) fann signifikanta vinster; KTH-uppsats (1998–2022): positivt men **inte statistiskt signifikant** (t=1,53); DivA-uppsats (2014–2024): i svenska **småbolag** fann studien **reversal** — vinnare underpresterade med −1,60 %/mån (t=−2,29) — medan big-cap-momentum fungerade. En sektor-justerad ("residual momentum") studie av svenska småbolag 2010–2026 (uppsatser.se) ger Sharpe 0,8 vs 0,57 för traditionell, men **bootstrap visar att skillnaden inte är signifikant och alpha försvinner under realistiska kostnader**.
- **Decay/trängsel:** kraftigt urholkad i USA sedan publicering (McLean & Pontiff 2013); momentumkrascher (Barroso & Santa-Clara).
- **Billighet att beräkna: mycket billig** (enbart prisdata; se 1-mån-reversal-skip).
- **Nordic-small-cap-notis:** den senaste svenska småbolagseviden är inte vänlig mot klassisk 12-1. Behåll momentum men vikt ner, eller använd residual/sektor-justerad variant; förvänta dig att den kan vara svag i just småbolag.

### 1.3 Värde (P/B, EV/EBIT, FCF-yield)

- **Evidensstyrka: stark, men värde har haft ett förlorat decennium; i Norden bara i småbolag.**
- Fama-French (1992, 2012), Asness et al. (2013): värde fungerar internationellt. Grobys (2018): i Norden gav value **excessavkastning endast när småbolag ingick** i portföljen (1993–2017).
- **EV/EBIT (earnings yield) är den bättre måttstocken** än P/B: Novy-Marx (2013) och Greenblatts Magic Formula använder EBIT/EV; Magic Formula-studie (EUR, 1987–2021): alpha fram till ~2010, **inte efter** — värde-signalen är trängd.
- **FCF-yield:** Novy-Marx (2013): FCF har viss inkrementell kraft men **gross profitability är starkare prediktor** än både earnings och FCF.
- **Decay/trängsel:** HML-svaghet efter 2007 (value "crash"); men värde fungerar som hedge mot momentum/kvalitet (korrelation −).
- **Billighet: mycket billig.**
- **Nordic-notis:** småbolagvärde i Norden är dokumenterat; var försiktig med bokslutsdatum (punkt-i-tid!) — svenska bolag rapporterar sent, restatement är vanligt.

### 1.4 Kvalitet (ROIC, gross profitability)

- **Evidensstyrka: stark; bland de mest robusta moderna faktorerna.**
- Novy-Marx (2013, JFE): **gross profits-to-assets har ungefär samma kraft som book-to-market** (0,33 %/mån spread, FF3-alpha 0,55 %/mån, t=4,75); **korrelerar negativt med värde** → perfekt hedge; att kombinera value+profitability nästan dubblar Sharpe (0,85 vs 0,34 för marknaden). Fångar även framtida tillväxt i vinster/kassaflöden.
- Asness, Frazzini & Pedersen (2019, QMJ): quality minus junk — robust internationellt. **MarketScans nuvarande 0,40-vikt på kvalitet i QMJ-kompositen har direkt stöd** i litteraturen.
- Ivey/Novy-Marx (quality dimension): i small-cap-universum är **F-Score och gross profitability de klart bästa kvalitetsmåtten** att kombinera med värde; ROIC (Greenblatt) fungerar också men sämre.
- **Billighet: billig** (bokslutsdata). **Decay:** lägre än value/momentum; har blivit institutionellt standard men med mindre urholkning hittills.
- **Nordic-notis:** kvalitetsmått behöver punkt-i-tid-bokslut; IFRS-redovisning gör GP/A beräkningsbar.

### 1.5 Piotroski F-Score

- **Evidensstyrka: stark och internationellt reproducerad — särskilt i småbolag.**
- Piotroski (2000): 9 binära signaler från bokslut; bland hög-B/M (value)-bolag gav high-F-score ≈ +13,4 % vs −9,6 % för low-F-score (~23 %-spread) på ett år. Kraften kommer **från små, finansiellt svaga bolag utan analytikertäckning**.
- Internationell evidens 2000–2018 (Springer *Journal of Asset Management* 2020): **~10 %/år** i utvecklade marknader (inkl. Europa) och 12 % i tillväxtmarknader; signifikant i **alla storlekssegment** inkl. stora bolag; överlever kontroll för storlek, B/M, momentum, lönsamhet och investeringar; kraften avtar små→stor.
- Australien (Bettman et al.): 0,8 %/mån large, **1,4 %/mån small** — men Carhart-alpha bara för equal-weighted småbolag, och mycket av avkastningen kommer från korta sidan (oinvesterbar för institutioner).
- Tyskland (2021): F-Score förbättrade **alla** 12 testade lång-only-strategier (nettoavkastning 12,2 % → 15,0 %/år), även på 3-årshorisont.
- **Varningar:** Kim & Lee (2014) hävdar att Piotroskis ursprungliga siffror är kraftigt överskattade pga. **look-ahead bias**; effekten är delvis short-driven och kostnadskänslig (småbolagsspreadar); 2024-uppföljning visar att F-Score påverkas kraftigt av makro/penningpolitik under kontraktionsfaser (makrovariabler 5× viktigare i kontraktion).
- **Billighet: extremt billig** — inga konsensusdata, inga modeller; bara 9 0/1-flagg från bokslut. **Den bästa "gratis"-faktorn i denna lista.**
- **Nordic-notis:** passar perfekt på nordiska småbolag (låg analyst coverage); kräver punkt-i-tid-bokslut.

### 1.6 Insiderköp (PDMR)

- **Evidensstyrka: måttlig; signaleffekt vid annonsering, särskilt i småbolag; långsiktig drift omdebatterad.**
- Sverige 2014–2016 (DivA): CAR (0;1) **+1,27 % för köp, −1,03 % för försäljningar**; för småbolag **+1,9 %/−1,6 %** vs +0,66 %/−0,48 % för stora — signaleffekten är starkare i småbolag (högre informationsasymmetri). GU-uppsats (2025, 2022–2024): köp följs av signifikant positiva CAR, **större i small cap**.
- **Men** GU-uppsats (2026, 2019–2024, FI:s PDMR-register): insiderköp följs **inte** av positiva abnormal returns (nära noll kortsiktigt, signifikant negativt på längre horisonter); försäljningar följs av negativa. Slutsats: semi-stark effektivitet i en transparent miljö — signalen är "prissatt" vid annonsering. Norges registerstudie (*Flying below the radar*, 2026): chefer under toppen tjänar abnormal avkastning på köp i egna bolag.
- EU-övergripande (Dardas & Güttler, 8 länder 2003–2009): annonseringseffekter i 4/8 länder, starkast för köp, beroende av transaktionsstorlek, bolagsstorlek, B/M och multipla insiders; Sverige bland länderna med signaleffekt.
- **Nordic-notis:** PDMR-registret hos FI är **gratis och maskinläsbart** — kostnaden är nära noll. Evidensen säger: utnyttja annonseringsögonblicket och köp-sidan i småbolag; var skeptisk till att "mimicking" ger långsiktig drift i dagens marknad. Kombinera med transaktionstyp (första köp, storlek relativt lön, placeringsprogram = svag signal).

### 1.7 PEAD (earnings drift)

- **Evidensstyrka: stark i småbolag, svag/obefintlig i stora — och netto efter kostnader bäst i small cap.**
- USA: Quant Decoded-backtest (2000–2025): drift i micro/small **~3× större än mega** (dag 60: 5,8 % micro / 4,9 % small / 1,5 % mega); **netto efter kostnader är small-cap-kvintilen bäst (3,8 %)** eftersom micro-kostnaderna äter upp 3,0 p.p.; driften varar 60+ dagar i små vs ~20 i stora; kvoten micro/mega stabil (3,2–4,3×) trots absolut nedgång.
- HHS-uppsats (*Resurgence of PEAD*, 220 228 annonseringar 2005–2024): small caps 6,81 % abnormal på 60 dagar (≈28 %/år annualiserat); storbolags-PEAD har dock *återhämtat sig* post-2020.
- **Motbevisen är viktiga:** Subrahmanyam (2026): PEAD finns **inte** utanför microcaps efter decimaliseringen 2001 (t=1,43 exkl. micro; t=2,18 inkl.). Columbia (Zhao et al.): nedgången i PEAD förklaras av minskad earnings-persistence, inte bara arbitrage.
- **Norden:** Setterberg (2011), Sverige 1990–2005: **11,4 %/år** med 12-månaders hållperiod, driven av long-sidan. GU (2024, "Sleepy Markets", Norden 2014–2022): drift finns i både LONG och SHORT men **hedge-spreaden ger ingen signifikant avkastning** — svagare än klassisk US-evidens. Svensk governance-studie (2010–2022): PEAD finns upp till 12 mån, starkare i dåligt styrda bolag. Finland: drift främst vid negativa överraskningar (Kallunki 1996).
- **Billighet: billig om du har konsensusdata** (SUE = faktisk EPS − konsensus); annars svår (kräver forecast-serier). **Decay:** komprimerad men proportionellt kvar i småbolag.
- **Nordic-notis:** PEAD är den faktor där "långsam informationspridning i småbolag" faktiskt är mätbar — men förvänta dig mindre än US-siffrorna och var kostnadsmedveten.

### 1.8 Short interest

- **Evidensstyrka: stark i USA, svår i Norden.**
- Rapach, Ringgenberg & Zhou (JFE 2016): **aggregerad short interest är den starkaste kända prediktorn för aktiemarknadens riskpremie** (annualiserad R² = 12,89 % in-sample, 13,24 % OOS; kassaflödeskanal). Korssnittet: Boehmer-Jones-Zhang (2008), Asquith-Pathak-Ritter (2005): hög short interest → lägre framtida avkastning; shorts är informerade (Engelberg-Reed-Ringgenberg 2012).
- **Nordic-notis:** FI publicerar blankningspositioner ≥ 0,5 % (daglig uppdatering) — användbar som **trängselvarning** (crowding/framed-reversal), inte som primär signal. Finlands korta sida historiskt begränsad. Evidens för *nordisk* cross-sectional short-interest-signal saknas i stort sett.

### 1.9 Säsongseffekter (januari-effekten)

- Haug & Hirschey (FAJ 2006, 1802–2004): **januari-effekten för småbolag är remarkabelt ihållande** och överlever TRA86 — 2,3 %/mån SMB i januari vs 4 bps resten av året (Asness et al. 2018 bekräftar: hela size-premien bor i januari). Umeå-uppsats: januari-effekten finns på Stockholmsbörsens Small Cap.
- **Men:** Szakmary & Kiefer (2004): turn-of-the-year-effekten försvann efter ~1993 i futures; modern konsensus (Investopedia/quant-strategy-genomgångar): kraftigt urholkad och trängd.
- **Billighet: gratis. Nordic-notis:** kan användas som kalibrerings-varning (decemberförsäljning → januariköp i småbolag), men räkna inte med tradeable edge.

### 1.10 Indexinkluderingseffekten

- S&P 500: inkluderingseffekten föll från 3,4 % (1980-tal) / 7,6 % (1990-tal) till **0,8 % (2010-tal), statistiskt noll** — trots växande indexering (Sammon, NBER 2022). S&P DJI: median 8,32 % (1995–1999) → **−0,04 % (2011–2021)**.
- Småbolagsindex (USA): S&P SmallCap 600-ändringar ger temporär priseffekt som **reverseras inom 60 dagar** (price-pressure-hypotesen; Amihud/Jain-forskning). Dimensional (2014–2023): Russell 2000/S&P 600-rekonstituering = 5–30 bps/år kostnad; **+3,5 % före rekonstitueringen, −2,3 % reversal efter** — handelsbar men liten och trängd.
- **Nordic-notis:** OMXSSC/First North-övergångar har mycket mindre trackat kapital → effekten i Norden är marginell. Räkna inte med detta.

---

## 2. Där LLM/AI mätbart tillför värde (med evidens)

### 2.1 Earnings-call-ton (mest evidens av allt LLM-relaterat)

- Price, Doran, Peterson & Bliss (JBF 2012): **konferenssamtalets lingvistiska ton predicerar abnormal avkastning och volym upp till 60 dagar**; tonen dominerar earnings surprise; **Q&A-delen har inkrementell förklaringskraft** (och är viktigast i icke-utdelande bolag); domänspecifik ordlista slår generell (Harvard IV-4).
- Druz, Wagner & Zeckhauser (NBER 2015): "tone surprise" (residual när negativitet regressas på prestation + CEO-fix) **predicerar framtida vinster och analytikerosäkerhet**; post-call-drift tyder på underreaktion; erfarna analytiker justerar korrekt, oerfarna över-/underreagerar.
- FinBERT-studie (arXiv 2026, 16 428 samtal 2015–2025): **sektionsviktad sentiment (analytiker 49 % vikt) ger OOS Spearman IC 0,142, long-short-alpha 2,03 %/mån (t=6,49)** efter FF5; FinBERT **subsumerar helt** Loughran-McDonald-ordlistan (FinBERT t=5,90 vs LM t=0,86); drift är gradvis (trög assimilering av mjuk information).
- Mayew & Venkatachalam (JF 2011): även röst-affekt predicerar.
- **Kostnad/effort:** transkription (gratis för många US-bolag; i Norden ofta betalvägg/scrape) + FinBERT-inferens på CPU. **Värde: reellt men koncentrerat till kvartalssamtal; i nordiska småbolag hålls få formella calls** — detta är en storbolagssignal med småbolagspotential via rapporter/Q&A-webbinarier.
- **Nordic-notis:** börja med *svenska/engelska rapport-pressmeddelanden + Q&A-transkript* där de finns (t.ex. via MarketScreener/hembud); tona förväntningarna — litteraturen är US-storbolag.

### 2.2 Nyhetssentiment i skala med moderna språkmodeller

- Kirtac & Germano (*Finance Research Letters* 2024, 965 375 US-artiklar 2010–2023): **OPT (GPT-3-arkitektur) når 74,4 % riktningsaccuracy** vs 50,1 % för LM-ordlistan; long-short med 10 bps kostnad ger **Sharpe 3,05** (+355 % aug 2021–jul 2023); FinBERT följer nära.
- ACL EvalEval 2026 (973 481 handelbara nyhetsitems, 5 bps kostnad, juni 2024–jan 2026): **LLaMA-3 78,2 % accuracy; +180 % kumulativt, Sharpe 2,85; ordliste-strategin −9 %**. Moderna LLM:er behåller ekonomisk signalkraft under realistiska friktioner; lexikon-metoder presterar ≈ slump.
- FinBERT-originalet (arXiv 1908.10063): state-of-the-art på finansiell sentimentklassificering; FinBERT når 80 % accuracy med bara 250 träningsexempel — viktigt: **domänspecifika småmodeller behöver inte enorma dataset**.
- Lopez-Lira & Tang (2023, rev. 2026): **ChatGPT-betyg på nyhetsrubriker predicerar nästa dags avkastning**; self-financing daglig strategi +38 bps/dag före kostnad, ~650 % kumulativt (okt 2021–dec 2023); **prediktiv kraft starkare bland mindre bolag och efter negativa nyheter** (stöd för småbolagsanvändning!) — men se hypesektionen för brister.
- **Kostnad/effort:** inferens med öppen modell (FinBERT/OPT) på CPU, eller API för stora volymer; kräver nyhetsflöde (Reuters/Modular Finance/egen scrape). **Värde: reellt som *screening/övervakning***; som tradeable signal på illikvida nordiska småbolag — svagare (se hype 3.3).

### 2.3 RAG-Q&A över rapporter

- **Nyckelstudiens siffra:** GPT-4-Turbo med retrieval **svarade fel eller vägrade på 81 % av kuraterade SEC-frågor** (Islam et al. 2023, citerad i FinGround 2026). Utan verifiering är RAG-svar farliga.
- Mitigationsforskning är mogen: **FinGround** (2026) minskar hallucinationer **68–78 %** via atomisk claim-verifiering + formel-rekonstruktion (8B-modell, $0,003/fråga, p95 3,8 s); **RLFKV** (2026) RL-baserad kunskapsverifiering; **FinAgent-RAG** (2026): program-of-thought med exekverbar Python — 76,8 % korrekthet på FinQA (+5,6–9,3 p.p.); **DCRC** (2026): data-centric "compile-and-execute" med 99,6 % audit-log-korrekthet, hallucinationsreduktion 12,4 % → 6,8 %.
- Generell LLM-finanshallucination: MAE 6 357 USD vid zero-shot aktiekursfrågor; RAG och verktygsanrop hjälper kraftigt (ar5iv 2311.15548).
- **Kostnad/effort:** medelhög; öppen 8B-modell gör det billigt, men **verifieringspipelinen (claim-verifiering mot tabellceller) är det som kostar**. **Värde: beslutstöd och tidsbesparing — inte signal.**

---

## 3. Där AI är hype (och varför)

### 3.1 LLM-prisprognos / "LLM-alpha"

- **FINSABER** (Li, Kim, Cucuringu & Ma, arXiv 2025) är den viktigaste motvikten: när LLM-investeringsstrategier utvärderas med bias-korrigerad backtesting (punkt-i-tid-universum, delistade bolag inkluderade, breda symbolurval, långa perioder) **försvinner alpha** — "LLM-derived alpha är sannolikt en metodologisk artefakt av snäva, partiska utvärderingar". Tidigare studier: <1 år, <10 aktier (ofta TSLA/AMZN — historiska vinnare = survivorship), naïve jämförelser.
- Lopez-Lira & Tang:s egna siffror är före transaktionskostnader, daglig rebalans (turnover exploderar), och **LLM:er är tränade på data som överlappar testperioden** (data-leakage — författarna erkänner att detta inte kan uteslutas). Siffran "90 % hit rate" gäller den *initiala reaktionen* (ej handelbar), inte en tradeable signal.
- **Failure mode:** backtest-inflation via tidsläckage (TEMP_CENTER) och exekveringsläckage (EXEC_OPEN) — *"When Alpha Disappears"* (2026) visar att **LightGBM är bland de mest känsliga modellfamiljerna** (LG-SR@5bps > 15, ibland > 20 under läckage). MarketScan använder LightGBM — detta är den mest konkreta risken i er pipeline.

### 3.2 Överanpassning på ~700 aktier

- ~700 aktier × några års daglig data är **femtio gånger för lite** för att träna fria ML-modeller: signalförhållandet är ~lågt, antalet hypoteser som testas är stort. Symptom: backtest-Sharpe > 3 ≈ nästan säkert överanpassat; > 100 features med < 5 år data; försämring när testfönstret flyttas (tradealgo 2026).
- **Lösningar som gäller er:** purged k-fold / **walk-forward** (träna bara på data före beslutstidpunkten, aldrig normalisera på hela samplet), deflated Sharpe / PBO för att korrigera antalet tester (Lopez de Prado, AFML), färre features, starka priors från litteraturen ovan.

### 3.3 Headlinesentiment på illikvida småbolag

- Evidensen för nyhetssentiment (2.2) är från stora US-universum med tiotusentals nyheter. **Ett nordiskt småbolag har kanske 2–10 nyheter/kvartal** — sentimentet blir en funktion av *vilka nyheter som råkar publiceras*, inte av ett mätbart informationsflöde. Få bolag, ingen analytikertäckning → de få nyheterna är redan prissatta eller brus.
- **Undantag som fungerar:** negativa/positiva *händelser* (vinstvarning, emission, kontrakt, FDA-besked) — händelseextraktion är robust; kontinuerlig sentiment-score är det inte.

### 3.4 Ogrundade "AI-score" och generativa analyser

- En LLM kan producera "analys" som ser övertygande ut men som inte är grundad: 81 % fel/refusering på SEC-frågor (Islam et al. 2023), fabricerade siffror och citat (FinGround/Kang-Liu 2023). **Utan claim-verifiering mot tabellceller är en "AI-fundamental-analys" en hallucinationskälla, inte en signal.**
- Look-ahead via **restaterade bokslut** (reviderade siffror används som om de fanns vid rapporttillfället) är den vanligaste tysta biasen — förödande i bokslutsdrivna faktorer (F-Score, kvalitet, PEAD). Survivorship bias är **värst i småbolag** (högre avlistningsgrad; 1–2 %/år i breda US-databaser, mer i kriser).

### 3.5 Sammanfattning av failure modes (kontrollista för MarketScan)

| Bias | Mekanism | Fix |
|---|---|---|
| Look-ahead bias | Reviderade/restaterade siffror; framtida indexmedlemskap; signal+fill i samma bar | Punkt-i-tid-data med releasedatum; fill nästa open |
| Survivorship bias | Avlistade bolag saknas (värst i småbolag) | Inkludera delistade + slutkurser |
| Walk-forward-läckage | Normalisering/feature-engineering över hela samplet; purged-fönster saknas | Purged CV, embargo, walk-forward |
| Exekveringsläckage | Signal från dag t, fill dag t close | Fill t+1 open |
| Överanpassning | ~700 aktier, många hypoteser | Deflated Sharpe, PBO, få features |
| LLM-hallucination | Fabricerade finansiella siffror | Claim-verifiering mot strukturerade data |

---

## 4. Konkret rekommendation: 5–8 applikationer rankade

Rankingkriterier: **evidens × billighet × nordisk-small-cap-passform**. (1 = starkast rekommendation.)

### 1. Punkt-i-tid-datapipeline + purged walk-forward-validering (infrastruktur, inte feature)
- **Varför:** Det enda som garanterat mätbart förbättrar MarketScan är att veta att befintliga siffror inte är falska. LightGBM är särskilt känslig för exekveringsläckage; 700 aktier är överanpassningskänsligt.
- **Data:** bokslut med releasedatum (inte räkenskapsperiodens slut), avlistade bolag inkluderade, konsensus vid publiceringsdatum.
- **Modell:** befintlig LightGBM; ändra bara valideringen (purged k-fold + walk-forward med embargo; deflated Sharpe; PBO < 0,3).
- **Cachning:** point-in-time-snapshot per ticker/datum; feature-store med as-of-tidstämpel.
- **Ärlig förväntad effekt:** ingen ny alpha, men eliminerar risken för *imaginär* alpha; gör alla andra steg valida. Kostnad: medelhög engångsinsats, ingen löpande kostnad.

### 2. PEAD som signal (SUE → långsam rebalansering)
- **Evidens:** US small 3× drift, netto bäst i small cap (3,8 %/60 dagar); Norden: Setterberg 11 %/år (12 mån), GU 2024 blandat men riktningsmässigt stöd.
- **Data:** faktisk EPS vs konsensus (Modular Finance/Refinitiv — eller egen prognosmodell), annonseringsdatum, punkt-i-tid.
- **Modell:** ingen ML — decilrankning av SUE; håll 1–6 månader; skippa de dyraste micro-namnen.
- **Cachning:** event-tabell per bolag (senaste SUE, drift-ackumulering).
- **Ärlig förväntad effekt:** 1–4 %/år brutto i urvalet; känslig för spreadar; använd marknadsorders i små poster. **Bästa evidens-per-krona i hela listan.**

### 3. Piotroski F-Score som kvalitetsfilter ovanpå värde
- **Evidens:** ~10 %/år internationellt, starkast i små/lågtäckta bolag; förbättrar alla lång-only-strategier (Tyskland).
- **Data:** 9 variabler från senaste bokslut (ROA, CFO, förändringar, accruals, margin, leverage, likviditet, emissioner). **Ingen ML, inga konsensusdata.**
- **Modell:** summa av 9 0/1-signaler; använd som *filter* (F ≥ 7) ovanpå värde-/momentumranking, eller som ingång i QMJ-kompositens kvalitetsdel.
- **Cachning:** årsvis beräkning per bolag; enkel tabell.
- **Ärlig förväntad effekt:** 2–5 %/år i urvalet om det kombineras med värde; långsam rotation (årsvis) → låga kostnader.

### 4. Earnings-call/rapport-NLP: händelseextraktion + Q&A-ton (LLM-delen med mest evidens)
- **Evidens:** FinBERT sektionsviktad alpha 2,03 %/mån OOS; Price et al. 2012 (Q&A viktigast); ton-surprise predicerar vinster (Druz-Wagner-Zeckhauser).
- **Data:** pressmeddelanden (hembud), Q&A-transkript där de finns; svensk+engelska. FinBERT (eller modernare encoder) på CPU — inget API behövs.
- **Modell:** (a) händelseextraktion: vinstvarning/guidance-ändring/kontrakt/emission → klassificerare; (b) ton: FinBERT-score per sektion, viktad mot Q&A.
- **Cachning:** per-bolag senaste händelse + ton lagrad; analyseras kvartalsvis, inte dagligen.
- **Ärlig förväntad effekt:** händelseextraktion: robust, hög nytta som *triage* (vad hände, när, hur allvarligt). Ton-signalen: reell i stora bolag, osäker i nordiska småbolag — börja som screening, utvärdera efter 2 år. Kostnad: låg (öppen modell).

### 5. Insider-/PDMR-eventflöde som trigger (köp-sidan, småbolag)
- **Evidens:** annonserings-CAR +1,9 % (0;1) småbolag Sverige; nyare studier visar svag långsiktig drift — använd som *trigger*, inte som långsiktig hållsignal.
- **Data:** FI:s PDMR-register (gratis); berika med transaktionstyp, storlek, roll, historik (första köpet efter lång tystnad = starkast).
- **Modell:** regel-klassificering (inget ML): köp > 3× månadslön, ej placeringsprogram, small cap, 2+ insiders samma dag → flagga.
- **Cachning:** eventlogg + "senaste köp per bolag" — trivielldrift.
- **Ärlig förväntad effekt:** få signaler/år (därför bra som *en* trigger bland flera); ~1–2 % CAR per event i genomsnitt, inga garantier.

### 6. Kvalitetsfaktorn (gross profitability) som komplement — stödjer befintlig QMJ-vikt
- **Evidens:** Novy-Marx: GP/A ≈ B/M-styrka; korrelerar − med value → höjer Sharpe; bäst ihop med F-Score i small cap.
- **Data:** GP/A och/eller ROIC (EBIT/investerat kapital) från punkt-i-tid-bokslut. Ingen ML.
- **Modell:** ranka in i QMJ-kompositen (ni har redan 0,40 på kvalitet — litteraturen stödjer det; överväg att byta ROE mot GP/A som kvalitetsmått).
- **Cachning:** årsvis.
- **Ärlig förväntad effekt:** riskjusteringsförbättring snarare än raw alpha; hedge-effekt mot värde och momentum.

### 7. RAG-Q&A över rapporter som *verifierat* beslutstöd (inte signal)
- **Evidens:** hallucination är norm (81 %), men verifieringspipelines (FinGround-stil, claim-verifiering + formel-rekonstruktion; $0,003/fråga) gör det användbart.
- **Data:** årsredovisningar/Q-rapporter som strukturerade tabeller + text; punkt-i-tid.
- **Modell:** öppen 8B-LLM + (kritisk!) verifieringssteg mot tabellceller; aldrig "fritt" svar till beslut.
- **Cachning:** embeddings per rapportversion; claim-verifiering per fråga.
- **Ärlig förväntad effekt:** tidsbesparing och färre feltolkningar — inte avkastning. Gör det *efter* att 1–3 är på plats.

### (Avråds) 8. LLM-prisprognos, generativa "AI-betyg", daglig nyhetssentiment på småbolag, short-interest-strategi i Norden, index-inclusion-spel
- Alla fem saknar antingen nordisk data, har försvunnen evidens (index-effekten), eller dör under bias-korrigering (LLM-alpha) eller kostnader (småbolagssentiment, short sida). Skriv in dem som "medvetet avstått" i SYSTEM_AI-dokumentationen.

---

## 5. Prioriterad ordning (implementera i denna följd)

1. Punkt-i-tid-pipeline + purged walk-forward (skyddar allt annat; dagar–veckor)
2. F-Score-filter (1 dags arbete; omedelbar screening-nytta)
3. PEAD-signal (några veckor med konsensusdata)
4. PDMR-eventflöde (1–2 dagar; gratis data)
5. Rapport-NLP: händelseextraktion + ton (2–4 veckor; öppen modell)
6. Kvalitetsmått byte till GP/A i QMJ-kompositen (timmar)
7. Verifierad RAG (senare; när 1–6 körs)
8. Avstå från LLM-prisprognoser och generativa score tills vidare

---

## Källförteckning (verifierade via sökning + djupavläsning)

**Small-cap-premien:**
- van Dijk (2011), *Is size dead? A review of the size effect in equity returns* — https://ideas.repec.org/a/eee/jbfina/v35y2011i12p3263-3274.html
- Asness, Frazzini, Israel, Moskowitz & Pedersen (2018), *Size matters, if you control your junk* — https://www.sciencedirect.com/science/article/pii/S0304405X18301326
- *Why has the size premium disappeared?* (APJFS) — https://apjfs.org/file/download/6359?view=1
- *The resurrected size effect still sleeps in the (monetary) winter* (2024) — https://www.sciencedirect.com/science/article/abs/pii/S1057521924000139
- *Fact, Fiction, and the Size Effect* (Hou/Xue/Zhang-området) — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3177539

**Momentum / värde (Norden):**
- Grobys (2018), *Combining value and momentum: evidence from the Nordic equity market* — https://www.tandfonline.com/doi/abs/10.1080/00036846.2018.1558364
- DivA (2024), *The Profitability of Momentum… Swedish small and big stocks 2014–2024* — https://www.diva-portal.org/smash/get/diva2:1962607/FULLTEXT01.pdf
- KTH (2023), *Cross-sectional and time series momentum… Swedish stock market 1998–2022* — http://urn.kb.se/resolve?urn=urn:nbn:se:kth:diva-342322
- *Sector-relative momentum in Swedish Small-Cap stocks 2010–2026* — https://www.uppsatser.se/uppsats/39aaaa21cf/
- LUT (2024), *Combining value and momentum in Nordic markets 1999–2023* — https://lutpub.lut.fi/handle/10024/167780
- Novy-Marx (2013), *The other side of value: The gross profitability premium* (JFE) — https://www.sciencedirect.com/science/article/pii/S0304405X13000225 (kopia: https://oldschoolvalue-files.s3.amazonaws.com/pdf/Novy-Marx_Gross-Profitability-Anomaly_JFE_2013.pdf)
- Kreft (EUR), *Unravelling the magic of Magic Formula investing* — https://thesis.eur.nl/pub/65582/MasterThesis_MartijnKreft_474788.pdf
- Novy-Marx, *The Quality Dimension of Value Investing* — https://www.ivey.uwo.ca/media/3775548/novy-marx.pdf

**Piotroski F-Score:**
- Piotroski (2000) original (UCLA-kopia) — https://www.anderson.ucla.edu/documents/areas/prg/asam/2019/F-Score.pdf
- *Piotroski's FSCORE: international evidence* (2020) — https://link.springer.com/article/10.1057/s41260-020-00157-2
- *Piotroski F-score: evidence from Australia* — https://onlinelibrary.wiley.com/doi/10.1111/acfi.12216
- *Can the FSCORE add value… German stock market* (2021) — https://link.springer.com/article/10.1007/s11408-021-00400-9
- *Piotroski's Fscore under varying economic conditions* (2024) — https://link.springer.com/article/10.1007/s11156-024-01331-y

**Insider/PDMR (Sverige):**
- GU (2026), *When Insider Signals Meet Uncertainty: PDMR Disclosures… Swedish Stock Market 2019–2024* — https://gupea.ub.gu.se/items/f412d9de-0236-419f-aaa1-2ad1da56b1ab
- GU (2025), *Explaining Abnormal Returns from Insider Purchases: large vs small cap* — https://gupea.ub.gu.se/items/d213ae81-4b0c-4240-a522-e913d255bc93
- *The Signaling Effect of Insider Trading on the Swedish Stock Market 2014–2016* — https://www.diva-portal.org/smash/get/diva2:1296843/FULLTEXT01.pdf
- *Flying below the radar: Insider trading by executives below the top* (Norge) — https://www.sciencedirect.com/science/article/pii/S0304405X2600053X
- *Are Directors' Dealings Informative? Evidence from European Stock Markets* — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1615607

**PEAD:**
- Quant Decoded (2026), *Post-Earnings Drift Is ~3× Larger in Small Caps* — https://quantdecoded.com/en/post-earnings-drift-by-market-cap-size-matters
- HHS (2024), *The Resurgence of Post-Earnings Announcement Drift* — http://arc.hhs.se/download.aspx?MediumId=6317
- Subrahmanyam (2026), *Keeping It Simple: How Post-earnings Return Drift Can Exist and Not Exist Simultaneously* — https://doi.org/10.11648/j.jim.20261501.11
- Zhao et al. (Columbia), *Why Has PEAD Declined Over Time?* — https://business.columbia.edu/sites/default/files-efs/imce-uploads/CEASA/Events%20Page/PEAD_Declined_over_time.pdf
- GU (2024), *Sleepy Markets and the Post-Earnings-Announcement Drift (Nordics 2014–2022)* — https://gupea.ub.gu.se/server/api/core/bitstreams/a33a2d59-f568-4b82-bc66-efcc81a7d204/content
- Setterberg (2011) refererad i ovan + *PEAD on the Swedish Stock Market* (governance-studie) — https://www.diva-portal.org/smash/get/diva2:1452207/FULLTEXT01.pdf

**Short interest:**
- Rapach, Ringgenberg & Zhou (JFE 2016), *Short interest and aggregate stock returns* — https://www.sciencedirect.com/science/article/abs/pii/S0304405X16300320

**Säsong/Index:**
- Haug & Hirschey (FAJ 2006), *The January Effect* — https://www.tandfonline.com/doi/abs/10.2469/faj.v62.n5.4284
- Sammon (NBER 2022), *The Disappearing Index Effect* — https://www.nber.org/system/files/working_papers/w30748/w30748.pdf
- S&P DJI, *What Happened to Index Effect?* — https://www.spglobal.com/spdji/en/documents/research/research-what-happened-to-the-index-effect.pdf
- *Market Reaction to Changes in the S&P SmallCap 600 Index* — https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6288.2006.00146.x
- Dimensional, *Index Reconstitution Effect Within Small Caps* — https://www.dimensional.com/chmedia/490356/source/index-reconstitution-effect-within-small-caps.pdf

**Earnings call-ton / NLP:**
- Price, Doran, Peterson & Bliss (JBF 2012) — https://ideas.repec.org/a/eee/jbfina/v36y2012i4p992-1011.html
- Druz, Wagner & Zeckhauser (NBER 20991) — https://www.nber.org/system/files/working_papers/w20991/w20991.pdf
- *FinBERT section-weighted sentiment* (arXiv 2026) — https://arxiv.org/pdf/2604.13260
- Mayew & Venkatachalam (JF 2011), *The Power of Voice* — https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.2011.01705.x

**Nyhetssentiment / LLM:**
- Kirtac & Germano (FRL 2024), *Sentiment trading with large language models* — https://doi.org/10.1016/j.frl.2024.105227
- *Evaluating LLMs for Financial News Sentiment under Market Frictions* (ACL EvalEval 2026) — https://aclanthology.org/2026.evaleval-1.4.pdf
- FinBERT (arXiv 1908.10063) — https://arxiv.org/abs/1908.10063v1
- Lopez-Lira & Tang, *Can ChatGPT Forecast Stock Price Movements?* — https://arxiv.org/html/2304.07619v6

**Hype / bias / hallucination:**
- Li, Kim, Cucuringu & Ma (2025), *Can LLM-based Financial Investing Strategies Outperform the Market in Long Run?* (FINSABER) — https://doi.org/10.48550/arxiv.2505.07078
- *When Alpha Disappears: A One-Switch Benchmark for Decision-Time Leakage* (2026) — https://doi.org/10.48550/arxiv.2605.23959
- *Deficiency of LLMs in Finance: An Empirical Examination of Hallucination* (ar5iv 2311.15548) — https://ar5iv.labs.arxiv.org/html/2311.15548
- FinGround (arXiv 2026) — https://arxiv.org/html/2604.23588
- FinAgent-RAG (arXiv 2026) — https://arxiv.org/html/2605.05409
- *Fighting Numerical Hallucinations via Data-centric Compilation* (DCRC, arXiv 2026) — https://arxiv.org/html/2605.31064
- *Backtesting Pitfalls: Overfitting and Selection Bias* (Lopez de Prado/AFML-referat) — https://paperswithbacktest.com/course/backtesting-pitfalls-overfitting
- *The Three Ways Backtests Lie* — https://tesseraalpha.com/methodology/backtesting-survivorship-lookahead
- *Machine Learning for Stock Prediction: Does It Work?* — https://www.tradealgo.com/trading-guides/ai-trading/machine-learning-stock-prediction

**Nordisk marknadsstruktur:**
- OMX Stockholm Small Cap-index — https://indexes.nasdaqomx.com/Index/Overview/OMXSSCPI ; https://indexes.nasdaqomx.com/Index/Overview/OMXSSCGI
