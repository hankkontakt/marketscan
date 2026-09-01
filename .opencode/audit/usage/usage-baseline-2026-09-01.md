# AI Usage Baseline Report — 2026-09-01

## 1. Totalsummor (Senaste 30 dagarna)

| Parameter | Totalt | Dagssnitt (30 d) |
|---|---:|---:|
| **Poster / Anrop** | 6,534 | 217.8 |
| **Prompt Tokens (Input)** | 118,382,227 | 3,946,074 |
| **Completion Tokens (Output)** | 20,964,444 | 698,815 |
| **Cache Read Tokens** | 6,205,636,497 | 206,854,550 |
| **Cache Write Tokens** | 39,042,436 | 1,301,415 |
| **Total Kostnad USD** | $2,897.60 | $96.59 |
| **Total Kostnad SEK (USD × 11)** | 31,873.62 SEK | 1,062.45 SEK |

## 2. Fördelning per Modell & Harness

| Harness | Modell | Anrop/Sessioner | Input | Output | Cache Read | Cache Write | Kostnad (USD) | Kostnad (SEK) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| claude-code | `claude-opus-5` | 4,326 | 215,846 | 4,677,994 | 1,212,787,856 | 30,863,485 | $2751.96 | 30271.55 SEK |
| claude-code | `claude-sonnet-5` | 1,143 | 204,753 | 818,656 | 159,885,765 | 7,662,117 | $89.59 | 985.52 SEK |
| opencode | `deepseek-v4-flash (default)` | 832 | 59,103,181 | 9,363,490 | 1,726,448,128 | 0 | $20.83 | 229.14 SEK |
| opencode | `deepseek-v4-flash (max)` | 52 | 28,714,315 | 3,175,281 | 1,847,441,032 | 0 | $12.31 | 135.38 SEK |
| opencode | `deepseek-v4-flash-vision-exp (max)` | 24 | 11,487,073 | 1,195,410 | 552,661,881 | 494,780 | $8.87 | 97.52 SEK |
| opencode | `minimax-m3 (default)` | 21 | 2,452,714 | 480,270 | 98,911,407 | 0 | $7.25 | 79.72 SEK |
| opencode | `deepseek-v4-flash (high)` | 76 | 9,466,827 | 597,493 | 406,229,888 | 0 | $1.60 | 17.59 SEK |
| opencode | `glm-5.3 (default)` | 6 | 281,405 | 9,532 | 1,359,744 | 0 | $0.96 | 10.57 SEK |
| opencode | `minimax-m3 (thinking)` | 1 | 1,873,896 | 96,332 | 18,603,649 | 0 | $0.93 | 10.27 SEK |
| opencode | `deepseek-v4-flash-vision-exp (high)` | 1 | 1,426,625 | 107,924 | 53,876,352 | 0 | $0.85 | 9.37 SEK |
| opencode | `glm-5.3 (high)` | 9 | 189,304 | 50,447 | 1,142,603 | 0 | $0.78 | 8.62 SEK |
| opencode | `mimo-v2.5 (default)` | 15 | 1,542,456 | 195,594 | 100,121,984 | 0 | $0.57 | 6.24 SEK |
| opencode | `deepseek-v4-pro (max)` | 3 | 617,948 | 43,937 | 2,839,168 | 0 | $0.45 | 4.95 SEK |
| opencode | `deepseek-v4-flash-vision-exp (default)` | 8 | 367,928 | 78,819 | 19,612,160 | 0 | $0.32 | 3.51 SEK |
| opencode | `z-ai/glm-5.3-flash (max)` | 1 | 81,359 | 62,960 | 3,358,592 | 0 | $0.14 | 1.59 SEK |
| opencode | `kimi-k2.7-code (default)` | 4 | 82,365 | 664 | 80,128 | 0 | $0.10 | 1.13 SEK |
| opencode | `glm-5.2 (default)` | 1 | 20,967 | 3 | 128 | 0 | $0.03 | 0.32 SEK |
| opencode | `deepseek-v4-pro (default)` | 2 | 43,515 | 26 | 0 | 0 | $0.02 | 0.27 SEK |
| opencode | `glm-5.3-flash (max)` | 1 | 71,172 | 8,773 | 236,800 | 0 | $0.01 | 0.16 SEK |
| opencode | `deepseek-v4-flash (low)` | 4 | 81,760 | 545 | 27,904 | 0 | $0.01 | 0.06 SEK |
| opencode | `deepseek/deepseek-v4-flash (max)` | 1 | 23,032 | 56 | 0 | 0 | $0.01 | 0.06 SEK |
| opencode | `qwen3.8-flash (default)` | 1 | 6 | 69 | 0 | 22,054 | $0.00 | 0.05 SEK |
| opencode | `glm-5.3-flash (default)` | 2 | 33,780 | 169 | 11,328 | 0 | $0.00 | 0.03 SEK |

