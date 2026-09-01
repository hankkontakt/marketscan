# 🗄️ Kapitel 5: Database Schema & RLS Security

> **Domän:** Supabase Postgres databas, relationella modeller, RLS-säkerhetspolicyer, anslutningspooler och behörigheter.  
> **Status:** Aktiv produktion (76 migrationer).

---

## 1. Executive Summary & TL;DR

MarketScan använder Supabase Postgres i region `eu-north-1` (Stockholm). Databasen är strikt uppdelad mellan publika analysdata (`scan_results`, `insider_trades`), användarisolerad data med Row Level Security (`portfolios`, `holdings`, `price_alerts`) och systemcache (`ai_cache`, `pipeline_runs`).

---

## 2. Kärntabeller & Datamodell (ERD)

```
  ┌─────────────────────────────────────────────────────────────┐
  │                        scan_results                         │
  │  ticker (PK), company_name, master_rank, master_tier,       │
  │  score_quality, score_value, score_momentum, score_analyst, │
  │  score_insider, score_catalyst, score_dividend, score_growth│
  │  price, market_cap, pe, rsi, thin_data, bubble_risk         │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
  ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
  │insider_trades│        │short_position│        │earnings_surpr│
  │ticker, date, │        │ticker, owner,│        │ticker, eps,  │
  │insider_name, │        │percent, date │        │surprise_pct, │
  │shares, price │        └──────────────┘        │report_date   │
  └──────────────┘                                └──────────────┘

  ┌─────────────────────────────────────────────────────────────┐
  │                    Användardata (RLS-skyddad)               │
  │                                                             │
  │  ┌──────────────┐       ┌──────────────┐     ┌────────────┐ │
  │  │  portfolios  │ ◄───► │   holdings   │ ◄──►│transactions│ │
  │  │  id, user_id │       │id, portf_id, │     │id, type,   │ │
  │  │  name, cash  │       │ticker, shares│     │price, date │ │
  │  └──────────────┘       └──────────────┘     └────────────┘ │
  │                                                             │
  │  ┌──────────────┐       ┌──────────────┐     ┌────────────┐ │
  │  │  watchlist   │       │ price_alerts │     │  ai_cache  │ │
  │  │user_id,ticker│       │user_id,ticker│     │hash, prompt│ │
  │  └──────────────┘       └──────────────┘     └────────────┘ │
  └─────────────────────────────────────────────────────────────┘
```

---

## 3. Row Level Security (RLS) & Behörighetsmatris

| Tabell | RLS Aktivt? | `anon` Roll | `authenticated` Roll | `service_role` (Worker/Admin) |
|---|---|---|---|---|
| `scan_results` | Nej (Lästabell) | `SELECT` | `SELECT` | `ALL` (Upsert av pipeline) |
| `insider_trades` | Nej (Publik data) | `SELECT` | `SELECT` | `ALL` |
| `short_positions` | Nej (Publik data) | `SELECT` | `SELECT` | `ALL` |
| `portfolios` | **JA** | Ingen åtkomst | `ALL` (där `user_id = auth.uid()`) | `ALL` |
| `holdings` | **JA** | Ingen åtkomst | `ALL` (via portfolio ägarskap) | `ALL` |
| `transactions` | **JA** | Ingen åtkomst | `ALL` (via portfolio ägarskap) | `ALL` |
| `watchlist` | **JA** | Ingen åtkomst | `ALL` (där `user_id = auth.uid()`) | `ALL` |
| `price_alerts` | **JA** | Ingen åtkomst | `ALL` (där `user_id = auth.uid()`) | `ALL` |
| `ai_cache` | Nej (Prestandacache) | `SELECT` | `SELECT`, `INSERT` | `ALL` |
| `pipeline_runs` | Nej (Systemlogg) | Ingen åtkomst | `SELECT` (Admin) | `ALL` |

---

## 4. Anslutningsarkitektur: Pooler vs Direct

1. **Session Pooler (Port 6543):**
   - **MÅSTE användas i produktion** för `DATABASE_URL` på grund av Vercels serverless arkitektur. Varje serverless request kan skapa en ny anslutning, vilket gör att PgBouncer/Supabase Pooler krävs för att inte spräcka Postgres max-connections.
2. **Direct Connection (Port 5432):**
   - Används endast för manuella SQL-migrationer i Supabase Dashboard SQL Editor eller tunga batch-skript utanför Vercel.

---

## 5. Kritiska Gotchas & Fallgropar

- **Postgres `42501 permission denied`:**
  - Om en ny tabell skapas via migration utan `GRANT`-satser blockeras även inloggade användare trots att RLS är konfigurerat.
  - *Åtgärd:* Kör alltid `supabase/migrations/023_grant_table_privileges.sql` eller inkludera explicita `GRANT SELECT, INSERT, UPDATE, DELETE ON table_name TO authenticated;`.
- **Obligatorisk RLS-regel för alla tabeller:**
  - Varje ny tabellmigration **MÅSTE** innehålla `ENABLE ROW LEVEL SECURITY` och minst en explicit policy (t.ex. publik läsning eller användarisolering via `auth.uid() = user_id`). Skrivningar från anonyma/oautentiserade anrop är blockerade som standard.
- **Soft Deletes vs Cascades:**
  - När en portfölj raderas i `portfolios` kaskaderas borttagningen automatiskt till `holdings` och `transactions` via `ON DELETE CASCADE`.

---

## 6. Källkodskarta

| Resurs | Sökväg | Syfte |
|---|---|---|
| Migrationer | `supabase/migrations/` | 76 inkrementella DDL-skript |
| Initialt Schema | `supabase/migrations/001_initial_schema.sql` | Kärntabeller för portfölj och aktier |
| RLS Härdning | `supabase/migrations/018_rls_hardening.sql` | Strikt isolering per användar-ID |
| Table Grants | `supabase/migrations/023_grant_table_privileges.sql` | Behörighetstilldelning till roller |
| MasterRank DDL | `supabase/migrations/068_master_rank.sql` | Kolumner för Rond 8 poängsystem |
