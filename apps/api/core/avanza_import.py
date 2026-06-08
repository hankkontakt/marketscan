"""
Avanza CSV import — parse holdings export, map names to tickers.
No pandas dependency, pure Python + csv module (API-compatible).
"""
import csv
import io
import json
import logging

logger = logging.getLogger(__name__)

# Built-in ticker map: Avanza company name → Yahoo Finance ticker
# Inlined directly (no file dependency) for Vercel serverless compatibility.
_BUILTIN_MAP: dict[str, str] = {
    "ericsson b": "ERIC-B.ST",
    "ericsson a": "ERIC-A.ST",
    "volvo b": "VOLV-B.ST",
    "volvo a": "VOLV-A.ST",
    "h&m b": "HM-B.ST",
    "hennes & mauritz b": "HM-B.ST",
    "investor b": "INVE-B.ST",
    "investor a": "INVE-A.ST",
    "industrivärden c": "INDU-C.ST",
    "industrivärden a": "INDU-A.ST",
    "atlas copco a": "ATCO-A.ST",
    "atlas copco b": "ATCO-B.ST",
    "assa abloy b": "ASSA-B.ST",
    "seb a": "SEB-A.ST",
    "handelsbanken a": "SHB-A.ST",
    "swedbank a": "SWED-A.ST",
    "nordea bank": "NDA-SE.ST",
    "telia": "TELIA.ST",
    "telia company": "TELIA.ST",
    "abb": "ABB.ST",
    "sandvik": "SAND.ST",
    "skf b": "SKF-B.ST",
    "alfa laval": "ALFA.ST",
    "boliden": "BOL.ST",
    "ssab b": "SSAB-B.ST",
    "ssab a": "SSAB-A.ST",
    "sca b": "SCA-B.ST",
    "nibe industrier b": "NIBE-B.ST",
    "essity b": "ESSITY-B.ST",
    "getinge b": "GETI-B.ST",
    "astrazeneca": "AZN.ST",
    "evolution": "EVO.ST",
    "embracer group b": "EMBRAC-B.ST",
    "eqt": "EQT.ST",
    "latour b": "LATO-B.ST",
    "lifco b": "LIFCO-B.ST",
    "castellum": "CAST.ST",
    "wihlborgs": "WIHL.ST",
    "fabege": "FABG.ST",
    "sagax b": "SAGA-B.ST",
    "balder b": "BALD-B.ST",
    "lundin energy": "LUNE.ST",
    "mips": "MIPS.ST",
    "invisio": "INVISIO.ST",
    "ncab group": "NCAB.ST",
    "vitrolife": "VITROLIFE.ST",
    "sinch": "SINCH.ST",
    "tele2 b": "TEL2-B.ST",
    "kinnevik b": "KINV-B.ST",
    "trelleborg b": "TRELLEBORG-B.ST",
    "hexagon b": "HEXA-B.ST",
    "peab b": "PEAB-B.ST",
    "ncc b": "NCC-B.ST",
    "jm": "JM.ST",
    "bure equity": "BURE.ST",
    "indutrade": "INDT.ST",
    "bufab": "BUFAB.ST",
    "troax": "TROAX.ST",
    "apple": "AAPL",
    "microsoft": "MSFT",
    "alphabet a": "GOOGL",
    "alphabet c": "GOOG",
    "amazon": "AMZN",
    "meta platforms": "META",
    "meta": "META",
    "nvidia": "NVDA",
    "tesla": "TSLA",
    "broadcom": "AVGO",
    "oracle": "ORCL",
    "salesforce": "CRM",
    "adobe": "ADBE",
    "amd": "AMD",
    "advanced micro devices": "AMD",
    "intel": "INTC",
    "cisco": "CSCO",
    "qualcomm": "QCOM",
    "texas instruments": "TXN",
    "palantir": "PLTR",
    "snowflake": "SNOW",
    "jp morgan": "JPM",
    "jpmorgan": "JPM",
    "bank of america": "BAC",
    "goldman sachs": "GS",
    "morgan stanley": "MS",
    "blackrock": "BLK",
    "visa": "V",
    "mastercard": "MA",
    "berkshire hathaway b": "BRK-B",
    "paypal": "PYPL",
    "johnson & johnson": "JNJ",
    "unitedhealth": "UNH",
    "eli lilly": "LLY",
    "pfizer": "PFE",
    "abbvie": "ABBV",
    "merck": "MRK",
    "bristol-myers squibb": "BMY",
    "gilead": "GILD",
    "walmart": "WMT",
    "costco": "COST",
    "coca-cola": "KO",
    "pepsico": "PEP",
    "mcdonald's": "MCD",
    "nike": "NKE",
    "starbucks": "SBUX",
    "home depot": "HD",
    "netflix": "NFLX",
    "disney": "DIS",
    "exxon mobil": "XOM",
    "chevron": "CVX",
    "asml": "ASML.AS",
    "asml holding": "ASML.AS",
    "sap": "SAP.DE",
    "siemens": "SIE.DE",
    "allianz": "ALV.DE",
    "basf": "BAS.DE",
    "bayer": "BAYN.DE",
    "volkswagen": "VOW3.DE",
    "bmw": "BMW.DE",
    "mercedes-benz": "MBG.DE",
    "lvmh": "MC.PA",
    "totalenergies": "TTE.PA",
    "sanofi": "SAN.PA",
    "bnp paribas": "BNP.PA",
    "shell": "SHEL.L",
    "hsbc": "HSBA.L",
    "unilever": "ULVR.L",
    "bp": "BP.L",
    "rio tinto": "RIO.L",
    "nestle": "NESN.SW",
    "novartis": "NOVN.SW",
    "roche": "ROG.SW",
    "novo nordisk b": "NOVO-B.CO",
    "novo nordisk": "NOVO-B.CO",
    "equinor": "EQNR.OL",
    "nokia": "NOKIA.HE",
}


