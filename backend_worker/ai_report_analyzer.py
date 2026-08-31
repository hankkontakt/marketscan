"""
ai_report_analyzer.py — DeepSeek OpenRouter Multi-Agent AI Finansmotor.

Utför avancerade språkliga och forensiska analyser på nordiska bolag:
  1. analyze_interim_report: Extraherar verkligt EBIT, aktiverad FoU, kassarunway och emissionsrisk
  2. analyze_ceo_tone_shift: Jämför VD-ord mellan kvartal och mäter förtroendedelta
  3. analyze_press_release: Beräknar orderbetydelse (% av årsomsättning) och katalysatoreffekt
  4. generate_investment_thesis: Skapar institutionella 1-sidiga analysmemos (Bull/Bear/Moat)

Körs via OpenRouter API (DeepSeek V3/V4 Flash).
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DEFAULT_OPENROUTER_KEY = ""
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "deepseek/deepseek-chat"


def get_api_key() -> str:
    return os.environ.get("OPENROUTER_API_KEY") or os.environ.get("DEEPSEEK_API_KEY") or DEFAULT_OPENROUTER_KEY


def _query_openrouter(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.1,
    timeout: int = 45
) -> dict:
    """Standardiserad OpenRouter-anropsfunktion med felhantering."""
    key = get_api_key()
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://marketscan.app",
        "X-Title": "MarketScan AI Multi-Agent Engine"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature
    }
    t0 = time.time()
    try:
        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=timeout)
        elapsed = time.time() - t0
        if resp.status_code == 200:
            data = resp.json()
            usage = data.get("usage", {})
            choice = data["choices"][0]["message"]
            content = choice.get("content", "")
            return {
                "success": True,
                "elapsed_s": round(elapsed, 2),
                "model": data.get("model", model),
                "tokens_prompt": usage.get("prompt_tokens"),
                "tokens_completion": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
                "content": content
            }
        else:
            return {"success": False, "status_code": resp.status_code, "error": resp.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _clean_json_response(raw_text: str) -> Optional[dict]:
    """Rensar markdown code blocks och parsar JSON."""
    if not raw_text:
        return None
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except Exception:
        # Försök hitta json block inuti texten
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        return None


# ═════════════════════════ AI MULTI-AGENT MODULER ═════════════════════════════

def analyze_interim_report(report_text: str, ticker: str = "") -> dict:
    """Agent 1: Forensisk Kvartalsrapport-granskare.

    Identifierar aktiverad FoU, kassarunway, dolda låneklausuler och emissionsrisk.
    """
    prompt = f"""
Du är en erfaren forensisk finansanalytiker specialiserad på nordiska börsnoterade bolag (First North, Spotlight, OMXS).
Analysera följande textutdrag ur delårsrapporten för {ticker}.

Svara ENBART i strikt JSON-format:
{{
  "revenue_msek": float eller null,
  "ebit_reported_msek": float eller null,
  "capitalized_rd_msek": float eller null,
  "operating_cash_flow_msek": float eller null,
  "cash_and_equivalents_msek": float eller null,
  "real_ebit_without_capitalization_msek": float eller null,
  "cash_runway_months": float eller null,
  "dilution_emission_risk_level": "LÅG" | "MEDEL" | "MYCKET_HÖG",
  "forensic_red_flags": list[str],
  "covenant_or_debt_warnings": list[str],
  "verdict_summary_swedish": str
}}

RAPPORTTEXT:
{report_text[:12000]}
"""
    res = _query_openrouter([{"role": "user", "content": prompt}], temperature=0.0)
    if not res["success"]:
        return {"success": False, "error": res.get("error")}
    
    parsed = _clean_json_response(res["content"])
    return {
        "success": True,
        "elapsed_s": res["elapsed_s"],
        "tokens": res["total_tokens"],
        "data": parsed or {"raw": res["content"]}
    }


def analyze_ceo_tone_shift(q_current_text: str, q_previous_text: str, ticker: str = "") -> dict:
    """Agent 2: VD-Ord & Guidance Tonfalls-Delta.

    Mäter lingvistiskt självförtroende och varnar vid plötsliga skiften till alibifraser.
    """
    prompt = f"""
Jämför VD-ordet för {ticker} mellan föregående kvartal (Q_prev) och det aktuella kvartalet (Q_curr).
Analysera tonfall, framtidsutsikter, orderläge och garderingar.

