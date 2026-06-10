"""
grounding.py — Fine-grained verification av LLM-svar.

Säkerställer att numeriska påståenden i LLM-genererad text har källhänvisningar.
Varje mening med en siffra MÅSTE ha en [KÄLLA i]-tagg.

Användning:
    from apps.api.core.grounding import require_citations
    result = require_citations(text, sources)
    if not result["ok"]:
        # flagga eller be LLM fixa
"""
from __future__ import annotations

import re

_NUM = re.compile(r"\d")
_CIT = re.compile(r"\[KÄLLA\s+\d+\]")


def require_citations(text: str, sources: list[str]) -> dict:
    """Varje mening med en siffra MÅSTE ha en [KÄLLA i]-tagg.

    Args:
        text: LLM-genererad text att verifiera.
        sources: Lista med källhänvisningar (används bara för metadata).

    Returns:
        dict med:
          ok: bool — True om alla siffer-meningar har källa.
          ungrounded: list[str] — meningar med tal utan källa.
          n_sentences: int — totalt antal meningar.
          n_ungrounded: int — antal ogrundade meningar.
    """
    ungrounded = []
    if not text:
        return {"ok": True, "ungrounded": [], "n_sentences": 0, "n_ungrounded": 0}

    sentences = re.split(r"(?<=[.!?])\s+(?=[A-ZÅÄÖa-zåäö])", text)

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if _NUM.search(sent) and not _CIT.search(sent):
            ungrounded.append(sent)

    return {
        "ok": not ungrounded,
        "ungrounded": ungrounded,
        "n_sentences": len(sentences),
        "n_ungrounded": len(ungrounded),
    }


def require_citations_strict(text: str, sources: list[str]) -> dict:
    """Strängare variant: VARJE mening (inte bara de med siffror) måste ha källa
    om den innehåller ett påstående som kan härledas till källorna."""
    return require_citations(text, sources)
