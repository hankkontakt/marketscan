# Advisor Model Selection — OpenCode Go Roster (2026-08-31)

**Date:** 2026-08-31
**Scope:** Model-selection study for the advisor/expert agent (reviewer) consulted by the cheap executor (deepseek-v4-flash) in this fleet, restricted to the actual OpenCode Go roster. Complements `advisor-agent-research.md` (which covered the advisor *pattern*; this covers *which Go model*).
**Method:** Official OpenCode Go docs (roster/pricing/privacy) + provider primary sources (xAI, Z.ai, Moonshot, DeepSeek, Alibaba, MiniMax) + independent benchmarks (Artificial Analysis, Vals AI) as supplemental. Verified facts and inference are separated inline. No benchmark scores invented — every number below is cited.

---

## Task Report

**Direct answer: Keep `opencode-go/glm-5.3` as primary advisor — the current choice is evidence-supported. Add `opencode-go/kimi-k3` as fallback #1 (highest independently-verified intelligence in the roster, best tool-use) and `opencode-go/gpt-5.6-luna` as fallback #2 (cheapest frontier-tier advisor). Keep `opencode-go/deepseek-v4-flash` as cheap executor; A/B-test `glm-5.3-flash` as an executor upgrade candidate.**

### Recommendation

| Role | Model ID | Why (evidence-backed) | Watch-outs |
|---|---|---|---|
| **Primary advisor** | `opencode-go/glm-5.3` | Cross-family vs DeepSeek executor (fleet's documented reviewer principle); frontier-adjacent coding/reasoning (Terminal-Bench 2.1 88.2, DeepSWE v1.1 66.9, GDPval-AA 1769 — top of its vendor table); token-efficient (31.4% @ ~50K output tokens vs Opus 4.8's 29.5% @ ~120K at High effort); 1M context + 128K output; **0-day retention**; $15/mo allocation, 220 req/5h | All benchmarks vendor-reported (Z.ai); weights were pending ~2 weeks post-launch (Aug 14) — independent verification still thin |
| **Fallback advisor #1** | `opencode-go/kimi-k3` | Highest *independently verified* intelligence among open models in Go (AA Intelligence Index 60, 4th overall, 1st open-weight); best tool-use evidence in roster (MCPMark-Verified 94.5, MCP-Atlas 84.2, Toolathlon-Verified 76.5); 1M context; 0-day retention | Most expensive per request in Go (110 req/5h, $15/mo); slowest frontier model (38 t/s via Kimi provider, TTFT 3.07s); early AA testing flagged higher hallucination rate than K2.6 |
| **Fallback advisor #2** | `opencode-go/gpt-5.6-luna` | Cheapest frontier-tier advisor in Go ($0.20/$1.20 ≤272K; 2,050 req/5h); solid official scorecard (SWE-Bench Pro 62.7, Terminal-Bench 2.1 84.7, DeepSWE 1.1 67.2, GPQA 92.3); OpenAI tool ecosystem | **30-day retention** (abuse logs) — avoid for sensitive data; AA Intelligence Index 51.2 is the lowest of the four advisor candidates |
| **Cheap executor** | `opencode-go/deepseek-v4-flash` (current) | Fastest + cheapest per task in roster (AA: 103–125 t/s, TTFT 1.13s, ~$0.11/task); 7,600 req/5h, $30/mo; AA Intelligence Index 52; SWE-bench Verified 79.0 (Max mode) | DeepSeek ZDR agreement expires **2026-08-31 (today)** — September renewal unconfirmed; peak-hour pricing 3× off-peak |
| **Executor upgrade candidate (A/B)** | `opencode-go/glm-5.3-flash` | AA Intelligence Index **57** vs V4 Flash's 52 at similar cost ($0.15/$0.50, $15/mo, 1,580 req/5h with 2× promo); TTFT 1.54s | 44 t/s output (slower than V4 Flash); $15/mo allocation is half of V4 Flash's $30/mo |
| **Watch, not yet** | `opencode-go/hy4-preview` | 1M context, $30/mo, 1,350 req/5h | Released 2026-08-28 — no benchmark evidence found; preview status |
| **Not recommended as advisor** | `grok-4.6`, `qwen3.8-max`, `deepseek-v4-pro`, `minimax-m3` | See "Why not" below | — |

### Why not the others (evidence)

