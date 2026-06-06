"use client";

import { InfoTooltip } from "@/components/ui/InfoTooltip";
import {
  TrendingUp,
  SlidersHorizontal,
  BrainCircuit,
  BookOpen,
  BarChart3,
  ShieldCheck,
  Gauge,
  ArrowUpRight,
  Clock,
  Search,
} from "lucide-react";

type SectionProps = {
  id?: string;
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
};

function Section({ id, title, icon, children }: SectionProps) {
  return (
    <section
      id={id}
      className="rounded-2xl p-6 sm:p-8 bg-[var(--color-bg-surface)]"
      style={{ border: "1px solid var(--color-border-strong)" }}
    >
      <h2 className="text-lg font-semibold flex items-center gap-2.5 mb-4 text-[var(--color-text-primary)]">
        {icon && <span className="text-[var(--color-accent)] shrink-0">{icon}</span>}
        {title}
      </h2>
      {children}
    </section>
  );
}

type FactorCardProps = {
  name: string;
  label: string;
  description: string;
};

function FactorCard({ name, label, description }: FactorCardProps) {
  return (
    <div
      className="rounded-xl p-4"
      style={{ border: "1px solid var(--color-border)", background: "var(--color-bg-elevated)" }}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-sm font-semibold text-[var(--color-text-primary)]">{label}</span>
        <span className="text-xs font-mono text-[var(--color-text-muted)]">({name})</span>
      </div>
      <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">{description}</p>
    </div>
  );
}

