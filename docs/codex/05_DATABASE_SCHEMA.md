# 🗄️ Kapitel 5: Database Schema & RLS Security

> **Domän:** Supabase Postgres databas, relationella modeller, RLS-säkerhetspolicyer, anslutningspooler och behörigheter.  
> **Status:** Aktiv produktion (81 migrationer).

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
2. **Direct Connection & CLI Migrations:**
   - Migrationer appliceras direkt via `supabase db push --linked` med Supabase CLI. Direct connection (Port 5432) används för tunga batch-skript och migrationskörningar.

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
| Migrationer | `supabase/migrations/` | 79 inkrementella DDL-skript |
| Initialt Schema | `supabase/migrations/001_initial_schema.sql` | Kärntabeller för portfölj och aktier |
| RLS Härdning | `supabase/migrations/018_rls_hardening.sql` | Strikt isolering per användar-ID |
| Table Grants | `supabase/migrations/023_grant_table_privileges.sql` | Behörighetstilldelning till roller |
| MasterRank DDL | `supabase/migrations/068_master_rank.sql` | Kolumner för Rond 8 poängsystem |
| Forensik & Alpha | `supabase/migrations/075_fundamentals_and_forensics.sql` | Forensiska mått och fundamentalia |
| RLS Säkerhet & Index | `supabase/migrations/077_rls_security_hardening.sql` | Härdning av RLS och saknade index |
| Segmentintegritet | `supabase/migrations/080_segment_integrity.sql` | CHECK constraint och segment-backfill |
| Likviditetskolumner | `supabase/migrations/081_liquidity_columns.sql` | Likviditetsgrader A–F och 20d medianomsättning |
| V3 beslutskärna | `supabase/migrations/083_decision_manifest_foundation.sql` | Security Master, PIT-observationer, immutabla beslut och atomisk publiceringspekare |
| Corporate actions & metric-kontrakt | `supabase/migrations/084_corporate_actions_metric_catalog.sql` | Corporate-action-lager (CPRX MERGED), enhetskontrakt i `metric_catalog`, listing-state-övergångar |

## 7. V3 Decision Manifest Foundation

Migration 083 skapar en separat, append-only beslutsväg utan att ändra `scan_results`, som fortfarande är legacy/kompatibilitet under migreringen. `decision_snapshots` startar i `STAGED`; worker persisterar en manifest per `listing_id` och anropar därefter `publish_decision_snapshot`. Funktionen avvisar tomma snapshots och handlingsbara beslut på inaktiva listningar innan den atomiskt ersätter den enda publiceringspekaren.

Samtliga V3-tabeller har RLS. Anonyma och inloggade klienter får endast `SELECT` på publicerade beslut och begränsad evidens; råpayloads, karantänposter och alla skrivningar är service-only. Kör alltid migrationen i staging, kontrollera verkligt migreringshuvud och kör RLS-tester innan den appliceras i produktion.

### 7.1 Corporate actions & tradability (migration 084)

`corporate_actions` är det auktoritativa lagret för listningstillstånd (M&A, avnotering, halt, konkurs). Rader har `announced_at`/`known_at`/`effective_at` + `status` (ANNOUNCED/EFFECTIVE/CANCELLED); anon läser endast EFFECTIVE. `apply_effective_corporate_actions()` (SECURITY DEFINER, service_role-only) överför EFFECTIVE-åtgärder till `listings.state`/`valid_to`.

**CPRX-regeln (regression-invariant):** Catalyst Pharmaceuticals är MERGED efter Angelini-förvärvet (stängt 2026-07-15, $31,50/aktie). Seeden ligger i 084; bootstrap skapar listningen direkt i MERGED-tillstånd och publications-bryggan exkluderar rader vars listing inte är ACTIVE som explicit karantän (`excluded_count` + reasons i quality_report). Att publicera ett handlingsbart manifest för en icke-ACTIVE listing avvisas alltid i DB.

### 7.2 Metric Catalog & enhetskontrakt (migration 084)

`metric_catalog` (083) är seedad med 14 kanoniska kontrakt där enhet/period/definition är entydig — `debt_to_equity_ratio` är ett **ratio** (1.0 = 100 %), inte procentenheter. Worker-sidan har `backend_worker/metric_contracts.py`: `normalize_debt_to_equity` omvandlar bara med explicitt `source_unit`, karantänar vid okänd enhet (UNIT_UNKNOWN), flaggar implausibla värden och negativt eget kapital, och gör aldrig tyst winsorize eller positiv default vid saknat värde. Transformen är ännu inte inkopplad i `master_rank.py` (kräver provider-verifiering mot live-data, se Known Unknowns i `docs/audit/ultimate-rebuild-v3-progress.md`).

### 7.3 Venue-policy i Security Master bootstrap

Legacy-data saknar venue-fält per ticker. `bootstrap_security_master.py` följer därför en dokumenterad policy: verifierade suffix (.ST/.DE/...) → specifik MIC + ACTIVE; suffixlösa tickers → US-default (XNAS/USD) med state **UNKNOWN** (= NO_SIGNAL enligt planen) tills venue-verifiering finns. EFFECTIVE corporate actions styr initial-state direkt. Körningen är idempotent (befintliga listings dupliceras aldrig).
