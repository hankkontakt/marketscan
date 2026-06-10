"""
reranker.py — Cross-encoder reranking för RAG-relevans.

Använder sentence-transformers CrossEncoder för att reranka chunkar efter
relevans mot en query. Fallback: om modellen inte kan laddas → returnera
chunks[:top_n] (ingen krasch).

Modell: cross-encoder/ms-marco-MiniLM-L-6-v2 (liten, fungerar på svenska).
Alternativ: BAAI/bge-reranker-base.

Används av RAG-pipelinen och earnings-memo-generering för att förbättra
relevansen på de chunkar som skickas till LLM:en.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_MODEL = None
_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def _load():
    """Ladda CrossEncoder-modellen (lazy, cachas i process)."""
    global _MODEL
    if _MODEL is None:
        try:
            from sentence_transformers import CrossEncoder
            _MODEL = CrossEncoder(_MODEL_NAME)
            logger.info("CrossEncoder loaded: %s", _MODEL_NAME)
        except Exception as e:
            logger.warning("Failed to load CrossEncoder %s: %s", _MODEL_NAME, e)
            _MODEL = False  # Sentinel: misslyckad laddning
    return _MODEL if _MODEL is not False else None


def rerank(
    query: str,
    chunks: list[dict],
    top_n: int = 6,
    text_key: str = "content",
) -> list[dict]:
    """Sortera chunkar efter cross-encoder-relevans mot query, returnera topp-n.

    Args:
        query: Frågan/söksträngen.
        chunks: Lista med chunk-dicts (måste ha text_key-fältet).
        top_n: Antal chunkar att returnera.
        text_key: Nyckel i varje chunk-dict som innehåller texten.

    Returns:
        Topp-n chunkar sorterade efter relevans (högst först).
        Fallback: chunks[:top_n] om modell ej tillgänglig.
    """
    if not chunks:
        return []

    model = _load()
    if model is None:
        logger.debug("Rerank fallback: no model available")
        return chunks[:top_n]

    try:
        pairs = [(query, c.get(text_key, "")) for c in chunks]
        scores = model.predict(pairs)
        ranked = [
            {**c, "rerank_score": float(s)}
            for c, s in sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
        ]
        return ranked[:top_n]
    except Exception as e:
        logger.warning("Rerank fallback (prediction failed): %s", e)
        return chunks[:top_n]