- **Grok 4.6** — highest AA Intelligence Index in Go (61, ties GPT-5.6 Sol) and best knowledge-work scores (GDPval-AA 1753, AA-Briefcase 1577), but: only 169 req/5h (most expensive per request in Go), **30-day retention**, weak terminal/SE (Terminal-Bench 3.0 26% vs Sol 34.6%; DeepSWE 65.9% vs Sol 73%), AA non-hallucination rate 65.7% (below peers), ProofBench 45% vs 77–78% for Sol/Fable 5. Only if advisory becomes knowledge-work-heavy at low volume.
- **Qwen3.8 Max** — best instruction-following evidence in roster (IFBench 82.8 vs Sol 72.7) and strong agentic rows (Terminal-Bench 2.1 86.6, PaperBench 93.0), but weak on hard reasoning/knowledge (HLE 43.6 — last of the four flagships in its own table) and SWE-bench Pro 67.7 vs Fable 5's 80.0; all vendor-reported; 160 req/5h.
- **DeepSeek V4 Pro** — strong SWE (SWE-bench Verified 80.6, LiveCodeBench 93.5, Codeforces 3206) and cheap ($0.66/$1.98 off-peak, 1,050 req/5h), but **same family as the executor** — violates the fleet's documented cross-family review principle ("okända blindspots ska INTE delas med författar-familjen"); ZDR expiry flag (below).
- **MiniMax M3** — good value ($60/mo allocation, 3,200 req/5h, 0-day retention, ~100 t/s vendor-claimed) but mid-pack capability (SWE-Bench Pro 59.0, Terminal-Bench 2.1 66.0) — below the four advisor candidates; better as a mid-tier executor.

### Evidence by dimension (advisor-relevant)

**Difficult coding/reasoning** (verified, mixed vendor/independent):
- GLM-5.3 (vendor, Z.ai blog): Terminal-Bench 2.1 88.2 · TB 3.0 28.3 · DeepSWE v1.1 66.9 · SWE-Marathon 42.5 · FrontierSWE 78.1 · GDPval-AA 1769 · HLE w/tools 62.5
- Kimi K3 (vendor + independent): TB 2.1 88.3 vendor (85 AA) · DeepSWE 67.5 · ProgramBench 77.8 · SWE-Marathon 42.0 · GPQA 93.5 · **AA Intelligence Index 60 (independent)**
- GPT 5.6 Luna (OpenAI official): SWE-Bench Pro 62.7 · TB 2.1 84.7 · DeepSWE 1.1 67.2 · GPQA 92.3 · AA Coding Agent Index 74.6 · AA Intelligence Index 51.2
- Grok 4.6 (xAI + AA): **AA Intelligence Index 61 (independent)** · GDPval-AA 1753 · CursorBench 3.2 69.9 · DeepSWE 65.9 · TB 3.0 26.0 · SWE-bench Verified 95.6 (Vals)
- DeepSeek V4 Pro (official): SWE-bench Verified 80.6 · LiveCodeBench 93.5 · Codeforces 3206 · GPQA 90.1 · TB 2.0 67.9
- Qwen3.8 Max (vendor): TB 2.1 86.6 · SWE-bench Pro 67.7 · PaperBench 93.0 · GPQA 92.6 · HLE 43.6
- MiniMax M3 (vendor): SWE-bench Pro 59.0 · TB 2.1 66.0 · MCP Atlas 74.2 · GPQA 92.68

**Codebase review** (proxy benchmarks — no direct "review" benchmark exists; inference): DeepSWE/FrontierSWE/SWE-Marathon measure long-horizon repo work. GLM-5.3 FrontierSWE 78.1 and Kimi K3 SWE-Marathon 42.0 are the strongest open-model rows; GPT 5.6 Luna DeepSWE 67.2. All four advisor candidates are frontier-adjacent; no clean winner — this is why the eval protocol (below) uses real repo reviews.

**Instruction following**: Qwen3.8 Max IFBench 82.8 (best in its vendor table, ahead of Sol 72.7 / Fable 5 63.5). No IFBench data found for GLM-5.3, Kimi K3, DeepSeek V4 Pro, Grok 4.6, Luna — **gap** (inference: OpenAI-family models are generally strong here, but unverified for Luna specifically).

