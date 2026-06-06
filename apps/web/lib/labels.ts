export const FACTOR_LABELS: Record<string, string> = {
  score_value: "Värde",
  score_quality: "Kvalitet",
  score_momentum: "Momentum",
  score_growth: "Tillväxt",
  score_risk: "Risk",
  score_dividend: "Utdelning",
  score_sentiment: "Sentiment",
  score_size: "Storlek",
};

export const FACTORS = Object.entries(FACTOR_LABELS).map(([key, label]) => ({ key, label }));

export const PERIOD_LABELS = ["1M", "3M", "6M", "12M"] as const;

export const SCREENER_PRESETS = [
  { label: "Värde", params: { score_min: 55, preset_used: "Value" } },
  { label: "Tillväxt", params: { score_min: 50, preset_used: "Growth" } },
  { label: "Hög kvalitet", params: { piotroski_min: 6, score_min: 60 } },
  { label: "Momentum", params: { entry_signal: "STARK", trend_signal: "Upptrend" } },
  { label: "Översåld", params: { entry_signal: "VÄNTA" } },
] as const;

export const EMPTY_STATES = {
  portfolio: {
    title: "Inga innehav ännu",
    description: "Lägg till dina första aktier för att börja följa portföljen.",
    action: "Lägg till innehav",
    href: "/portfolj",
  },
  watchlist: {
    title: "Du bevakar inga aktier ännu",
    description: "Lägg till aktier du vill hålla koll på.",
    action: "Sök aktier",
    href: "/screener",
  },
  screener: {
    title: "Inga aktier matchar dina filter",
    description: "Prova att bredda kriterierna eller välj en förinställning ovan.",
    action: "Återställ filter",
  },
  alerts: {
    title: "Inga prisbevakningar aktiva",
    description: "Skapa en prisbevakning för en aktie för att få notis vid kursrörelser.",
    action: "Lägg till bevakning",
  },
};