## 3. Komponent- och Prefix-fotavtryck

| Komponent | Storlek | Uppskattade Tokens | Kommentar |
|---|---:|---:|---|
| **`~/.config/opencode/AGENTS.md`** | 59 rader (3,235 B) | ~808 | Global systemprefix-injektion |
| **Manifest Skills (.agents/skills)** | 15 kataloger | ~450 | Inaktiva bör arkiveras (mål ≤15) |
| **Manifest Skills (.claude/skills)** | 13 kataloger | ~390 | Claude-specifika skills |
| **Superpowers Skills** | 14 kataloger | ~420 | Plugin-interna (rör ej) |
| **MarketScan Docs Stack (Före Diet)** | 1,623 rader (90.9 KB) | ~23,277 | Tvångsläsning via "läs först"-kedja |

### Detaljerad Docs-stack (Före Diet)
| Fil | Rader | Storlek (Bytes) |
|---|---:|---:|
| `SYSTEM_AI.md` | 58 | 2,656 B |
| `docs/SYSTEM_AI.md` | 15 | 1,046 B |
| `HANDOFF.md` | 17 | 837 B |
| `SETUP.md` | 351 | 12,018 B |
| `DEBUGGING.md` | 88 | 4,453 B |
| `docs/plan/00_MASTER_PLAN.md` | 249 | 13,147 B |
| `SYSTEM_INDEX.md` | 59 | 5,935 B |
| `docs/codex/00_SYSTEM_BLUEPRINT.md` | 83 | 5,092 B |
| `docs/codex/01_QUANT_MASTERRANK.md` | 118 | 8,286 B |
| `docs/codex/02_DATA_PIPELINE.md` | 96 | 6,295 B |
| `docs/codex/03_AI_RAG_SYNTHESIS.md` | 98 | 8,593 B |
| `docs/codex/04_API_ARCHITECTURE.md` | 104 | 6,549 B |
| `docs/codex/05_DATABASE_SCHEMA.md` | 98 | 6,877 B |
| `docs/codex/06_FRONTEND_STATE_UX.md` | 90 | 5,675 B |
| `docs/codex/07_PORTFOLIO_RISK.md` | 99 | 5,652 B |

## 4. Fångad Rådata & Bevis

### `opencode db path`
```
C:\Users\hthur\.local\share\opencode\opencode.db
```

### `opencode stats --days 30`
```
Large dataset detected (1067 sessions). This may take a while...
┌────────────────────────────────────────────────────────┐
│                       OVERVIEW                         │
├────────────────────────────────────────────────────────┤
│Sessions                                          1,067 │
│Messages                                         36,010 │
│Days                                                 30 │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│                    COST & TOKENS                       │
├────────────────────────────────────────────────────────┤
│Total Cost                                       $57.11 │
│Avg Cost/Day                                      $1.90 │
│Avg Tokens/Session                                 4.9M │
│Median Tokens/Session                              1.0M │
│Input                                            119.9M │
│Output                                            15.8M │
│Cache Read                                      5057.5M │
│Cache Write                                      516.8K │
└────────────────────────────────────────────────────────┘


┌────────────────────────────────────────────────────────┐
│                      TOOL USAGE                        │
├────────────────────────────────────────────────────────┤
│ read               ████████████████████ 15503 (30.3%)  │
│ bash               ██████████████████   14212 (27.8%)  │
│ grep               ████████             6640 (13.0%)   │
│ edit               ███████              6192 (12.1%)   │
│ glob               ███                  2908 ( 5.7%)   │
│ write              █                    1403 ( 2.7%)   │
│ skill              █                    950 ( 1.9%)    │
│ task               █                    932 ( 1.8%)    │
│ websearch          █                    642 ( 1.3%)    │
│ webfetch           █                    518 ( 1.0%)    │
│ searxng            █                    431 ( 0.8%)    │
│ todowrite          █                    387 ( 0.8%)    │
│ question           █                    114 ( 0.2%)    │
│ exa_web_search_exa █                    114 ( 0.2%)    │
│ exa_web_fetch_exa  █                     96 ( 0.2%)    │
│ invalid            █                     25 ( 0.0%)    │
│ apply_patch        █                     21 ( 0.0%)    │
│ list_mcp_resources █                     11 ( 0.0%)    │
│ context7_query-d.. █                      9 ( 0.0%)    │
│ list_mcp_resourc.. █                      6 ( 0.0%)    │
│ context7_resolve.. █                      4 ( 0.0%)    │
│ cmd_plan_summary   █                      2 ( 0.0%)    │
└────────────────────────────────────────────────────────┘
```
