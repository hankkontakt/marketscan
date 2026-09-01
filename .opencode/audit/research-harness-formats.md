# Research: Session-log storage formats & MCP/memory integration points per AI coding harness (Windows-focused)

**Date:** 2026-08-31
**Purpose:** Feed adapter design for a universal "taste/memory" CLI + MCP server that mines agent session logs and injects learned preferences back into each harness.
**Scope:** opencode, Claude Code, Google Antigravity (CLI), Codex CLI, Gemini CLI, Cursor CLI.

---

## Task Report (direct answers)

| Harness | Session log location (Windows) | Format | MCP config | Can we observe tool calls / accept-reject? | Memory injection point |
|---|---|---|---|---|---|
| **opencode** | `%USERPROFILE%\.local\share\opencode\` (SQLite `opencode.db` + legacy `storage/` JSON) | SQLite (tables `session`, `message`, `part`) + legacy per-message JSON | `opencode.json` → `mcp` key (JSON) | **Yes** — plugin events `tool.execute.before/after`, `permission.asked/replied` | Plugin hooks + AGENTS.md-style project files |
| **Claude Code** | `%USERPROFILE%\.claude\projects\<encoded-path>\<session-uuid>.jsonl` | JSONL, one event object per line | `.mcp.json` (project) / `~/.claude.json` (local+user); `claude mcp add` | **Yes** — hooks `PreToolUse`, `PostToolUse`, `PermissionRequest`, `PermissionDenied`, `Stop` | `CLAUDE.md` scopes + auto-memory `~/.claude/projects/<path>/memory/` |
| **Antigravity CLI (`agy`)** | `%USERPROFILE%\.gemini\antigravity-cli\brain\<conv-id>\.system_generated\logs\transcript.jsonl` (+ `transcript_full.jsonl`) | JSONL transcripts; `history.jsonl` index; `conversations/` protobuf | `~/.gemini/config/mcp_config.json` (global), `.agents/mcp_config.json` (workspace) | **Yes** — plugin `hooks.json` (pre/post tool event hooks) | `~/.gemini/GEMINI.md`, `~/.gemini/config/AGENTS.md`, workspace `GEMINI.md`/`AGENTS.md`, `.agents/rules/` |
| **Codex CLI** | `%USERPROFILE%\.codex\sessions\YYYY\MM\DD\rollout-<ts>-<uuid>.jsonl` (`.zst` when cold) | JSONL "rollout" (types: `session_meta`, `turn_context`, `response_item`, `event_msg`, `compacted`) | `~/.codex/config.toml` → `[mcp_servers.<name>]` (TOML); `codex mcp add` | **Partial** — rollout records tool calls + approval decisions; no hook API documented | `~/.codex/AGENTS.md` (global), project `AGENTS.md` |
| **Gemini CLI** | `%USERPROFILE%\.gemini\tmp\<project_hash>\chats\` | Format **not verified** (official docs don't state it) | `settings.json` → `mcpServers` (JSON); `gemini mcp add` | **No** — no hook/plugin API documented | Hierarchical `GEMINI.md` (global `~/.gemini/GEMINI.md`, project, subdirs) + Memory tool |
| **Cursor CLI** | `%USERPROFILE%\.cursor\chats\<projectId>\<chatId>\store.db` (SQLite) + `%USERPROFILE%\.cursor\projects\<encoded>\agent-transcripts\**\*.jsonl` | SQLite (`blobs`, `meta` tables) + JSONL transcripts | `~/.cursor/mcp.json` (per agentcmd doc); IDE: Cursor Settings → MCP | **Partial** — JSONL transcripts contain tool calls; no hook API documented | `.cursor/rules/*.mdc` (YAML-frontmatter markdown), `AGENTS.md`, legacy `.cursorrules` |

**Bottom line for the adapter design:** the two richest, most machine-readable targets are **Claude Code** (JSONL transcripts + hook events + auto-memory) and **opencode** (SQLite + plugin event hooks). Antigravity CLI and Codex CLI are also JSONL-based and directly parseable. Gemini CLI and Cursor CLI are weaker: Gemini's chat format is undocumented, and Cursor's CLI storage is SQLite + JSONL but with no event/hook surface.

---

## 1. opencode

### Storage path
- **Windows:** `%USERPROFILE%\.local\share\opencode\` (official docs: "Press WIN+R and paste `%USERPROFILE%\.local\share\opencode\log`" for logs; data root is `%USERPROFILE%\.local\share\opencode`). [opencode.ai/docs/troubleshooting]
- **macOS/Linux:** `~/.local/share/opencode/`.
- Directory contents: `auth.json`, `log/`, `project/` — project-specific session/message data. If the project is in a Git repo → `./<project-slug>/storage/`; if not → `./global/storage/`. [opencode.ai/docs/troubleshooting]
- **⚠ Discrepancy:** the community tool `opencode-export` claims the DB is at `%LOCALAPPDATA%\opencode\opencode.db` on Windows. This contradicts the official docs and a real Windows bug report (issue #29855) showing `%USERPROFILE%\.local\share\opencode\opencode.db` (~627 MB). Treat `%LOCALAPPDATA%` claim as unverified/outdated. [github.com/ZelinZhou-THU/opencode-export; github.com/anomalyco/opencode/issues/29855]

### Format
- **Primary (current):** SQLite database `opencode.db` with tables `session`, `message` (JSON blobs in `data` column), and `part` (activity stream: tool + text rows, JSON in `data`). [agentarchaeology.ai/field-guide/session-stores; github.com/anomalyco/opencode/issues/29855]
- **Legacy (pre-SQLite migration):** per-message JSON files under `storage/message/<sessionId>/*.json`, parts under `storage/part/<messageId>/*.json`, session metadata under `storage/session/<projectHash>/<sessionId>.json`. Tool calls use `tool_name` + `arguments`. Dropped when SQLite is present. [agentarchaeology.ai; github.com/catlog22/Claude-Code-Workflow ccw parser]
- Sample legacy session JSON shape (from parser): `{ id, projectID, directory, title, time: { created, updated } }`; message: `{ id, sessionID, role, modelID, tokens: {input, output, total}, time: {created} }`. [github.com/catlog22/Claude-Code-Workflow]

### MCP config (exact JSON shape, `opencode.json`)
```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "my-local-mcp-server": {
      "type": "local",
      "command": ["npx", "-y", "my-mcp-command"],   // array, not string+args
      "enabled": true,
      "environment": { "MY_ENV_VAR": "value" },      // optional
      "cwd": "./server-directory",                   // optional
      "timeout": 5000                                // optional, ms, default 5000
    },
    "my-remote-mcp": {
      "type": "remote",
      "url": "https://my-mcp-server.com",
      "enabled": true,
      "headers": { "Authorization": "Bearer {env:GITHUB_TOKEN}" }  // {env:VAR} interpolation
    }
  }
}
```
Source: official docs mcp-servers.mdx + config schema (`packages/core/src/v1/config/mcp.ts`). [github.com/anomalyco/opencode docs; opencode.ai/docs/plugins]

### Plugin API (events/hooks — YES, tool calls + permission accept/reject observable)
Plugins are JS/TS modules exporting plugin functions that return a hooks object. Event list includes:
- **Tool events:** `tool.execute.before`, `tool.execute.after`
- **Permission events:** `permission.asked`, `permission.replied` ← accept/reject capture
- Session: `session.created/updated/compacted/deleted/diff/error/idle/status`; Message: `message.updated/removed`, `message.part.updated/removed`; plus `command.executed`, `file.edited`, `todo.updated`, etc.
- Example: `.env`-protection plugin intercepts `tool.execute.before` and throws when `input.tool === "read"` on `.env`. [opencode.ai/docs/plugins]

### Memory/rules injection
- Project context files (AGENTS.md-style) are read by the agent; plugins can also inject via hooks. Not a first-class "memory file" system like Claude Code — injection is via plugin hooks or project instruction files. (Not deeply verified beyond plugin docs.)

---

## 2. Claude Code

### Storage path
- **Windows:** `%USERPROFILE%\.claude\projects\<encoded-path>\<session-uuid>.jsonl` (project path URL-encoded into folder name, e.g. `C:\Users\you\code\my-app` → `C-Users-you-code-my-app`). [claude-dev.tools/docs/jsonl-format]
- **macOS/Linux:** `~/.claude/projects/<encoded-path>/<session-id>.jsonl`. One file per session, append-only.

### Format (JSONL, per-line shape)
Every line is one JSON object with top-level fields: `type` (`user`/`assistant`/`system`/…), `uuid`, `parentUuid`, `timestamp` (ISO 8601), `sessionId`, `cwd`, `gitBranch`, `version`.
- `type: "user"` → `message.content` is a string (prompt) or array of content blocks; **tool results arrive as `tool_result` blocks referencing `tool_use_id`**.
- `type: "assistant"` → `message.content` array of `text` / `thinking` / `tool_use` blocks; `tool_use` has `id`, `name` (Read, Edit, Bash, Grep, Task…), `input` object; `message.usage` has `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`.
- Also: compaction boundaries, summary insertions, hook output, file snapshots, subagent coordination. [claude-dev.tools/docs/jsonl-format]

### MCP config
- **Project scope:** `.mcp.json` at repo root, committed:
```json
{
  "mcpServers": {
    "claude-code-docs": { "type": "http", "url": "https://code.claude.com/docs/mcp" },
    "playwright": { "type": "stdio", "command": "npx", "args": ["-y", "@playwright/mcp@latest"] }
  }
}
```
- **Scopes:** `local` (default) → `~/.claude.json` under the project's entry; `project` → `.mcp.json`; `user` → `~/.claude.json` top-level `mcpServers`. On Windows `~/.claude.json` = `%USERPROFILE%\.claude.json` (or `$CLAUDE_CONFIG_DIR`). [code.claude.com/docs/en/mcp-servers]
- **CLI:** `claude mcp add [--transport http|stdio] [--scope local|project|user] <name> -- <cmd> [args]`; `claude mcp add-json <name> '<json>'`. **Windows note:** `claude mcp add-json` (or hand-editing JSON) is the safest path on Windows — the CLI form has a shell-quoting bug where `--` rewrites `/c` to `C:/` (anthropics/claude-code #4019). Also: Claude Code spawns via `CreateProcess` which doesn't resolve `.cmd` shims — wrap `npx` as `"command": "cmd", "args": ["/c", "npx", ...]`. [maketocreate.com; code.claude.com/docs/en/mcp-servers]

### Hooks (YES — accept/reject/edit events capturable)
Configured in `settings.json` (`~/.claude/settings.json`, `.claude/settings.json`) under `hooks` key, or via Agent SDK callbacks. Events relevant to taste/memory mining:
- `PreToolUse` — before tool executes; **can block** via `hookSpecificOutput.permissionDecision` (`allow`/`deny`/`ask`/`defer`) + `permissionDecisionReason`. Fires before permission-mode checks, even in bypass mode.
- `PostToolUse` / `PostToolUseFailure` — after tool success/failure (tool already ran; can't undo).
- `PermissionRequest` — when a permission dialog is about to appear.
- `PermissionDenied` — when auto mode denies a tool call.
- `Stop` / `SubagentStop` — end of turn; can `decision: "block"` with reason.
- Also `SessionStart/End`, `UserPromptSubmit`, `PostToolBatch`, `FileChanged`, `InstructionsLoaded`, etc.
- Hook types: `command`, `http`, `mcp_tool`, `prompt`, `agent`. Matchers filter by tool name (e.g. `Bash`, `Edit|Write`, `mcp__.*`). [code.claude.com/docs/en/hooks; code.claude.com/docs/en/hooks-guide]

### Memory files
- **CLAUDE.md scopes** (load order broadest→most specific): managed policy (Windows: `C:\Program Files\ClaudeCode\CLAUDE.md`; macOS `/Library/Application Support/ClaudeCode/CLAUDE.md`; Linux `/etc/claude-code/CLAUDE.md`), user `~/.claude/CLAUDE.md`, project `./CLAUDE.md` or `./.claude/CLAUDE.md`, local `./CLAUDE.local.md` (gitignored). Rules: `.claude/rules/*.md` with optional `paths` YAML frontmatter (glob-scoped). [code.claude.com/docs/en/memory]
- **Auto memory:** per-project dir `~/.claude/projects/<encoded-path>/memory/` containing `MEMORY.md` index + topic files; frontmatter `type` ∈ `user` | `feedback` | `project` | `reference`. First 200 lines / 25 KB of `MEMORY.md` loaded each session. Toggle: `autoMemoryEnabled` in settings; relocate via `autoMemoryDirectory`. [code.claude.com/docs/en/memory]

---

## 3. Google Antigravity (CLI = `agy`)

### CLI existence
- **Yes, a CLI exists** (`agy`), built in Go, replacing Gemini CLI; shares the agent harness with Antigravity 2.0 and the IDE. Runs natively on macOS, Linux, Windows; Windows binary installed to `C:\Users\<user>\AppData\Local\agy\bin`. [antigravity.google/docs/cli/install; medium.com/google-cloud]

### Storage path (Windows + unix)
- **Windows (verified):** `%USERPROFILE%\.gemini\antigravity-cli\brain\` — machine-verified for agy 1.0.3 and 1.1.0 on Windows; same root on macOS 1.0.7. Linux 1.0.2 reported at `~/.antigravity-cli/brain`. [github.com/arcobaleno64/gemini-plugin-cc agy-transcript.mjs]
- The `.gemini` folder is **hardcoded** to `C:\Users\<username>\.gemini` on Windows — ignores `GEMINI_CLI_HOME`/`GEMINI_HOME` env vars. [stackoverflow.com/questions/79944245]
- Per-conversation layout: `~/.gemini/antigravity-cli/brain/<conversation-uuid>/.system_generated/logs/transcript.jsonl` (truncated) + `transcript_full.jsonl` (untruncated); plus `implementation_plan.md`, `task.md`, `walkthrough.md` artifacts and `scratch/`. A `history.jsonl` index sits in `~/.gemini/antigravity-cli/`; a `conversations/` folder holds protobuf-format data. [medium.com/google-cloud Antigravity CLI tutorial; github.com/arcobaleno64/gemini-plugin-cc]
- IDE (Antigravity app) on Windows stores brain logs under `%USERPROFILE%\.gemini\antigravity\…` (conversations in AES-GCM-encrypted `.pb` files — not parseable). [discuss.ai.google.dev forum]

### MCP config
- **Global:** `~/.gemini/config/mcp_config.json` (post-migration; legacy `~/.gemini/antigravity-cli/mcp_config.json`). **Workspace:** `.agents/mcp_config.json`. Format: single `mcpServers` object; keys per server: `command`, `args`, `env`, `cwd`, `headers`, `authProviderType` (`google_credentials`), `oauth` (`clientId`/`clientSecret`), `disabled`, `disabledTools`; remote servers use `serverUrl` (not legacy `url`/`httpUrl`). [antigravity.google/docs/cli/mcp; antigravity.google/docs/cli/gcli-migration]
- **⚠ Caveat:** GitHub issue #60 documents that project-local `.antigravitycli/mcp_config.json` is read but ignored; `.agents/mcp_config.json` worked as a workaround on 1.0.3 but reportedly regressed on 1.1.3. HOME-level config is authoritative. [github.com/google-antigravity/antigravity-cli/issues/60]

### Hooks / plugins
- Plugins are bundles (`plugin.json` + optional `mcp_config.json`, **`hooks.json` (pre/post tool event hooks)**, `skills/`, `agents/`, `rules/`) staged at `~/.gemini/antigravity-cli/plugins/<name>/`. So yes — event hooks exist for observing tool calls. [antigravity.google/docs/cli/features; antigravity.google/docs/cli/plugins]

### Rules / memory
- Global rules: `~/.gemini/GEMINI.md` (applied across all workspaces). Workspace rules: `.agents/rules/` (backward compat `.agent/rules/`). Rule activation modes: Manual / Always On / Model Decision / Glob. [antigravity.google/docs/rules-workflows]
- `AGENTS.md` supported natively since v1.20.3 (March 2026); precedence: GEMINI.md > AGENTS.md > `.agent/rules/`. Global customizations root is `~/.gemini/config/` — `~/.gemini/config/AGENTS.md` is loaded automatically. [agentpedia.codes; different.com]
- CLI best practices: create `GEMINI.md` or `AGENTS.md` at workspace root; settings at `~/.gemini/antigravity-cli/settings.json`. [antigravity.google/docs/cli/best-practices]

---

## 4. Codex CLI (OpenAI)

### Storage path
- **Windows:** `%USERPROFILE%\.codex\sessions\YYYY\MM\DD\rollout-<ISO8601-ts>-<uuid>.jsonl` (root `~/.codex/sessions`, or `$CODEX_HOME/sessions` when `CODEX_HOME` is set). Date-sharded by session start time. [github.com/openai/codex recorder.rs; docs.rs txcript codex.md]
- Cold (old) rollouts are compressed with Zstandard → `.jsonl.zst`; materialized back to plain JSONL on resume/append. [deepwiki.com/openai/codex rollout-persistence]

### Format (JSONL "rollout")
Each line: `{"timestamp", "type", "payload"}`. Record types:
- `session_meta` — id, cwd, timestamp, cli_version, model_provider, source (cli vs subagent), parent_thread_id
- `turn_context` — per-turn model/approval/sandbox snapshot
- `response_item` — protocol log: `message` (role/content), `function_call` (name, arguments, call_id), `function_call_output`, `custom_tool_call`, `reasoning`
- `event_msg` — display log: `user_message`, `agent_message`, `item_completed`, `patch_apply_end` (file changes), `task_complete`, `turn_aborted`, `token_count`
- `compacted` — compaction summaries
Sub-agents are separate rollout files in the same tree. SQLite stores in `~/.codex/` (`state_*.sqlite`, `logs_2.sqlite`, `memories_1.sqlite`, `goals_1.sqlite`) are caches/indexes, **not** the conversation source of truth. [github.com/neochoon/agenthud codex-session.md; codex.danielvaughan.com; github.com/daymade/claude-code-skills]

### MCP config
- **TOML, not JSON:** `~/.codex/config.toml` (user) or `.codex/config.toml` (project, trusted projects only). Table key is `[mcp_servers.<name>]` (snake_case — `mcpServers`/`mcp.servers` are silently ignored). [learn.chatgpt.com/docs/extend/mcp; policylayer.com]
```toml
[mcp_servers.context7]
command = "npx"
args = ["-y", "@upstash/context7-mcp"]
env_vars = ["LOCAL_TOKEN"]

[mcp_servers.figma]
url = "https://mcp.figma.com/mcp"
bearer_token_env_var = "FIGMA_OAUTH_TOKEN"
http_headers = { "X-Figma-Region" = "us-east-1" }
```
- CLI: `codex mcp add <name> -- <cmd>` (stdio) / `codex mcp add <name> --url <URL>` (streamable HTTP); `codex mcp list/get/remove`. Keys: `command`, `args`, `env`, `env_vars`, `cwd`, `url`, `auth`, `bearer_token_env_var`, `http_headers`, `enabled`, `required`, `startup_timeout_sec`, `tool_timeout_sec`, `enabled_tools`/`disabled_tools`, per-tool `approval_mode`. [developers.openai.com/codex/config-reference; learn.chatgpt.com/docs/extend/mcp]

### Hooks / capture
- **No hook API documented.** Rollout files do record tool calls (`function_call`/`custom_tool_call`) and approval decisions (turn_context approval policy), so mining is possible from the JSONL directly. [docs.rs txcript codex.md]

### Memory
- `AGENTS.md` standing instructions (global `~/.codex/AGENTS.md`, project root), re-injected into rollouts; `~/.codex/skills/`. [different.com; github.com/daymade/claude-code-skills]

---

## 5. Gemini CLI

### Storage path
- **Windows:** `%USERPROFILE%\.gemini\tmp\<project_hash>\chats\` (project hash derived from project root path). **macOS/Linux:** `~/.gemini/tmp/<project_hash>/chats/`. Shell history at `~/.gemini/tmp/<project_hash>/shell_history`. [github.com/google-gemini/gemini-cli docs/cli/session-management.md; geminicli.com/docs/cli/session-management]
- Retention configurable via `settings.json` (`enabled`, `maxAge` default `30d`, `maxCount`, `minRetention` default `1d`). [geminicli.com/docs/cli/session-management]

### Format
- **Not verified.** Official docs state what is saved (prompts, responses, tool executions in/out, token usage, reasoning summaries) but not the on-disk file format. Community sources describe the `~/.gemini/` tree but not the chat file encoding. → Treat as unverified; inspect a live `chats/` dir before building the adapter.

### MCP config
- `settings.json` (`~/.gemini/settings.json` user, `.gemini/settings.json` project) → top-level `mcpServers` object; `mcp` object for global settings. Server keys: `command`, `args`, `env` (supports `$VAR`/`${VAR}`/`%VAR%` on Windows), `cwd`, `url` (SSE), `httpUrl` (streamable HTTP), `headers`, `timeout`, `trust`. Tools prefixed `mcp_<serverAlias>_<tool>`. CLI: `gemini mcp add/remove/list/enable/disable` with `-s/--scope`. Enablement state in `~/.gemini/mcp-server-enablement.json`. [github.com/google-gemini/gemini-cli docs/tools/mcp-server.md + docs/reference/configuration.md]
- ⚠ Avoid underscores in server aliases (FQN parsing). [github.com/google-gemini/gemini-cli configuration.md]

### Hooks / capture
- **No hook/plugin event API documented** (extensions exist but are prompt/tool bundles, not lifecycle hooks). Mining must be done from session files.

### Memory
- Hierarchical `GEMINI.md` context: global `~/.gemini/GEMINI.md`, project root + ancestor dirs, sub-directories (≤200 dirs). `/memory show|refresh|list`. Memory tool persists facts by editing markdown files (project `GEMINI.md`, private per-project memory folder, global `~/.gemini/GEMINI.md`). [github.com/google-gemini/gemini-cli docs/tools/memory.md + configuration.md]

---

## 6. Cursor CLI

### Storage path (Windows + unix)
- **CLI (`cursor-agent`):** `~/.cursor/chats/<projectId>/<chatId>/store.db` (SQLite; `blobs` + `meta` tables, meta JSON hex-encoded) + optional `meta.json`; transcripts at `~/.cursor/projects/<encoded-path>/agent-transcripts/**/*.jsonl` (readable JSONL with role/message/tool calls). On Windows `~/.cursor` = `%USERPROFILE%\.cursor`. Overrides: `CURSOR_CONFIG_DIR` (deja-vu) / `CURSOR_AGENT_HOME` (tokenuse). [github.com/jnarowski/agentcmd; github.com/S2thend/cursor-history#31; vshulcz.github.io/deja-vu/registry/cursor.html; tokenuse.app]
- **IDE:** `%APPDATA%\Cursor\User\globalStorage\state.vscdb` (Windows) / `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb` (macOS) / `~/.config/Cursor/User/globalStorage/state.vscdb` (Linux); conversation content in `cursorDiskKV` table (`bubbleId:{composerId}:{bubbleId}` keys), central index `composer.composerHeaders` (Cursor 3.0+). [tokenuse.app; github.com/Callum-Ward/cursaves]
- ⚠ Note: one community tool reports agent-CLI storage as "Linux only", but Windows-hosted/WSL setups demonstrably write `~/.cursor/chats/` + `agent-transcripts/` (GitHub issue #31). [github.com/iksnae/cursor-session; github.com/S2thend/cursor-history#31]

### Format
- SQLite `store.db` (binary blobs — needs `better-sqlite3`/sqlite3 decoding) + JSONL transcripts under `agent-transcripts/` (the JSONL is the practical mining target; one maintainer: "treat store.db as metadata and the JSONL files as message truth"). [github.com/S2thend/cursor-history#31; github.com/jnarowski/agentcmd]

### MCP config
- CLI: `~/.cursor/mcp.json` (per agentcmd doc); CLI config `~/.cursor/cli-config.json`. IDE: Cursor Settings → Tools & MCP (GUI-managed). [github.com/jnarowski/agentcmd; cursor.com/docs/mcp]

### Hooks / capture
- **No hook API documented.** Mining from JSONL transcripts only.

### Rules / memory
- Modern format: `.cursor/rules/*.mdc` — markdown with YAML frontmatter (Project/Team/User rules); legacy `.cursorrules` still works; `AGENTS.md` supported. [cursor.com/docs/rules; deployhq.com/guides/cursor]

---

## Verification Receipts (sources)

| # | Source (URL) | Accessed | Backs claims |
|---|---|---|---|
| 1 | https://opencode.ai/docs/troubleshooting/ | 2026-08-31 | opencode Windows path `%USERPROFILE%\.local\share\opencode`, dir contents, project/global storage split |
| 2 | https://github.com/anomalyco/opencode/issues/29855 | 2026-08-31 | opencode.db at `%USERPROFILE%\.local\share\opencode\opencode.db` on Windows; legacy storage/ dirs |
| 3 | https://agentarchaeology.ai/field-guide/session-stores/ | 2026-08-31 | opencode SQLite schema (part/message tables), legacy JSON format |
| 4 | https://github.com/catlog22/Claude-Code-Workflow (ccw opencode-session-parser.ts) | 2026-08-31 | opencode legacy session/message/part JSON shapes |
| 5 | https://github.com/ZelinZhou-THU/opencode-export | 2026-08-31 | (contradicting) `%LOCALAPPDATA%\opencode\opencode.db` claim — flagged |
| 6 | https://opencode.ai/docs/plugins | 2026-08-31 | opencode plugin events incl. tool.execute.before/after, permission.asked/replied |
| 7 | https://github.com/anomalyco/opencode (docs mcp-servers.mdx, config/mcp.ts) via Context7 | 2026-08-31 | opencode MCP JSON shape (local/remote, command array, {env:VAR}) |
| 8 | https://claude-dev.tools/docs/jsonl-format | 2026-08-31 | Claude Code JSONL layout, per-line fields, tool_use/tool_result, Windows path |
| 9 | https://code.claude.com/docs/en/hooks | 2026-08-31 | Claude Code hook events incl. PreToolUse/PermissionRequest/PermissionDenied/Stop, decision fields |
| 10 | https://code.claude.com/docs/en/hooks-guide | 2026-08-31 | Hook matchers, permissionDecision semantics, hook types |
| 11 | https://code.claude.com/docs/en/mcp-servers | 2026-08-31 | .mcp.json shape, scopes, claude mcp add/add-json, Windows `~/.claude.json` |
| 12 | https://code.claude.com/docs/en/memory | 2026-08-31 | CLAUDE.md scopes (incl. Windows managed path), auto-memory dir + MEMORY.md |
| 13 | https://maketocreate.com/claude-code-mcp-server-configuration-2026-setup-guide/ | 2026-08-31 | Windows CreateProcess/.cmd shim issue, #4019 quoting bug |
| 14 | https://antigravity.google/docs/cli/mcp/ | 2026-08-31 | Antigravity MCP config paths + mcpServers schema |
| 15 | https://antigravity.google/docs/cli/gcli-migration/ | 2026-08-31 | Antigravity CLI replaces Gemini CLI; GEMINI.md/AGENTS.md context; serverUrl key |
| 16 | https://medium.com/google-cloud/antigravity-cli-tutorial-series-part-2 (Romin Irani) | 2026-08-31 | brain/ layout, transcript.jsonl + transcript_full.jsonl, history.jsonl, conversations/ protobuf |
| 17 | https://github.com/arcobaleno64/gemini-plugin-cc (agy-transcript.mjs) | 2026-08-31 | Windows/macOS brain root `~/.gemini/antigravity-cli/brain` machine-verified |
| 18 | https://stackoverflow.com/questions/79944245 | 2026-08-31 | Windows `.gemini` hardcoded to `C:\Users\<user>\.gemini` |
| 19 | https://github.com/google-antigravity/antigravity-cli/issues/60 | 2026-08-31 | Project-local MCP config caveats (`.agents/` vs `.antigravitycli/`) |
| 20 | https://antigravity.google/docs/rules-workflows/ | 2026-08-31 | Global rules `~/.gemini/GEMINI.md`, workspace `.agents/rules/`, activation modes |
| 21 | https://antigravity.google/docs/cli/features + /cli/plugins/ | 2026-08-31 | Plugin bundle layout incl. hooks.json, skills, rules |
| 22 | https://agentpedia.codes/blog/antigravity-agents-md-guide | 2026-08-31 | AGENTS.md support since v1.20.3, precedence GEMINI.md > AGENTS.md |
| 23 | https://different.com/posts/gemini-cli-to-antigravity/ | 2026-08-31 | `~/.gemini/config/AGENTS.md` global customizations root |
| 24 | https://github.com/openai/codex (codex-rs/rollout/src/recorder.rs) | 2026-08-31 | Codex rollout JSONL path `~/.codex/sessions/YYYY/MM/DD/`, filename pattern |
| 25 | https://deepwiki.com/openai/codex/3.5.2-rollout-persistence-and-replay | 2026-08-31 | .zst compression, SQLite index, resume materialization |
| 26 | https://docs.rs/crate/txcript/latest/source/docs/formats/codex.md | 2026-08-31 | Rollout record types (session_meta/turn_context/response_item/event_msg/compacted) |
| 27 | https://github.com/neochoon/agenthud (codex-session.md) | 2026-08-31 | Sub-agent rollout files, SQLite stores are caches not source of truth |
| 28 | https://learn.chatgpt.com/docs/extend/mcp | 2026-08-31 | Codex `[mcp_servers.<name>]` TOML format, codex mcp add, OAuth |
| 29 | https://developers.openai.com/codex/config-reference | 2026-08-31 | Codex config.toml keys, project-scoped .codex/config.toml |
| 30 | https://github.com/google-gemini/gemini-cli (docs/cli/session-management.md, docs/tools/mcp-server.md, docs/tools/memory.md, docs/reference/configuration.md) | 2026-08-31 | Gemini CLI chats path, mcpServers JSON, GEMINI.md hierarchy, Memory tool |
| 31 | https://geminicli.com/docs/cli/session-management/ | 2026-08-31 | Gemini session retention settings |
| 32 | https://github.com/jnarowski/agentcmd (.agent/docs/cursor-agent.md) | 2026-08-31 | Cursor CLI store.db layout, ~/.cursor/mcp.json, cli-config.json |
| 33 | https://github.com/S2thend/cursor-history/issues/31 | 2026-08-31 | Cursor agent-transcripts JSONL + store.db on Windows/WSL |
| 34 | https://tokenuse.app/docs/development/tools/cursor/ | 2026-08-31 | Cursor IDE Windows `%APPDATA%\Cursor\User\globalStorage\state.vscdb`, CURSOR_AGENT_HOME |
| 35 | https://vshulcz.github.io/deja-vu/registry/cursor.html | 2026-08-31 | Cursor CLI JSONL under `~/.cursor/projects/<encoded>/agent-transcripts/` |
| 36 | https://cursor.com/docs/rules + https://www.deployhq.com/guides/cursor | 2026-08-31 | .cursor/rules/*.mdc format, AGENTS.md, legacy .cursorrules |

## Blockers / Inte gjort

- **Gemini CLI chat file format: not verified.** Official docs describe what is saved but not the encoding. Inspect a live `~/.gemini/tmp/<hash>/chats/` before building the adapter.
- **opencode Windows DB path discrepancy:** official docs + real Windows bug reports say `%USERPROFILE%\.local\share\opencode\opencode.db`; one community tool claims `%LOCALAPPDATA%\opencode\opencode.db`. Official/issue evidence wins; verify on a live machine.
- **Antigravity CLI MCP workspace config is buggy** (issue #60: `.agents/mcp_config.json` worked on 1.0.3, regressed on 1.1.3; HOME-level config authoritative). Design for global config injection.
- **Claude Code managed-policy Windows path** differs between official docs (`C:\Program Files\ClaudeCode\CLAUDE.md`) and a third-party mirror (`C:\ProgramData\ClaudeCode\CLAUDE.md`) — official docs used.
- **Cursor CLI storage on Windows** is documented mostly via community tooling (cursor-session says "Linux only" for agent storage, but Windows/WSL evidence exists). Verify on a live Windows install.
- **Codex CLI hooks:** no hook/plugin API found; mining must be from rollout JSONL.
- **Gemini CLI hooks:** no hook/plugin event API found.
- No live-machine verification was performed (research-only task); all paths are from docs/issues/community tooling dated 2025–2026.