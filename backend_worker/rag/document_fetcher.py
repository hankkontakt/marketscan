"""
document_fetcher.py — Hämtar svenska års-/delårsrapporter för RAG-systemet.

Källor (gratis):
  1. MFN.se (Modular Finance News) — publika feeds per bolag
  2. Bolagens IR-sidor via Nasdaq Nordic IR-portal

PDF→text via pypdf/pdfplumber. Sektionstaggar via rubrik-heuristik.
Idempotent: hoppar dokument som redan finns i company_documents.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# Sektioner att identifiera i svenska rapporter
SECTION_PATTERNS = {
    "outlook": [
        r"utsikter", r"framtidsutsikter", r"framtiden", r"kommande\s+period",
        r"marknadsutsikter", r"branschutsikter", r"under\s+kommande\s+kvartal",
    ],
    "ceo_letter": [
        r"vd\s+har\s+ordet", r"verkställande\s+ direktör", r"chefens\s+ord",
        r"kommentar\s+från\s+vd", r"ordföranden\s+har\s+ordet",
    ],
    "risk": [
        r"väsentliga\s+risker", r"riskfaktorer", r"risker\s+och\s+osäkerhetsfaktorer",
        r"finansiella\s+risker", r"riskhantering", r"operativa\s+risker",
    ],
    "financials": [
        r"resultaträkning", r"balansräkning", r"kassaflöde", r"finansiella\s+rapporter",
        r"noter", r"nyckeltal", r"finansiell\s+ställning", r"resultat",
    ],
}

# API-endpoints (gratis)
MFN_BASE = "https://www.mfn.se/api"

PDF_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "pdf_cache"
PDF_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _detect_section(text: str) -> str:
    """Identifiera sektion baserat på rubrik-heuristik (svenska)."""
    text_lower = text.lower()
    for section, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return section
    return "other"


def _extract_text_from_pdf(pdf_path: Path) -> Optional[str]:
    """Extrahera text från PDF med fallback-ordning."""
    # Försök pdfplumber först (bättre på svenska PDFer)
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            pages = [page.extract_text() for page in pdf.pages if page.extract_text()]
            if pages:
                return "\n\n".join(pages)
    except ImportError:
        pass
    except Exception as e:
        logger.debug("pdfplumber failed for %s: %s", pdf_path.name, e)

    # Fallback till pypdf
    try:
        import pypdf
        reader = pypdf.PdfReader(pdf_path)
        pages = [page.extract_text() for page in reader.pages if page.extract_text()]
        if pages:
            return "\n\n".join(pages)
    except ImportError:
        logger.error("pdfplumber eller pypdf krävs för PDF-extraktion")
    except Exception as e:
        logger.debug("pypdf failed for %s: %s", pdf_path.name, e)

    return None


def _chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list[dict]:
    """Dela text i chunkar med overlap, sektionstaggade.

    Varje chunk: {"content": str, "section": str, "chunk_index": int}
    """
    if not text:
        return []

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current_chunk = []
    current_size = 0
    chunk_idx = 0

    for sent in sentences:
        sent_size = len(sent)
        if current_size + sent_size > chunk_size and current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append({
                "content": chunk_text,
                "section": _detect_section(chunk_text),
                "chunk_index": chunk_idx,
            })
            chunk_idx += 1
            # Overlap: behåll sista meningarna
            overlap_sents = []
            overlap_size = 0
            for s in reversed(current_chunk):
                if overlap_size + len(s) > overlap:
                    break
                overlap_sents.insert(0, s)
                overlap_size += len(s)
            current_chunk = overlap_sents
            current_size = overlap_size

        current_chunk.append(sent)
        current_size += sent_size

    if current_chunk:
        chunk_text = " ".join(current_chunk)
        chunks.append({
            "content": chunk_text,
            "section": _detect_section(chunk_text),
            "chunk_index": chunk_idx,
        })

    return chunks


def fetch_mfn_reports(ticker: str, days_back: int = 30) -> list[dict]:
    """Hämta rapporter från MFN.se för en ticker.

    Returns:
        Lista med dicts: {ticker, doc_type, title, published_date, source_url, raw_text}
    """
    reports = []
    try:
        # MFN API: sök efter pressmeddelanden/rapporter per bolag
        url = f"{MFN_BASE}/feed?ticker={ticker}&days={days_back}"
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            logger.debug("MFN returned %d for %s", resp.status_code, ticker)
            return reports

        data = resp.json()
        items = data if isinstance(data, list) else data.get("items", [])

        for item in items:
            doc_type = "press_release"
            title = item.get("title", "")
            source_url = item.get("link", "")
            pub_date = item.get("published", "")[:10] if item.get("published") else ""

            # Klassificera dokumenttyp
            title_lower = title.lower()
            if any(kw in title_lower for kw in ["årsredovisning", "annual report", "årsrapport"]):
                doc_type = "annual_report"
            elif any(kw in title_lower for kw in ["delårsrapport", "kvartalsrapport", "interim"]):
                doc_type = "interim_report"

            reports.append({
                "ticker": ticker,
                "doc_type": doc_type,
                "title": title,
                "published_date": pub_date,
                "source_url": source_url,
                "language": "sv",
                "raw_text": None,  # Laddas vid behov
            })
    except Exception as e:
        logger.warning("MFN fetch failed for %s: %s", ticker, e)

    return reports


def process_document(
    report: dict,
    conn,
    embed_func=None,
) -> Optional[dict]:
    """Processa ett dokument: extrahera text, chunka, embedda, spara.

    Args:
        report: Dict med dokument-info (ticker, doc_type, title, etc.)
        conn: DB-anslutning (psycopg2).
        embed_func: Funktion för embedding (llm_embed), om None hoppas embedding.

    Returns:
        Dict med {document_id, n_chunks} eller None.
    """
    cur = conn.cursor()

    # Kolla om dokument redan finns
    cur.execute(
        """SELECT id FROM company_documents
           WHERE ticker = %s AND doc_type = %s
             AND published_date = %s AND source_url = %s""",
        (report["ticker"], report["doc_type"], report["published_date"], report["source_url"]),
    )
    existing = cur.fetchone()
    if existing:
        logger.info("Dokument finns redan: %s/%s", report["ticker"], report["title"][:50])
        return None

    # Ladda PDF om source_url finns
    raw_text = report.get("raw_text")
    if not raw_text and report.get("source_url"):
        pdf_url = report["source_url"]
        if pdf_url.endswith(".pdf") or "/pdf/" in pdf_url:
            try:
                resp = requests.get(pdf_url, timeout=60)
                if resp.status_code == 200:
                    # Spara PDF till cache
                    pdf_hash = hashlib.md5(pdf_url.encode()).hexdigest()[:16]
                    pdf_path = PDF_CACHE_DIR / f"{pdf_hash}.pdf"
                    pdf_path.write_bytes(resp.content)

                    # Extrahera text
                    text = _extract_text_from_pdf(pdf_path)
                    if text:
                        raw_text = text
            except Exception as e:
                logger.warning("PDF download failed for %s: %s", pdf_url[:80], e)

    if not raw_text:
        logger.warning("Ingen text för %s/%s", report["ticker"], report["title"][:50])
        return None

    # Spara till company_documents
    cur.execute(
        """INSERT INTO company_documents
           (ticker, doc_type, title, published_date, source_url, language, raw_text)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           RETURNING id""",
        (report["ticker"], report["doc_type"], report["title"],
         report["published_date"], report["source_url"], report["language"], raw_text),
    )
    doc_id = cur.fetchone()[0]
    conn.commit()

    # Chunking
    chunks = _chunk_text(raw_text)

    # Embedding + spara chunkar
    texts_to_embed = [c["content"] for c in chunks]
    embeddings = embed_func(texts_to_embed) if embed_func else [[0.0] * 768] * len(chunks)

    for chunk, embedding in zip(chunks, embeddings):
        cur.execute(
            """INSERT INTO document_chunks
               (document_id, ticker, section, chunk_index, content, embedding)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (doc_id, report["ticker"], chunk["section"], chunk["chunk_index"],
             chunk["content"], embedding),
        )
    conn.commit()

    logger.info("Processat %s/%s: %d chunkar", report["ticker"], report["doc_type"], len(chunks))
    return {"document_id": str(doc_id), "n_chunks": len(chunks)}


