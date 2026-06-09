# Spec 06 — #19: Riskprofil + LLM-Black-Litterman portföljkonstruktion

> **Repo:** `marketscan`. Kan använda LLM-lagret från Spec 04 (#7) och AI-kommittén.
> **Mål:** Låt användaren sätta en riskprofil och få ett portföljförslag konstruerat med
> Black-Litterman (marknadsprior + AI-kommitténs "views") under riskprofilens begränsningar.
> **VIKTIGT (säkerhet):** Systemet ger ENBART FÖRSLAG på vikter. Det lägger ALDRIG order,
> överför aldrig pengar, och ger ingen personlig finansiell rådgivning (visa disclaimer).
> **Evidensgrund:** LLM-Enhanced Black-Litterman (arXiv:2504.14345); riskparitet (AQR) som
> robust fallback (kräver bara volatilitet, inte avkastningsprognos).
> **Läs först:** master §2, §6.3–6.6. Läs `apps/api/routers/portfolio.py`,
> `apps/api/schemas/portfolio.py`, migration `012_profile_extensions.sql`,
> `apps/api/routers/ai.py` (committee), `apps/api/core/llm_client.py` (Spec 04, om byggd).

---

## A. Riskprofil

### A1. Migration `0NN_risk_profile.sql`
```sql
CREATE TABLE IF NOT EXISTS user_risk_profiles (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  profile TEXT NOT NULL,            -- 'trygg'|'balanserad'|'tillvaxt'|'aggressiv'|'maxrisk'
  risk_score INTEGER,               -- 0-100 från frågeformuläret
  time_horizon_years INTEGER,
  max_position_pct FLOAT,           -- t.ex. 0.10 för trygg, 0.30 för maxrisk
  target_volatility FLOAT,          -- årlig målvolatilitet
  answers JSONB,                    -- råa svar för spårbarhet
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE user_risk_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own_profile_rw" ON user_risk_profiles
  USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
GRANT SELECT, INSERT, UPDATE ON user_risk_profiles TO authenticated;
```

### A2. Frågeformulär → profil
6 frågor (tidshorisont, förlusttolerans, inkomststabilitet, erfarenhet, ålder, mål).
Varje svar 1–5 poäng → summa → `risk_score` (0–100) → mappa till 5 profiler:

| Profil | risk_score | max_position_pct | target_volatility |
|---|---|---|---|
| Trygg | 0–25 | 0.08 | 0.08 |
| Balanserad | 26–45 | 0.12 | 0.12 |
| Tillväxt | 46–65 | 0.18 | 0.16 |
| Aggressiv | 66–85 | 0.25 | 0.22 |
| Maxrisk | 86–100 | 0.35 | 0.30 |

- API: `POST /api/profile/risk` (spara svar+profil), `GET /api/profile/risk`.
- Frontend: onboarding-steg / inställningssida med 6 frågor → visar profil + förklaring.

---

## B. Portföljkonstruktion

**Fil:** `apps/api/core/portfolio_construction.py` (ny). Ren NumPy/SciPy (open source).

### B1. Riskparitet (robust baslinje — bygg FÖRST)
```python
def equal_risk_contribution(cov: np.ndarray) -> np.ndarray:
    """Vikter där varje tillgång bidrar lika mycket till portföljrisken.
       SciPy-minimering av sum((rc_i - rc_mean)^2). Long-only, summa=1."""
```
Kräver bara kovariansmatris (skattas robust ur 1–2 års dagliga returns via befintlig
pris-httpx i `apps/api/core/prices.py`). Detta är fallback om BL-views saknas.

### B2. Black-Litterman (med AI-views)
```python
def black_litterman(
    market_caps: np.ndarray,      # för marknadsprior (equilibrium)
    cov: np.ndarray,
    views: list[dict],            # [{ticker, expected_excess_return, confidence}]
    risk_aversion: float,         # från riskprofil (lägre för trygg)
    tau: float = 0.05,
) -> np.ndarray:
    """Returnerar posterior-vikter. Standard BL-matematik (Idzorek):
       1. Implied equilibrium returns Π = δ Σ w_mkt
       2. Kombinera med views (P, Q, Ω) → posterior E[R]
       3. Mean-variance med riskprofilens constraints."""
```
**Views = AI-kommitténs output** (eller `qualitative_signals` från #7):
- committee-verdict/score (0–100) → `expected_excess_return` (t.ex. score 80 → +12% / 30d,
  linjär mappning, KLIPP rimligt).
- `confidence` = kommitténs konfidens (andel överens / 3).
Begränsningar från riskprofil: `weight_i <= max_position_pct`, portföljvol `<= target_vol`
(annars skala ner risktillgångar / lägg in kontant-buffert).

**Acceptanstest B:** ERC ger lika riskbidrag (verifiera numeriskt); BL med en stark positiv
view tippar vikten mot den aktien men respekterar `max_position_pct`; vol-constraint hålls.

---

## C. API + frontend

### C1. API
`apps/api/routers/portfolio.py` (utöka):
- `POST /api/portfolio/construct` body: `{tickers?: string[], use_profile: true}` →
  returnerar `{method, weights, expected_return, expected_volatility, sharpe, var_95,
  per_position: [...], disclaimer}`.
  - Om inga tickers: använd topp-`ml_rank`/`score_total` ur scan_results filtrerat på
    riskprofil (trygg → större/lägre vol; aggressiv → mer småbolag/MEWS).
  - Om profil saknas: defaulta till "balanserad" + uppmaning att göra testet.

### C2. Frontend
**Fil:** `apps/web/app/(app)/portfolj/byggare/` (ny "Portföljbyggare"-flik).
- Visar riskprofil (eller länk till testet).
- Knapp "Föreslå portfölj" → anropar `/construct` → visar allokering (donut + lista),
  förväntad avkastning/vol/Sharpe/VaR.
- **Disclaimer (obligatorisk):** "Detta är ett automatiskt förslag, inte finansiell
  rådgivning. Inga affärer läggs automatiskt." (§6.6).
- Återanvänd Recharts-mönster från portföljsidan.

---

## D. Kostnad
- Riskparitet + BL = ren matematik, **0 kr**.
- AI-views återanvänder REDAN cachade committee/qualitative-resultat (ingen ny LLM-kostnad
  om de finns; annars 1 cachad körning per bolag via LLM-lagret).

---

## Filer som rörs
| Fil | Åtgärd |
|---|---|
| `supabase/migrations/0NN_risk_profile.sql` | NY |
| `apps/api/core/portfolio_construction.py` | NY — ERC + Black-Litterman |
| `apps/api/routers/portfolio.py` | `/construct`-endpoint |
| `apps/api/routers/profile.py` | `/profile/risk` GET/POST |
| `apps/api/schemas/portfolio.py` | scheman för construct-svar |
| `apps/web/app/(app)/portfolj/byggare/` | NY flik |
| `apps/web/app/(app)/installningar/` el. onboarding | riskprofil-test |
| `apps/web/hooks/usePortfolio.ts` | hook för construct + profil |

## Definition of Done
- [ ] Riskprofil-test sparar profil (RLS: bara egen läsning/skrivning).
- [ ] ERC-baslinje fungerar utan views; BL använder AI-views + respekterar constraints.
- [ ] `/construct` ger vikter + risk/avkastningsmått + disclaimer.
- [ ] Portföljbyggare-fliken visar förslag; INGEN orderläggning.
- [ ] Disclaimer synlig; ingen personlig rådgivning utlovas.
- [ ] `docs/SYSTEM_AI.md` uppdaterad.
