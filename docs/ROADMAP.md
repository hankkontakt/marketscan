# Roadmap — Nybörjar-produkten

> Tailorad efter dina val (2026-06-10):
> **Slutmål:** lärprojekt med *optionalitet* — byggd så den går att **lansera ELLER sälja**.
> **Plattform:** webb först → **native mobilapp** senare.
> **Marknad:** **Sverige först → Norden** som slutmål.
> **Tempo:** hobby — kvällar, solo + AI.
>
> Detaljerad produkt-/UX-plan finns i [`NYBORJARE_PRODUKT_ROADMAP.md`](NYBORJARE_PRODUKT_ROADMAP.md).
> Det här dokumentet är **milstolpe-roadmappen**: vad varje fas är, vad du siktar efter, och
> slutmålet. **Milstolpar — inte datum.** Skeppa litet, en fas i taget; gå vidare först när
> föregående känns klar och använd.

---

## 🎯 Slutmålet (vad du siktar mot)

En **lugn, svensk-först (sedan nordisk)** app — på **webb och mobil** — som lär folk *utan
ekonomiutbildning* att **hitta och förstå** bra aktiekandidater, och känna sig trygga medan de
lär sig. Byggd som ett lärprojekt, men **arkitekterad och dokumenterad så att den kan flippas
till antingen en lansering eller en försäljning** när/om du vill:

- **Lanserbar:** riktiga användare, licensierad data, GDPR/villkor, betalning på plats.
- **Säljbar:** bevisbar traction (aktivering/retention), ren kodbas, tydlig dokumentation,
  unik svensk pedagogik som tillgång.

Du behöver **inte bestämma vilket nu** — roadmappen håller båda dörrarna öppna ända till M9.

**Designsjälen genom allt:** översätt siffror → begriplighet, dölj komplexitet tills den
efterfrågas, lugn Lysa-ton, *utbildning — inte personlig rådgivning*.

---

## Hur du ska tänka om tempo (hobby, solo + AI)

- **En milstolpe i taget.** Varje fas ska lämna något *användbart* efter sig.
- **Skeppa smått.** Hellre ett klart omdömeskort än en halv massa funktioner.
- **Bygg inte native (M7) förrän webben (M1–M5) är något du själv älskar att använda.**
- **Spar de kommersiella delarna (M9) till sist** — de låser inget och kostar pengar.
- Låt AI göra grovjobbet; din tid går åt till *pedagogiken och känslan* (det är edgen).

---

## Faserna

### M0 — Fundament & riktning
**Vad:** Lås positionering, persona och den regulatoriska framingen (utbildning, ej rådgivning).
Skapa en **plain-language-ordbok** (varje nyckeltal → en svensk mening + tooltip). Bestäm
mätetal + lägg in enkel, GDPR-vänlig analytics. Ta ett **arkitekturbeslut för framtida native**:
håll affärslogik i delbara hooks/typer/api-klient så mobilen senare kan återanvända dem.
**Du siktar efter:** ett tydligt "vad och för vem", och en kodbas som inte målar in dig i ett hörn.
**Beror på:** inget. *Litet.*