def run_fetch(days_back: int = 3, tickers: Optional[list[str]] = None):
    """Huvudfunktion: hämta dokument för tickers och processa.

    Args:
        days_back: Antal dagar bakåt att söka.
        tickers: Lista med tickers (None = alla i scan_results).
    """
    import psycopg2
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL required")
        return

    conn = psycopg2.connect(database_url)

    # Hämta tickers om inte givna
    if tickers is None:
        tickers_df = pd.read_sql(
            "SELECT ticker FROM scan_results ORDER BY ticker LIMIT 500", conn
        )
        tickers = tickers_df["ticker"].tolist()

    logger.info("Hämtar dokument för %d tickers (%d dagar)", len(tickers), days_back)

    # Försök använda llm_embed för embeddings
    embed_func = None
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "apps"))
        from api.core.llm_client import llm_embed
        embed_func = llm_embed
    except Exception as e:
        logger.warning("llm_client not available: %s — skipping embeddings", e)

    total_docs = 0
    total_chunks = 0

    for ticker in tickers:
        reports = fetch_mfn_reports(ticker, days_back)
        for report in reports:
            result = process_document(report, conn, embed_func)
            if result:
                total_docs += 1
                total_chunks += result.get("n_chunks", 0)
        time.sleep(0.2)  # Rate limiting

    conn.close()
    logger.info("Klart: %d dokument, %d chunkar", total_docs, total_chunks)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    run_fetch()
