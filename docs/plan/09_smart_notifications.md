# Spec 09 — #1 Smart Notifications + #20 Insider Flash

> **Repo:** marketscan (worker + migration + API + frontend). **Insats:** M.
> **Skriven för:** DeepSeek v4-flash. Läs `docs/plan/00_MASTER_PLAN.md §6` först.
> **Kanal: in-app + e-post. INGEN Web Push** (användarbeslut). Bygger på befintlig notis-motor.

## Mål
Personliga notiser när något händer på DIN watchlist/portfölj: ny STARK, score-rörelse >tröskel,
**nytt insiderkluster (Insider Flash, #20)**, ny MEWS-flagga, nytt earnings-memo (#08).

## Återanvänd (exakta signaturer)
- `backend_worker/smart_alert_engine.py` → `run_alert_engine(dsn) -> dict[str,int]`; bygger
  `notifications`-rader + `triggered_alerts`. Kopiera dess INSERT-mönster.
- `notifications` (013): `id, user_id, type CHECK IN ('price_alert','earnings','score_change','system','insider'), title, body, link, read_at, created_at`.
- `triggered_alerts` (020): `id, user_id, rule_id, rule_name, rule_type, ticker, detail, score_at, price_at, triggered_at`.
- `insider_cluster_signals` (029): `ticker PK, unique_buyers_30d, total_buy_amount_30d, cluster_score, is_cluster, exec_buy_90d, updated_at`.
- `signal_transitions` (020): `ticker, transition_date, field, from_value, to_value, score_total_at, price_at`.
- `score_history` (020): `ticker, scan_date, score_total, entry_signal, price, ...`.
- `scan_results`: har `mews_flag` (migration 028) + `ml_rank`.
- `watchlist` (001): `user_id, ticker`. `holdings` via `portfolios(user_id)` → `holdings(portfolio_id, ticker)`.
- E-post: `backend_worker/email/sender.py` → `send_notification(to, template_name, **kwargs) -> bool`. Mallar i `backend_worker/email/components.py`.
- `NotificationBell` (`components/notifications/NotificationCenter.tsx`) pollar redan — inget extra där.

## Steg

### 1. Migration `supabase/migrations/034_notification_prefs.sql`
```sql
CREATE TABLE IF NOT EXISTS notification_prefs (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  on_new_stark BOOLEAN DEFAULT TRUE,
  on_score_move BOOLEAN DEFAULT TRUE,
  on_insider_cluster BOOLEAN DEFAULT TRUE,
  on_mews_flag BOOLEAN DEFAULT TRUE,
  on_earnings_memo BOOLEAN DEFAULT TRUE,
  score_move_threshold INTEGER DEFAULT 15,
  email_enabled BOOLEAN DEFAULT FALSE,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE notification_prefs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own_prefs_rw" ON notification_prefs
  USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
GRANT SELECT, INSERT, UPDATE ON notification_prefs TO authenticated;
COMMENT ON TABLE notification_prefs IS 'Per-user notification prefs. Migration 034. Diagnostic marker: migration_034_notification_prefs.';
```
Lägg markören i `diagnostics.py` USER_TABLES.

### 2. `backend_worker/watchlist_alerts.py` (NY)
`run_watchlist_alerts(dsn: str) -> dict[str,int]`:
1. Bygg `user_tickers: dict[user_id, set[ticker]]` = union av `watchlist` + `holdings`
   (join `portfolios`).
2. Ladda `notification_prefs` per user (default-värden om rad saknas).
3. Ladda dagens trigger-set EN gång (cross-user):
   - **new_stark:** `SELECT ticker FROM signal_transitions WHERE transition_date = CURRENT_DATE AND field='entry_signal' AND to_value='STARK'`.
   - **score_move:** per ticker, diff senaste två `score_history.scan_date`; behåll de med `abs(delta) >= user.score_move_threshold` (beräkna max-delta-set för minsta tröskel, filtrera per user).
   - **insider_cluster (Insider Flash):** nuvarande `SELECT ticker FROM insider_cluster_signals WHERE is_cluster=TRUE`. **Diffa mot föregående körning** — håll en `seen_clusters`-mängd i en `worker_state`-tabell (skapa enkel `CREATE TABLE IF NOT EXISTS worker_state(key TEXT PRIMARY KEY, value JSONB, updated_at TIMESTAMPTZ DEFAULT NOW())` i migration 034, eller jämför `updated_at::date = CURRENT_DATE`). NYA kluster = flash.
   - **mews_flag:** `SELECT ticker FROM scan_results WHERE mews_flag=TRUE`, diffa mot föregående (samma worker_state-mönster).
   - **earnings_memo:** `SELECT ticker FROM earnings_memos WHERE created_at::date = CURRENT_DATE`.
4. För varje user: för varje trigger-typ vars pref är på, `user_tickers[uid] ∩ trigger_set`.
   **Dedup:** hoppa om `triggered_alerts` redan har (user_id, ticker, rule_type) senaste 3 dagarna.
5. Skapa `notifications`-rad. `type`-mappning: insider→`'insider'`, score_move→`'score_change'`,
   earnings_memo→`'earnings'`, new_stark/mews→`'system'`. `title`/`body` beskrivande (t.ex.
   "Insiderkluster i {ticker}: {unique_buyers_30d} köpare"), `link = '/aktie/'+ticker`.
   Skriv även `triggered_alerts`-rad (rule_type = trigger-typen, rule_name = "Watchlist: "+typ).
6. Om `email_enabled` OCH triggern är viktig (insider_cluster eller new_stark): hämta user-email
   (`SELECT email FROM auth.users WHERE id=%s` via service_role) → `send_notification(email,
   "watchlist_alert", ticker=..., reason=...)`. Lägg `watchlist_alert`-mall i `email/components.py`.

`main()`: DSN från env, kör, JSON-summary, `sys.exit(1)` vid DB-fel. **Återanvänd**
INSERT-strukturen från `smart_alert_engine.py`.

### 3. API `apps/api/routers/notifications.py`
- `GET /api/notifications/prefs` → egen rad (skapa default om saknas).
- `PUT /api/notifications/prefs` → upsert egna (RLS skyddar). Pydantic `NotificationPrefs`.

### 4. Frontend
- Hook `apps/web/hooks/useNotificationPrefs.ts`: GET + mutation PUT.
- Sektion "Notiser" i `app/(app)/installningar/InstallningarView.tsx`: toggle per `on_*`,
  number-input/slider för `score_move_threshold`, toggle `email_enabled`. Spara via mutation.

### 5. Schemaläggning
Nytt steg i en daglig workflow (efter `fi_insider.yml` + efter pipeline):
`python -m backend_worker.watchlist_alerts`. Om egen workflow-fil → registrera i admin
`_WORKFLOW_INPUTS` + `AdminSections.tsx`.

## Acceptanstest
- Lägg testaktie i watchlist; infoga rad i `signal_transitions` (to_value='STARK', CURRENT_DATE)
  → kör `watchlist_alerts` → `notifications`-rad skapas, syns i `NotificationBell`.
- Sätt `is_cluster=TRUE` på en bevakad ticker (ny) → flash-notis. Kör igen samma dag → ingen
  dubblett (dedup via triggered_alerts).
- `email_enabled=true` + insider → `send_notification` anropas (mocka Resend). Prefs GET/PUT
  funkar; RLS hindrar läsning av annan users prefs. `tsc` grönt.

## Definition of Done
- [ ] Migration 034 (+ worker_state) + diagnostics-markör.
- [ ] `watchlist_alerts.py` med diff (insider/mews) + dedup + e-post för viktiga.
- [ ] prefs API + hook + Inställningar-sektion.
- [ ] Schemalagt.
- [ ] `docs/SYSTEM_AI.md` uppdaterad.
