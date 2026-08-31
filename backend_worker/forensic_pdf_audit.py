"""
forensic_pdf_audit.py — 1-Klicks Forensisk Delårs-Audit & Fotnotsgranskare.

Analyserar delårsrapporter och prospekt för att upptäcka dolda redovisningsrisker:
  1. Aktiverad FoU vs Rapporterad EBIT (Aggressiv vinstuppblåsning).
  2. Kassarunway och förestående nyemissionsrisk (månader kvar till likviditetsbrist).
  3. Låneklausuler (covenants) och förfalloprofil inom 12 månader.
  4. Kundfordringsavvikelser (kundfordringar som ökar snabbare än försäljning).
  5. Trafikljusbedömning (GRÖN / GUL / RÖD) med handlingsbar sammanfattning.

Drivs av DeepSeek V4 Pro (0813 GA) / DeepSeek R1 via OpenRouter.
"""
from __future__ import annotations

import io
import json
import logging
import os
import time
import urllib.request

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "deepseek/deepseek-v4-pro-0813"


def get_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    if key:
        return key
    for env_path in [".env.local", ".env"]:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("DEEPSEEK_API_KEY=") or line.startswith("OPENROUTER_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val and val.startswith("sk-"):
                            return val
    return ""


def extract_text_from_pdf_bytes(pdf_bytes: bytes, max_pages: int = 40) -> str:
    """Extraherar råtext och tabeller från PDF-bytes via pypdf eller pdfplumber."""
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        pages_text = []
        for i, page in enumerate(reader.pages[:max_pages]):
            t = page.extract_text() or ""
            if t.strip():
                pages_text.append(f"--- SIDA {i+1} ---\n{t}")
        return "\n\n".join(pages_text)
    except Exception as e:
        logger.warning("PDF-extraktion misslyckades: %s", e)
        return ""


def run_forensic_audit(
    report_text: str,
    ticker: str = "",
    company_name: str = "",
    model: str = DEFAULT_MODEL
) -> dict:
    """Kör den forensiska granskningen mot DeepSeek V4 Pro / R1."""
    key = get_api_key()
    if not key:
        return {
            "success": False,
            "error": "DEEPSEEK_API_KEY / OPENROUTER_API_KEY saknas",
            "traffic_light": "GUL",
            "verdict_summary_sv": "AI-nyckel ej konfigurerad."
        }

    system_prompt = (
        "Du är en forensisk chefsrevisor och finansanalytiker specialiserad på nordiska börsbolag. "
        "Ditt uppdrag är att skydda investerare från dolda minor, aggressiv redovisning och förestående emissioner.\n"
        "Svara ENBART i strikt JSON-format."
    )

    user_prompt = f"""
Granska följande utdrag ur delårsrapporten/årsredovisningen för {company_name} ({ticker}).

Svara STRICT i följande JSON-format:
{{
  "ticker": "{ticker}",
  "company_name": "{company_name}",
  "traffic_light": "GRÖN" | "GUL" | "RÖD",
  "audit_score": 0-100,
  "dilution_emission_risk": "LÅG" | "MEDEL" | "HÖG" | "KRITISK",
  "cash_runway_months": float eller null,
  "capitalized_rd_pct_of_ebit": float eller null,
  "real_ebit_adjusted_msek": float eller null,
  "covenant_and_debt_risks": list[str],
  "accounting_red_flags": list[str],
  "positive_qualities": list[str],
  "verdict_summary_sv": "Koncis och professionell forensisk slutsats på 3-4 meningar på flytande svenska."
}}

RAPPORTTEXT (INKLUSIVE FOTNOTER & BALANSRÄKNING):
{report_text[:35000]}
"""

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://marketscan.app",
        "X-Title": "MarketScan Forensic PDF Audit"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 2500,
        "response_format": {"type": "json_object"}
    }

    t0 = time.time()
    try:
        req = urllib.request.Request(
            OPENROUTER_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers
        )
        resp = urllib.request.urlopen(req, timeout=45)
        elapsed = round(time.time() - t0, 2)
        raw_data = json.loads(resp.read().decode("utf-8"))
        
        choice = raw_data["choices"][0]["message"]
        content = choice.get("content") or choice.get("reasoning") or ""
        
        # Parse JSON output
        clean_content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        audit_data = json.loads(clean_content)
        
        usage = raw_data.get("usage", {})
        
        return {
            "success": True,
            "elapsed_s": elapsed,
            "tokens": usage.get("total_tokens", 0),
            "model_used": raw_data.get("model", model),
            "audit": audit_data
        }
    except Exception as e:
        logger.error("Forensic audit failed: %s", e)
        return {
            "success": False,
            "error": str(e),
            "traffic_light": "GUL",
            "verdict_summary_sv": f"Granskningen kunde inte slutföras: {e}"
        }
