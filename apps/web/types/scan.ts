export interface ScanRow {
  ticker: string;
  name: string;
  segment: "large_cap" | "mid_cap" | "small_cap" | "micro_cap";
  sector: string | null;
  country: string;
  market: string | null;
  alpha_rank: number | null;
  quality_z: number | null;
  momentum_z: number | null;
  value_z: number | null;
  stratum: string | null;

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

  // MasterRank (ROND 8) — berikas från /market-intel/master/rank i ScreenerView
  master_rank: number | null;
  master_tier: string | null;
  trend_tech: "Upptrend" | "Sidled" | "Nedtrend" | null;
  analyst_flags: string[];
  target_dispersion: number | null;
  currency: string | null;

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

  low_liquidity: boolean | null;
  has_holding: boolean | null;
  scan_date: string | null;

  // MEWS (#3)
  mews_score: number | null;
  mews_flag: boolean | null;
  mews_fcf_yield: number | null;
  mews_small_size: number | null;
  mews_low_ps: number | null;
  mews_operating_leverage: number | null;
  mews_revenue_accel: number | null;
  mews_clean_accruals: number | null;

  // Nyhetsbäring (API levererar efter 053 — framåtriktad, kan saknas i äldre svar)
  news_bias?: number | null;
  news_bias_n?: number | null;
}
