export interface ScanRow {
  ticker: string;
  name: string;
  segment: "large_cap" | "mid_cap" | "small_cap" | "micro_cap";
  sector: string | null;
  country: string;

  score_total: number | null;
  score_value: number | null;
  score_quality: number | null;
  score_momentum: number | null;
  score_growth: number | null;
  score_risk: number | null;
  score_size: number | null;
  score_dividend: number | null;
  score_sentiment: number | null;

  entry_signal: "STARK" | "OK" | "VÄNTA" | "EJ_AKTUELL" | null;
  confidence_label: "Hög" | "Medel" | "Låg" | null;
  trend_signal: "Upptrend" | "Sidled" | "Nedtrend" | null;
  predicted_return: number | null;
  ml_rank: number | null;
  piotroski_f: number | null;

  price: number | null;
  change_pct: number | null;
  market_cap: number | null;
  pe_trailing: number | null;
  pe_forward: number | null;
  roe: number | null;
  roa: number | null;
  revenue_growth: number | null;
  earnings_growth: number | null;
  debt_to_equity: number | null;
  current_ratio: number | null;
  gross_margin: number | null;
  operating_margin: number | null;
  dividend_yield: number | null;
  beta: number | null;
  vol_20d: number | null;

  low_liquidity: boolean;
  has_holding: boolean;
  scan_date: string | null;
}
