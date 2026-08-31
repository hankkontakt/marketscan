"""
Legal Order & Regulatory Press Release Classifier (Catalyst NLP Stream).

Classifies press releases into distinct legal categories:
  - BINDING_FIRM_ORDER: Fast bindande kommersiell order (Högst Alpha)
  - FRAMEWORK_AGREEMENT: Ramavtal utan garanterad minimivolym (Måttlig Alpha)
  - NON_BINDING_LOI: Avsiktsförklaring / Letter of Intent / MOU (Låg Alpha, ofta hype)
  - REGULATORY_APPROVAL: FDA 510(k), CE-märke, MDR, Marknadsgodkännande (Genombrott)
  - ACQUISITION_ACQUISITIVE: Värdeskapande förvärv med positiv EPS-effekt
  - PILOT_STUDY: Testorder / utvärderingsavtal utan intäktseffekt

Calculates:
  - Estimated order value (MSEK)
  - Revenue Impact Ratio: Order Value / TTM Revenue
  - Catalyst Alpha Score (0 - 100)
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# Regex patterns for contract types
PATTERNS_BINDING_ORDER = [
    r'\berhåller\s+(?:en\s+)?(?:bindande\s+)?(?:order|beställning)\b',
    r'\bfår\s+(?:en\s+)?(?:fast\s+)?(?:order|beställning)\b',
    r'\btecknar\s+(?:ett\s+)?(?:bindande\s+)?kundavtal\b',
    r'\bavrop\s+(?:om|på|omfattande)\b',
    r'\brecord\s+order\b',
    r'\border\s+värd\s+[0-9]+',
]

PATTERNS_FRAMEWORK = [
    r'\bramavtal\b',
    r'\bframework\s+agreement\b',
    r'\bleverantörsavtal\b',
    r'\bdistributörsavtal\b',
    r'\bavtal\s+med\s+(?:ett\s+)?potential\s+värde\b',
]

PATTERNS_LOI = [
    r'\bavsiktsförklaring\b',
    r'\bletter\s+of\s+intent\b',
    r'\bloi\b',
    r'\bmemorandum\s+of\s+understanding\b',
    r'\bmou\b',
    r'\binleder\s+samarbete\b',
    r'\butvärderar\s+samarbete\b',
    r'\bicke-bindande\b',
]

PATTERNS_REGULATORY = [
    r'\bmarknadsgodkännande\b',
    r'\bfda\s*(?:510\(k\)|godkännande|approval|clearance)\b',
    r'\bce-märk(?:ning|t|as)\b',
    r'\bmdr-godkännande\b',
    r'\bpatentsökt|beviljat\s+patent\b',
    r'\bregulatoriskt\s+godkännande\b',
]

PATTERNS_ACQUISITION = [
    r'\bförvärvar\b',
    r'\bköper\s+(?:100\s*%\s+av\s+)?(?:bolaget|aktierna)\b',
    r'\bacquires?\b',
    r'\btillträde\s+av\s+förvärv\b',
]


def extract_order_amount_msek(text: str) -> Optional[float]:
    """
    Extracts monetary order value in MSEK from text.
    Handles MSEK, Mkr, MUSD, MEUR, TSEK.
    """
    if not text:
        return None
        
    # Match MSEK / Mkr (e.g. "45,5 MSEK", "120 Mkr", "15 miljoner kronor")
    m_sek = re.search(r'([0-9]+(?:[,.][0-9]+)?)\s*(?:msek|mkr|miljoner\s*kronor|miljoner\s*sek)', text, re.IGNORECASE)
    if m_sek:
        return float(m_sek.group(1).replace(",", "."))
        
    # Match MUSD (approx 1 USD = 10.5 SEK)
    m_usd = re.search(r'([0-9]+(?:[,.][0-9]+)?)\s*(?:musd|m\$|\$\s*miljoner|miljoner\s*dollar)', text, re.IGNORECASE)
    if m_usd:
        return float(m_usd.group(1).replace(",", ".")) * 10.5
        
    # Match MEUR (approx 1 EUR = 11.5 SEK)
    m_eur = re.search(r'([0-9]+(?:[,.][0-9]+)?)\s*(?:meur|m€|€\s*miljoner|miljoner\s*euro)', text, re.IGNORECASE)
    if m_eur:
        return float(m_eur.group(1).replace(",", ".")) * 11.5
        
    # Match TSEK / KSEK (thousands SEK)
    m_tsek = re.search(r'([0-9]+(?:[,.][0-9]+)?)\s*(?:tsek|ksek|tusental\s*kronor)', text, re.IGNORECASE)
    if m_tsek:
        return float(m_tsek.group(1).replace(",", ".")) / 1000.0
        
    return None


def classify_press_release(
    headline: str,
    body: str,
    ttm_revenue_msek: Optional[float] = None
) -> dict:
    """
    Classifies a press release into a structured catalyst report.
    """
    full_text = f"{headline} {body}".lower()
    
    # 1. Check Regulatory Approval
    if any(re.search(p, full_text) for p in PATTERNS_REGULATORY):
        return {
            "category": "REGULATORY_APPROVAL",
            "is_binding": True,
            "order_value_msek": None,
            "revenue_impact_pct": None,
            "catalyst_score": 90.0,
            "badge": "🧬 REGULATORISKT GENOMBROTT",
            "summary": "Bolaget har erhållit marknadsgodkännande / regulatorisk certifiering"
        }
        
    # 2. Check Acquisition
    if any(re.search(p, full_text) for p in PATTERNS_ACQUISITION):
        amount = extract_order_amount_msek(full_text)
        return {
            "category": "ACQUISITION_ACQUISITIVE",
            "is_binding": True,
            "order_value_msek": amount,
            "revenue_impact_pct": None,
            "catalyst_score": 75.0,
            "badge": "🏢 STRATEGISKT FÖRVÄRV",
            "summary": f"Förvärv genomfört/avtalat{f' (värde {amount:.1f} MSEK)' if amount else ''}"
        }
        
    # 3. Check LOI / MOU (Must precede firm order to avoid false positives)
    if any(re.search(p, full_text) for p in PATTERNS_LOI):
        amount = extract_order_amount_msek(full_text)
        return {
            "category": "NON_BINDING_LOI",
            "is_binding": False,
            "order_value_msek": amount,
            "revenue_impact_pct": None,
            "catalyst_score": 25.0,
            "badge": "⚠️ ICKE-BINDANDE AVSIKTSFÖRKLARING",
            "summary": "Icke-bindande samarbete/LOI (risk för marknadshype utan substans)"
        }
        
    # 4. Check Framework Agreement
    if any(re.search(p, full_text) for p in PATTERNS_FRAMEWORK):
        amount = extract_order_amount_msek(full_text)
        return {
            "category": "FRAMEWORK_AGREEMENT",
            "is_binding": True,
            "order_value_msek": amount,
            "revenue_impact_pct": None,
            "catalyst_score": 55.0,
            "badge": "📜 RAMAVTAL",
            "summary": f"Ramavtal slutet{f' (potentiellt värde {amount:.1f} MSEK)' if amount else ' (volymer ej garanterade)'}"
        }
        
    # 5. Check Binding Firm Order
    if any(re.search(p, full_text) for p in PATTERNS_BINDING_ORDER):
        amount = extract_order_amount_msek(full_text)
        impact_pct = None
        score = 70.0
        
        if amount and ttm_revenue_msek and ttm_revenue_msek > 0:
            impact_pct = (amount / ttm_revenue_msek) * 100.0
            if impact_pct >= 50.0:
                score = 98.0
            elif impact_pct >= 20.0:
                score = 88.0
            elif impact_pct >= 10.0:
                score = 78.0
            else:
                score = 65.0
        elif amount:
            score = 75.0
            
        return {
            "category": "BINDING_FIRM_ORDER",
            "is_binding": True,
            "order_value_msek": amount,
            "revenue_impact_pct": round(impact_pct, 1) if impact_pct else None,
            "catalyst_score": score,
            "badge": "🚀 TRANSFORMATIV FAST ORDER" if (impact_pct and impact_pct >= 20.0) else "📦 BINDANDE KUNDORDER",
            "summary": f"Fast order mottagen: {f'{amount:.1f} MSEK' if amount else 'Belopp ej angivet'}{f' ({impact_pct:.1f}% av omsättning)' if impact_pct else ''}"
        }
        
    # Default neutral/other PR
    return {
        "category": "GENERAL_PRESS_RELEASE",
        "is_binding": False,
        "order_value_msek": None,
        "revenue_impact_pct": None,
        "catalyst_score": 40.0,
        "badge": "📰 ALLMÄNT PRESSMEDDELANDE",
        "summary": "Generell bolagsinformation"
    }
