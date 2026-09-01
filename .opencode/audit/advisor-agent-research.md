# Advisor/Expert Agent — Research Report (2025–2026 best practices)

**Date:** 2026-08-31
**Scope:** Best practices for a strong advisor/expert agent that a cheaper model consults on hard questions, for integration into a FastAPI + Next.js/Supabase app.
**Method:** Multi-source research; primary sources (Anthropic/OpenAI official docs & engineering posts, arXiv/ACL papers) cross-checked against independent secondary sources. All claims cited in Verification Receipts.

---

## Task Report

**Direct answer: Yes — the "cheap executor + strong advisor" architecture is now a first-class, well-documented pattern, and it is the right shape for this app.** Anthropic shipped the **advisor tool** (April 9, 2026) as a server-side primitive: a cheap executor model (Haiku/Sonnet) runs the loop and consults a stronger advisor (Opus) mid-generation inside a single API request; OpenRouter shipped a provider-agnostic equivalent (June 10, 2026). Measured results: **Sonnet + Opus advisor = +2.7 pp on SWE-bench Multilingual AND −11.9% cost per task vs Sonnet alone; Haiku + Opus advisor = 41.2% vs 19.7% solo on BrowseComp at 85% lower cost than Sonnet solo** (Anthropic official). The pattern generalizes the older cascade/router literature (FrugalGPT 2023, RouteLLM 2024) from request-level to decision-level escalation.

**Key recommendations (top 10):**

1. **Use the advisor pattern, not a full orchestrator-worker swarm.** Anthropic's own data: multi-agent systems cost ~15× tokens of a chat; the advisor pattern gets most of the quality lift at executor-level cost. Start with a single executor + one advisor tool call.
2. **Escalation policy: let the executor decide, but steer with the system prompt.** Anthropic's tested guidance: call the advisor early (after a few exploratory reads) and once before declaring done; on Haiku, a prompt block raised pass rates ~7.5 pp. Cap consultations (`max_uses`); Anthropic's own evals used 2–3 per task.
3. **Context handoff = compact escalation packet, not full transcript.** The advisor sees the full conversation automatically in Anthropic's tool, but for a self-built version, forward a curated packet (decision under review, evidence, uncertainty signals, specific question). Keep inline handoff messages < ~2,000 tokens; store large artifacts externally and pass keys. Use a typed Pydantic `HandoffContext` as the contract between executor and advisor.
4. **Structured response contracts: use provider structured outputs (strict JSON Schema / Pydantic).** OpenAI Structured Outputs (`strict: true`, constrained decoding, `refusal` field) and Anthropic structured outputs guarantee schema adherence; always validate downstream anyway (refusals, truncation, unenforced keywords like `pattern`/`format`).
5. **Tool permissions & prompt-injection: containment beats prompting.** Enforce constraints in code, not prompts ("constraints must be enforced in code, not in prompts" — Anthropic). Untrusted content goes in `tool_result` blocks, never system prompts; credentials never enter the executor's context (scoped per-session tokens, vault/proxy); sandbox + egress controls; a small fast classifier can screen tool outputs for injection before they reach context.
6. **Model selection: pick the cheapest executor that completes most tasks, then the strongest advisor you can afford.** Current list prices (Aug 2026): Claude Haiku 4.5 $1/$5 per MTok, Sonnet 5 $2/$10, Opus 4.8 $5/$25; OpenAI GPT-5.6 Luna $0.20/$1.20, Terra $2/$12, Sol $4/$20. Advisor calls are short (400–700 tokens), so advisor-tier cost is bounded.
7. **Uncertainty & verification: prefer deterministic verifiers; use calibrated confidence for escalation.** Raw model confidence is miscalibrated; self-consistency/semantic dispersion and verifier feedback are the strongest signals (UniCR). For open-ended answers, LLM-as-judge verification is nearly as hard as the task — be skeptical of cascade economics on prose. Escalation rate is the live cost metric to watch.
8. **Memory/caching: prompt caching is the highest-leverage cost lever.** Cache reads cost 0.1× base input on both Anthropic and OpenAI; writes 1.25× (5-min TTL) / 2× (1-h TTL) on Anthropic. Put stable content (system prompt, advisor instructions, tool defs) first in the prefix; enable caching when ≥3 advisor calls per conversation. For cross-session memory use structured note-taking (agent writes notes to Supabase), not raw history.
9. **Observability/evals: build a small eval set (~20 queries) with an LLM-as-judge rubric + human review, and trace everything.** Judge calibration is mandatory (position/verbosity/self-preference/style biases are documented; CoT prompting is the safest debiaser). Grade outcomes in the environment, not claims in the transcript. Log executor model, advisor calls, tokens, cost, escalation rate per run.
10. **Privacy/security: PII redaction before any third-party model call, zero/low data retention where possible, RLS-scoped data access via Supabase.** OpenAI/Anthropic offer zero data retention options; EU data residency endpoints exist (10% uplift on OpenAI). Treat every tool result as untrusted input.