export function GuideView() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-8 sm:py-12 space-y-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold text-[var(--color-text-primary)] mb-2">
          Guide
        </h1>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Lär dig använda MarketScan — från poängsystem till analyskommittén.
        </p>
      </div>

      {/* 1. Intro */}
      <Section
        id="intro"
        title="Vad är MarketScan?"
        icon={<TrendingUp size={20} />}
      >
        <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed mb-3">
          MarketScan är ett automatiserat aktieanalysverktyg som hjälper dig hitta och jämföra
          aktier på den svenska och internationella marknaden. Varje aktie betygsätts med ett
          sammanfattande <strong>poäng (0–100)</strong> baserat på åtta olika faktorer — från
          värdering och kvalitet till momentum och risk.
        </p>
        <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
          Systemet scannar regelbundet tusentals aktier och ger dig en snabb överblick över vilka
          bolag som ser intressanta ut just nu. Du kan använda MarketScan för att upptäcka nya
          investeringsidéer, följa dina befintliga innehav och förstå marknaden bättre.
        </p>
      </Section>

      {/* 2. Poängsystemet */}
      <Section
        id="score-system"
        title="Poängsystemet"
        icon={<Gauge size={20} />}
      >
        <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed mb-4">
          Varje aktie får ett totalbetyg mellan <strong>0 och 100</strong> där 100 är bäst.
          Betyget är en sammanvägning av åtta underfaktorer, där varje faktor kan bidra med upp
          till 100 poäng. Totalbetyget är ett viktat medelvärde som visar aktiens övergripande
          attraktivitet.
        </p>
        <div
          className="rounded-xl p-4 mb-4"
          style={{ background: "var(--color-bg-elevated)", border: "1px solid var(--color-border)" }}
        >
          <h4 className="text-sm font-semibold mb-2 text-[var(--color-text-primary)]">Vad betygar poängen?</h4>
          <ul className="space-y-1.5 text-sm text-[var(--color-text-secondary)]">
            <li className="flex items-start gap-2">
              <span className="text-[var(--color-score-high)] font-bold shrink-0 mt-0.5">70–100</span>
              <span>Stark — aktien ser attraktiv ut på flera fronter</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-[var(--color-score-mid)] font-bold shrink-0 mt-0.5">50–69</span>
              <span>Godkänd — hyfsat betyg med vissa styrkor och svagheter</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-[var(--color-score-low)] font-bold shrink-0 mt-0.5">30–49</span>
              <span>Svag — flera faktorer pekar nedåt</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-[var(--color-text-muted)] font-bold shrink-0 mt-0.5">0–29</span>
              <span>Låg — betydande brister i analysen</span>
            </li>
          </ul>
        </div>
        <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
          Poängen är framför allt användbar för att jämföra aktier inom samma sektor eller segment.
          En aktie med 75 poäng är inte nödvändigtvis en bättre investering än en med 60 — det
          beror på din personliga strategi och tidshorisont.
        </p>
      </Section>

      {/* 3. Faktorerna */}
      <Section
        id="factors"
        title="De åtta faktorerna"
        icon={<BarChart3 size={20} />}
      >
        <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed mb-4">
          Varje aktie betygsätts inom åtta områden. Här är en kort förklaring av varje faktor:
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          <FactorCard
            name="score_value"
            label="Värdering"
            description="Är aktien billig eller dyr? Tittar på P/E, P/B och andra prismultiplar jämfört med branschen."
          />
          <FactorCard
            name="score_quality"
            label="Kvalitet"
            description="Hur bra är verksamheten? Hög avkastning på eget kapital (ROE), stabila marginaler och låg skuldsättning ger höga poäng."
          />
          <FactorCard
            name="score_momentum"
            label="Momentum"
            description="Går aktien bra just nu? Mäter kursutvecklingen över 1, 3 och 6 månader."
          />
          <FactorCard
            name="score_growth"
            label="Tillväxt"
            description="Växer bolaget? Tittar på historisk intäkts- och vinsttillväxt samt analytikers förväntningar."
          />
          <FactorCard
            name="score_risk"
            label="Risk"
            description="Hur stabil är aktien? Hög volatilitet, hög skuldsättning och svaga finanser ger lägre poäng."
          />
          <FactorCard
            name="score_dividend"
            label="Utdelning"
            description="Vad ger aktien i direktavkastning? Både utdelningsnivå och hållbarhet vägs in."
          />
          <FactorCard
            name="score_sentiment"
            label="Sentiment"
            description="Vad tycker marknaden? Baseras på nyhetssentiment, analytikerkommentarer och marknadsreaktioner."
          />
          <FactorCard
            name="score_size"
            label="Storlek"
            description="Bolagets marknadsvärde. Större bolag får högre poäng då de ofta är mer stabila och likvida."
          />
        </div>
      </Section>

      {/* 4. Entry-signaler */}
      <Section
        id="entry-signals"
        title="Entry-signaler"
        icon={<ArrowUpRight size={20} />}
      >
        <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed mb-4">
          Entry-signalen är vår samlade rekommendation för varje aktie och bygger på en
          kombination av poäng, teknisk analys och marknadsläge.
        </p>
        <div
          className="rounded-xl p-4 mb-4"
          style={{ background: "var(--color-bg-elevated)", border: "1px solid var(--color-border)" }}
        >
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[var(--color-text-muted)] text-xs uppercase tracking-wider">
                <th className="text-left pb-2 font-medium">Signal</th>
                <th className="text-left pb-2 font-medium">Betyder</th>
              </tr>
            </thead>
            <tbody className="text-[var(--color-text-secondary)]">
              <tr>
                <td className="py-2 pr-4 font-semibold text-[var(--color-score-high)]">STARK</td>
                <td className="py-2">Starkt köpläge. Hög totalpoäng, positivt momentum och bra värdering.</td>
              </tr>
              <tr>
                <td className="py-2 pr-4 font-semibold text-[var(--color-score-mid)]">OK</td>
                <td className="py-2">Bra läge. Solid aktie som kan passa de flesta investerare.</td>
              </tr>
              <tr>
                <td className="py-2 pr-4 font-semibold text-[var(--color-text-warning)]" style={{ color: "var(--color-score-low)" }}>VÄNTA</td>
                <td className="py-2">Avvakta. Betyget är svagt eller så finns negativa signaler som talar för att vänta.</td>
              </tr>
              <tr>
                <td className="py-2 pr-4 font-semibold text-[var(--color-text-muted)]">EJ AKTUELL</td>
                <td className="py-2">Ej aktuell just nu. Lågt betyg, negativ trend eller otillräcklig data.</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
          Signalerna är inte köpråd — de är en indikation på vad data säger just nu. Använd dem
          som <strong>utgångspunkt</strong> för din egen analys.
        </p>
      </Section>

      {/* 5. Piotroski F-Score */}
      <Section
        id="piotroski"
        title="Piotroski F-Score"
        icon={<ShieldCheck size={20} />}
      >
        <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed mb-3">
          Piotroski F-Score är ett enkelt men kraftfullt verktyg för att bedöma ett bolags
          <strong>fundamentala styrka</strong>. Det bygger på nio ja/nej-frågor om bolagets
          lönsamhet, finansiella ställning och operativa effektivitet.
        </p>
        <div
          className="rounded-xl p-4 mb-3"
          style={{ background: "var(--color-bg-elevated)", border: "1px solid var(--color-border)" }}
        >
          <h4 className="text-sm font-semibold mb-2 text-[var(--color-text-primary)]">De 9 kriterierna</h4>
          <ul className="space-y-1 text-sm text-[var(--color-text-secondary)]">
            <li className="flex items-start gap-2">
              <span className="text-[var(--color-accent)] shrink-0">1–4.</span>
              <span><strong>Lönsamhet:</strong> Positivt nettoresultat, positivt kassaflöde, ökande ROA, positivt periodiserat resultat</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-[var(--color-accent)] shrink-0">5–6.</span>
              <span><strong>Finansiell ställning:</strong> Minskande skuldsättning, ökande likviditet</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-[var(--color-accent)] shrink-0">7–8.</span>
              <span><strong>Operativ effektivitet:</strong> Ökande bruttomarginal, ökande tillgångsomsättning</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-[var(--color-accent)] shrink-0">9.</span>
              <span>Ingen utspädning av aktier (antalet aktier har inte ökat)</span>
            </li>
          </ul>
        </div>
        <div
          className="rounded-xl p-4"
          style={{ background: "var(--color-bg-elevated)", border: "1px solid var(--color-border)" }}
        >
          <h4 className="text-sm font-semibold mb-2 text-[var(--color-text-primary)]">Tolkning</h4>
          <ul className="space-y-1.5 text-sm text-[var(--color-text-secondary)]">
            <li className="flex items-start gap-2">
              <span className="font-bold shrink-0 mt-0.5">8–9</span>
              <span>Mycket stark fundamentals — hög sannolikhet för fortsatt god utveckling</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="font-bold shrink-0 mt-0.5">5–7</span>
              <span>Godkänd — blandad bild, värd en närmare titt</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="font-bold shrink-0 mt-0.5">0–4</span>
              <span>Varning — bolaget har svaga fundamenta och högre risk</span>
            </li>
          </ul>
        </div>
      </Section>

      {/* 6. Hur man använder scannern */}
      <Section
        id="how-to-use"
        title="Hur man använder scannern"
        icon={<SlidersHorizontal size={20} />}
      >
        <ol className="space-y-3 text-sm text-[var(--color-text-secondary)]">
          <li className="flex gap-3">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent)] text-xs font-bold shrink-0 mt-0.5">
              1
            </span>
            <div>
              <strong className="text-[var(--color-text-primary)]">Välj segment</strong>
              <p className="leading-relaxed mt-0.5">
                Börja med att välja vilka segment du vill titta på — stora bolag, medelstora,
                småbolag eller mikrobolag. Du kan välja flera samtidigt.
              </p>
            </div>
          </li>
          <li className="flex gap-3">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent)] text-xs font-bold shrink-0 mt-0.5">
              2
            </span>
            <div>
              <strong className="text-[var(--color-text-primary)]">Filtrera</strong>
              <p className="leading-relaxed mt-0.5">
                Använd filtren för att smalna av sökningen. Sätt en lägsta totalpoäng, välj sektor,
                entry-signal eller Piotroski-score. Du kan också söka på specifika aktier.
              </p>
            </div>
          </li>
          <li className="flex gap-3">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent)] text-xs font-bold shrink-0 mt-0.5">
              3
            </span>
            <div>
              <strong className="text-[var(--color-text-primary)]">Sortera och analysera</strong>
              <p className="leading-relaxed mt-0.5">
                Tabellen är sorterad efter totalpoäng som standard. Klicka på en aktie för att
                se detaljerad analys, diagram och AI-kommentarer.
              </p>
            </div>
          </li>
          <li className="flex gap-3">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent)] text-xs font-bold shrink-0 mt-0.5">
              4
            </span>
            <div>
              <strong className="text-[var(--color-text-primary)]">Spara och följ</strong>
              <p className="leading-relaxed mt-0.5">
                Lägg aktier i din bevakningslista för att enkelt hålla koll på dem, eller lägg
                till dem i din portfölj för att följa utvecklingen över tid.
              </p>
            </div>
          </li>
          <li className="flex gap-3">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent)] text-xs font-bold shrink-0 mt-0.5">
              5
            </span>
            <div>
              <strong className="text-[var(--color-text-primary)]">Exportera</strong>
              <p className="leading-relaxed mt-0.5">
                Du kan exportera aktuella sökresultat som CSV för vidare bearbetning i kalkylark.
              </p>
            </div>
          </li>
        </ol>
      </Section>

      {/* 7. Analyskommittén */}
      <Section
        id="ai-analysis"
        title="Analyskommittén"
        icon={<BrainCircuit size={20} />}
      >
        <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed mb-3">
          Analyskommittén är vår AI-drivna funktion som ger dig en <strong>sammanfattande analys</strong>{" "}
          av varje aktie. För varje aktie i scannern kan du be AI:n om en snabbanalys som
          sammanfattar styrkor, svagheter och en övergripande bedömning.
        </p>
        <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed mb-3">
          Analysen bygger på:
        </p>
        <ul className="space-y-1.5 text-sm text-[var(--color-text-secondary)] mb-3">
          <li className="flex items-start gap-2">
            <span className="text-[var(--color-accent)] shrink-0 mt-0.5">•</span>
            <span>Aktuella poäng för varje faktor</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-[var(--color-accent)] shrink-0 mt-0.5">•</span>
            <span>Senaste nyheter och marknadssentiment</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-[var(--color-accent)] shrink-0 mt-0.5">•</span>
            <span>Historiska trender i poängutvecklingen</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-[var(--color-accent)] shrink-0 mt-0.5">•</span>
            <span>Tekniska indikatorer och prismönster</span>
          </li>
        </ul>
        <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
          AI-analysen är inte ett investeringsråd utan ett komplement till din egen
          due diligence. Använd den som en <strong>tankestartare</strong>, inte som en färdig
          investeringsplan.
        </p>
      </Section>

      {/* 8. Ordlista */}
      <Section
        id="glossary"
        title="Ordlista"
        icon={<BookOpen size={20} />}
      >
        <div className="space-y-3 text-sm">
          {[
            {
              term: "P/E (Price/Earnings)",
              def: "Pris i förhållande till vinst per aktie. Ett högt P/E kan betyda att aktien är dyr, eller att marknaden förväntar sig hög tillväxt.",
            },
            {
              term: "ROE (Return on Equity)",
              def: "Avkastning på eget kapital. Visar hur effektivt bolaget använder sina ägares pengar för att generera vinst.",
            },
            {
              term: "Beta",
              def: "Ett mått på aktiens risk i förhållande till marknaden. Beta > 1 betyder att aktien svänger mer än marknaden. Beta < 1 betyder mindre svängningar.",
            },
            {
              term: "Direktavkastning",
              def: "Utdelning i procent av aktiekursen. Om en aktie kostar 100 kr och ger 4 kr i utdelning är direktavkastningen 4 %.",
            },
            {
              term: "Likviditet",
              def: "Hur lätt det är att köpa eller sälja aktien utan att påverka kursen. Låg likviditet = större spread och svårare att handla.",
            },
            {
              term: "Marknadsvärde",
              def: "Aktiens totala värde = antal aktier x kurs. Stora bolag har ofta lägre risk men lägre tillväxtpotential.",
            },
            {
              term: "Volatilitet",
              def: "Ett mått på hur mycket aktiekursen svänger över tid. Hög volatilitet betyder större svängningar och högre risk.",
            },
            {
              term: "Sektor",
              def: "En branschgruppering av bolag som verkar inom samma område, t.ex. teknik, hälsovård eller finans.",
            },
            {
              term: "Upptrend / Sidled / Nedtrend",
              def: "Tekniska beskrivningar av aktiens kursriktning över tid. En upptrend betyder högre toppar och högre bottnar.",
            },
            {
              term: "Score",
              def: "Betyg på en skala 0–100 som sammanfattar en aspekt av aktiens analys. Exempel: score_value = betyg på värderingen.",
            },
          ].map(({ term, def }) => (
            <div key={term}>
              <dt className="font-medium text-[var(--color-text-primary)] mb-0.5">{term}</dt>
              <dd className="text-[var(--color-text-secondary)] leading-relaxed">{def}</dd>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}
