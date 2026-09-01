# Claude Code /context Breakdown Log

Datum: 2026-09-01
Projekt: MarketScan

| Session | Datum | System / Mode | MCP-schemas | Skills / Tools | Samtalsinnehåll | Total Context |
|---|---|---|---|---|---|---|
| Session 1 | 2026-09-01 | ~12k tokens (Claude Code base) | Context7 + Supabase + Vercel (~18k) | ~15k tokens | ~25k tokens | ~70k tokens |
| Session 2 | 2026-09-01 | ~12k tokens | Context7 dominant schema (~12k) | ~15k tokens | ~32k tokens | ~71k tokens |
| Session 3 | 2026-09-01 | ~12k tokens | Supabase + Vercel + Git (~10k) | ~15k tokens | ~18k tokens | ~55k tokens |

### Slutsats för Wave 2:C (MCP-beslut)
1. System/Mode & MCP schemas utgör ~30k tokens i baseline prefix.
2. Context7 mcp-instruktionsblock i `CLAUDE.md` bör brytas ut till separat referensfil `docs/ai/reference/mcp-context7.md` så det endast konsumeras on-demand.
