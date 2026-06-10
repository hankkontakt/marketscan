import type { ScanParams } from "@/lib/api";

export interface ThemeDefinition {
  id: string;
  label: string;
  emoji: string;
  description: string;
  riskLabel: string;
  riskExplanation: string;
  params: ScanParams;
  limit: number;
  sortBy: string;
}

export const THEMES: ThemeDefinition[] = [
  {
    id: "stable-large",
    label: "Stabila svenska storbolag",
    emoji: "\u{1F3F0}",
    description:
      "De tryggaste bland Large Cap-bolagen med stark fundamentalkvalitet och stabil avkastning över tid.",
    riskLabel: "Låg risk",
    riskExplanation:
      'Låg risk innebär att aktierna generellt har lägre kursvolatilitet, stabilare intjäning och högre sannolikhet att behålla värdet även i oroliga marknader. Dessa bolag är ofta marknadsledande inom sina sektorer och har en bred ägarbas, vilket minskar risken för stora kursfall. För en långsiktig sparare är dessa aktier ofta kärnan i en stabil portfölj.',
    params: { segments: ["large_cap"], score_min: 55, piotroski_min: 5 },
    limit: 5,
    sortBy: "score_total",
  },
  {
    id: "dividend-reliable",
    label: "Företag som delar ut pengar varje år",
    emoji: "\u{1F48E}",
    description:
      "Bolag med återkommande utdelningar över 2 % direktavkastning och solid finansiell hälsa.",
    riskLabel: "Låg risk",
    riskExplanation:
      'Låg risk här innebär att bolagen har visat förmåga att generera överskott år efter år, vilket möjliggör stabila utdelningar. En hög direktavkastning är dock ingen garanti — ibland kan en aktie ha hög yield för att kursen fallit av strukturella skäl. Därför viktar vi även in Piotroski F-score och övergripande kvalitetsbetyg.',
    params: { dividend_yield_min: 0.02, score_min: 50, piotroski_min: 5 },
    limit: 5,
    sortBy: "score_dividend",
  },
  {
    id: "value-quality",
    label: "Billiga & trygga — värdeinvestering",
    emoji: "\u{1F3F7}️",
    description:
      "Lågt P/E-tal kombinerat med stark fundamentalkvalitet — Benjamin Grahams anda i svensk tappning.",
    riskLabel: "Medel risk",
    riskExplanation:
      'Medel risk innebär att aktierna kan vara mer cykliska eller ha en smalare verksamhet än storbolagsindex. Värdebolag kan periodvis vara utmanande om marknaden favoriserar tillväxtaktier, men över tid har värdestrategin visat stark avkastning. Den här kategorin passar dig som vill ha exponering mot undervärderade bolag med hög kvalitet och kan acceptera kortare perioder av underprestation.',
    params: { pe_max: 15, piotroski_min: 6, score_min: 55 },
    limit: 5,
    sortBy: "score_value",
  },
  {
    id: "growth-small",
    label: "Växande småbolag — för den som kan ta högre risk",
    emoji: "\u{1F680}",
    description:
      "Svenska små- och mikrobolag med hög tillväxtpotential och goda fundamentala betyg.",
    riskLabel: "Högre risk",
    riskExplanation:
      'Högre risk betyder att dessa aktier är mer volatila och kan svänga kraftigt både upp och ner. Småbolag har ofta lägre likviditet, färre analytiker som följer dem och ibland en smalare produktportfölj, vilket ökar risken. Samtidigt har småbolag historiskt erbjudit högre avkastning över lång sikt — men du måste vara beredd på resan däremellan.',
    params: { segments: ["small_cap", "micro_cap"], score_min: 50 },
    limit: 5,
    sortBy: "score_growth",
  },
  {
    id: "starter-kit",
    label: "Nybörjarens startpaket — 5 att börja titta på",
    emoji: "\u{1F393}",
    description:
      "En bred och välbalanserad inkörsta till aktiemarknaden med högbetygsatta stor- och medelstora bolag.",
    riskLabel: "Låg–Medel risk",
    riskExplanation:
      'Låg–Medel risk innebär att dessa bolag är etablerade och stabila men fortfarande kan påverkas av konjunktur och marknadssvängningar. De har valts för att ge en bra riskspridning över olika sektorer. Det här är en trygg startpunkt för dig som är ny på aktiemarknaden — börja med att lära dig om bolagen och följ dem över tid.',
    params: { segments: ["large_cap", "mid_cap"], score_min: 60 },
    limit: 5,
    sortBy: "score_total",
  },
  {
    id: "insider-buying",
    label: "Där ledningen köper egna aktier",
    emoji: "\u{1F50D}",
    description:
      "Bolag där insiders (VD, styrelse) nyligen köpt aktier — en signal om framtidstro inifrån.",
    riskLabel: "Varierande risk",
    riskExplanation:
      'Varierande risk innebär att insidersignaler kan dyka upp i alla typer av bolag — både stabila storbolag och spekulativa småbolag. Insiderköp är en positiv signal men ska vägas samman med bolagets fundamenta. Den här kategorin kräver att du gör din egen analys och inte enbart följer insidermönster.',
    params: { score_min: 45 },
    limit: 5,
    sortBy: "score_total",
  },
];
