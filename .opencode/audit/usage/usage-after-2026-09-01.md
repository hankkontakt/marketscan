# AI Usage Reduction — Slutrapport & Jämförelse (2026-09-01)

> **Datum:** 2026-09-01
> **Projekt:** MarketScan & External Workspaces (BudgetApp, OpenCode, Claude Code)
> **Genomförd av:** Google Antigravity
> **Status:** Samtliga vågor (1–4) fullföljda och 100% verifierade mot live-kodbas.

---

## 1. Före / Efter Sammanfattning (Prefix & Arkitektur)

| Komponent | Före Åtgärd | Efter Åtgärd | Besparing / Förbättring | Kommentar |
|---|---:|---:|---:|---|
| **`~/.config/opencode/AGENTS.md`** | 60 rader (3,233 B) | 59 rader (3,235 B) | Regelstruktur bevarad | Skills-cap införd; strikt UTF-8 & subagent-brief budget (<= 2 KB) |
| **Manifest Skills (`.agents/skills`)** | 67 kataloger (~2,010 tokens) | 15 kataloger (~450 tokens) | **-77.6% (-1,560 tokens)** | 52 inaktiva skills säkert flyttade till `skills-archive\` |
| **MarketScan Docs Stack (Totalt)** | 3,745 rader (219.4 KB) | 1,623 rader (90.9 KB) | **-56.7% (-128.5 KB)** | Historik & gamla planer flyttade till `docs/archive/` |
| **Krävd Sessionstart-läsning** | ~170 KB fullreads | ~6 KB (Index + 1 kapitel) | **-96.5% (~164 KB)** | Tvångskedjor ersatta av pekare till Living AI Codex |
| **Default Claude Modell** | `sonnet` | `sonnet` | Säkerställd | Inga dyra `opus`-defaults för vardagskodning |
| **Default OpenCode Modell** | `deepseek-v4-flash` | `deepseek-v4-flash` | Säkerställd | Pay-as-you-go via `opencode-go`, subagent-tak <= 1-2 |

---

## 2. Historisk 30-Dagars Baseline (Från Instrumentering)

| Parameter | Totalt (30 d) | Dagssnitt |
|---|---:|---:|
| **Totalt Antal Anrop/Sessioner** | 6,534 | 217.8 |
| **Prompt Tokens (Input)** | 118,382,227 | 3,946,074 |
| **Completion Tokens (Output)** | 20,964,444 | 698,815 |
| **Cache Read Tokens** | 6,205,636,497 | 206,854,550 |
| **Cache Write Tokens** | 39,042,436 | 1,301,415 |
| **Total Kostnad (USD)** | $2,897.60 | $96.59 |
| **Total Kostnad (SEK vid USDx11)** | 31,873.62 SEK | 1,062.45 SEK |

### Top Kostnadsdrivare i Baselinemätningen
1. `claude-opus-5` (Claude Code): $2,751.96 (30,271.55 SEK) — 4,326 anrop.
2. `claude-sonnet-5` (Claude Code): $89.59 (985.52 SEK) — 1,143 anrop.
3. `deepseek-v4-flash (default)` (OpenCode): $20.83 (229.14 SEK) — 832 sessioner.
4. `deepseek-v4-flash (max)` (OpenCode): $12.31 (135.38 SEK) — 52 sessioner.

*Notis om framtida mätning:* Fullständig empirisk före/efter-tokenmätning över 7+ dagar kräver drift över tid. Baseline är nu fullt instrumenterad via `scripts/usage_report.py` och redo för veckovisa uppföljningar.

---

## 3. Faktisk Utdata från Verifieringsgates (Wave 4)

### Gate 1: Living Codex Ground Truth
```powershell
python scripts/verify_codex.py
```
**Faktisk Utdata:**
```
============================================================
   MARKETSCAN CODEX VERIFIER (LIVING DOCS GATE)
============================================================
[1/3] Kontrollerar filer och linjebudgetar...
  [OK] SYSTEM_INDEX.md (59/250 rader)
  [OK] llms.txt (21/250 rader)
  [OK] docs/codex/00_SYSTEM_BLUEPRINT.md (83/500 rader)
  [OK] docs/codex/01_QUANT_MASTERRANK.md (118/500 rader)
  [OK] docs/codex/02_DATA_PIPELINE.md (96/500 rader)
  [OK] docs/codex/03_AI_RAG_SYNTHESIS.md (98/500 rader)
  [OK] docs/codex/04_API_ARCHITECTURE.md (104/500 rader)
  [OK] docs/codex/05_DATABASE_SCHEMA.md (98/500 rader)
  [OK] docs/codex/06_FRONTEND_STATE_UX.md (90/500 rader)
  [OK] docs/codex/07_PORTFOLIO_RISK.md (99/500 rader)

[2/3] Verifierar länkade kodankare och filvägar...
  [OK] Verifierade 70 unika kodankare och filvägar.

[3/3] Kontrollerar täckning av FastAPI-routes...
  [INFO] Hittade 153 aktiva API-routes i apps.api.main.
RESULTAT: Alla filer, budgetar och länkar är 100% verifierade!
```

### Gate 2: FastAPI Routing & Imports
```powershell
PYTHONPATH=. python -c "from apps.api.main import app; print(len(app.routes))"
```
**Faktisk Utdata:**
```
154
```

### Gate 3: Live Smoke Probes (29 Endpoints)
```powershell
python scripts/smoke_test.py
```
**Faktisk Utdata:**
```
Smoke test  →  https://marketscan-api.vercel.app
PUBLIC (expect 200)             → 16/16 OK
AUTH-REQUIRED (expect 401/403)  → 10/10 OK
ADMIN-REQUIRED (expect 401/403) →  3/3  OK
==============================================================================
RESULT: 29/29 passed, 0 failed
```

### Gate 4: Frontend Typecheck
```powershell
cd apps/web; npx tsc --noEmit
```
**Faktisk Utdata:**
```
Exit code: 0 (0 fel)
```

### Gate 5: Backend Unit & Integration Tests
```powershell
PYTHONPATH=. python -m pytest apps/api/tests backend_worker/tests -v
```
**Faktisk Utdata:**
```
======================= 397 passed, 2 warnings in 4.42s =======================
```

### Gate 6: Usage Reporting Pipeline
```powershell
python scripts/usage_report.py
```
**Faktisk Utdata:**
```
[1/5] Collecting OpenCode database statistics... Found 1065 session records in opencode.db (30d).
[2/5] Collecting Claude Code project logs... Found 5469 Claude Code assistant turn records (30d).
[3/5] Measuring prefix footprint...
[4/5] Writing baseline CSV... Saved CSV to .opencode/audit/usage/usage-baseline-2026-09-01.csv
[5/5] Generating baseline Markdown report... Saved Markdown to .opencode/audit/usage/usage-baseline-2026-09-01.md
Done! Baseline generated successfully.
```

---

## 4. Säkerhets- och PII-svep
```powershell
git grep -iE "sk-|api[_-]?key|token" -- scripts/ .opencode/audit/
```
Inga API-nycklar, lösenord eller personuppgifter påträffades. All data i rapporter och CSV-filer är aggregerad och fri från hemligheter.
