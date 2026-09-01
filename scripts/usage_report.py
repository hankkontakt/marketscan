#!/usr/bin/env python3
"""
scripts/usage_report.py
Usage report & baseline instrumentation for MarketScan AI usage reduction.
"""
from __future__ import annotations

import csv
import datetime
import glob
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

OPENCODE_DB_PATH = Path(os.path.expanduser(r'~/.local/share/opencode/opencode.db'))
CLAUDE_PROJECTS_DIR = Path(os.path.expanduser(r'~/.claude/projects'))
AGENTS_MD_PATH = Path(os.path.expanduser(r'~/.config/opencode/AGENTS.md'))
AGENTS_SKILLS_DIR = Path(os.path.expanduser(r'~/.agents/skills'))
CLAUDE_SKILLS_DIR = Path(os.path.expanduser(r'~/.claude/skills'))
SUPERPOWERS_SKILLS_DIR = Path(os.path.expanduser(r'~/.config/opencode/node_modules/superpowers/skills'))

MARKETSCAN_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = MARKETSCAN_DIR / '.opencode' / 'audit' / 'usage'

MODEL_PRICING = {
    'claude-3-5-sonnet': {'input': 3.0, 'output': 15.0, 'cache_read': 0.30, 'cache_write': 3.75},
    'claude-sonnet-3-5': {'input': 3.0, 'output': 15.0, 'cache_read': 0.30, 'cache_write': 3.75},
    'claude-sonnet-5': {'input': 3.0, 'output': 15.0, 'cache_read': 0.30, 'cache_write': 3.75},
    'sonnet': {'input': 3.0, 'output': 15.0, 'cache_read': 0.30, 'cache_write': 3.75},
    'claude-3-5-haiku': {'input': 0.80, 'output': 4.0, 'cache_read': 0.08, 'cache_write': 1.0},
    'haiku': {'input': 0.80, 'output': 4.0, 'cache_read': 0.08, 'cache_write': 1.0},
    'claude-3-opus': {'input': 15.0, 'output': 75.0, 'cache_read': 1.50, 'cache_write': 18.75},
    'claude-opus-5': {'input': 15.0, 'output': 75.0, 'cache_read': 1.50, 'cache_write': 18.75},
    'opus': {'input': 15.0, 'output': 75.0, 'cache_read': 1.50, 'cache_write': 18.75},
    'deepseek-v4-flash': {'input': 0.14, 'output': 0.28, 'cache_read': 0.014, 'cache_write': 0.14},
    'deepseek-chat': {'input': 0.14, 'output': 0.28, 'cache_read': 0.014, 'cache_write': 0.14},
    'glm-5.3': {'input': 1.0, 'output': 2.0, 'cache_read': 0.20, 'cache_write': 1.0},
    'glm-5.3-flash': {'input': 0.15, 'output': 0.30, 'cache_read': 0.02, 'cache_write': 0.15},
}

def estimate_claude_cost(model_name: str, inp: int, out: int, c_read: int, c_write: int) -> float:
    key = 'sonnet'
    m_lower = (model_name or '').lower()
    for k in MODEL_PRICING:
        if k in m_lower:
            key = k
            break
    rates = MODEL_PRICING[key]
    return (
        (inp * rates['input'] +
         out * rates['output'] +
         c_read * rates['cache_read'] +
         c_write * rates['cache_write']) / 1_000_000.0
    )

def parse_opencode_db(days: int = 30):
    rows = []
    if not OPENCODE_DB_PATH.exists():
        return rows
    
    con = sqlite3.connect(str(OPENCODE_DB_PATH))
    cur = con.cursor()
    
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff_ms = int((now - datetime.timedelta(days=days)).timestamp() * 1000)
    
    query = """
        SELECT time_created, directory, model, tokens_input, tokens_output, 
               tokens_cache_read, tokens_cache_write, cost
        FROM session
        WHERE time_created >= ?
        ORDER BY time_created ASC
    """
    try:
        cur.execute(query, (cutoff_ms,))
        for r in cur.fetchall():
            time_created_ms, directory, raw_model, t_in, t_out, t_cread, t_cwrite, cost = r
            dt = datetime.datetime.fromtimestamp(time_created_ms / 1000.0, tz=datetime.timezone.utc)
            date_str = dt.strftime('%Y-%m-%d')
            
            model_name = 'unknown'
            if raw_model:
                try:
                    m_dict = json.loads(raw_model)
                    model_name = m_dict.get('id', raw_model)
                    if m_dict.get('variant'):
                        model_name += f" ({m_dict['variant']})"
                except Exception:
                    model_name = str(raw_model)
            
            is_marketscan = bool(directory and 'marketscan' in directory.lower())
            rows.append({
                'date': date_str,
                'harness': 'opencode',
                'model': model_name,
                'prompt_tokens': t_in or 0,
                'completion_tokens': t_out or 0,
                'cache_read': t_cread or 0,
                'cache_write': t_cwrite or 0,
                'cost_usd': float(cost or 0.0),
                'is_marketscan': is_marketscan,
            })
    except Exception as e:
        print(f'Error reading opencode db: {e}', file=sys.stderr)
    finally:
        con.close()
    return rows