---

## Evidence by topic

### 1. Escalation / routing policies

- **Advisor strategy (decision-level escalation)** — Anthropic's official pattern: executor (Sonnet/Haiku) runs end-to-end, consults Opus advisor mid-task; advisor returns a plan/correction/stop signal (typically 400–700 tokens), never calls tools or produces user output; all inside one `/v1/messages` request. Benchmarks: Sonnet+Opus +2.7 pp SWE-bench Multilingual, −11.9% cost/task; Haiku+Opus 41.2% vs 19.7% solo on BrowseComp, −85% vs Sonnet solo. Beta header `anthropic-beta: advisor-tool-2026-03-01`, `max_uses` cap, advisor tokens billed separately. (Anthropic, 2026-04-09)
- **Cascade vs router (request-level)** — Cascade (FrugalGPT 2023, AutoMix NeurIPS 2024): cheap model first, verifier decides escalation; quality floor = strong model, but pays cheap+verify+expensive on every escalation. Router (RouteLLM 2024): classify before generation, one hop, low latency, but misroutes are unrecoverable. RouteLLM: >85% cost cut at ~95% GPT-4 quality on MT-Bench; honest mixed-traffic figure ~20–25%; LLMRouterBench 2026 found several commercial routers (incl. OpenRouter's) did NOT beat always-using-the-best-single-model (−24.7% relative). **Lesson: measure your own escalation rate; a router needs its own evals.**
- **Orchestrator-worker** (Anthropic multi-agent research system): lead agent decomposes, spawns 3–5 parallel subagents with fresh context windows, each returns a distilled summary (1,000–2,000 tokens). Prompt principles: teach delegation (objective + output format + tools + boundaries), embed effort-scaling rules (simple fact-finding = 1 agent/3–10 tool calls; complex research = 10+ subagents), parallel tool calls cut time up to 90%. Cost honesty: agents ~4× tokens of chat, multi-agent ~15×.
- **OpenAI guide**: maximize single-agent capability first; split only on complex conditional logic or overlapping tools; manager pattern (agents as tools) vs decentralized handoffs; human intervention on failure thresholds and high-risk actions.

### 2. Context handoff

- **Handoff artifact** (aipatternbook + AI Tools Guidebook): a structured briefing with Objective, Constraints, Prior decisions (highest value — prevents redoing rejected work), Current state, Next steps. Never dump full conversation history ("context dump fallacy" — stale reasoning misleads the receiver). Typed Pydantic `HandoffContext` as API contract between agents; `{handoff_context}` slot in every system prompt; large artifacts in shared store (Redis/S3/Supabase), messages carry keys not payloads; inline handoff < ~2,000 tokens.
- **Case-facts block** (Anthropic cert course): progressive summarization destroys transactional specifics (amounts, IDs, dates). Extract facts into a protected block included in every prompt, never summarized. Front-load key info (lost-in-the-middle effect); trim tool results before they enter history.
- **Context engineering** (Anthropic, 2025-09-29): compaction (summarize near window limit; tune prompt for recall then precision), structured note-taking/agentic memory (NOTES.md pattern), sub-agents returning distilled summaries, just-in-time loading (lightweight identifiers, load on demand). Context rot is real — smallest set of high-signal tokens wins.
- **Advisor tool handoff**: full conversation forwarded automatically server-side; no client orchestration. For self-built: compact escalation packet (see recommendations).

### 3. Structured response contracts

- **OpenAI Structured Outputs** (official docs): `response_format: {type: "json_schema", strict: true}` or function calling with `strict: true`; constrained decoding (CFG) guarantees schema adherence; `refusal` field for safety refusals; Pydantic/Zod SDK `parse()` helpers; supported subset of JSON Schema (all properties required, `additionalProperties: false`, no unenforced keywords — validate `pattern`/`format`/ranges yourself); first request with a new schema has a latency penalty (schema preprocessing).
- **Anthropic**: structured outputs in public beta (2025); tool use with strict schemas; advisor tool itself is a structured tool contract.
- **Multi-agent structured outputs** (OpenAI cookbook): strict tool schemas for triage/routing between agents — the router's `agents` array + `query` fields are schema-enforced.

### 4. Tool permissions & prompt-injection defenses

- **Containment first** (Anthropic "How we contain Claude", 2025): supervision is fallible (users approved ~93% of permission prompts → approval fatigue); containment (sandboxes, VMs, filesystem boundaries, egress controls) is the hard boundary. Credentials never enter the sandbox → can't be exfiltrated. Tool output is an attack surface even from trusted tools (poisoned README via GitHub connector); inspect tool returns with a small fast classifier before they enter context. Model-layer defenses never 100%: Opus 4.7 ~0.1% single-attempt injection success on Gray Swan, 5–6% after 100 adaptive attempts.
- **"Constraints must be enforced in code, not in prompts"** (Anthropic defending-code-reference-harness security docs). Untrusted data in `<untrusted_data>` blocks / `tool_result` blocks; JSON-encode untrusted strings to prevent breakout.
- **Claude Code permission modes**: default / acceptEdits / plan / auto / dontAsk / bypassPermissions; auto mode is a research-preview classifier, not a production safety gate. Agent SDK `can_use_tool` permission callbacks allow allow/deny/input-modification per tool.
- **IPIGUARD** (EMNLP 2025): plan-then-execute with a Tool Dependency Graph — decouple action planning from external data interaction; prohibit tools not pre-approved in the plan; structural defense against indirect prompt injection (AgentDojo benchmark).
- **OpenAI guardrails** (practical guide): 7 types — relevance classifier, safety classifier, PII filter, moderation, tool safeguards (risk-rate each tool low/med/high by reversibility/access/financial impact → pause or HITL before high-risk calls), rules-based protections, output validation. Layered, not single.

### 5. Model selection / cost / latency

- **Current list prices (Aug 2026, official):** Claude — Haiku 4.5 $1/$5, Sonnet 5 $2/$10, Opus 4.8 $5/$25 per MTok (in/out). OpenAI — GPT-5.6 Luna $0.20/$1.20, Terra $2/$12, Sol $4/$20; GPT-5 $1.25/$10. Cache reads 0.1× on both platforms.
- **Advisor economics:** advisor generates only 400–700 tokens/call; executor handles bulk at its own rate. Sonnet+Opus beats Sonnet alone on quality AND cost (fewer wasted tool calls). Haiku+Opus = 2× Haiku solo quality at a fraction of Sonnet cost. Crossover rule of thumb: cost-split wins while escalation rate < ~60%; typical production escalation 10–20%.
- **Routing economics:** static rules capture 60–70% of available savings with zero training; learned routers add 15–25% on top but need training data + retraining cadence; semantic/embedding routing is milliseconds and cheap. Latency: cascade doubles latency on escalation and breaks streaming; classifier routers add ~ms; LLM-as-judge routers add seconds (offline labeling only).
- **Model-pair sanity:** don't route between models too far apart in capability (GPT-5 vs 1B model); pick neighboring tiers. Lock model per session if UX consistency matters.

### 6. Uncertainty & verification

- **UniCR** (arXiv 2509.01455, 2025): fuse heterogeneous evidence (sequence likelihoods, self-consistency dispersion, retrieval compatibility, tool/verifier feedback) into a calibrated probability of correctness; conformal risk control gives distribution-free guarantees; abstention when expected loss > reject cost. If latency is tight, keep self-consistency + retrieval compatibility.
- **80-model study** (arXiv 2505.23854): Linguistic Verbal Uncertainty (hedging language judged by a separate LLM) outperforms token-probability and numeric verbal confidence; reasoning tasks calibrate better than knowledge-heavy ones; high accuracy ≠ reliable uncertainty.
- **"In the wild" study** (ACL 2025): most UE methods are highly sensitive to threshold selection under distribution shift; vulnerable to adversarial prompts; ensembling multiple UE scores gives a notable boost.
- **Verification practice:** deterministic verifiers (JSON validates, code compiles, tests pass) are free and can't be fooled — prefer them; LLM-as-verifier only for genuinely subjective output. Self-consistency/Best-of-N with confidence-based early stopping improves accuracy at fixed sample budget (arXiv 2503.00031). Cascade economics live and die on the verifier's calibration — watch escalation rate as a live metric.

### 7. Memory / caching

- **Prompt caching (Anthropic, official):** automatic (`cache_control` top-level) or explicit breakpoints (max 4); 5-min TTL default, 1-h option; reads 0.1× base, writes 1.25× (5m) / 2× (1h); minimum cacheable prompt length per model; cache hits don't count against rate limits; verify via `cache_creation_input_tokens`/`cache_read_input_tokens`.
- **Prompt caching (OpenAI, official):** implicit by default; min 1,024 tokens (GPT-5.6+); reads 0.1×, writes 1.25× (GPT-5.6+); `prompt_cache_key` improves routing stickiness (one customer: 60% → 87% hit rate); ~15 RPM per prefix+key; explicit breakpoints on GPT-5.6+; TTL 30m.
- **Context primitives** (Anthropic cookbook): compaction (lossy, whole-transcript), tool-result clearing (lossless for re-fetchable results, cheapest), memory tool (cross-session persistence). Map workload → primitive: dialogue-heavy → compaction; large re-fetchable tool results → clearing; cross-session preferences → memory.
- **Advisor caching:** enable caching for conversations with ≥3 advisor calls (breaks even at 3+).

### 8. Observability / evals

- **Eval setup** (Anthropic multi-agent research system): start with ~20 test queries; LLM-as-judge rubric over factual accuracy, citation precision, completeness, source quality, tool efficiency; keep human review in the loop (caught agents favoring SEO content farms). Evaluate outcomes, not prescribed steps (non-deterministic paths).
- **LangSmith**: offline evals (datasets with references) + online evals (production traces, reference-free); 10–20 curated examples to start; LLM-as-judge needs calibration; convert production failures into regression datasets.
- **Langfuse**: judge calibration with TPR/TNR against human labels; prefer binary/categorical verdicts over scales; one failure mode per judge (no "God Evaluator"); reasoning-first judge prompts; "grade the outcome in the environment, not the claim in the transcript"; code evaluators before LLM judges where possible.
- **Judge bias is documented and measurable**: position bias, verbosity bias, self-preference/family bias, style bias (CALM catalogs 12 types; Jury panel reaches 98.1% agreement vs 87.6% single judge; CoT prompting is the only universally beneficial debiaser; style bias 0.76–0.92 dominates position bias ≤0.04 in one 2026 study). Calibrate judges against human-annotated samples before trusting trend lines.
- **Trace everything**: executor model, advisor calls (when/why/tokens/cost), escalation rate, tool calls, final decision path. Rainbow deployments for stateful agent systems.

### 9. Privacy / security

- **PII redaction before third-party model calls**; EU data residency endpoints (OpenAI regional processing, +10% uplift for models ≥2026-03-05); zero data retention options on both OpenAI and Anthropic platforms; DPAs and audit logs for agent platforms (GDPR).
- **Credential hygiene** (Anthropic): scoped per-session tokens with minimum permissions; credentials in vault/proxy, never in agent context or readable files; egress allowlists are NOT sufficient alone (March 2026 "Claudy Day" attack: attacker-supplied API key + Files API exfiltration through an allowlisted domain — validate credentials, not just destinations).
- **Supabase-specific**: RLS + GRANTs are the enforcement layer (per repo CLAUDE.md: RLS/GRANTs/auth-dependencies are not optional); service_role only behind admin; the advisor agent should read through the same RLS-scoped client as the app.

### 10. Concrete implementation patterns (FastAPI + Next.js/Supabase)

- **Anthropic advisor tool** (if on Claude stack): one-line addition to Messages API — `tools: [{type: "advisor_20260301", name: "advisor", model: "claude-opus-4-6", max_uses: 3}]`; system prompt steers when to consult; advisor tokens reported separately in usage. Beta, needs header + account access.
- **OpenRouter Advisor** (provider-agnostic, June 2026): server-side tool; configurable advisor model/instructions/tools; recursion blocked; consultations capped per request; advisor memory scoped per advisor; multiple named advisors (security reviewer, architect, cost reviewer) each with a narrow contract.
- **Self-built escalation (portable, any provider)** — the pattern this app would most likely implement in FastAPI:
  1. Executor loop (cheap model) with a `consult_advisor` tool exposed to it.
  2. Escalation triggers: early call after orientation reads; before committing to an approach; on repeated failure (e.g., 3 consecutive failures); before declaring done. Baseline defaults from pi-lifeline: ≥5 rounds before first advisor call, escalate after 3 consecutive failures, plateau detection after 6 rounds, max 10 advisor calls/session.
  3. Advisor endpoint: receives compact escalation packet (typed Pydantic model), calls strong model with narrow instructions, returns structured advice (JSON schema), executor resumes.
  4. Circuit breakers: max consultations, max advisor tokens, max wall-clock, fail-closed behavior.
  5. Budget: session-level spend cap; count advisor calls client-side; remove advisor tool when cap reached.
  6. Observability: log escalation events (executor, advisor, tokens, cost, decision path) to Supabase; eval set in CI.
- **FastAPI specifics**: advisor call is just another HTTP call from the executor loop (or a background task via `asyncio`); use Pydantic models for both the escalation packet and the advisor response contract (validates at the boundary); Supabase Postgres for handoff artifacts, memory notes, and eval traces; prompt caching via stable prefixes (system prompt + advisor instructions first).

---

## Verification Receipts

| # | Source | URL | Accessed | Backs claims |
|---|--------|-----|----------|--------------|
| 1 | Anthropic — "The advisor strategy: Give agents an intelligence boost" (official blog, 2026-04-09) | https://claude.com/blog/the-advisor-strategy | 2026-08-31 | Advisor tool mechanics; +2.7 pp / −11.9%; Haiku 41.2% vs 19.7%, −85%; 400–700 tokens; max_uses; beta header |
| 2 | Anthropic — Advisor tool docs (platform.claude.com) | https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool | 2026-08-31 | Advisor pairing rules, max_tokens cap, caching guidance, executor system-prompt steering (+7.5 pp Haiku) |
| 3 | Anthropic — "How we built our multi-agent research system" (2025-06-13) | https://www.anthropic.com/engineering/multi-agent-research-system | 2026-08-31 | Orchestrator-worker; delegation principles; scaling rules; ~20-query evals; rainbow deployments; 15× token cost |
| 4 | Anthropic — "Building effective agents" (2024-12-19) | https://www.anthropic.com/engineering/building-effective-agents | 2026-08-31 | Workflows vs agents; routing; orchestrator-workers; evaluator-optimizer; ACI/tool design |
| 5 | Anthropic — "Effective context engineering for AI agents" (2025-09-29) | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents | 2026-08-31 | Context rot; compaction; structured note-taking; just-in-time; sub-agent summaries |
| 6 | Anthropic — "How we contain Claude" | https://www.anthropic.com/engineering/how-we-contain-claude | 2026-08-31 | Containment; 93% approval rate; egress controls; tool-output inspection; credentials out of sandbox |
| 7 | Anthropic — "Mitigating the risk of prompt injections in browser use" (2025-11-24) | https://www.anthropic.com/news/prompt-injection-defenses | 2026-08-31 | RL-trained injection resistance; classifiers; red teaming; ~1% attack success Opus 4.5 |
| 8 | Anthropic — Prompt caching docs | https://platform.claude.com/docs/en/build-with-claude/prompt-caching | 2026-08-31 | Cache pricing (reads 0.1×, writes 1.25×/2×); TTLs; min cacheable length; Claude model prices |
| 9 | Anthropic — defending-code-reference-harness security docs | https://github.com/anthropics/defending-code-reference-harness/blob/main/docs/security.md | 2026-08-31 | "Constraints enforced in code, not prompts"; sandboxing; untrusted_data blocks |
| 10 | Anthropic — Context engineering cookbook (compaction/clearing/memory) | https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools | 2026-08-31 | Primitive selection framework; compaction vs clearing vs memory |
| 11 | Anthropic Certifications — Conversation context management (5.1) | https://www.anthropiccertifications.com/courses/claude-certified-architect-foundations/conversation-context-management | 2026-08-31 | Case-facts block; lost-in-the-middle; tool-result trimming |
| 12 | OpenAI — "A practical guide to building agents" (PDF) | https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf | 2026-08-31 | Single-agent first; manager vs decentralized; 7 guardrail types; tool risk ratings; HITL triggers |
| 13 | OpenAI — Structured Outputs guide | https://developers.openai.com/api/docs/guides/structured-outputs | 2026-08-31 | strict:true; constrained decoding; refusal; schema subset; JSON mode vs structured |
| 14 | OpenAI — Prompt caching guide | https://developers.openai.com/api/docs/guides/prompt-caching | 2026-08-31 | Implicit caching; 1,024-token min; 0.1× reads / 1.25× writes; prompt_cache_key; 15 RPM |
| 15 | OpenAI — Prompt Caching 201 cookbook | https://developers.openai.com/cookbook/examples/prompt_caching_201 | 2026-08-31 | 60%→87% hit-rate case; Flex vs Batch; retention policies |
| 16 | OpenAI — Pricing page | https://developers.openai.com/api/docs/pricing | 2026-08-31 | GPT-5.6 Sol/Terra/Luna prices; regional 10% uplift |
| 17 | OpenAI — GPT-5 model page | https://developers.openai.com/api/docs/models/gpt-5 | 2026-08-31 | GPT-5 $1.25/$10 |
| 18 | OpenAI — Structured Outputs for Multi-Agent Systems cookbook | https://developers.openai.com/cookbook/examples/structured_outputs_multi_agent/ | 2026-08-31 | Strict tool schemas for triage/routing agents |
| 19 | OpenAI — Building Governed AI Agents cookbook | https://developers.openai.com/cookbook/examples/partners/agentic_governance_guide/agentic_governance_cookbook | 2026-08-31 | Triage agent + handoffs; red-team eval; guardrail precision/recall; NIST/ISO alignment |
| 20 | RouteLLM (LMSYS) — GitHub + arXiv 2406.18665 | https://github.com/lm-sys/RouteLLM ; https://arxiv.org/abs/2406.18665v2 | 2026-08-31 | Router framework; >85% cost cut at ~95% GPT-4 quality (MT-Bench); threshold calibration |
| 21 | Sean Geng — "The honest guide to LLM model routing" (2026-06-03) | https://seangeng.com/writing/the-honest-guide-to-llm-routing | 2026-08-31 | LLMRouterBench 2026 results (OpenRouter −24.7% vs Best-Single); honest ~20–25% savings; adversarial rerouting; router evals |
| 22 | dreaming.press — "LLM Cascade vs Router" (2026-07-02) | https://dreaming.press/posts/llm-cascade-vs-router.html | 2026-08-31 | Cascade vs router economics; verifier calibration; escalation-rate math |
| 23 | dreaming.press — "Build a Cost-Aware Model Router" (2026-07-13) | https://dreaming.press/posts/build-cost-aware-model-router-for-your-agent.html | 2026-08-31 | ~35-line cascade router; deterministic verifier first; break-even analysis |
| 24 | Aakash Sharan — "Model Escalation Is a Tool Call" (2026-06-11) | https://aakashsharan.com/model-escalation-is-a-tool-call/ | 2026-08-31 | OpenRouter Advisor (2026-06-10); escalation packet; circuit breakers; escalation telemetry |
| 25 | aipatternbook — "Handoff" | https://aipatternbook.com/handoff | 2026-08-31 | Handoff artifact 5 elements; context dump fallacy; harness support (Agents SDK, LangGraph) |
| 26 | AI Tools Guidebook — "Agent Handoff Loses Context" (2026-05-25) | https://aitoolsguidebook.com/en/articles/agent-handoff-loses-context/ | 2026-08-31 | Typed HandoffContext (Pydantic); external store + keys; {handoff_context} slot; <2,000-token inline rule |
| 27 | UniCR — "Trusted Uncertainty in LLMs" (arXiv 2509.01455, 2025) | https://doi.org/10.48550/arxiv.2509.01455 | 2026-08-31 | Multi-evidence calibration; conformal risk control; abstention; ablation findings |
| 28 | "Revisiting Uncertainty Estimation and Calibration of LLMs" (arXiv 2505.23854) | https://arxiv.org/html/2505.23854v1 | 2026-08-31 | 80-model study; LVU > NVU > TPU; reasoning vs knowledge calibration |
| 29 | "Reconsidering LLM Uncertainty Estimation Methods in the Wild" (ACL 2025) | https://aclanthology.org/2025.acl-long.1429.pdf | 2026-08-31 | Threshold sensitivity; adversarial vulnerability; ensembling UE scores helps |
| 30 | "Self-Calibration" test-time scaling (arXiv 2503.00031) | https://arxiv.org/pdf/2503.00031 | 2026-08-31 | Confidence-based early stopping for Best-of-N; 94.2% sample savings |
| 31 | IPIGUARD (EMNLP 2025) | https://aclanthology.org/2025.emnlp-main.53.pdf | 2026-08-31 | Tool Dependency Graph; plan-then-execute; AgentDojo |
| 32 | LangSmith — Evaluation concepts | https://docs.langchain.com/langsmith/evaluation-concepts | 2026-08-31 | Offline vs online evals; 10–20 examples; LLM-as-judge; reference-free vs reference-based |
| 33 | Langfuse — "LLM Evaluation: Methods, Best Practices" (2025-11-12, upd. 2026-07) | https://langfuse.com/blog/2025-11-12-evals | 2026-08-31 | Eval method table; judge calibration; $0.01–0.10/assessment; CI gates |
| 34 | Langfuse — "Writing evaluators" academy | https://langfuse.com/academy/evaluate/writing-evaluators | 2026-08-31 | One failure mode per judge; binary verdicts; reasoning-first; judge calibration TPR/TNR; "grade the outcome in the environment" |
| 35 | LangChain — "Evaluating LLMs and Agents" (2026-06-23) | https://www.langchain.com/resources/how-to-evaluate-llms | 2026-08-31 | Judge bias (Dec 2025 study: top judges fail ~25% of difficult cases); trajectory evals; sandboxes; gateway governance |
| 36 | IJISAE — "Auditing and Debiasing LLM-as-a-Judge" (2025-07-18) | https://ijisae.org/index.php/IJISAE/article/view/8407 | 2026-08-31 | Verdict-Bench; Jury panel 98.1% vs 87.6% single judge; bias rates |
| 37 | CALM — "PREJUDICE?" (ICLR 2025) | https://proceedings.iclr.cc/paper_files/paper/2025/file/fdca08d371e4b6c031397909e20043bd-Paper-Conference.pdf | 2026-08-31 | 12 judge bias types; attack-and-detect framework |
| 38 | "Judging the Judges: Bias Mitigation Strategies" (arXiv 2604.23178) | https://arxiv.org/html/2604.23178 | 2026-08-31 | Style bias dominant (0.76–0.92); CoT safest debiaser; conciseness preference |
| 39 | HarrisonSec — "Agent Architecture Is a Compute Allocation Problem" (2026-06-15) | https://harrisonsec.com/blog/agent-architecture-compute-allocation-advisor-strategy/ | 2026-08-31 | Advisor strategy convergence (Anthropic/Lütke/HazyResearch); pi-lifeline escalation defaults |
| 40 | agerix — "The advisor pattern" (2026-04-22) | https://www.agerix.fr/en/blog-en/the-advisor-pattern-what-claude-code-teaches-us-about-delegation | 2026-08-31 | Advisor never outputs to user / no tools; subsidiarity framing; 400–700 tokens |
| 41 | Claude Code docs — Advisor | https://code.claude.com/docs/en/advisor | 2026-08-31 | Advisor pairing table; when to use; cost accounting |
| 42 | Springer — "Zero Data Retention in LLM-Based Enterprise Assistants" | https://link.springer.com/chapter/10.1007/978-3-032-15395-1_17 | 2026-08-31 | ZDR policies (Salesforce AgentForce, MS Copilot) |
| 43 | agent-works — "GDPR Compliant AI: EU Data Residency" | https://agent-works.ai/insights/gdpr-compliant-ai-data-residency | 2026-08-31 | PII redaction before third-party models; EU residency; audit logs; DPAs |
| 44 | truto.one — "EU Data Residency and GDPR Compliance for MCP Servers" (2026) | https://truto.one/blog/how-to-handle-eu-data-residency-and-gdpr-compliance-for-mcp-servers/ | 2026-08-31 | ZDR vendor policies (OpenAI/Anthropic); PII minimization; MCP GDPR traps |

**Double-sourced critical claims:**
- Advisor strategy economics (#1 + #2 + #21/#39/#40 secondary) — 3+ independent sources.
- Prompt caching pricing 0.1× reads / 1.25× writes (#8 + #14) — both providers' official docs agree.
- RouteLLM 85%/95% figures (#20 GitHub + #20 arXiv + #21/#22) — primary repo + paper + independent analyses.
- Judge bias existence/mitigation (#35 + #36 + #37 + #38) — four independent academic/industry sources.

---

## Blockers / Inte gjort

- **Anthropic advisor tool is beta** (header `anthropic-beta: advisor-tool-2026-03-01`, account-team access per one source). Verify current availability/GA status and exact model IDs before implementation — model names/prices in this report are as of 2026-08-31 and change frequently.
- **Anthropic structured outputs** — confirmed in beta via secondary source only (cuttlesoft 2025-11-12); exact schema-subset rules for Anthropic's implementation not verified against primary docs in this pass. Check `platform.claude.com` structured-outputs docs before relying on it.
- **OpenRouter Advisor** — documented via one detailed secondary source (#24) plus OpenRouter's own prompt-caching docs; the OpenRouter advisor announcement page itself was not fetched directly. Treat exact API shape as unverified.
- **Claude model prices** — taken from the prompt-caching pricing table on platform.claude.com (authoritative); the standalone pricing page was not separately fetched. Opus 4.1/4 "retired" status noted in that table.
- **Latency numbers** for specific models (TTFT, tokens/sec) — not verified; only qualitative tradeoffs (cascade doubles latency, classifier routers add ms) are cited.
- **No application code or docs/codex was modified** — this is a research-only deliverable.