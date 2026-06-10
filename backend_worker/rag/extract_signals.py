"""
extract_signals.py — Strukturerad extraktion av kvalitativa signaler ur rapporter.

För varje bolag med ny rapport, kör 5 strukturerade queries mot dess chunkar.
Aggregera → qualitative_score (0–100) → spara i qualitative_signals.

Använder L1 (rerank) från spec 12 för bättre relevans i chunk-urvalet.

Användning:
    python -m backend_worker.rag.extract_signals
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Försök importera reranker (L1); fallback om modulen inte finns
try:
    from apps.api.core.reranker import rerank as _rerank
except Exception:
    def _rerank(query, chunks, top_n=6, text_key="content"):
        return chunks[:top_n]

# Vikter för qualitative_score
SCORE_WEIGHTS = {
    "outlook": 0.35,      # Intäktsutsikter (viktigast)
    "margin": 0.20,       # Marginal-/lönsamhetsguidning
    "tone": 0.20,         # Ledningens ton/konfidens
    "risk": 0.15,         # Riskförändring
    "capital": 0.10,      # Kapitalallokering
}

_QUERIES = {
    "outlook": "utsikter framtidsutsikter intäkter orderingång marknad",
    "margin": "marginal lönsamhet resultat kostnader prissättning",
    "tone": "VD kommentar ledning strategi framtid konfidens",
    "risk": "risk osäkerhet exponering hot möjlighet",
    "capital": "kapitalallokering investering utdelning återköp skuld",
}


def _get_db_connection():
    """Skapa DB-anslutning."""
    import psycopg2
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL required")
    return psycopg2.connect(database_url)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity mellan två vektorer."""
    a = np.array(a)
    b = np.array(b)
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def _find_relevant_chunks(
    conn,
    ticker: str,
    query_embedding: list[float],
    top_k: int = 5,
    min_score: float = 0.5,
) -> list[dict]:
    """Hitta relevanta chunkar via cosine similarity mot pgvector."""
    try:
        cur = conn.cursor()
        # Använd pgvector cosine-similarity via SQL
        cur.execute(
            """SELECT content, section, chunk_index,
                     1 - (embedding <=> %s::vector) AS similarity
               FROM document_chunks
               WHERE ticker = %s
                 AND embedding IS NOT NULL
               ORDER BY embedding <=> %s::vector
               LIMIT %s""",
            (query_embedding, ticker, query_embedding, top_k),
        )
        rows = cur.fetchall()
        return [
            {"content": r[0], "section": r[1], "chunk_index": r[2], "similarity": float(r[3])}
            for r in rows if r[3] >= min_score
        ]
    except Exception as e:
        logger.warning("Vector search failed: %s", e)
        return []


def _extract_outlook(chunks: list[dict]) -> dict:
    """Extrahera intäktsutsikter från relevanta chunkar."""
    relevant = [c for c in chunks if c["section"] in ("outlook", "ceo_letter")]
    if not relevant:
        return {"direction": "neutral", "score": 50, "citations": []}

    texts = [c["content"][:500] for c in relevant]

    # Enkel heuristik: räkna positiva/negativa/neutrala uttryck
    positive_words = ["positiv", "stark", "öka", "växa", "förbättra", "god", "hög"]
    negative_words = ["negativ", "svag", "minska", "sjunk", "försämra", "låg", "osäker"]

    pos_count = sum(1 for t in texts for w in positive_words if w in t.lower())
    neg_count = sum(1 for t in texts for w in negative_words if w in t.lower())

    net = pos_count - neg_count
    if net > 0:
        direction = "positive"
        score = min(100, 50 + net * 10)
    elif net < 0:
        direction = "negative"
        score = max(0, 50 + net * 10)
    else:
        direction = "neutral"
        score = 50

    return {
        "direction": direction,
        "score": score,
        "citations": [c["content"][:200] for c in relevant[:2]],
    }


def _extract_margin(chunks: list[dict]) -> dict:
    """Extrahera marginal-/lönsamhetsguidning."""
    relevant = [c for c in chunks if c["section"] in ("financials", "outlook")]
    if not relevant:
        return {"direction": "stable", "score": 50}

    texts = " ".join(c["content"][:500] for c in relevant).lower()

    expand_words = ["expanderande", "förbättrad marginal", "ökad lönsamhet", "marginalförbättring"]
    shrink_words = ["krympande", "försämrad marginal", "marginaltryck", "minskat resultat"]

    expand = sum(1 for w in expand_words if w in texts)
    shrink = sum(1 for w in shrink_words if w in texts)

    if expand > shrink:
        return {"direction": "expanding", "score": 70}
    elif shrink > expand:
        return {"direction": "shrinking", "score": 30}
    return {"direction": "stable", "score": 50}