Svara ENBART i strikt JSON-format:
{{
  "q_prev_confidence_score": float (-1.0 till +1.0),
  "q_curr_confidence_score": float (-1.0 till +1.0),
  "tone_delta": float,
  "signal": "ACCELERATION" | "NEUTRAL" | "VARNING" | "KRAFTIG_FÖRSÄMRING",
  "key_linguistic_shifts": list[str],
  "investment_takeaway_swedish": str
}}

FÖREGÅENDE KVARTAL:
"{q_previous_text[:4000]}"

AKTUELLT KVARTAL:
"{q_current_text[:4000]}"
"""
    res = _query_openrouter([{"role": "user", "content": prompt}], temperature=0.0)
    if not res["success"]:
        return {"success": False, "error": res.get("error")}
    
    parsed = _clean_json_response(res["content"])
    return {
        "success": True,
        "elapsed_s": res["elapsed_s"],
        "tokens": res["total_tokens"],
        "data": parsed or {"raw": res["content"]}
    }


def analyze_press_release(pr_text: str, ttm_revenue_msek: Optional[float] = None, ticker: str = "") -> dict:
    """Agent 3: Cision MAR Pressmeddelande & Katalysator-kalkylator.

    Klassificerar händelsen och beräknar ordervärde i relation till årsomsättningen.
    """
    context_rev = f"Bolagets rullande årsomsättning (TTM) är cirka {ttm_revenue_msek:.1f} MSEK." if ttm_revenue_msek else "Bolagets årsomsättning är okänd."
    prompt = f"""
Analysera följande regulatoriska pressmeddelande för {ticker}. {context_rev}

Svara ENBART i strikt JSON-format:
{{
  "event_type": "GENOMBROTTSORDER" | "FÖRVÄRV" | "PRODUKTLANSERING" | "RUTINNOTIS" | "VINSTVARNING" | "LEDNINGSFÖRÄNDRING",
  "order_value_msek": float eller null,
  "significance_pct_of_annual_rev": float eller null,
  "catalyst_impact_score": int (0-100),
  "ai_verdict_swedish": str
}}

PRESSMEDDELANDE:
{pr_text[:6000]}
"""
    res = _query_openrouter([{"role": "user", "content": prompt}], temperature=0.0)
    if not res["success"]:
        return {"success": False, "error": res.get("error")}
    
    parsed = _clean_json_response(res["content"])
    return {
        "success": True,
        "elapsed_s": res["elapsed_s"],
        "tokens": res["total_tokens"],
        "data": parsed or {"raw": res["content"]}
    }


def generate_investment_thesis_memo(ticker: str, metrics: dict, company_name: str = "") -> dict:
    """Agent 4: 1-sidig Investeringspromemoria (Institutional Thesis Memo)."""
    metrics_str = json.dumps(metrics, indent=2, ensure_ascii=False)
    prompt = f"""
Du är Lead Quantitative Analyst på en framstående nordisk småbolagsfond.
Generera ett koncist, institutionellt 1-sidigt investeringsmemo för {company_name} ({ticker}).

Nyckeltal och faktorsignaler:
{metrics_str}

Formatera svaret i strukturerad Markdown med följande rubriker:
# 📋 Investeringsmemo: {company_name} ({ticker})
## 1. Sammanfattande Betyg & Slutsats (Köp / Avvakta / Undvik)
## 2. Kärntes & Affärsmodell (Moat / Vallgrav)
## 3. Bull Case (Vad kan få aktien att dubblas?)
## 4. Bear Case & Forensiska Risker (Dolda minor, kassaflöde, utspädning)
## 5. Katalysatorer & Kommande Triggers (6–12 månader)
## 6. Forensisk Revisionscheck (Kassaflödeskvalitet & Ägarskap)
"""
    res = _query_openrouter([{"role": "user", "content": prompt}], temperature=0.2)
    if not res["success"]:
        return {"success": False, "error": res.get("error")}
    
    return {
        "success": True,
        "elapsed_s": res["elapsed_s"],
        "tokens": res["total_tokens"],
        "memo_markdown": res["content"]
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    print("Testing AI Report Analyzer with OpenRouter...")
    sample = "Plejd tecknar avtal om smart belysning värt 30 MSEK med tysk grossist."
    r = analyze_press_release(sample, ttm_revenue_msek=650.0, ticker="PLEJD.ST")
    print(json.dumps(r, indent=2, ensure_ascii=False))
