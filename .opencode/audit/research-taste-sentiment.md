# Research: Sentiment on Command Code "Taste" & Preference-Learning in AI Coding Tools

**Date:** 2026-08-31
**Agent:** research (deepseek-v4-flash)
**Purpose:** Inform a build of a similar "taste" system (signal capture → distillation → storage → context injection → sync). Not building a full coding agent.

---

## Task Report (direct answer)

**Verdict: The preference-learning layer is the most praised and most criticized part of Command Code at the same time.** Users praise the *concept* (learning from accept/reject/edit beats static rules files) and the *artifact* (human-readable, confidence-scored, editable `taste.md` files). They criticize the *execution and trust surface*: silent failures (Windows), TUI spam, a "local learning" claim that an independent bundle audit found misleading, a thin evidence model (confidence numbers without provenance), and heavy "meta neuro-symbolic taste-1" marketing that skeptics call forced. Competitor evidence (Cursor, Claude Code, Windsurf) shows the dominant failure mode across ALL preference/memory systems is **stale or wrong learned rules silently steering the agent** — so dedup/decay/evidence/audit is where a new build should differentiate. No independent benchmark validates Command Code's "10× faster / 5× fewer bugs" claims.

---

## Gillar (what users praise)

1. **The core concept — learning beats rules files.** Multiple independent reviews single out that Taste captures implicit feedback (accept/reject/edit) that static `.cursorrules`/AGENTS.md cannot. Volanea: *"A persistent preference layer can be useful when it captures the implicit feedback in your accept-and-edit behavior"* — "more practical value than generic personalization." (volanea.com, 2026-08-15)
2. **It actually works in practice for some users.** AI Founder Kit (10-day test, 8.8/10): *"Command Code actually remembers your preference for Vitest over Mocha after just one correction… It effectively eliminates the loop of fixing the same variable naming conventions every morning."* Also: when they deleted a directory structure it created, it didn't attempt that structure again. (aifounderkit.com, 2026-03-31)
3. **Direct user comparison vs. competitors.** A user in the Command Code GitHub issue tracker (quoting their Discord post): *"I know taste works for me because unlike my past experiences with Claude or Cursor and even setting memory or rules i kept stopping it and typing 'no no no don't do that' and honestly I can't remember the last time I had to do that with Command Code + taste."* (github.com/CommandCodeAI/command-code#717, 2026-08-20)
4. **Human-readable, editable, portable artifacts.** The OpenAgents teardown (an independent audit of the shipped npm bundle) calls the separation of four planes — explicit instructions (AGENTS.md), learned preference (taste.md), settings, conversation state — *"Command Code's most important architectural contribution."* It also praises the **compiler boundary**: normal read/write/edit tools are blocked from taste files; a separate learning agent with a narrowed toolset owns them — *"the best implementation choice in the product."* (github.com/OpenAgentsInc/openagents, 2026-07-16)
5. **Team sharing via `npx taste push/pull`.** AI Founder Kit: *"The npx taste push command allows you to ship your coding standards to a team member so your junior devs produce code that looks like yours."* (aifounderkit.com, 2026-03-31)
6. **CLI ergonomics / non-intrusiveness.** Ghazi Fadil (1-week test): *"It's a tool you invoke intentionally… The diff review process builds trust."* (ghazifadil.com, 2026-05-05)
7. **Reduced "AI slop" / correction-loop claims.** Command Code's own blog claims correction loops drop from 4.2 → 0.4 edits on CLI scaffolding after a month (vendor claim, unverified). (commandcode.ai/blog/rules-rot-skills-decay, 2026-05-01)

---

## Ogillar / risker (what users criticize)

1. **"Taste is nothing special" + forced marketing (Reddit).** The most direct critical review (r/opencodeCLI, "My Honest Command Code Review After Few Days of Daily Use", 2026-06-09): *"Their 'taste' is nothing special, it's just a simple memory with…"* and *"Their marketing is very forced too, which gives that feeling of something is…"* (thread truncated by Reddit blocking; snippet from search index). HN launch thread got only 3 points and zero discussion (news.ycombinator.com/item?id=48031887) — low community engagement. Slashdot has **no user reviews at all** (slashdot.org/software/p/Command-Code/, accessed 2026-08-31).
2. **"Local learning" claim is misleading (independent bundle audit).** OpenAgents teardown: *"The security page says Taste learning runs locally… The bundle does store the resulting Markdown locally. It also [sends] prompt batches and compiled learning context to the Command Code generation API."* Conclusion: *"'local learning' cannot honestly be read as 'all derivation happens on the device.'"* Also: **default-on learning is "the wrong default for a system that may inspect private sessions and send material to a hosted derivation model."** (github.com/OpenAgentsInc/openagents, 2026-07-16)
3. **Thin evidence model — confidence without provenance.** Same teardown: the taste.md format records preference text + numeric confidence but *not* observation/session refs, which action produced the signal, derivation model version, timestamps/recency decay, contradictory observations, applicability predicates, owner review state, or activation counts. *"Confidence without evidence and calibration is a persuasive number, not a governed fact."* (2026-07-16)
4. **Advertised-but-missing commands.** `cmd taste learn` (git-history mining) is advertised in docs but absent from the Taste subcommand registry in the audited runtime. (OpenAgents teardown, 2026-07-16)
5. **Windows support was broken silently.** GitHub issue #395 (2026-05-23): on Windows 11 / PowerShell 7, Taste loaded ("TASTE Using your taste packages") but **never saved anything** — empty `taste.md` files, no error message, user only noticed by checking files. Fixed 2026-06-12 ("You can now use Taste on Windows as well"). Lesson: silent learning failure is the worst failure mode. (github.com/CommandCodeAI/command-code#395)
6. **TUI spam / feedback noise.** Issue #717 (2026-08-20): every learned preference prints a "TASTE Learned" row that pushes the transcript up mid-generation; with many learnings it's "kinda annoying." The user's complaint itself got learned as a preference ("Prefers TASTE Learned notifications grouped into a single collapsible chevron… Confidence 92%") — a nice demo of the loop, but also of how noisy signals get captured. (github.com/CommandCodeAI/command-code#717)
7. **Rigidity / over-personalization.** AI Founder Kit: the agent *"occasionally stayed too rigid to its learned rules when we actually wanted a one-off experimental pattern"* — it even questioned intent when deviating from learned taste. (aifounderkit.com, 2026-03-31)
8. **Lock-in risk.** Volanea: *"They can also make switching tools harder if your learned workflow, custom skills, and team habits become deeply tied to one platform."* Mitigation: keep durable guidance in version-controlled files. (volanea.com, 2026-08-15)
9. **Privacy caveats (secondary sources).** Oflight deep dive: *"accept/reject/edit signals may go to Command Code servers; for sensitive projects, verify this carefully."* (oflight.co.jp, 2026-07-11). Command Code's own privacy policy says prompts/attached files/code snippets are transmitted to third-party model providers, retained up to 30 days, and that taste sync uploads structured rules (not source code) when opted in (commandcode.ai/privacy, accessed 2026-08-31). The gap between "local learning" marketing and provider transmission is the recurring complaint.
10. **"taste-1" neuro-symbolic claims are unverifiable marketing.** The founder's own AI Engineer talk describes taste-1 as *"more like a regex of my preferences"* and talks about building "the world's intuition" (ai.engineer, accessed 2026-08-31). The OpenAgents audit could not verify how the hosted API implements taste-1. Oflight: *"'10× faster, 5× fewer bugs' is a vendor claim; independent benchmarks pending."* (2026-07-11)
11. **Learning takes time.** Multiple sources: taste-1's effect "emerges after weeks to months"; "a developer should not expect a meaningful personalization advantage after one small task." (oflight.co.jp; volanea.com)
12. **Pricing/limits friction.** Medium review: "$1 is just the entry fee, not unlimited usage"; heavy users outgrow plans; limited analytics on lowest tier. (medium.com/readers-club, 2026-05-23)

---

## Konkurrent-jämförelse (competitor preference learning + sentiment)

### Cursor — Memories vs Rules
- **Mechanics:** Memories = auto-generated, sentence-sized facts, project-scoped, personal, **not versioned, not shared**; Rules = `.cursor/rules/*.mdc` with frontmatter, versioned in git, shared. (localskills.sh, 2026-07-05)
- **Complaints (extensive):**
  - Memories applied **globally** when users expect project scope — "it's obviously a screw-up" (forum.cursor.com/t/137149, 2025-10-12).
  - **Rules/memories ignored at an unacceptable rate** — "I've got eight memories like that, what is the point?"; rules visible to the AI and ignored; "The 'Automatic' AI chat in Cursor begins to behave when you remind it to follow the rules, which it will then turn into a memory, which it will then ignore." (forum.cursor.com/t/132458, 2025-09-02; t/135079, 2025-09-26)
  - **Phantom rules / confabulation:** the model invents rules that don't exist; "model answers to what rules are you following are not reliable." (forum.cursor.com/t/168764, 2026-08-18)
  - **Stale memory is worse than no memory:** "Memories accumulate silently, and a stale memory is worse than no memory — it keeps steering the agent toward a convention you abandoned months ago." (localskills.sh, 2026-07-05)
  - **Team failure modes:** onboarding blind spot (new hires get none of your memories), silent divergence between engineers, no review/history/rollback for memories. (localskills.sh)

### Claude Code — CLAUDE.md + Auto Memory
- **Mechanics:** CLAUDE.md (user-written, versioned, project/user/org scope) + Auto Memory (Claude-written notes; `MEMORY.md` index capped at 200 lines / 25KB, loaded every session; detail in topic files loaded on demand). (code.claude.com/docs/en/memory, accessed 2026-08-31)
- **Complaints (extensive GitHub issue trail):**
  - **Memory preamble bloat:** ~11–16k tokens of memory preamble load even with `autoMemoryEnabled: false` (issue #63903, 2026-05-30).
  - **Silent truncation:** MEMORY.md over 25KB silently drops the *most recent* (chronologically last) rules — "the truncated portion is the most-recently-added (most-relevant) content" (issue #57574). Related: flat index loses entries at 200-line cap, topic files orphaned (issue #40614).
  - **Index-curation tax:** at heavy scale every memory write forces mid-task hand-trimming of the index ("MEMORY.md went 55 over cap — trimming my own line"); measured MEMORY.md as the strongest predictor of startup context cost (r=+0.76, ~0.44 tokens/byte). (issue #83114)
  - **Auto-memory/compaction race** corrupting context (issue #29175).
  - **Adherence failures:** Opus 4.7 "violates 'ABSOLUTELY NEVER' rules in MEMORY.md" (issues #52382, #56419, #53753).
  - Community fixes: Alzheimer (hierarchical index via hooks), claude-brain (SQLite store), cozempic (bloat pruning) — evidence the built-in system's index management is the pain point.

### Windsurf — Cascade Memories
- **Mechanics:** auto-generated workspace-scoped short notes at `~/.codeium/windsurf/memories/`; rules in `global_rules.md` / `.windsurfrules`. (memorylake.ai, 2026-05-22)
- **Complaints:**
  - **Memories cling to outdated patterns after refactors:** "After I migrated from Redux to Zustand, Cascade kept proposing Redux solutions for three days until I manually edited the memory." (geniusfirms.com, 2026-05-13); SimilarLabs: "After major refactors, Memories occasionally clings to outdated patterns… suggesting the old folder structure." (similarlabs.com, 2026-02-19)
  - **Memories are short notes, not a document store** — per-session context loss, auto-summarization is lossy. (memorylake.ai)
  - **Security:** the `create_memory` tool runs without approval and can be prompt-injected (SpAIware — attacker instructions persist across sessions); CVE-2025-62353 (CVSS 9.8) path traversal; code-snippet telemetry on by default. (ptkd.com, 2026-05-17)

### Aider — CONVENTIONS.md
- **Mechanics:** conventions file must be **manually loaded** (`/read CONVENTIONS.md` or `--read`), read-only, cache-friendly; community convention repo (github.com/Aider-AI/conventions). (aider.chat/docs/usage/conventions.html, accessed 2026-08-31)
- **Sentiment:** no auto-learning — it's the "static rules" baseline that Taste positions against. 2026 guides argue AGENTS.md wins over CONVENTIONS.md for multi-tool repos (thepromptshelf.dev, 2026).

### opencode — AGENTS.md
- **Mechanics:** auto-loaded rules (project root, subdirectories, global `~/.config/opencode/AGENTS.md`); CLAUDE.md as fallback; `instructions` field in opencode.json for modular files. (open-code.ai/docs/rules, accessed 2026-08-31)
- **Complaints:**
  - **Large AGENTS.md consumes the entire context window** → immediate compaction loop; 331KB file = 81% of a 128K window (github.com/anomalyco/opencode#18037).
  - **No expiration mechanism** — "AGENTS.md has no way to say 'this rule no longer applies'… The model treats every line as current truth" (github.com/criterium/opencode-lab, agents_md-danger research).
  - **Attack surface:** anyone who can write to the repo can plant an auto-loading AGENTS.md; global AGENTS.md is always loaded and cannot be disabled except by deletion. (opencode-lab)
  - **Cache misses:** frequent AGENTS.md edits break KV prefix cache (costly on disk-persisted KV models). (opencode-lab)

---

## Byggmönster / best practices (for our preference-learning layer)

### Signal capture
- **Accept/reject/edit as signals is validated** — but the *edit delta* is the most valuable signal ("the delta between what was generated and what you wanted" — commandcode.ai/launch; echoed by Volanea and the OpenAgents teardown).
- **Capture provenance at capture time.** The OpenAgents teardown's core critique of taste.md: no observation refs, no action type, no timestamps, no contradiction handling. A governed design needs: typed observations, evidence refs, first/last-seen timestamps, and the action that produced the signal. (OpenAgents teardown)
- **Never silently fail.** The Windows bug (#395) and Claude Code's silent truncation (#57574) both show silent learning failure destroys trust. Surface write failures and truncation visibly.

### Distillation
- **LLM distillation of preferences is the practical mechanism** (taste.md = distilled rules with confidence), not a trained model. The "neuro-symbolic" framing is marketing; the shipped artifact is markdown + confidence.
- **Research-grade distillation recipes exist:** CodeFavor (Amazon Science) trains code-preference models from synthetic evolution (commits → preference pairs; critiques → revisions); key findings: human preference labeling is expensive (23.4 person-min/task, 15–40% unsolved) and *suboptimal for non-functional objectives* (security: 73.9% ties); strip code comments to avoid LLM self-bias; classification beats generation for correctness. (github.com/amazon-science/llm-code-preference; ar5iv 2410.03837)
- **On-policy data is key** for preference learning (PLUM, arxiv 2406.06887); self-generated tests + minimax selection build reliable preference pairs without annotations (DSTC, arxiv 2411.13611).

### Dedup / decay / confidence
- **Two-pass dedup pattern (proven in the field):** Pass 1 embedding similarity (cheap, frequent, cosine > ~0.9) for literal duplicates; Pass 2 LLM reconciliation (expensive, infrequent) for *assertion equivalence* — "don't merge on similarity alone, merge on assertion equivalence." (letta-ai/letta issue #3116 discussion, 2025-12-22)
- **Never delete raw episodes.** LLM-generated summaries degrade factual accuracy when they rewrite source material; consolidated summaries must point back to episodic sources (provenance trace). (letta issue #3116; mem0.ai blog)
- **Mem0 Dream pattern:** supersede (retire outdated facts), merge (fold duplicates), synthesize (distill recurring signal into pattern memories) — all background, non-destructive, reviewable, with a `latest_only` read flag. (mem0.ai/blog, 2026-08-05)
- **Decay/expiry is a gap everywhere.** AGENTS.md has no expiration mechanism (opencode-lab); Windsurf memories cling to old patterns; Claude Code truncates newest-first. A `valid-until`/recency-decay field is a differentiator.
- **Confidence must be calibrated and evidence-linked** — "Confidence without evidence and calibration is a persuasive number, not a governed fact." (OpenAgents teardown)

### Storage & context injection
- **Human-readable markdown as the portability primitive** — "reviewed, diffed, committed, removed, imported without requiring the original model weights" (OpenAgents teardown). This is the strongest cross-tool pattern (AGENTS.md/CLAUDE.md convergence, dev.to/rulestack 2026-07-15).
- **Index vs. store separation (the #1 Claude Code lesson):** one always-loaded index file doing double duty as routing table + budget target causes the "curation tax." Budget the index, never the store; regenerate the index from fact-file frontmatter rather than hand-appending. (claude-code issue #83114)
- **Size discipline:** CLAUDE.md/AGENTS.md target <200 lines (Claude docs); >400 lines agents start skipping (terminalblog 2026-07-13); opencode's 331KB AGENTS.md broke sessions (#18037). Progressive disclosure: root index + on-demand topic files.
- **Lazy/on-demand loading beats always-on injection** for large rule sets (opencode-lab; opencode issue #1028 task-aware routing).
- **Compiler boundary (steal this):** a dedicated learning agent with a narrowed toolset owns the taste files; normal tools are blocked from editing them; path traversal rejected. (OpenAgents teardown — "best implementation choice in the product")

### Sync / portability
- **Merge semantics matter:** Command Code's `taste push/pull` intelligently merges (new learnings added, changed confidence updated, identical unchanged) with `--overwrite` escape hatch — a good pattern. (commandcode.ai/docs/taste)
- **Scope tiers:** project / personal (global) / remote (team) — matches the AGENTS.md/CLAUDE.md global-vs-project convention and Cursor's memory-vs-rules split.
- **Lock-in mitigation:** keep durable guidance in version-controlled files; learned preferences should be exportable to plain markdown. (volanea.com)

### Trust & safety (from competitor failures)
- **Default-on learning is contested** — OpenAgents calls it "the wrong default" for a system that sends material to hosted derivation. Consider opt-in or a visible, informed-consent flow.
- **Learned preferences must never widen authority** — "A learned preference may influence planning or code review. It must never widen tools, filesystem, execution, spend, publication, or release authority." (OpenAgents teardown)
- **Prompt-injection into memory is a demonstrated attack** (Windsurf `create_memory` SpAIware, CVE-2025-62353). Treat the memory store as secrets-adjacent; review stored entries; allow deletion. (ptkd.com)
- **Human review loop:** Cursor's pending-approval for auto-memories and "audit like a dotfile" guidance (localskills.sh) is the counterweight to full automation.

---

## Verification Receipts (sources)

| # | Source | URL | Accessed | Backs claims |
|---|--------|-----|----------|--------------|
| 1 | OpenAgents teardown of command-code bundle | github.com/OpenAgentsInc/openagents/blob/main/docs/teardowns/2026-07-16-command-code-teardown.md | 2026-08-31 | Local-learning gap, evidence model, compiler boundary, 4-plane separation, default-on critique, authority limits |
| 2 | Command Code Taste docs | commandcode.ai/docs/taste | 2026-08-31 | taste.md format, confidence, push/pull merge, scopes, taste-1 claims |
| 3 | Command Code launch post | commandcode.ai/launch | 2026-08-31 | Signal model, neuro-symbolic claims, "10×/2×/5×" claims |
| 4 | Command Code privacy policy | commandcode.ai/privacy | 2026-08-31 | Provider transmission, 30-day retention, no-training claims |
| 5 | Command Code security docs | commandcode.ai/docs/resources/security | 2026-08-31 | "Taste learning runs locally" claim (contradicted by #1) |
| 6 | GitHub issue #395 (Windows) | github.com/CommandCodeAI/command-code/issues/395 | 2026-08-31 | Windows silent learning failure, fixed 2026-06-12 |
| 7 | GitHub issue #717 (TUI spam) | github.com/CommandCodeAI/command-code/issues/717 | 2026-08-31 | TUI feedback noise; user praise quote vs Cursor/Claude |
| 8 | Reddit r/opencodeCLI review | reddit.com/r/opencodeCLI/comments/1u0vi9b/ | 2026-08-31 (snippet via search; full thread 403-blocked) | "Taste is nothing special", "marketing is very forced" |
| 9 | HN launch thread | news.ycombinator.com/item?id=48031887 | 2026-08-31 | 3 points, no discussion |
| 10 | Slashdot Command Code page | slashdot.org/software/p/Command-Code/ | 2026-08-31 | Zero user reviews |
| 11 | AI Founder Kit review | aifounderkit.com/ai-tools/command-code-ai-coding-agent/ | 2026-08-31 | Vitest learning, rigidity, lock-in, readable files |
| 12 | Volanea GOAT plan review | volanea.com/blog/command-code-goat-plan-review | 2026-08-31 | Taste value, lock-in risk, ramp-up caveat |
| 13 | Oflight deep dive | oflight.co.jp/en/columns/commandcode-taste-1-personalized-coding-agent-2026-07 | 2026-08-31 | Privacy caveats, unverified claims, learning time, team collisions |
| 14 | Medium review | medium.com/readers-club/command-code-ai-review-2026-d8172fa1f96c | 2026-08-31 | Pricing friction, taste takes time |
| 15 | Ghazi Fadil blog | ghazifadil.com/blog/commandcode-ai-the-cli-coding-assistant-that-gets-out-of-your-way | 2026-08-31 | CLI ergonomics praise |
| 16 | Founder talk (AI Engineer) | ai.engineer/talks/developing-taste-in-coding-agents-applied-meta-neuro-symbolic-rl-ahmad-awais-command-code | 2026-08-31 | "regex of my preferences", marketing register |
| 17 | Command Code blog "Rules Rot" | commandcode.ai/blog/rules-rot-skills-decay | 2026-08-31 | Vendor benchmark claims (4.2→0.4 edits) |
| 18 | Cursor forum: memories global bug | forum.cursor.com/t/rules-vs-memories-and-global-vs-project/137149 | 2026-08-31 | Cursor memory scope complaints |
| 19 | Cursor forum: rules ignored | forum.cursor.com/t/cursor-does-not-respect-rules/132458; t/how-to-get-rules-memories-to-actually-work/135079 | 2026-08-31 | Cursor rule-following failures |
| 20 | Cursor forum: phantom rules | forum.cursor.com/t/user-rules-docs-are-not-explicit-ai-agent-misinterpretsthem/168764 | 2026-08-31 | Confabulated rules |
| 21 | localskills.sh Cursor Memories guide | localskills.sh/blog/cursor-memories-guide | 2026-08-31 | Memories vs rules matrix, stale-memory warning, team caveats |
| 22 | Claude Code memory docs | code.claude.com/docs/en/memory | 2026-08-31 | CLAUDE.md + auto memory mechanics, 200-line/25KB cap |
| 23 | Claude Code issues: preamble bloat | github.com/anthropics/claude-code/issues/63903 | 2026-08-31 | 11–16k token preamble even when disabled |
| 24 | Claude Code issues: truncation | github.com/anthropics/claude-code/issues/57574; #40614 | 2026-08-31 | Silent newest-first truncation, orphaned topic files |
| 25 | Claude Code issues: curation tax | github.com/anthropics/claude-code/issues/83114 | 2026-08-31 | Index budget mechanics, 0.44 tokens/byte, r=+0.76 |
| 26 | Claude Code issues: compaction race | github.com/anthropics/claude-code/issues/29175 | 2026-08-31 | Auto-memory/compaction corruption |
| 27 | Windsurf reviews | similarlabs.com/blog/windsurf-review; geniusfirms.com/blog/windsurf-in-real-workflows-my-3-month-experience | 2026-08-31 | Memories cling to old patterns |
| 28 | Windsurf memory/security | memorylake.ai/en/blogs/windsurf-forgets-cascade-context; ptkd.com/journal/does-windsurf-cascade-leak-api-keys-in-the-prompt-history | 2026-08-31 | Short-note limits; create_memory injection, CVE-2025-62353 |
| 29 | Aider conventions docs | aider.chat/docs/usage/conventions.html; github.com/Aider-AI/conventions | 2026-08-31 | Manual-load conventions pattern |
| 30 | opencode AGENTS.md issues | github.com/anomalyco/opencode/issues/18037; #1028 | 2026-08-31 | Context-window blowup, task-aware routing |
| 31 | opencode-lab AGENTS.md research | github.com/criterium/opencode-lab/blob/main/research/agents_md-danger/README.md | 2026-08-31 | No-expiry, attack surface, cache misses, global always-loaded |
| 32 | AGENTS.md guides | dev.to/rulestack/agentsmd-how-to-write-the-one-rules-file-most-coding-agents-now-read-1p21; terminalblog.com/blog/agents-md-complete-guide | 2026-08-31 | 200–400 line discipline, Reason: lines, canary rule, progressive disclosure |
| 33 | CodeFavor (Amazon Science) | github.com/amazon-science/llm-code-preference; ar5iv.labs.arxiv.org/html/2410.03837 | 2026-08-31 | Synthetic-evolution distillation, human-label cost, self-bias |
| 34 | PLUM / DSTC papers | arxiv.org/html/2406.06887v2; arxiv.org/html/2411.13611 | 2026-08-31 | On-policy preference learning, self-generated tests |
| 35 | Mem0 (incl. Dream) | github.com/mem0ai/mem0; mem0.ai/blog/stale-ai-agent-memory-and-how-mem0-dream-fixes-it | 2026-08-31 | Supersede/merge/synthesize, latest_only, non-destructive |
| 36 | Letta/MemGPT | github.com/letta-ai/letta; github.com/letta-ai/letta/issues/3116; letta.com/blog/agent-memory | 2026-08-31 | Hierarchical memory, sleep-time consolidation, two-pass dedup, provenance |

**Double-sourced critical claims:**
- *Taste = accept/reject/edit → confidence-scored taste.md:* sources 2, 3, 11, 13, 1.
- *"Local learning" vs. cloud derivation gap:* sources 1, 5, 4, 13.
- *Marketing skepticism / unverified taste-1 claims:* sources 8, 9, 1, 13, 16.
- *Stale/wrong learned rules are the dominant competitor failure:* sources 21, 24, 25, 27, 31.

---

## Blockers / Inte gjort

- **Reddit thread content incomplete.** The critical r/opencodeCLI review (source 8) is 403-blocked for direct fetch (Reddit + r.jina.ai + redlib all blocked). Only the search-index snippet is citable: "Their 'taste' is nothing special, it's just a simple memory with…" and "Their marketing is very forced too…". Full thread text could not be verified.
- **No independent benchmark** of Command Code's performance claims exists (confirmed by sources 13, 1). "10× faster / 2× reviews / 5× fewer bugs" and the 4.2→0.4 correction-loop numbers are vendor-only.
- **taste-1 internals unverifiable.** The hosted API's implementation of taste-1 could not be audited (source 1 explicitly states this limitation); the shipped client is closed-source (`UNLICENSED`).
- **X/Twitter sentiment** not systematically captured (no reliable archive access); YouTube reviews referenced by Volanea (source 12) but not independently fetched.
- **Pricing figures conflict across sources** (AI Founder Kit lists Pro $15/mo with 250 premium requests; Oflight/Medium list $1/mo Pro entry; Volanea lists $10 GOAT). Pricing appears to have changed over 2026; treat specific numbers as time-stamped, not current.