import { ScanRow } from "@/types/scan";
import { FACTOR_LABELS } from "@/lib/labels";

export interface VerdictReason {
  icon: "check" | "warning" | "info";
  title: string;
  detail: string;
  scoreKey?: string;
}

export interface StockVerdict {
  qualityLabel: "exceptionell" | "stark" | "bra" | "okej" | "svag";
  qualitySentence: string;
  reasons: VerdictReason[];
  risk: VerdictReason;
  overallScore: number;
}

const QUALITY_SENTENCES: Record<StockVerdict["qualityLabel"], string> = {
  exceptionell:
    "En ovanligt stark kandidat — höga betyg på i stort sett alla fronter.",
  stark: "En stark kandidat med flera styrkor.",
  bra: "En helt okej kandidat — men det finns saker att hålla koll på.",
  okej: "En blandad bild — vissa saker ser bra ut, andra mindre bra.",
  svag: "Siffrorna är svaga just nu — det kan finnas bättre kandidater.",
};

function factorPositiveDetail(key: string, value: number): string {
  const map: Record<string, string> = {
    score_value: `Aktien ser billig ut jämfört med liknande bolag (${Math.round(value)}/100).`,
    score_quality: `Bolaget har hög lönsamhet och stark balansräkning (${Math.round(value)}/100).`,
    score_momentum: `Kursen har gått starkt på sistone — medvind just nu (${Math.round(value)}/100).`,
    score_growth: `Både intäkter och vinster växer (${Math.round(value)}/100).`,
    score_risk: `Bolaget har relativt stabil kurs och låg skuldsättning (${Math.round(value)}/100).`,
    score_dividend: `Bolaget delar ut pengar till aktieägarna (${Math.round(value)}/100).`,
    score_sentiment: `Marknaden är positiv till aktien just nu (${Math.round(value)}/100).`,
    score_size: `Bolaget är tillräckligt stort för att vara stabilt men kan fortfarande växa (${Math.round(value)}/100).`,
  };
  return map[key] || `Högt betyg (${Math.round(value)}/100).`;
}

function factorNeutralDetail(key: string, value: number): string {
  const map: Record<string, string> = {
    score_value: `Aktien varken billig eller dyr (${Math.round(value)}/100).`,
    score_quality: `Lönsamheten är genomsnittlig (${Math.round(value)}/100).`,
    score_momentum: `Kursutvecklingen är varken stark eller svag (${Math.round(value)}/100).`,
    score_growth: `Tillväxten är måttlig (${Math.round(value)}/100).`,
    score_risk: `Risknivån är genomsnittlig (${Math.round(value)}/100).`,
    score_dividend: `Utdelningen är genomsnittlig (${Math.round(value)}/100).`,
    score_sentiment: `Marknaden har en neutral syn på aktien (${Math.round(value)}/100).`,
    score_size: `Bolagsstorleken är mitt i skalan (${Math.round(value)}/100).`,
  };
  return map[key] || `Neutralt betyg (${Math.round(value)}/100).`;
}

function factorNegativeDetail(key: string, value: number): string {
  const map: Record<string, string> = {
    score_value: `Aktien kan vara dyr jämfört med liknande bolag (${Math.round(value)}/100).`,
    score_quality: `Lönsamheten eller balansräkningen är svag (${Math.round(value)}/100).`,
    score_momentum: `Kursen har gått svagt på sistone — motvind just nu (${Math.round(value)}/100).`,
    score_growth: `Varken intäkter eller vinster växer (${Math.round(value)}/100).`,
    score_risk: `Kursen kan vara instabil eller bolaget har hög skuldsättning (${Math.round(value)}/100).`,
    score_dividend: `Bolaget delar inte ut pengar till aktieägarna (${Math.round(value)}/100).`,
    score_sentiment: `Marknaden är negativ till aktien just nu (${Math.round(value)}/100).`,
    score_size: `Bolaget är litet och kan vara mer instabilt (${Math.round(value)}/100).`,
  };
  return map[key] || `Lågt betyg (${Math.round(value)}/100).`;
}

