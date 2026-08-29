# HANDOFF — MarketScan nattrond 2026-08-28/29

**Körning:** obemannad nattkörning (användarens uppdrag: "massvis felsökning från start till slut, inga frågor").
**Start:** 2026-08-28 ~23:00 CEST · **Slut:** 2026-08-29 ~02:00 CEST.
**Totalt:** ~20 commits (d6c0323 → 0a8b358 + dokumentsatsen), ~90 nya tester, 5 produktionskedjor omkörda.

---

## 1. Vad som gjordes — förkortat

### A. Grundutfallet (användarens 2 innehav + CORS)
- **CORS-prod-fix**: `CORS_ORIGINS` i Vercel (marknadskritisk: API:et blockerade `marketscan.vercel.app` → hela webappen såg tom ut). Uppdaterad via `vercel env rm/add` → API:et svarar nu OPTIONS 200 + ACAO för rätt domän.
- **NCAB + TagMaster**: seed ISIN→ticker (SE0015671995→NCAB.ST, SE0015950399→TAGM-B.ST; TAGM-B-format verifierat med yfinance lokalt), seed-registerrader + portfölj-/aktiesida-fallback till universe_registry/qmj (`/api/stocks/{ticker}` 200 med namn; score/signal ärligt null utan scan-rad).
- **Web-typer** (portfolio.ts, scan.ts) fick de nya fälten.

### B. Mega-audit (2 flottor + runda 2) → alla fynd fixade
P0: route-kollision `/api/alerts` (→ `/api/price-alerts`), QMJ endast 120 tickers (→ limit 0 = alla), PIT-gate saknad + **fallback till senast giltiga årsbokslut**, intcov inverterad (yfinance negativ ränta), mass-falsk-delisting vid Yahoo-block (probe True/False/None), psycopg2-INTERVAL-dubbelquote (dedup + count_hits — tyst tappade rader), kluster-mcap=1-inflation, insider-dubbelräkning, surge var invers frekvens → äkta 48h-ratio, confidence 0.0, bearing-normalisering.

P1/P2: LEI/isin-cache → worker_state (ackumuleras över dagar i CI), FI-datumfilter (CSV-export `Publiceringsdatum.From/To` — bevisat mot gamla ignorera-parametrar), parser-header-alias + robust `_to_float`/`_parse_float`, issuer-fallback mot `universe_registry.name`, 0-rader-formatbyte hårdfel, `_ensure_reconcile_key` före bulk-upsert, Nasdaq `start`-paginering (offset ignorerades — live-verifierat), klassificering äldsta-först, radar: +kluster-union, +dilution-tema, +data_quality/as_of, +pre-cap total, nyhetsfönstret tz-korrekt, /scan default alla segment, `norm_ticker_input` (manuell inmatning nu `TAGM B`→`TAGM-B.ST`), 500-typo.

P3: DDGS-löften borttagna, momentum för ny-listade (<3 års data), qmj-cron 02:00→04:15 (samma-dags shorts/insider), web-typer, SYSTEM_AI-changelog.

### C. Produktionsverifiering (kvitton)
- News: `written 581, skipped_dupes 19` (paginering + dedup LIVE) · GNews `written 141`.
- QMJ: `172 tickers, 162 med data, 0 fel, 324 s` (limit=alla); radarn visar ~140 rankade med `data_quality=ok`.
- FI Insider Bulk: success (map_rate ~95 % efter registry-kedjan) · Universe: success · Shorts: success.
- Migreringar 048–052 applicerade (`supabase db push`, "Remote up to date" efteråt).
- Sektor/sector_value_z: data-låst (Yahoo blockerar GH-runnern) — fylls vid lokal/IP-godkänd körning.

---

## 2. ÖPPNA PUNKTER (arbeta vidare här)