# ── Market suffix mapping: Avanza market code → Yahoo Finance suffix ──────────
_MARKET_SUFFIX: dict[str, str | None] = {
    "XSTO": ".ST",   # Nasdaq Stockholm
    "FNSE": ".ST",   # First North Sweden
    "NGMX": ".ST",   # Nordic Growth Market
    "XHEL": ".HE",   # Helsinki
    "XCSE": ".CO",   # Copenhagen
    "XOSL": ".OL",   # Oslo
    "XLON": ".L",    # London
    "XETR": ".DE",   # Frankfurt / Xetra
    "XPAR": ".PA",   # Euronext Paris
    "XAMS": ".AS",   # Euronext Amsterdam
    "XMIL": ".MI",   # Borsa Italiana
    "XNYS": "",      # NYSE (no suffix in Yahoo)
    "XNAS": "",      # Nasdaq (no suffix)
    "FUND": None,    # Actively managed fund — no exchange-traded ticker
}


def kortnamn_to_ticker(kortnamn: str, marknad: str) -> str | None:
    """
    Derive Yahoo Finance ticker from Avanza kortnamn + market code.
    Examples:
      "INVE B" + "XSTO" → "INVE-B.ST"
      "NCAB"   + "XSTO" → "NCAB.ST"
      "AAPL"   + "XNAS" → "AAPL"
    Returns None for funds (FUND) or unknown markets.
    """
    key = (marknad or "").upper().strip()
    if key not in _MARKET_SUFFIX:
        return None  # unknown market — don't guess
    suffix = _MARKET_SUFFIX[key]
    if suffix is None:
        return None  # actively managed fund
    base = kortnamn.strip().replace(" ", "-")
    return f"{base}{suffix}" if base else None


def normalize_name(name: str) -> str:
    return (
        name.lower()
        .strip()
        .replace(",", "")
        .replace(".", "")
        .replace("  ", " ")
    )


def find_ticker(name: str, custom_map: dict[str, str] | None = None) -> str | None:
    """Look up ticker by company name. Checks custom_map, then built-in map."""
    norm = normalize_name(name)
    if custom_map and norm in custom_map:
        return custom_map[norm]
    if norm in _BUILTIN_MAP:
        return _BUILTIN_MAP[norm]
    return None


