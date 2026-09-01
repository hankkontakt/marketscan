# MarketScan R14 Implementeringsrapport: Segmentintegritet & Segmentdifferentiering

> **Datum:** 2026-09-01  
> **Omfattning:** Tasks 1–8 (P0–P2), låsta institutionella beslut D1–D8, verifierade fynd F1–F8.  
> **Status:** Genomförd och verifierad.

---

## 1. Executive Summary

Rond 14 har systematiskt genomfört övergången från global segmentblind ranking till en segmentdifferentierad kvantitativ motor. Genom strikt segmentintegritet, separata värderings- och momentum-percentiler, likviditetsgrader A–F, skyddande grindar (Junk-gate, Likviditetsgate, Nyemissionssköld) och ren frontend-presentation i screener och smallcap-vyn har MarketScan uppnått institutionell kvalitet över alla storlekssegment.

---

## 2. Genomförda Uppgifter & Leveranser

| Task | Beskrivning | Huvudfiler | Commit |
|---|---|---|---|
| **Task 1** | **Segmentintegritet & enhetsguard (P0, F1)** | `backend_worker/db_loader.py`, `backend_worker/pipeline/entrypoint.py`, `supabase/migrations/080_segment_integrity.sql`, `backend_worker/tests/test_roe_pe_raw.py` | `9469c5b` |
| **Task 2** | **MasterRank sort & pctl i screener (P0, F3)** | `apps/api/schemas/scan.py`, `apps/api/routers/screener.py` | `4c67c2c` |
| **Task 3** | **Global blockdata: rapportdatum & analytiker (P0, F2, F7)** | `backend_worker/catalyst_fetcher.py`, `backend_worker/analyst_fetcher.py`, `backend_worker/tests/test_catalyst_fetcher.py` | `157b93f` |
| **Task 5** | **Likviditetsmotor: grader A–F & golv (P1, D5)** | `backend_worker/liquidity.py`, `backend_worker/technical_snapshot.py`, `supabase/migrations/081_liquidity_columns.sql`, `backend_worker/tests/test_liquidity.py` | `b80f9d2` |
| **Task 4** | **Segment-aware MasterRank: weights v2, gates, normalisering (P1, D1–D6)** | `backend_worker/master_rank.py`, `backend_worker/macro_regime.py`, `backend_worker/resources/weights.json`, `backend_worker/tests/test_master_rank.py` | `c43ca6e` |
| **Task 6** | **Smallcap data & segmentrelativ presentation (P1, F4, F8)** | `apps/api/routers/smallcap.py`, `apps/web/app/(app)/screener/ScreenerView.tsx`, `apps/web/components/screener/ResultTable.tsx`, `apps/web/lib/api.ts`, `apps/web/types/scan.ts` | `e271704` |
| **Task 7** | **Codex in-place uppdatering (P2, F5)** | `docs/codex/01_QUANT_MASTERRANK.md`, `docs/codex/02_DATA_PIPELINE.md`, `docs/codex/05_DATABASE_SCHEMA.md` | `c16f400` |
| **Task 8** | **Sanity-gates & historisk validering (P2, D7, D8)** | `scripts/ranking_sanity_gate.py`, `backend_worker/backtest_runner.py` | Pågående commit |

---

## 3. Implementerade Institutionella Beslut (D1–D8)

- **D1 (Vikt-delta per segment):** `weights.json` v2 innehåller basvikter och `segment_overrides` för `small_cap` och `micro_cap` (Värde 18 %, Tillväxt 2 %). `macro_regime.py` bevarar dessa vid EMA-utjämning.
- **D2 (Kvalitets-junk-gate):** Små/mikrobolag med $quality\_z < 55.0$ cappas till max $61.999$ med flaggan `junk_gate` (kan aldrig nå Tier 1).
- **D3 (Segment×Sektor-normalisering & Momentum-percentil):** P/E normaliseras inom `(segment, sector)` vid $\ge 5$ peers, annars sektor vid $\ge 15$ peers, annars globalt. Momentum-z percentileras inom segment vid $\ge 10$ bolag.
- **D4 (Smallcap-data fallback):** `/api/smallcap` hämtar från `smallcap_results` med fallback till `scan_results` filtrerat på `small_cap` och `micro_cap` samt berikat med `master_rank`-data.
- **D5 (Likviditet som gate & badge):** Likviditetsgrader A–F beräknas mot fasta segmentgolv (500k, 2M, 10M, 20M SEK). Grader E/F cappas till max $49.999$ (`liquidity_gate`). Låg likviditet definieras som D, E, F.
- **D6 (Coverage-skalning för analytiker):** 1–2 analytiker krymps linjärt mot neutral 50 ($50 + (az - 50) \cdot N/3$).
- **D7 (Per-segment IC utvärdering):** `evaluate_segment_ic` i `backtest_runner.py` möjliggör separat utvärdering per segment.
- **D8 (UI-visning):** Screener visar "Pctl" (MasterRank-percentil inom segment) och Lucide-likviditetsbadge (`Droplet`) med utförlig tooltip.

---

## 4. Test- och Verifieringsresultat

1. **Backend Worker Testsvit:**
   - Kommando: `python -m pytest backend_worker/tests -q`
   - Resultat: **366 passed** (0 failures).
2. **FastAPI Testsvit:**
   - Kommando: `python -m pytest apps/api/tests -q`
   - Resultat: **66 passed** (0 failures).
3. **Frontend Typkontroll:**
   - Kommando: `cd apps/web; npx tsc --noEmit`
   - Resultat: **Exit code 0** (0 fel).
4. **Living Docs Gate:**
   - Kommando: `python scripts/verify_codex.py`
   - Resultat: **100% verifierad** (78 kodankare, 151 routes, alla linjebudgetar gröna).
5. **MasterRank Dry-Run:**
   - Kommando: `python -m backend_worker.master_rank --dry-run`
   - Resultat: **Exit code 0**, genererar förväntad demo-rad med triage-cappning.

---

## 5. Slutsats

Alla 8 deluppgifter i `PLAN.md` är slutförda i exakt ordning enligt projektets arkitekturregler och kvalitetsgrindar.