function factorDetail(key: string, value: number): string {
  if (value >= 60) return factorPositiveDetail(key, value);
  if (value >= 40) return factorNeutralDetail(key, value);
  return factorNegativeDetail(key, value);
}

function factorIcon(value: number): "check" | "warning" | "info" {
  if (value >= 60) return "check";
  if (value >= 40) return "info";
  return "warning";
}

export function categorizeScore(score: number): StockVerdict["qualityLabel"] {
  if (score >= 85) return "exceptionell";
  if (score >= 70) return "stark";
  if (score >= 55) return "bra";
  if (score >= 40) return "okej";
  return "svag";
}

const SCORE_KEYS: (keyof Pick<
  ScanRow,
  | "score_value"
  | "score_quality"
  | "score_momentum"
  | "score_growth"
  | "score_risk"
  | "score_dividend"
  | "score_sentiment"
  | "score_size"
>)[] = [
  "score_value",
  "score_quality",
  "score_momentum",
  "score_growth",
  "score_risk",
  "score_dividend",
  "score_sentiment",
  "score_size",
];

export function buildVerdict(stock: ScanRow): StockVerdict {
  const total = stock.score_total ?? 0;
  const label = categorizeScore(total);

  // Collect non-null factors as {key, value} pairs
  const factors = SCORE_KEYS.map((key) => ({
    key,
    value: stock[key] ?? 0,
  }));

  // Sort descending by value
  const sorted = [...factors].sort((a, b) => b.value - a.value);

  // Top 3 become reasons
  const top3 = sorted.slice(0, 3);
  const reasons: VerdictReason[] = top3.map((f) => ({
    icon: factorIcon(f.value),
    title: FACTOR_LABELS[f.key] ?? f.key,
    detail: factorDetail(f.key, f.value),
    scoreKey: f.key,
  }));

  // Determine risk: worst factor if < 60, else check fundamentals
  const worst = sorted[sorted.length - 1];
  const lowScoreRisk: VerdictReason | null =
    worst.value < 60
      ? {
          icon: "warning",
          title: FACTOR_LABELS[worst.key] ?? worst.key,
          detail: factorDetail(worst.key, worst.value),
          scoreKey: worst.key,
        }
      : null;

  const fundamentalRisks: VerdictReason[] = [];

  if (stock.debt_to_equity != null && stock.debt_to_equity > 2) {
    fundamentalRisks.push({
      icon: "warning",
      title: "Hög skuldsättning",
      detail: `Bolaget har höga skulder i förhållande till eget kapital (${stock.debt_to_equity.toFixed(1)}x).`,
    });
  }

  if (stock.low_liquidity) {
    fundamentalRisks.push({
      icon: "warning",
      title: "Låg likviditet",
      detail: "Aktien omsätts i liten volym — kan vara svår att köpa eller sälja utan att påverka kursen.",
    });
  }

  if (stock.current_ratio != null && stock.current_ratio < 1) {
    fundamentalRisks.push({
      icon: "warning",
      title: "Svag likviditet",
      detail: `Bolagets kortfristiga tillgångar täcker inte dess kortfristiga skulder (${stock.current_ratio.toFixed(2)}x).`,
    });
  }

  if (stock.beta != null && stock.beta > 1.5) {
    fundamentalRisks.push({
      icon: "warning",
      title: "Hög risk (beta)",
      detail: `Aktien är mer volatil än marknaden (beta ${stock.beta.toFixed(2)}).`,
    });
  }

  // Prefer fundamental risks over the low-score factor when both exist
  const risk =
    fundamentalRisks.length > 0
      ? fundamentalRisks[0]
      : lowScoreRisk ?? {
          icon: "info" as const,
          title: "Inga uppenbara risker",
          detail: "Inga varningssignaler har flaggats för detta bolag.",
        };

  return {
    qualityLabel: label,
    qualitySentence: QUALITY_SENTENCES[label],
    reasons,
    risk,
    overallScore: total,
  };
}