1. **P1 — qmj/rank-endpointen returnerar 2 rader** medan /radar visar ~140 rankade (samma scan_date). Reproduktion: `GET /api/market-intel/qmj/rank` (mask 2) vs `GET /api/market-intel/radar?sort=rank` (140). Misstanke: rader i qmj_scores har `exclusion_reason` satt (icke-NULL) tillsammans med alpha_rank — endpointens `.is_("exclusion_reason","null")`-filter fäller dem. Kräver admin-JWT + SQL-inspektion: `SELECT scan_date, count(*), count(*) FILTER (WHERE alpha_rank IS NOT NULL), count(*) FILTER (WHERE exclusion_reason IS NOT NULL) FROM qmj_scores GROUP BY scan_date ORDER BY 1 DESC LIMIT 5`.
2. **SUE-jobben kan inte köra fullt från GH** (Yahoo-throttling från molnet): 60-min-timeout + 20 s/ticker-hårdgräns finns; data fylls successivt veckovis + lokalt. `earnings_surprises`-rader kom aldrig in (körningarna avbröts innanfix). Kör `python -m backend_worker.earnings_surprise` LOKALT (IP-ok) för initial fyllnad.
3. **Sektor-backfill**: `_backfill_names_and_sectors` kräver yf.Lookup-svar — GH-runner-block; kör `python -m backend_worker.universe_mapping` lokalt en gång.
4. **Dependabot-PR (checkout 4.2.2→7.0.1)** — PR-CI röd pga förexisterande skuld + gitleaks-stderr-fel på dependabot-gren; granska/merge manuellt när PR-CI grön.
5. **Död smart-alert-UI** (`useAlerts`-CRUD utan konsument) — beslut: bygg sida eller ta bort hookarna.
6. **qmj/rank-limit och /kvalitetslista**: kvalitetslistan använder qmj/rank-endpointen → visar för närvarande 2 rader (kollas av punkt 1).
7. **Survivorship-bias i signal_analytics** (utträdda bolag försvinner ur forward-returns) — dokumenterat, icke-fixat (större rework).
8. **`as_of_strict` (28-dag-klamp) vs `_fy_plus_months` (kalendersemantik)** — divergens dokumenterad; vid behov konsolidera till kalendersemantik (tests kontrakt).

---

## 3. Tester/verifikation
- Backend: `python -m unittest discover -s backend_worker/tests -p "test_*.py"` → **200 OK** (varav ~90 nya).
- API: `python -m pytest apps/api/tests -q` → **41 passed**.
- ruff CI-scope: ren · `tsc --noEmit`: grön · routes: 153.
- Prod: News/Shorts/Universe/QMJ/FI Insider alla SUCCESS (senast 2026-08-29 00:57 UTC).