**Long context**: All advisor candidates 1M context except Grok 4.6 (500K). Kimi K3 AA-LCR 74.7 (independent long-context reasoning). DeepSeek V4 Pro MRCR 1M 83.5 / CorpusQA 62.0 (official). GPT 5.6 Luna MRCR v2 41.3 at 256K–1M (OpenAI — notably weaker). GLM-5.3 1M + 128K output ceiling. Qwen3.8 Max MRCR 92.9 @256K (vendor).

**Structured outputs / tool compatibility**:
- Endpoints (official Go docs): GLM/Kimi/DeepSeek → OpenAI `chat/completions`; Qwen/MiniMax → Anthropic `messages`; Grok/Luna → OpenAI `responses`. All three API shapes are exposed by Go.
- Tool-use benchmark evidence: Kimi K3 strongest (MCPMark-Verified 94.5, MCP-Atlas 84.2, Toolathlon-Verified 76.5); GLM-5.3 Toolathlon 73.0, MCP-Atlas 84.2; DeepSeek V4 Pro MCP-Atlas 73.6, Toolathlon 51.8, and documented function-calling + structured-output support; GPT 5.6 Luna Toolathlon 53.4.
- Caveat: Go's own structured-output support per model (JSON mode / strict schemas through the Go gateway) is **not documented on the Go page** — verify per endpoint before relying on it.