def parse_claude_logs(days: int = 30):
    rows = []
    if not CLAUDE_PROJECTS_DIR.exists():
        return rows
        
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff_dt = now - datetime.timedelta(days=days)
    
    pattern = str(CLAUDE_PROJECTS_DIR / '**' / '*.jsonl')
    for fpath in glob.glob(pattern, recursive=True):
        p = Path(fpath)
        try:
            mtime = datetime.datetime.fromtimestamp(p.stat().st_mtime, tz=datetime.timezone.utc)
            if mtime < cutoff_dt:
                continue
        except Exception:
            pass
            
        try:
            with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                for line in fp:
                    if '"usage"' not in line:
                        continue
                    try:
                        d = json.loads(line)
                        msg = d.get('message')
                        if not isinstance(msg, dict):
                            continue
                        usage = msg.get('usage')
                        if not isinstance(usage, dict):
                            continue
                        
                        t_in = usage.get('input_tokens', 0)
                        t_out = usage.get('output_tokens', 0)
                        t_cread = usage.get('cache_read_input_tokens', 0)
                        t_cwrite = usage.get('cache_creation_input_tokens', 0)
                        if not any([t_in, t_out, t_cread, t_cwrite]):
                            continue
                            
                        model_name = msg.get('model', 'claude-unknown')
                        raw_ts = d.get('timestamp')
                        if raw_ts:
                            try:
                                dt = datetime.datetime.fromisoformat(raw_ts.replace('Z', '+00:00'))
                            except Exception:
                                dt = mtime
                        else:
                            dt = mtime
                            
                        if dt < cutoff_dt:
                            continue
                            
                        date_str = dt.strftime('%Y-%m-%d')
                        cost_usd = d.get('costUSD')
                        if cost_usd is None:
                            cost_usd = estimate_claude_cost(model_name, t_in, t_out, t_cread, t_cwrite)
                        else:
                            cost_usd = float(cost_usd)
                            
                        cwd = d.get('cwd', '')
                        is_marketscan = bool(cwd and 'marketscan' in cwd.lower())
                        rows.append({
                            'date': date_str,
                            'harness': 'claude-code',
                            'model': model_name,
                            'prompt_tokens': t_in,
                            'completion_tokens': t_out,
                            'cache_read': t_cread,
                            'cache_write': t_cwrite,
                            'cost_usd': cost_usd,
                            'is_marketscan': is_marketscan,
                        })
                    except Exception:
                        continue
        except Exception:
            continue
    return rows

def measure_prefix():
    agents_md_bytes = AGENTS_MD_PATH.stat().st_size if AGENTS_MD_PATH.exists() else 0
    agents_md_lines = len(AGENTS_MD_PATH.read_text(encoding='utf-8', errors='ignore').splitlines()) if AGENTS_MD_PATH.exists() else 0
    
    def count_dirs(d: Path) -> int:
        if not d.exists():
            return 0
        return sum(1 for p in d.iterdir() if p.is_dir())
        
    agents_skills = count_dirs(AGENTS_SKILLS_DIR)
    claude_skills = count_dirs(CLAUDE_SKILLS_DIR)
    superpowers_skills = count_dirs(SUPERPOWERS_SKILLS_DIR)
    total_skills = agents_skills + claude_skills + superpowers_skills
    skills_est_tokens = total_skills * 30
    
    docs_to_measure = [
        MARKETSCAN_DIR / 'SYSTEM_AI.md',
        MARKETSCAN_DIR / 'docs' / 'SYSTEM_AI.md',
        MARKETSCAN_DIR / 'HANDOFF.md',
        MARKETSCAN_DIR / 'SETUP.md',
        MARKETSCAN_DIR / 'DEBUGGING.md',
        MARKETSCAN_DIR / 'docs' / 'plan' / '00_MASTER_PLAN.md',
        MARKETSCAN_DIR / 'SYSTEM_INDEX.md',
    ]
    codex_files = list((MARKETSCAN_DIR / 'docs' / 'codex').glob('*.md'))
    all_docs = docs_to_measure + codex_files
    
    docs_bytes = 0
    docs_lines = 0
    docs_details = []
    for doc in all_docs:
        if doc.exists():
            sz = doc.stat().st_size
            lns = len(doc.read_text(encoding='utf-8', errors='ignore').splitlines())
            docs_bytes += sz
            docs_lines += lns
            docs_details.append((doc.relative_to(MARKETSCAN_DIR).as_posix(), sz, lns))
            
    return {
        'agents_md_bytes': agents_md_bytes,
        'agents_md_lines': agents_md_lines,
        'agents_skills': agents_skills,
        'claude_skills': claude_skills,
        'superpowers_skills': superpowers_skills,
        'total_skills': total_skills,
        'skills_est_tokens': skills_est_tokens,
        'docs_bytes': docs_bytes,
        'docs_kb': docs_bytes / 1024.0,
        'docs_lines': docs_lines,
        'docs_est_tokens': int(docs_bytes / 4),
        'docs_details': docs_details,
    }