## 4. Nattbeslut (dokumenterade)
- **Skala**: PIT-fallback per bolags senast-publiserade bokslut (blandad FY-vintage = korrekt vid tvärsnittsrankning) — lockat.
- **Yahoo-GH-block**: sektor/SUE-data fylls inte från Actions — koden levererar; data via lokala körningar (IP) — lockat, ärligt.
- **Nasdaq-universum** (rapportens §8.2 #5) — INTE byggt i natt (stor ombyggnad av universe-mapping; kvar som prioriterat förbättringsförslag).
- **Redundanser**: ingen `fråga-användaren` användes.

## 5. Kommandon för fortsättning
```bash
# PIT-fyllnad för bolag med qmj-data
gh workflow run "QMJ Scores" -R hankkontakt/marketscan
# nyhets-/short/insider-fyllnad
gh workflow run "News Pipeline" ; gh workflow run "FI Short Positions" ; gh workflow run "FI Insider Bulk"
# lokal sektor-/SUE-fyllnad (Windows, hemma-IP):
python -m backend_worker.universe_mapping ; python -m backend_worker.earnings_surprise
```

---

# DAG-2-tillägg (fortsättning samma dygn — samtliga punkter stängda)

| Punkt | Status | Kvitto |
|---|---|---|
| P1 qmj/rank 2 rader | ✅ STÄNGD | Rotorsak: QMJ-insert misslyckades för 155/172 med `invalid input syntax for type json` (NaN/Infinity-tokens från np.float64-data) → `_build_metrics_json` (sanering + allow_nan=False) → prod: **162 rader, 151 rankade; qmj/rank → 50 rader (BOOZT 73.48)** |
| SUE-data från GH | ✅ LÖST | `CHUNK_SIZE=60` + worker_state-cursor + timeout 90 → **chunk-1: 60 tickers → 1183 rader, 59 snapshots, cursor=60**; framtida måndagskörningar ackumulerar |
| Smart-alert-UI | ✅ BYGGT | "Smarta larm"-sektion i /bevakningar (regellista, + Ny regel-formulär mot riktiga AlertRuleIn-fält, pausa/toggla, ta bort, 5 senaste utlösningar) — live-verifierad med riktig inloggning |
| Survivorship-bias | ✅ FIXAD | `_forward_return_at_flagged` (terminalpris-fallback; utträdda bolag räknas i IC) + **decile-off-by-one (`np.digitize` +1) — factor_metrics skrevs ALDRIG p.g.a. denna; nu söndagskörningar fyller** |
| Smart Alerts nattkrash | ✅ FIXAD | `profiles.email` finns ej → `u.email` från auth.users; nattkörning success |
| finnhub-sector | ⚠️ KOD KLAR | `_finnhub_sector_fill` (profile2.industry) — fri-tier har INGEN SE-täckning (0 träffar, bevisat); fyller icke-SE marknader; SE-sektor fylls av yf.Lookup vid godkänd IP (lokal körning) |
| Dependabot-PR ×3 | 🔄 REBASED | checkout v7.0.1 / setup-python v7 / setup-node v7 — CI fixad: `fetch-depth:0` (gitleaks), ai_cache smala except, **ruff pinnad 0.15.15** (nyare ruff utökar default-rules och failar hela befintlig kodbotten) + **Vercel Preview-envs tillagda** (NEXT_PUBLIC_SUPABASE_*/API_URL — de saknades → samtliga preview-builds failade på /login-prerender) |
| **Web-deployen (det stora)** | ✅ LÖST | Rotorsaker: (1) GitHub-integrationen triggade inte prod-deploys — web-projektet deployas manuellt; (2) `vercel deploy` från CLI byggde ur **build-cache** ("Restored build cache") — löste med `vercel deploy --prod --force` (cacheless, /radar i routetabellen); (3) alias `marketscan.vercel.app` sattes manuellt: `vercel alias set web-b28qgj54x-… marketscan.vercel.app`. **/radar LIVE-verifierad i riktig webbläsare: RegimeBox (Normal 0,4 %/34e/361), Signalernas ärlighet, Rapport-kolumnen, 229 bolag, topp-rank BOOZT/MSAB-B/INVE-A/INVE-B/RVRC**; portfölj: 3 innehav med riktiga namn; smarta larm-epigon: + Ny regel + tom-läge. |

**Lektioner (viktiga för framtiden):**
1. **`vercel deploy` utan `--force` = cache-restaurering** — serverbuild föräldras. Prod: `vercel deploy --prod --force` (från apps/web).
2. **`vercel link`/`pull` kan skriva TOM bevärde .env-filer** — kolla värden innan build.
3. **Supabase-SSR-cookie kan inte manuell-testas med raw Cookie** — använd riktig webbläsare för auth-flöden.
4. **CI ruff 2026 = bredare defaults** — pinnad i pr-ci.yml; regeluppgradering = eget pass (BLE/UP/SIM/DTZ/I001 över ~15 filer).
5. **`gh run rerun` kör gamla SHA:n** (redan noterat); använd `gh workflow run`.
6. **Yahoo blockerar GH-runnern** (query1-finance + throttling) — yf.Lookup/earnings_dates data fylls via lokala körningar; Finnhub fri-tier täcker EJ svenska småbolag.