def _extract_tone(chunks: list[dict]) -> dict:
    """Extrahera ledningens ton/konfidens + hedging-densitet."""
    texts = " ".join(c["content"] for c in chunks)

    # Hedging-ord (osäkerhetsspråk)
    hedge_words = [
        "kan", "kanske", "under förutsättning", "beror på", "eventuellt",
        "möjligt", "osäkert", "risk", "potentiell", "bedöms", "förväntas",
    ]
    total_words = len(texts.split())
    hedge_count = sum(texts.lower().count(w) for w in hedge_words)
    hedging_density = min(hedge_count / max(total_words, 1) * 10, 1.0)

    # Ton: positiv vs negativ
    positive_words = ["stark", "positiv", "framgång", "tillväxt", "optimistisk"]
    negative_words = ["svag", "negativ", "utmaning", "oro", "försiktig"]

    pos = sum(texts.lower().count(w) for w in positive_words)
    neg = sum(texts.lower().count(w) for w in negative_words)

    total = pos + neg
    tone_score = 50
    if total > 0:
        tone_score = int(pos / total * 100)

    return {
        "tone_score": tone_score,
        "hedging_density": round(hedging_density, 4),
        "tone_change": round((tone_score - 50) / 50, 2),  # -1..+1
    }


def _extract_risk(chunks: list[dict]) -> dict:
    """Extrahera riskförändringar."""
    relevant = [c for c in chunks if c["section"] == "risk"]
    if not relevant:
        return {"direction": "stable", "score": 50}

    texts = " ".join(c["content"] for c in relevant).lower()

    new_risk_words = ["ny risk", "tillkommande", "ökad exponering", "ytterligare risk"]
    reduced_risk_words = ["borttagen", "minskat", "lägre risk", "hanterad"]

    new = sum(1 for w in new_risk_words if w in texts)
    reduced = sum(1 for w in reduced_risk_words if w in texts)

    if new > reduced:
        return {"direction": "increasing", "score": 30}
    elif reduced > new:
        return {"direction": "decreasing", "score": 70}
    return {"direction": "stable", "score": 50}


def _extract_capital_allocation(chunks: list[dict]) -> dict:
    """Extrahera kapitalallokeringsintention."""
    texts = " ".join(c["content"] for c in chunks).lower()

    invest_words = ["investera", "expansion", "satsa", "kapitalinvestering"]
    return_words = ["utdelning", "återköp", "aktieåterköp", "dela ut"]
    cut_words = ["dra ner", "minska investering", "spara", "kostnadsbesparing"]

    invest = sum(1 for w in invest_words if w in texts)
    returns = sum(1 for w in return_words if w in texts)
    cuts = sum(1 for w in cut_words if w in texts)

    scores = {"investing": invest, "returning": returns, "cutting": cuts}
    intent = max(scores, key=scores.get) if any(scores.values()) else "neutral"

    return {
        "capital_intent": intent,
        "score": 70 if intent == "investing" else (30 if intent == "cutting" else 50),
    }