def parse_swedish_number(s: str) -> float | None:
    """Convert Swedish number format '1 234,56' → 1234.56"""
    if s is None or s.strip() == "":
        return None
    cleaned = str(s).strip().replace("\xa0", "").replace(" ", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_avanza_csv(content: str | bytes) -> list[dict]:
    """
    Parse Avanza CSV export format.

    Handles:
    - UTF-8 BOM / latin-1 encoding
    - Semicolon or comma separator
    - Swedish number format
    - Multiple column naming variants
    """
    if isinstance(content, bytes):
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
    else:
        text = content

    first_line = text.split("\n")[0]
    sep = ";" if ";" in first_line else ","

    reader = csv.DictReader(io.StringIO(text), delimiter=sep)

    # Normalize column names
    col_map = {}
    for col in reader.fieldnames or []:
        c = col.lower().strip()
        if any(x in c for x in ["värdepapper", "namn", "name", "security"]):
            col_map[col] = "name"
        elif any(x in c for x in ["antal", "quantity", "shares"]):
            col_map[col] = "shares"
        elif any(x in c for x in ["köpkurs", "genomsnittlig", "purchase", "cost"]):
            col_map[col] = "cost_basis"
        elif "kurs" in c and "köp" not in c and "price" in c:
            col_map[col] = "current_price"
        elif any(x in c for x in ["resultat", "result", "change"]):
            col_map[col] = "result"

    rows = []
    for row in reader:
        mapped = {}
        for orig_col, val in row.items():
            new_key = col_map.get(orig_col, orig_col)
            mapped[new_key] = val

        name = (mapped.get("name") or "").strip()
        if not name or name == "":
            continue

        result = {
            "name": name,
            "shares": parse_swedish_number(mapped.get("shares", "")),
            "cost_basis": parse_swedish_number(mapped.get("cost_basis", "")),
            "current_price": parse_swedish_number(mapped.get("current_price", "")),
        }
        rows.append(result)

    return rows


def parse_positioner_csv(content: str | bytes) -> list[dict]:
    """
    Parse Avanza 'positioner' CSV exported via Min ekonomi → Analys → Exportera data.

    Supports both variants:
    - Per konto:      Kontonummer;Namn;Kortnamn;Volym;Marknadsvärde;GAV (SEK);GAV;Valuta;Land;ISIN;Marknad;Typ
    - Sammanstallda: Namn;Kortnamn;Volym;Marknadsvärde;GAV (SEK);GAV;Valuta;Land;ISIN;Marknad;Typ

    Returns a list of dicts with:
        name, kortnamn, ticker, shares, cost_basis, isin, marknad, av_typ, mapped
    """
    if isinstance(content, bytes):
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
    else:
        text = content

    reader = csv.DictReader(io.StringIO(text), delimiter=";")

    rows: list[dict] = []
    for row in reader:
        row = {k: (v or "").strip() for k, v in row.items()}  # type: ignore[assignment]

        namn = row.get("Namn", "").strip()
        if not namn:
            continue

        kortnamn = row.get("Kortnamn", "").strip()
        volym = parse_swedish_number(row.get("Volym", ""))
        # GAV (SEK) is the cost basis in local currency — prefer it over GAV
        gav_raw = row.get("GAV (SEK)") or row.get("GAV") or ""
        gav_sek = parse_swedish_number(gav_raw)
        isin = row.get("ISIN", "").strip()
        marknad = row.get("Marknad", "").strip()
        av_typ = row.get("Typ", "").strip().upper()

        if volym is None or volym <= 0:
            continue

        # Primary: derive ticker from kortnamn + market code (exact, no guessing)
        ticker = kortnamn_to_ticker(kortnamn, marknad)

        # Fallback for stocks with unknown market: name-based lookup
        if ticker is None and av_typ != "FUND":
            ticker = find_ticker(namn)

        rows.append({
            "name":       namn,
            "kortnamn":   kortnamn,
            "ticker":     ticker,
            "shares":     volym,
            "cost_basis": gav_sek,
            "isin":       isin,
            "marknad":    marknad,
            "av_typ":     av_typ,
            "mapped":     ticker is not None,
        })

    return rows


def parse_inkopskurser_csv(
    content: str | bytes,
) -> dict[str, list[tuple[str, float]]]:
    """
    Parse Avanza 'Historiska inköpskurser' CSV.

    Format: Datum;Konto;ISIN;Namn;Inköpskurs (SEK);Antal

    Returns: {isin: [(date_str, antal), ...]} sorted ascending by date.
    Used to derive the original purchase date for each holding.
    """
    if isinstance(content, bytes):
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
    else:
        text = content

    reader = csv.DictReader(io.StringIO(text), delimiter=";")

    result: dict[str, list[tuple[str, float]]] = {}
    for row in reader:
        isin  = (row.get("ISIN") or "").strip()
        datum = (row.get("Datum") or "").strip()

        # "Antal" column name may vary slightly
        antal_str = ""
        for k, v in row.items():
            if "antal" in (k or "").lower():
                antal_str = v or ""
                break
        antal = parse_swedish_number(antal_str)

        if not isin or not datum or antal is None:
            continue

        if isin not in result:
            result[isin] = []
        result[isin].append((datum, antal))

    # Sort each ISIN's snapshots ascending (oldest first)
    for isin_key in result:
        result[isin_key].sort(key=lambda x: x[0])

    return result


def get_buy_date(
    isin: str,
    current_antal: float,
    inkopskurser: dict[str, list[tuple[str, float]]],
) -> str | None:
    """
    Estimate the purchase date from inkopskurser history.

    Strategy:
    1. Find the earliest snapshot where antal matches current_antal (±0.1% tolerance).
    2. If no exact match, return the first date the ISIN appears in the file.
    """
    snapshots = inkopskurser.get(isin, [])
    if not snapshots:
        return None
    tol = max(0.001, abs(current_antal) * 0.001)
    for date_str, antal in snapshots:  # already sorted ascending
        if abs(antal - current_antal) <= tol:
            return date_str
    return snapshots[0][0]  # fallback: first appearance


def build_preview(rows: list[dict], custom_map: dict[str, str] | None = None) -> list[dict]:
    """Build preview rows with ticker mapping results."""
    preview = []
    for row in rows:
        ticker = find_ticker(row["name"], custom_map)
        preview.append({
            "name": row["name"],
            "ticker": ticker,
            "shares": row["shares"],
            "cost_basis": row["cost_basis"],
            "current_price": row["current_price"],
            "mapped": ticker is not None,
        })
    return preview