### M1 — Nybörjarläge på webben (MVP-kärnan) 🌟
**Vad:** Plain-language-lagret + ett **omdömeskort** (omdöme + 3 enkla skäl + 1 risk + "visa
siffrorna"-expand) + en global **Nybörjarläge-toggle** som förenklar nav och döljer jargong.
**Du siktar efter:** en nybörjare förstår en akties omdöme **utan att googla en enda term**.
**Beror på:** M0. *Detta är hjärtat — lägg mest omsorg här.*

### M2 — Temabaserad upptäckt
**Vad:** Kollektioner/teman istället för screener ("Stabila svenska storbolag", "Delar ut varje
år", "Billiga & trygga", "Växande småbolag — högre risk"). Tryck → 3–5 förhandsgranskade
kandidater med en plain-language-rad. Spekulativt tydligt riskmärkt.
**Du siktar efter:** en nybörjare hittar en relevant kandidat **utan att bygga ett filter**.
**Beror på:** M1.

### M3 — AI-förklarare + utbildning-i-kontext
**Vad:** "Förklara som om jag är 12"-knapp (AI grundad i bolagets faktiska skäl — **förklarar,
råder aldrig**) + inline-mikrolektioner ("Vad är utdelning?"). Allt cachat → nära gratis.
**Du siktar efter:** användaren kan fråga *"varför?"* och få ett begripligt, ärligt svar.
**Beror på:** M1.

### M4 — Onboarding + bevakning-först + aktivering
**Vad:** Kort onboarding (en fråga per skärm) som levererar en **kurerad startlista direkt**
(värde före registrering). Nästa steg är *"lägg i bevakning, följ i 30 dagar"* — aldrig "köp".
Aktiverings-checklista.
**Du siktar efter:** time-to-first-"aha" **under 5 minuter**; D1/D7-retention mätbar.
**Beror på:** M1–M3. *Aktivering är produktens livlina (~4,5 % retention dag 30 är normen).*

### M5 — Förtroende + lugn design-polish
**Vad:** **Facit-transparens** (hur systemets signaler historiskt gått — inkl. missarna) +
genomgående Lysa-känsla (typografi, luft, lugna färger, mjuka animationer, trygghetston).
**Du siktar efter:** appen känns **lugn och trovärdig** — inte en trading-terminal.
**Beror på:** M1–M4. → **Här är webb-produkten "klar nog" att älska och visa upp.**

### M6 — PWA-brygga (billig väg mot mobil)
**Vad:** Gör webben **installerbar** på hemskärmen + push-notiser (Serwist finns redan halvvägs).
Fortfarande en kodbas.
**Du siktar efter:** en "app-känsla" på mobilen **innan** du tar det stora native-steget — och
ett test på om mobil-användningen tar fart.
**Beror på:** M5.

### M7 — Native mobilapp (Expo) 📱
**Vad:** Riktig iOS/Android-app (React Native/Expo) som **återanvänder** hooks/typer/api-klient
från webben (tack vare M0-beslutet). Återskapa kärnflödena: upptäck → förstå → bevaka.
**Du siktar efter:** nybörjarmålgruppens **mobil-först-beteende** på riktigt.
**Beror på:** M5/M6. *Stort steg — ta det först när webb-produkten bevisat sig.*

### M8 — Nordisk expansion
**Vad:** Lägg till Norge/Danmark/Finland (data + bolag) och i18n (svenska först, sedan no/da/fi/en).
**Du siktar efter:** ditt slutmål — **Norden**, inte bara Sverige.
**Beror på:** en produkt som funkar i Sverige (M5+). *Kräver bredare datatäckning.*

### M9 — Optionalitet: lansera **eller** sälja (valbart, sist)
**Vad (bara när/om du bestämmer dig):**
- **Om lansera:** byt till **licensierad datafeed** (yfinance får ej användas kommersiellt),
  GDPR + villkor + MAR/AI-friskrivning, **betalning/freemium** (Stripe), bolag/skatt, go-to-market
  (pedagogiskt innehåll på TikTok/YouTube/SEO).
- **Om sälja:** paketera traction (aktiverings-/retentionsdata), städa + dokumentera kodbasen,
  lyft fram den unika svenska pedagogiken som tillgång, identifiera köpare (mäklare/fintech).
**Du siktar efter:** att kunna **flippa till lansering eller försäljning** utan att ha låst dig tidigare.
**Beror på:** M5+ (helst M7/M8 för max värde).

### Löpande — beta, feedback, iteration
Testa på **riktiga nybörjare** tidigt (även från M1). Mät §-mätetalen, intervjua, iterera
pedagogiken. Innehåll ("förklara aktier enkelt på svenska") som tillväxtmotor om du går mot lansering.

---

## Beroendekarta (kort)

```
M0 ─► M1 ─► M2 ─► M4 ─► M5 ─► M6 ─► M7 ─► M8 ─► M9 (valbart)
        └─► M3 ─┘
        (Löpande beta/feedback från M1 och framåt)
```

## Vad "klar produkt" betyder för dig
- **Som lärprojekt:** klar redan vid **M5** — en lugn, begriplig webb-app du är stolt över.
- **Som lansering:** M5 → M6/M7 (mobil) → **M9 (lansera)** med licensierad data + betalning.
- **Som försäljning:** M5 → M7/M8 (mer värde/traction) → **M9 (sälja)** med ren kodbas + bevisad traction.

Du kan **pausa efter vilken milstolpe som helst** och fortfarande ha något helt och användbart.

---

## Ärliga påminnelser (gäller hela vägen)
- **Datalicens** är den enda hårda kommersiella blockeraren (M9) — bygg/test på yfinance, byt före betalning.
- **Aktivering > allt annat** (M4). En vacker app som ingen fattar första minuten dör.
- **Håll dig på utbildnings-sidan** av rådgivningsgränsen (AI förklarar, råder ej; bevaka, inte köp).
- **Edgen är pedagogiken**, inte mer data eller fler funktioner.