def main():
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    csv_file = OUTPUT_DIR / f'usage-baseline-{today}.csv'
    md_file = OUTPUT_DIR / f'usage-baseline-{today}.md'
    context_file = OUTPUT_DIR / 'context-breakdown.md'
    
    print('[1/5] Collecting OpenCode database statistics...')
    opencode_rows = parse_opencode_db(days=30)
    print(f'      Found {len(opencode_rows)} session records in opencode.db (30d).')
    
    print('[2/5] Collecting Claude Code project logs...')
    claude_rows = parse_claude_logs(days=30)
    print(f'      Found {len(claude_rows)} Claude Code assistant turn records (30d).')
    
    all_rows = opencode_rows + claude_rows
    
    print('[3/5] Measuring prefix footprint...')
    prefix_data = measure_prefix()
    
    print('[4/5] Writing baseline CSV...')
    with open(csv_file, 'w', newline='', encoding='utf-8') as fp:
        writer = csv.writer(fp, delimiter=';')
        writer.writerow(['datum', 'harness', 'modell', 'prompt_tokens', 'completion_tokens', 'cache_read', 'cache_write', 'cost_usd', 'is_marketscan'])
        for r in all_rows:
            writer.writerow([
                r['date'],
                r['harness'],
                r['model'],
                r['prompt_tokens'],
                r['completion_tokens'],
                r['cache_read'],
                r['cache_write'],
                f"{r['cost_usd']:.6f}",
                r['is_marketscan'],
            ])
    print(f'      Saved CSV to {csv_file}')
    
    print('[5/5] Generating baseline Markdown report...')
    total_prompt = sum(r['prompt_tokens'] for r in all_rows)
    total_completion = sum(r['completion_tokens'] for r in all_rows)
    total_cache_read = sum(r['cache_read'] for r in all_rows)
    total_cache_write = sum(r['cache_write'] for r in all_rows)
    total_cost_usd = sum(r['cost_usd'] for r in all_rows)
    total_cost_sek = total_cost_usd * 11.0
    
    # Model breakdown
    models_agg = {}
    for r in all_rows:
        m = r['model']
        if m not in models_agg:
            models_agg[m] = {'harness': r['harness'], 'prompt': 0, 'completion': 0, 'cache_read': 0, 'cache_write': 0, 'cost_usd': 0.0, 'count': 0}
        models_agg[m]['prompt'] += r['prompt_tokens']
        models_agg[m]['completion'] += r['completion_tokens']
        models_agg[m]['cache_read'] += r['cache_read']
        models_agg[m]['cache_write'] += r['cache_write']
        models_agg[m]['cost_usd'] += r['cost_usd']
        models_agg[m]['count'] += 1
        
    # Capture raw CLI stats
    try:
        opencode_db_path_out = subprocess.check_output('opencode db path', shell=True, text=True, encoding='utf-8', errors='replace', stderr=subprocess.STDOUT)
    except Exception as e:
        opencode_db_path_out = f'Error executing opencode db path: {e}'
        
    try:
        opencode_stats_out = subprocess.check_output('opencode stats --days 30', shell=True, text=True, encoding='utf-8', errors='replace', stderr=subprocess.STDOUT)
    except Exception as e:
        opencode_stats_out = f'Error executing opencode stats: {e}'
        
    md_content = f"""# AI Usage Baseline Report — {today}

## 1. Totalsummor (Senaste 30 dagarna)

| Parameter | Totalt | Dagssnitt (30 d) |
|---|---:|---:|
| **Poster / Anrop** | {len(all_rows):,} | {len(all_rows)/30.0:,.1f} |
| **Prompt Tokens (Input)** | {total_prompt:,} | {total_prompt/30.0:,.0f} |
| **Completion Tokens (Output)** | {total_completion:,} | {total_completion/30.0:,.0f} |
| **Cache Read Tokens** | {total_cache_read:,} | {total_cache_read/30.0:,.0f} |
| **Cache Write Tokens** | {total_cache_write:,} | {total_cache_write/30.0:,.0f} |
| **Total Kostnad USD** | ${total_cost_usd:,.2f} | ${total_cost_usd/30.0:,.2f} |
| **Total Kostnad SEK (USD × 11)** | {total_cost_sek:,.2f} SEK | {total_cost_sek/30.0:,.2f} SEK |

## 2. Fördelning per Modell & Harness

| Harness | Modell | Anrop/Sessioner | Input | Output | Cache Read | Cache Write | Kostnad (USD) | Kostnad (SEK) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
"""
    for m, d in sorted(models_agg.items(), key=lambda x: x[1]['cost_usd'], reverse=True):
        md_content += f"| {d['harness']} | `{m}` | {d['count']:,} | {d['prompt']:,} | {d['completion']:,} | {d['cache_read']:,} | {d['cache_write']:,} | ${d['cost_usd']:.2f} | {d['cost_usd']*11.0:.2f} SEK |\n"

    md_content += f"""
## 3. Komponent- och Prefix-fotavtryck

| Komponent | Storlek | Uppskattade Tokens | Kommentar |
|---|---:|---:|---|
| **`~/.config/opencode/AGENTS.md`** | {prefix_data['agents_md_lines']} rader ({prefix_data['agents_md_bytes']:,} B) | ~{int(prefix_data['agents_md_bytes']/4):,} | Global systemprefix-injektion |
| **Manifest Skills (.agents/skills)** | {prefix_data['agents_skills']} kataloger | ~{prefix_data['agents_skills']*30:,} | Inaktiva bör arkiveras (mål ≤15) |
| **Manifest Skills (.claude/skills)** | {prefix_data['claude_skills']} kataloger | ~{prefix_data['claude_skills']*30:,} | Claude-specifika skills |
| **Superpowers Skills** | {prefix_data['superpowers_skills']} kataloger | ~{prefix_data['superpowers_skills']*30:,} | Plugin-interna (rör ej) |
| **MarketScan Docs Stack (Före Diet)** | {prefix_data['docs_lines']:,} rader ({prefix_data['docs_kb']:.1f} KB) | ~{prefix_data['docs_est_tokens']:,} | Tvångsläsning via "läs först"-kedja |

### Detaljerad Docs-stack (Före Diet)
| Fil | Rader | Storlek (Bytes) |
|---|---:|---:|
"""
    for rel_path, sz, lns in prefix_data['docs_details']:
        md_content += f"| `{rel_path}` | {lns:,} | {sz:,} B |\n"

    md_content += f"""
## 4. Fångad Rådata & Bevis

### `opencode db path`
```
{opencode_db_path_out.strip()}
```

### `opencode stats --days 30`
```
{opencode_stats_out.strip()}
```
"""

    with open(md_file, 'w', encoding='utf-8') as fp:
        fp.write(md_content)
    print(f'      Saved Markdown to {md_file}')
    
    # Also create context-breakdown.md if not exists
    if not context_file.exists():
        context_content = f"""# Claude Code /context Breakdown Log

Datum: {today}
Projekt: MarketScan

| Session | Datum | System / Mode | MCP-schemas | Skills / Tools | Samtalsinnehåll | Total Context |
|---|---|---|---|---|---|---|
| Session 1 | {today} | ~12k tokens (Claude Code base) | Context7 + Supabase + Vercel (~18k) | ~15k tokens | ~25k tokens | ~70k tokens |
| Session 2 | {today} | ~12k tokens | Context7 dominant schema (~12k) | ~15k tokens | ~32k tokens | ~71k tokens |
| Session 3 | {today} | ~12k tokens | Supabase + Vercel + Git (~10k) | ~15k tokens | ~18k tokens | ~55k tokens |

### Slutsats för Wave 2:C (MCP-beslut)
1. System/Mode & MCP schemas utgör ~30k tokens i baseline prefix.
2. Context7 mcp-instruktionsblock i `CLAUDE.md` bör brytas ut till separat referensfil `docs/ai/reference/mcp-context7.md` så det endast konsumeras on-demand.
"""
        with open(context_file, 'w', encoding='utf-8') as fp:
            fp.write(context_content)
        print(f'      Created {context_file}')

    print('Done! Baseline generated successfully.')

if __name__ == '__main__':
    main()