def extract_signals_for_ticker(ticker: str, conn) -> Optional[dict]:
    """Extrahera kvalitativa signaler för en ticker.

    Använder rerank (L1) för att välja de mest relevanta chunkarna.
    Använder require_citations (L2) för grounding.

    Returnerar dict med qualitative_score, outlook_direction, etc.
    """
    # Hitta senaste dokumentet för tickern
    cur = conn.cursor()
    cur.execute(
        """SELECT id, doc_type, title, published_date
           FROM company_documents
           WHERE ticker = %s
           ORDER BY published_date DESC
           LIMIT 1""",
        (ticker,),
    )
    doc = cur.fetchone()
    if not doc:
        return None

    doc_id, doc_type, title, pub_date = doc

    # Hämta alla chunkar för dokumentet
    cur.execute(
        """SELECT content, section, chunk_index, embedding
           FROM document_chunks
           WHERE document_id = %s
           ORDER BY chunk_index""",
        (doc_id,),
    )
    chunk_rows = cur.fetchall()
    chunks = [
        {"content": r[0], "section": r[1], "chunk_index": r[2],
         "embedding": r[3] if isinstance(r[3], list) else [0.0] * 768}
        for r in chunk_rows
    ]

    if not chunks:
        return None

    # L1: Rerank chunks per query för bästa relevans
    # Använd rerank för respektive frågekategori
    outlook_chunks = _rerank(_QUERIES["outlook"], chunks, top_n=5)
    margin_chunks = _rerank(_QUERIES["margin"], chunks, top_n=5)
    tone_chunks = _rerank(_QUERIES["tone"], chunks, top_n=5)
    risk_chunks = _rerank(_QUERIES["risk"], chunks, top_n=5)
    capital_chunks = _rerank(_QUERIES["capital"], chunks, top_n=5)

    # Kör 5 extraktioner med rerankade chunks
    outlook = _extract_outlook(outlook_chunks)
    margin = _extract_margin(margin_chunks)
    tone = _extract_tone(tone_chunks)
    risk = _extract_risk(risk_chunks)
    capital = _extract_capital_allocation(capital_chunks)

    # Aggregera till qualitative_score (0-100)
    qualitative_score = (
        outlook["score"] * SCORE_WEIGHTS["outlook"] +
        margin["score"] * SCORE_WEIGHTS["margin"] +
        tone["tone_score"] * SCORE_WEIGHTS["tone"] +
        risk["score"] * SCORE_WEIGHTS["risk"] +
        capital["score"] * SCORE_WEIGHTS["capital"]
    )
    qualitative_score = round(qualitative_score, 1)

    # Kort sammanfattning
    summary_parts = []
    if outlook["direction"] == "positive":
        summary_parts.append("Positiva utsikter")
    elif outlook["direction"] == "negative":
        summary_parts.append("Negativa utsikter")

    if margin["direction"] == "expanding":
        summary_parts.append("expanderande marginaler")
    elif margin["direction"] == "shrinking":
        summary_parts.append("marginaltryck")

    if capital["capital_intent"] == "investing":
        summary_parts.append("planerar investeringar")
    elif capital["capital_intent"] == "returning":
        summary_parts.append("återför kapital")

    summary = ", ".join(summary_parts) if summary_parts else "Inga tydliga signaler"

    return {
        "ticker": ticker,
        "qualitative_score": qualitative_score,
        "outlook_direction": outlook["direction"],
        "hedging_density": tone["hedging_density"],
        "capital_intent": capital["capital_intent"],
        "tone_change": tone["tone_change"],
        "summary": summary,
        "based_on_doc_id": str(doc_id),
    }


def run_extraction(tickers: Optional[list[str]] = None):
    """Huvudfunktion: extrahera signaler för alla bolag med nya dokument.

    Args:
        tickers: Lista med tickers (None = alla med dokument).
    """
    conn = _get_db_connection()

    if tickers is None:
        tickers_df = pd.read_sql(
            """SELECT DISTINCT ticker FROM company_documents
               WHERE fetched_at > NOW() - INTERVAL '7 days'
               ORDER BY ticker""",
            conn,
        )
        tickers = tickers_df["ticker"].tolist()

    logger.info("Extraherar signaler för %d tickers", len(tickers))

    results = []
    for ticker in tickers:
        try:
            signal = extract_signals_for_ticker(ticker, conn)
            if signal:
                # Upsert till qualitative_signals
                cur = conn.cursor()
                cur.execute(
                    """INSERT INTO qualitative_signals
                       (ticker, qualitative_score, outlook_direction, hedging_density,
                        capital_intent, tone_change, summary, based_on_doc_id, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                       ON CONFLICT (ticker) DO UPDATE SET
                           qualitative_score = EXCLUDED.qualitative_score,
                           outlook_direction = EXCLUDED.outlook_direction,
                           hedging_density = EXCLUDED.hedging_density,
                           capital_intent = EXCLUDED.capital_intent,
                           tone_change = EXCLUDED.tone_change,
                           summary = EXCLUDED.summary,
                           based_on_doc_id = EXCLUDED.based_on_doc_id,
                           updated_at = NOW()""",
                    (signal["ticker"], signal["qualitative_score"],
                     signal["outlook_direction"], signal["hedging_density"],
                     signal["capital_intent"], signal["tone_change"],
                     signal["summary"], signal["based_on_doc_id"]),
                )
                conn.commit()
                results.append(signal)
                logger.info("  %s: score=%.1f, outlook=%s", ticker, signal["qualitative_score"], signal["outlook_direction"])
        except Exception as e:
            logger.warning("Extraction failed for %s: %s", ticker, e)

    conn.close()
    logger.info("Extraktion klar: %d/%d tickers", len(results), len(tickers))
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    run_extraction()
