export interface Holding {
  id: string;
  portfolio_id: string;
  ticker: string;
  shares: number;
  cost_basis: number | null;
  added_at: string;
  name: string | null;
  price: number | null;
  change_pct: number | null;
  score_total: number | null;
  entry_signal: string | null;
  trend_signal: string | null;
}

export interface Portfolio {
  id: string;
  user_id: string;
  name: string;
  created_at: string;
  holdings: Holding[];
}

export interface WatchlistItem {
  id: string;
  ticker: string;
  added_at: string;
  name: string | null;
  price: number | null;
  change_pct: number | null;
  score_total: number | null;
  entry_signal: string | null;
  trend_signal: string | null;
}

export interface PriceAlert {
  id: string;
  ticker: string;
  condition: string;
  target_price: number;
  note: string | null;
  active: boolean;
  triggered_at: string | null;
  created_at: string;
}

export interface PeriodReturn {
  pct: number | null;
  positive: boolean | null;
}

export interface PortfolioHistory {
  periods: Record<string, PeriodReturn>;
}

export interface SectorAllocation {
  sector: string;
  value: number;
  pct: number;
}

export interface PortfolioRisk {
  tickers: string[];
  sector_allocation: SectorAllocation[];
  concentration_pct: number;
  total_value: number;
  count: number;
  score_avg: number | null;
}

export interface Transaction {
  id: string;
  ticker: string;
  type: "buy" | "sell" | "deposit" | "withdrawal";
  shares: number | null;
  price: number | null;
  amount: number | null;
  traded_at: string;
  note: string | null;
  created_at: string;
}

export interface TWResponse {
  twr: number | null;
  total_return_pct: number | null;
  periods: Record<string, number | null>;
}