**Latency** (Artificial Analysis, independent — but measured on *non-Go* providers; Go's own hosting may differ — inference):
- DeepSeek V4 Flash: 103–125 t/s, TTFT 1.13s (fastest)
- GLM-5.3-Flash: 44 t/s, TTFT 1.54s
- Kimi K3 (max): 38 t/s via Kimi provider, TTFT 3.07s (slowest frontier; provider-dependent — Nebius serves it at 143.6 t/s)
- MiniMax M3: ~100 t/s at 1M context (vendor claim, unverified)
- Grok 4.6: qualitative reports of ~3× speed vs peers (eesel, 2026-08-13) — not a measured AA figure

**Reliability**:
- Go platform: "zero downtime in two weeks" (independent review, 2026-06-27); dollar-capped windows ($12/5h, $30/wk, $60/mo) with free-model fallback (official).
- Kimi K3: early AA testing found higher hallucination rate than K2.6 (independent analysis, 2026-07-17) — a real concern for an advisor whose value is catching executor errors.
- Grok 4.6: AA non-hallucination 65.7% (below peers).
- GLM-5.3: all scores vendor-reported; weights were pending at launch (Aug 14, "~2 weeks") — independent reproduction not yet possible at report time.
- Hy4 preview: released 2026-08-28 — no reliability evidence.

**Privacy/retention** (official Go privacy table):
- **0-day retention, no training**: GLM-5.3, Kimi K3, DeepSeek V4 Pro/Flash, Qwen3.8 Max, MiniMax M3, and all other open models.
- **30-day retention**: Grok 4.6 (ZDR disables stateful Responses API features) and GPT 5.6 Luna (abuse-monitoring logs).
- **Training permitted**: Muse Spark 1.2 Contributor (excluded from advisor use).
- **DeepSeek ZDR**: renewed monthly; "current agreement is valid through August 31, 2026" — **expires today; September renewal unconfirmed** (flag).

**Go quota/cost** (official docs, verified):
- $15/mo allocation: Grok 4.6 (169 req/5h), GPT 5.6 Luna (2,050), GLM-5.3 (220), Kimi K3 (110), Qwen3.8 Max (160), DeepSeek V4 Pro (1,050), GLM-5.3-Flash (1,580), MiMo V2.5 Pro (3,250)
- $30/mo: DeepSeek V4 Flash (7,600), Qwen3.8 Flash (5,400), Hy4 preview (1,350)
- $60/mo: MiniMax M3 (3,200), GLM-5.2 (880), Qwen3.7 Max (340), Kimi K2.7 Code (1,350), LongCat-2.0 (11,400), MiMo V2.5 (30,100), Hy3 (4,300), etc.
- Inference (rough advisor-call economics, base = official prices, ~50K cached input + 500 output per advisor call): Luna ~$0.0016/call (~9K calls within $15), DeepSeek V4 Pro off-peak ~$0.002/call (~7.5K), GLM-5.3 ~$0.015/call (~1K), Kimi K3 ~$0.023/call (~660), Grok 4.6 ~$0.028/call (~535). **The $15/mo allocation is the binding constraint for Kimi K3/Grok 4.6 as frequent advisors.**

### Evaluation protocol (proposed)

1. **Eval set (~20 queries)** drawn from this repo's real advisor tasks: (a) plan/spec stress-test (pre-mortem, severity grammar), (b) codebase review of a real diff (FastAPI router + Supabase migration), (c) security review (RLS/GRANTs, service_role usage), (d) data-correctness review (market-data pipeline), (e) 2–3 deliberately flawed plans to test catch-rate.
2. **A/B**: GLM-5.3 (primary) vs Kimi K3 vs GPT 5.6 Luna on the same 20 queries, same escalation packets. Optionally Grok 4.6 on the knowledge-work subset.
3. **Metrics**: verdict quality (LLM-as-judge rubric + human review of a 5-query subset), catch-rate on seeded flaws, escalation rate, cost per task (from Go console), wall-clock latency, quota burn per model.
4. **Gate**: switch primary only if a challenger wins ≥2 of: catch-rate, verdict quality, cost/task — on ≥15/20 queries, replicated twice.
5. **Cadence**: re-run monthly — the Go roster churns fast (GLM-5.3, Qwen3.8, Grok 4.6, Hy4 all landed in August 2026 alone).

---

## Verification Receipts

| # | Source | URL | Accessed | Backs claims |
|---|--------|-----|----------|--------------|
| 1 | OpenCode — Go docs (official; roster, limits, prices, endpoints, privacy table) | https://opencode.ai/docs/go/ | 2026-08-31 | Roster (25 models); $12/5h/$30/wk/$60/mo caps; per-model req estimates + prices + $15/$30/$60 allocations; endpoints (chat/completions, messages, responses); privacy table (0-day vs 30-day, Muse training, DeepSeek ZDR through 2026-08-31); model-id format `opencode-go/<id>` |
| 2 | OpenCode — Go landing page (official) | https://opencode.ai/go | 2026-08-31 | Roster; request/5h headline numbers; "curated lineup tested for agentic coding" |
| 3 | Julien.cloud — OpenCode Go Models tracker (API metadata + models.dev merge) | https://julien.cloud/opencode-go-models/ | 2026-08-31 | Release dates (Hy4 08-28, Qwen3.8 Flash 08-26, GLM-5.3 08-14, Grok 4.6 08-12, Qwen3.8 Max 08-03, DeepSeek V4 Flash 07-31, Kimi K3 07-16, GPT-5.6 Luna 07-09, MiniMax M3 05-31, DeepSeek V4 Pro 04-24); context windows (1M/500K/262K/203K/205K/256K); 2026-08-31 price changes |
| 4 | Z.ai — GLM-5.3 release blog (vendor primary) | https://z.ai/blog/glm-5.3 | 2026-08-31 | GLM-5.3 benchmarks (TB 2.1 88.2, TB 3.0 28.3, DeepSWE 66.9, SWE-Marathon 42.5, FrontierSWE 78.1, Toolathlon 73.0, AutomationBench 48.2, ALE 28.5, HLE w/tools 62.5, GDPval 1769, CyberGym 84.5); token efficiency (31.4% @ ~50K vs Opus 4.8 29.5% @ ~120K); weights ~2 weeks post-launch; 743B base = GLM-5.2 |
| 5 | Moonshot AI — Kimi K3 tech blog (vendor primary) | https://www.kimi.ai/blog/kimi-k3 | 2026-08-31 | Kimi K3 benchmarks (TB 2.1 88.3, DeepSWE 67.5, ProgramBench 77.8, SWE-Marathon 42.0, BrowseComp 91.2, GPQA 93.5, MCPMark 94.5, MCP-Atlas 84.2, Toolathlon 76.5); harness footnotes; 2.8T/104B active; 1M context; weights by 07-27 |
| 6 | MoonshotAI/Kimi-K3 — GitHub (vendor primary) | https://github.com/MoonshotAI/Kimi-K3 | 2026-08-31 | Full benchmark table + per-row harness/source footnotes; AA-LCR 74.7 |
| 7 | xAI — Grok 4.6 announcement (vendor primary) | https://x.ai/news/grok-4-6 | 2026-08-31 | Grok 4.6 release 08-12; AA Intelligence Index ties GPT-5.6 Sol; CursorBench 3.2 69.9, DeepSWE 65.9, FrontierCode 61.3, TB 3.0 26, APEX-SWE 56.4 |
| 8 | xAI — Grok 4.6 model card (vendor primary, PDF) | https://media.x.ai/v1/website/card-4p6-4cd2dc57.pdf | 2026-08-31 | Grok 4.6 evals detail (DeepSWE 65.9/67.0, SWE-Marathon 31.9, TB 3.0 26.0, APEX-SWE 56.4); 1.5T-scale family; 500K context class |
| 9 | DeepSeek-AI — DeepSeek-V4 paper (arXiv 2606.19348) + HF model card (vendor primary) | https://arxiv.org/html/2606.19348 ; https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro | 2026-08-31 | V4 Pro 1.6T/49B, V4 Flash 284B/13B, 1M context; SWE Verified 80.6, LiveCodeBench 93.5, Codeforces 3206, GPQA 90.1, TB 2.0 67.9, MCPAtlas 73.6, Toolathlon 51.8, MRCR 1M 83.5; 384K max output; MIT |
| 10 | Alibaba — Qwen3.8-Max release (vendor primary) | https://www.alibabacloud.com/blog/603421 ; https://qwen.ai/blog?id=qwen3.8 | 2026-08-31 | Qwen3.8 Max 2.4T/95B, 1M context; TB 2.1 86.6, SWE-bench Pro 67.7, PaperBench 93.0, IFBench 82.8, GPQA 92.6, HLE 43.6, OSWorld-Verified 86.1; reasoning_effort xhigh/medium/low |
| 11 | MiniMax — M3 release blog (vendor primary) | https://www.minimax.io/blog/minimax-m3 | 2026-08-31 | M3 SWE-bench Pro 59.0, TB 2.1 66.0, MCP Atlas 74.2, BrowseComp 83.5, GPQA 92.68; MSA; 1M context; thinking toggle; ~100 t/s at 1M (vendor) |
| 12 | OpenAI — GPT-5.6 scorecard via goml.io breakdown | https://www.goml.io/blog/gpt-5-6-benchmarks | 2026-08-31 | Luna official rows: SWE-Pro 62.7, TB 2.1 84.7, DeepSWE 67.2, GPQA 92.3, BrowseComp 83.3, Toolathlon 53.4, AA CAI 74.6, AA II 51.2; Luna = cost-optimized tier |
| 13 | Artificial Analysis — Kimi K3 release page + comparisons (independent) | https://artificialanalysis.ai/models/releases/kimi-k3 ; https://artificialanalysis.ai/models/comparisons/kimi-k3-vs-deepseek-v4-flash | 2026-08-31 | Kimi K3 AA Intelligence Index 60, 38 t/s, TTFT 3.07s, $0.84/task; DeepSeek V4 Flash 0731: II 52, 125 t/s, TTFT 1.13s, $0.11/task; GLM-5.3-Flash II 57, 44 t/s, TTFT 1.54s |
| 14 | Vals AI — SWE-bench Verified leaderboard (independent) | https://vals.ai/benchmarks/swebench | 2026-08-31 | DeepSeek V4 Pro 0813 96.40% (2nd overall), Kimi K3 93.40%, Claude Opus 4.8 88.60%, Grok 4.5 86.60% |
| 15 | Binaryverse AI — Grok 4.6 independent review (Vals rows) | https://binaryverseai.com/grok-4-6-review-benchmarks-pricing/ | 2026-08-31 | Grok 4.6 Vals rows: SWE-bench Verified 95.60, GPQA 94.70, LiveCodeBench 88.22, ProofBench 45.00, TB 2.1 78.28 |
| 16 | eesel AI — Grok 4.6 review (independent) | https://www.eesel.ai/blog/grok-4-6-review | 2026-08-31 | Grok 4.6 wins knowledge-work rows, loses SE rows; ~3× speed reports; AA non-hallucination 65.7% |
| 17 | Emergent.sh — Grok 4.6 benchmarks (independent) | https://emergent.sh/learn/grok-4-6-benchmarks | 2026-08-31 | AA II 61 (ties Sol, behind Opus 5 63 / Fable 5 62); TB version mismatch (26% v3.0 vs 88.4% v2.1); GDPval 1753, AA-Briefcase 1577 |
| 18 | NxCode — Kimi K3 benchmark guide (independent) | https://www.nxcode.io/resources/news/kimi-k3-benchmarks-coding-agent-evaluation-guide-2026 | 2026-08-31 | Harness caveats; AA II 57 at launch, 62 t/s, $2,690 eval cost; vendor vs independent score gaps |
| 19 | Jason Pollak — Fable 5 vs GPT-5.6 vs Kimi K3 vs DeepSeek V4 (independent) | https://jasonpollakmarketing.com/2026/07/16/fable-5-gpt-5-6-kimi-k3-glm-5-2-deepseek-v4/ | 2026-08-31 | Kimi K3 2.8T/1M/native vision; early AA hallucination-rate concern vs K2.6; model positioning table |
| 20 | CodingFleet — GPT-5.6 Luna vs DeepSeek V4 Pro (independent) | https://codingfleet.com/blog/gpt-5-6-luna-vs-deepseek-v4-pro/ | 2026-08-31 | Luna SWE-Pro 62.7 vs V4 Pro Max 55.4; Luna MRCR 41.3; V4 Pro 384K output; cache economics |
| 21 | Tony Reviews Things — OpenCode Go review (independent) | https://www.tonyreviewsthings.com/opencode-go-review/ | 2026-08-31 | Go platform stability ("zero downtime in two weeks"); 17/19 models zero-retention; Grok/Luna 30-day; Muse training; cap system |
| 22 | LLM Gateway — OpenCode Go pricing explainer (independent) | https://llmgateway.io/blog/opencode-go-pricing | 2026-08-31 | Dollar metering; $15/$30/$60 per-model allocations; free-model fallback; Zen balance option |
| 23 | Codingplan.org — OpenCode Go guide (independent) | https://codingplan.org/en/plans/opencode-go | 2026-08-31 | 24-model roster; August additions; $5 promo removed Aug 24; DeepSeek peak/off-peak windows |
| 24 | Local fleet config | C:\Users\hthur\.config\opencode\opencode.jsonc | 2026-08-31 | Current setup: executor `opencode-go/deepseek-v4-flash` (default + 13 agents), reviewer/reviewer-natt = `opencode-go/glm-5.3` (cross-family rationale in agent description), plan = `glm-5.3-flash`, vision = `deepseek-v4-flash-vision-exp` |

**Double-sourced decision-critical claims:**
- **Go roster + pricing/limits** (#1 official + #22 + #23 + #3) — official docs agree with two independent trackers.
- **GLM-5.3 capability** (#4 vendor + #17/#18-adjacent coverage + The New Stack/MarkTechPost/Decrypt via search) — vendor table cross-checked against 4+ independent write-ups; all flag vendor-reported status.
- **Kimi K3 capability** (#5/#6 vendor + #13 AA independent + #18/#19) — vendor table vs independent AA index both cited.
- **Privacy table** (#1 official + #21 independent review) — 0-day vs 30-day retention agreement.

---

## Blockers / Inte gjort

- **GLM-5.3 independent verification**: all benchmark rows are Z.ai-reported; weights were pending ~2 weeks after the Aug 14 launch (i.e., due ~Aug 28). Whether weights/independent evals have landed by today (Aug 31) was not verified. Re-check before relying on GLM-5.3 as the long-term primary.
- **DeepSeek ZDR renewal**: official Go docs state the ZDR agreement "is valid through August 31, 2026" — i.e., **expires today**. September renewal is unconfirmed as of report time. If it lapses, DeepSeek V4 Pro/Flash privacy posture changes (retention >0 days) — re-verify on the Go docs page.
- **Go-gateway structured outputs**: the Go docs list endpoints but not per-model JSON-mode/strict-schema support through the Go gateway. OpenAI/Anthropic-compatible endpoints imply the standard shapes, but exact behavior (e.g., `strict: true` on `responses` for Luna/Grok) is unverified.
- **Latency on Go's own infrastructure**: all AA latency/speed figures are measured on non-Go providers (Kimi, Nebius, Fireworks, etc.). Go's hosting may differ — measure in the eval protocol.
- **Instruction-following gap**: IFBench data exists only for Qwen3.8 Max among the candidates; no comparable data found for GLM-5.3/Kimi K3/DeepSeek V4 Pro/Grok 4.6/Luna. Do not rank on this dimension beyond Qwen's vendor row.
- **Hy4 preview**: no benchmark or reliability evidence found (released 08-28). Excluded from recommendations.
- **Reddit cost-economy thread** (r/opencode "De-Mystifying Opencode Model Economy") could not be fetched (Reddit blocked); its per-request cost percentages were not used.
- **No app code or docs modified** — research-only deliverable written to `.opencode/audit/advisor-model-selection.md`.