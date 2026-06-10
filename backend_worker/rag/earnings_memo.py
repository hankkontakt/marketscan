"""
earnings_memo.py — AI-rapportmemo per bolag och rapport (Spec 08 + #2).
=====================================================================

För varje bolag med en ny rapport i company_documents: hämta relevanta chunkar
(pgvector → cross-encoder rerank), kör LLM med strikt JSON-schema och grounding
(varje siffra måste citera en källa), spara i earnings_memos.

Inga svenska earnings-call-transkript finns → arbetar mot delårs-/årsrapporter
som RAG-pipelinen (#7) redan ingestat.

Anrop:
    python -m backend_worker.rag.earnings_memo               # alla med ny rapport
    python -m backend_worker.rag.earnings_memo --ticker ERIC-B.ST
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from typing import Optional

import psycopg2

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

_QUERY = "utsikter resultat marginal guidning risk kapitalallokering"
_NUM_RE = re.compile(r"\d")
_CIT_RE = re.compile(r"\[KÄLLA")

MEMO_SCHEMA = {
    "type": "object",
    "properties": {
        "nyckeltal_kommentar": {"type": "string"},
        "ledningston": {"type": "string", "enum": ["positiv", "neutral", "defensiv"]},
        "tre_citat": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
        "implicit_guidning": {"type": "string"},
        "sektor_jamforelse": {"type": "string"},
        "sammanfattning": {"type": "string"},
    },
    "required": ["ledningston", "tre_citat", "sammanfattning"],
}


def _grounding_ok(memo: dict) -> bool:
    """Returnerar False om någon mening med en siffra saknar [KÄLLA ...]."""
    text = " ".join(str(memo.get(k, "")) for k in ("nyckeltal_kommentar", "implicit_guidning", "sammanfattning"))
    for sent in re.split(r"(?<=[.!?])\s+", text):
        if _NUM_RE.search(sent) and not _CIT_RE.search(sent):
            return False
    return True


def generate_memo_for_ticker(ticker: str, conn) -> Optional[dict]:
    from backend_worker.rag.extract_signals import _find_relevant_chunks
    from apps.api.core.llm_client import llm_complete, llm_embed
    try:
        from apps.api.core.reranker import rerank
    except Exception:  # noqa: BLE001
        def rerank(query, chunks, top_n=6, text_key="content"):
            return chunks[:top_n]

    cur = conn.cursor()
    # Senaste rapport för ticker
    cur.execute(
        "SELECT id, published_date FROM company_documents WHERE ticker = %s ORDER BY published_date DESC LIMIT 1",
        (ticker,),
    )
    row = cur.fetchone()
    if not row:
        return None
    doc_id, published_date = row

    # Idempotens
    cur.execute("SELECT memo FROM earnings_memos WHERE ticker = %s AND doc_id = %s", (ticker, doc_id))
    existing = cur.fetchone()
    if existing:
        return existing[0] if isinstance(existing[0], dict) else json.loads(existing[0])

    # Hämta + rerank chunkar
    q_emb = asyncio.run(llm_embed([_QUERY]))[0]
    chunks = _find_relevant_chunks(conn, ticker, q_emb, top_k=12)
    if not chunks:
        logger.info("Inga chunkar för %s — hoppar", ticker)
        return None
    chunks = rerank(_QUERY, chunks, top_n=6)

    sources = "\n".join(f"[KÄLLA {c.get('chunk_index', i)}] {c.get('content', '')}" for i, c in enumerate(chunks))
    prompt = (
        f"Du skriver ett kort analysmemo för {ticker}s senaste rapport.\n"
        "Använd ENBART informationen i KÄLLORNA nedan. Varje siffra du nämner MÅSTE följas "
        "av [KÄLLA i] där i är källnumret. Hitta INTE på tal. Svara som JSON enligt schemat.\n\n"
        f"KÄLLOR:\n{sources}"
    )
    result = asyncio.run(llm_complete(prompt, task="earnings_memo", json_schema=MEMO_SCHEMA, prefer="quality"))
    if not result or result.get("error") or "ledningston" not in result:
        logger.warning("LLM gav inget giltigt memo för %s", ticker)
        return None

    if not _grounding_ok(result):
        result["_grounding_warning"] = True

    cur.execute(
        """INSERT INTO earnings_memos (ticker, doc_id, published_date, memo)
           VALUES (%s, %s, %s, %s)
           ON CONFLICT (ticker, doc_id) DO UPDATE SET memo = EXCLUDED.memo, created_at = NOW()""",
        (ticker, doc_id, published_date, json.dumps(result, ensure_ascii=False)),
    )
    conn.commit()
    logger.info("✅ Memo sparat för %s (doc %s)", ticker, doc_id)
    return result


def _tickers_with_new_report(conn) -> list[str]:
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT cd.ticker
        FROM company_documents cd
        LEFT JOIN earnings_memos em ON em.ticker = cd.ticker AND em.doc_id = cd.id
        WHERE em.id IS NULL
    """)
    return [r[0] for r in cur.fetchall()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", help="En enskild ticker (annars alla med ny rapport)")
    args = ap.parse_args()

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        logger.error("DATABASE_URL saknas")
        sys.exit(1)

    conn = psycopg2.connect(dsn)
    made = errors = 0
    try:
        tickers = [args.ticker] if args.ticker else _tickers_with_new_report(conn)
        logger.info("Genererar memo för %d bolag", len(tickers))
        for tk in tickers:
            try:
                if generate_memo_for_ticker(tk, conn):
                    made += 1
            except Exception as e:  # noqa: BLE001
                logger.warning("Memo misslyckades för %s: %s", tk, e)
                conn.rollback()
                errors += 1
    finally:
        conn.close()
    print(json.dumps({"memos_created": made, "errors": errors}))


if __name__ == "__main__":
    main()
