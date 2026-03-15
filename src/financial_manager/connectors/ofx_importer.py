"""OFX/QFX file importer for financial institution exports.

Parses Open Financial Exchange files — the standard format used by Quicken,
GnuCash, Microsoft Money, and most banks/brokerages for data export.

Uses the ``ofxtools`` library if available (full OFX 1.6 / 2.03 support),
with a built-in fallback parser for simple SGML-based OFX files so the
importer works even without the optional dependency.

Supported OFX message sets:
- **Banking (BANKMSGSRSV1)**: Checking/savings transactions
- **Investments (INVSTMTMSGSRSV1)**: Brokerage positions and trades
- **Credit cards (CREDITCARDMSGSRSV1)**: Credit card transactions
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Optional ofxtools import ──────────────────────────────────────────

_ofxtools_available = False
try:
    import ofxtools  # type: ignore[import-untyped,import-not-found]  # noqa: F401

    _ofxtools_available = True
except ImportError:
    pass


def is_ofxtools_available() -> bool:
    """Check whether the ``ofxtools`` library is installed.

    Returns:
        True if ofxtools is importable.
    """
    return _ofxtools_available


# ── Parsed record types ───────────────────────────────────────────────


@dataclass
class OfxTransaction:
    """A single transaction parsed from an OFX/QFX file.

    Attributes:
        date: Transaction date (YYYY-MM-DD).
        fit_id: Financial institution's unique transaction ID.
        name: Payee or description.
        memo: Additional memo text.
        amount: Dollar amount (positive = credit, negative = debit).
        tran_type: OFX transaction type (``DEBIT``, ``CREDIT``, ``INT``, ``DIV``, etc.).
        check_num: Check number (if applicable).
        account_id: Account number (last 4 digits or masked).
        account_type: ``CHECKING``, ``SAVINGS``, ``CREDITCARD``, ``INVESTMENT``.
    """

    date: str = ""
    fit_id: str = ""
    name: str = ""
    memo: str = ""
    amount: float = 0.0
    tran_type: str = ""
    check_num: str = ""
    account_id: str = ""
    account_type: str = ""


@dataclass
class OfxPosition:
    """An investment position from an OFX investment statement.

    Attributes:
        security_id: Security identifier (CUSIP, ticker, etc.).
        security_type: ``STOCK``, ``MFUND``, ``BOND``, ``OTHER``.
        units: Number of shares/units.
        unit_price: Price per unit.
        market_value: Total market value.
        date_acquired: Acquisition date (if available).
        cost_basis: Total cost basis (if available).
    """

    security_id: str = ""
    security_type: str = ""
    units: float = 0.0
    unit_price: float = 0.0
    market_value: float = 0.0
    date_acquired: str = ""
    cost_basis: float = 0.0


@dataclass
class OfxInvestmentTransaction:
    """An investment transaction from an OFX investment statement.

    Attributes:
        date: Transaction date (YYYY-MM-DD).
        fit_id: Transaction ID.
        security_id: Security identifier.
        buy_sell: ``BUY`` or ``SELL``.
        tran_type: Specific type (``BUYSTOCK``, ``SELLSTOCK``, ``INCOME``, ``REINVEST``).
        units: Shares transacted.
        unit_price: Price per share.
        total: Total dollar amount.
        fees: Commission/fees.
        income_type: For income transactions: ``DIV``, ``CGLONG``, ``CGSHORT``, ``INTEREST``.
    """

    date: str = ""
    fit_id: str = ""
    security_id: str = ""
    buy_sell: str = ""
    tran_type: str = ""
    units: float = 0.0
    unit_price: float = 0.0
    total: float = 0.0
    fees: float = 0.0
    income_type: str = ""


@dataclass
class OfxImportResult:
    """Result of importing an OFX/QFX file.

    Attributes:
        source_path: Path to the imported file.
        institution: Institution name from OFX header (if available).
        account_id: Account identifier (masked).
        account_type: Account type.
        date_start: Statement start date.
        date_end: Statement end date.
        currency: Currency code.
        transactions: Bank/credit card transactions.
        positions: Investment positions.
        investment_transactions: Investment buy/sell/income transactions.
        warnings: Non-fatal issues.
    """

    source_path: str = ""
    institution: str = ""
    account_id: str = ""
    account_type: str = ""
    date_start: str = ""
    date_end: str = ""
    currency: str = "USD"
    transactions: list[OfxTransaction] = field(default_factory=list)
    positions: list[OfxPosition] = field(default_factory=list)
    investment_transactions: list[OfxInvestmentTransaction] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ── Date parsing ──────────────────────────────────────────────────────

_OFX_DATE_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})")


def _parse_ofx_date(raw: str) -> str:
    """Parse an OFX date string (YYYYMMDD...) to ISO format.

    Args:
        raw: OFX date like ``20250115120000`` or ``20250115``.

    Returns:
        ISO date string like ``2025-01-15``, or the original string if unparseable.
    """
    if not raw:
        return ""
    m = _OFX_DATE_RE.match(raw.strip())
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return raw.strip()


# ── ofxtools-based parser ─────────────────────────────────────────────


def _import_with_ofxtools(path: Path) -> OfxImportResult:
    """Parse an OFX file using the ofxtools library (full-fidelity parser).

    Args:
        path: Path to the OFX/QFX file.

    Returns:
        Populated OfxImportResult.
    """
    from ofxtools.Parser import OFXTree  # type: ignore[import-untyped,import-not-found]

    result = OfxImportResult(source_path=str(path))

    try:
        parser = OFXTree()
        parser.parse(str(path))
        ofx = parser.convert()
    except Exception as exc:
        result.warnings.append(f"ofxtools parse error: {exc}")
        return result

    # Institution info
    if hasattr(ofx, "sonrs") and ofx.sonrs:
        fi = getattr(ofx.sonrs, "fi", None)
        if fi:
            result.institution = getattr(fi, "org", "") or ""

    # Bank statement messages
    for stmt in getattr(ofx, "statements", []):
        result.account_id = _mask_account(str(getattr(stmt, "account", {}).get("acctid", "") or ""))
        result.account_type = str(getattr(stmt, "account", {}).get("accttype", "CHECKING") or "CHECKING")

        if hasattr(stmt, "banktranlist") and stmt.banktranlist:
            result.date_start = _parse_ofx_date(str(getattr(stmt.banktranlist, "dtstart", "")))
            result.date_end = _parse_ofx_date(str(getattr(stmt.banktranlist, "dtend", "")))

            for txn in getattr(stmt.banktranlist, "transactions", []) or []:
                result.transactions.append(
                    OfxTransaction(
                        date=_parse_ofx_date(str(getattr(txn, "dtposted", ""))),
                        fit_id=str(getattr(txn, "fitid", "")),
                        name=str(getattr(txn, "name", "") or ""),
                        memo=str(getattr(txn, "memo", "") or ""),
                        amount=float(getattr(txn, "trnamt", 0)),
                        tran_type=str(getattr(txn, "trntype", "")),
                        check_num=str(getattr(txn, "checknum", "") or ""),
                        account_id=result.account_id,
                        account_type=result.account_type,
                    )
                )

    logger.info("ofxtools parsed %d transactions from %s", len(result.transactions), path.name)
    return result


# ── Fallback SGML/XML parser ─────────────────────────────────────────

# OFX v1 files are SGML (not proper XML).  We convert them to XML first.
_SGML_HEADER_RE = re.compile(r"^(OFXHEADER|DATA|VERSION|SECURITY|ENCODING|CHARSET|COMPRESSION|OLDFILEUID|NEWFILEUID):.*$", re.MULTILINE)  # noqa: E501
_UNCLOSED_TAG_RE = re.compile(r"<(\w+)>([^<]+)$", re.MULTILINE)


def _sgml_to_xml(content: str) -> str:
    """Convert OFX v1 SGML to well-formed XML.

    Args:
        content: Raw OFX file content.

    Returns:
        XML string that can be parsed by ElementTree.
    """
    # Strip the OFX header block
    cleaned = _SGML_HEADER_RE.sub("", content).strip()

    # Close unclosed tags: <TAG>value → <TAG>value</TAG>
    cleaned = _UNCLOSED_TAG_RE.sub(r"<\1>\2</\1>", cleaned)

    return cleaned


def _import_fallback(path: Path) -> OfxImportResult:
    """Parse an OFX file using the built-in fallback parser.

    This handles simple SGML OFX v1 files by converting to XML first.
    It extracts bank transactions (STMTRS) and basic investment data.

    Args:
        path: Path to the OFX/QFX file.

    Returns:
        Populated OfxImportResult.
    """
    result = OfxImportResult(source_path=str(path))

    try:
        raw_content = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError as exc:
        result.warnings.append(f"Could not read file: {exc}")
        return result

    # Determine if SGML or XML
    xml_content = raw_content if raw_content.strip().startswith("<?xml") else _sgml_to_xml(raw_content)

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        result.warnings.append(f"XML parse error: {exc}")
        return result

    # Extract institution
    fi_org = root.find(".//FI/ORG")
    if fi_org is not None and fi_org.text:
        result.institution = fi_org.text.strip()

    # Extract bank statement transactions
    _extract_bank_transactions(root, result)

    # Extract investment transactions
    _extract_investment_transactions(root, result)

    logger.info(
        "Fallback parser: %d bank txns, %d investment txns from %s",
        len(result.transactions),
        len(result.investment_transactions),
        path.name,
    )
    return result


def _extract_bank_transactions(root: ET.Element, result: OfxImportResult) -> None:
    """Extract bank transactions from an OFX XML tree.

    Args:
        root: Parsed XML root element.
        result: OfxImportResult to populate.
    """
    for stmtrs in root.iter("STMTRS"):
        # Account info
        acct_from = stmtrs.find("BANKACCTFROM")
        if acct_from is not None:
            acctid = acct_from.findtext("ACCTID", "")
            result.account_id = _mask_account(acctid)
            result.account_type = acct_from.findtext("ACCTTYPE", "CHECKING")

        # Date range
        banktranlist = stmtrs.find("BANKTRANLIST")
        if banktranlist is not None:
            result.date_start = _parse_ofx_date(banktranlist.findtext("DTSTART", ""))
            result.date_end = _parse_ofx_date(banktranlist.findtext("DTEND", ""))

            for stmttrn in banktranlist.iter("STMTTRN"):
                result.transactions.append(
                    OfxTransaction(
                        date=_parse_ofx_date(stmttrn.findtext("DTPOSTED", "")),
                        fit_id=stmttrn.findtext("FITID", ""),
                        name=stmttrn.findtext("NAME", "") or "",
                        memo=stmttrn.findtext("MEMO", "") or "",
                        amount=float(stmttrn.findtext("TRNAMT", "0") or "0"),
                        tran_type=stmttrn.findtext("TRNTYPE", ""),
                        check_num=stmttrn.findtext("CHECKNUM", "") or "",
                        account_id=result.account_id,
                        account_type=result.account_type,
                    )
                )

    # Credit card statements
    for ccstmtrs in root.iter("CCSTMTRS"):
        acct_from = ccstmtrs.find("CCACCTFROM")
        if acct_from is not None:
            acctid = acct_from.findtext("ACCTID", "")
            result.account_id = _mask_account(acctid)
            result.account_type = "CREDITCARD"

        banktranlist = ccstmtrs.find("BANKTRANLIST")
        if banktranlist is not None:
            for stmttrn in banktranlist.iter("STMTTRN"):
                result.transactions.append(
                    OfxTransaction(
                        date=_parse_ofx_date(stmttrn.findtext("DTPOSTED", "")),
                        fit_id=stmttrn.findtext("FITID", ""),
                        name=stmttrn.findtext("NAME", "") or "",
                        memo=stmttrn.findtext("MEMO", "") or "",
                        amount=float(stmttrn.findtext("TRNAMT", "0") or "0"),
                        tran_type=stmttrn.findtext("TRNTYPE", ""),
                        account_id=result.account_id,
                        account_type="CREDITCARD",
                    )
                )


def _extract_investment_transactions(root: ET.Element, result: OfxImportResult) -> None:
    """Extract investment transactions and positions from an OFX XML tree.

    Args:
        root: Parsed XML root element.
        result: OfxImportResult to populate.
    """
    for invstmtrs in root.iter("INVSTMTRS"):
        # Investment transactions
        invtranlist = invstmtrs.find("INVTRANLIST")
        if invtranlist is not None:
            # Buy transactions
            for buytag in ("BUYSTOCK", "BUYMF", "BUYOTHER"):
                for buy in invtranlist.iter(buytag):
                    invbuy = buy.find("INVBUY")
                    if invbuy is None:
                        continue
                    invtran = invbuy.find("INVTRAN")
                    secid = invbuy.find("SECID")

                    result.investment_transactions.append(
                        OfxInvestmentTransaction(
                            date=_parse_ofx_date(_ft(invtran, "DTTRADE")),
                            fit_id=_ft(invtran, "FITID"),
                            security_id=_ft(secid, "UNIQUEID"),
                            buy_sell="BUY",
                            tran_type=buytag,
                            units=float(_ft(invbuy, "UNITS") or "0"),
                            unit_price=float(_ft(invbuy, "UNITPRICE") or "0"),
                            total=float(_ft(invbuy, "TOTAL") or "0"),
                            fees=float(_ft(invbuy, "COMMISSION") or "0"),
                        )
                    )

            # Sell transactions
            for selltag in ("SELLSTOCK", "SELLMF", "SELLOTHER"):
                for sell in invtranlist.iter(selltag):
                    invsell = sell.find("INVSELL")
                    if invsell is None:
                        continue
                    invtran = invsell.find("INVTRAN")
                    secid = invsell.find("SECID")

                    result.investment_transactions.append(
                        OfxInvestmentTransaction(
                            date=_parse_ofx_date(_ft(invtran, "DTTRADE")),
                            fit_id=_ft(invtran, "FITID"),
                            security_id=_ft(secid, "UNIQUEID"),
                            buy_sell="SELL",
                            tran_type=selltag,
                            units=float(_ft(invsell, "UNITS") or "0"),
                            unit_price=float(_ft(invsell, "UNITPRICE") or "0"),
                            total=float(_ft(invsell, "TOTAL") or "0"),
                            fees=float(_ft(invsell, "COMMISSION") or "0"),
                        )
                    )

            # Income transactions (dividends, cap gains, interest)
            for income in invtranlist.iter("INCOME"):
                invtran = income.find("INVTRAN")
                secid = income.find("SECID")

                result.investment_transactions.append(
                    OfxInvestmentTransaction(
                        date=_parse_ofx_date(_ft(invtran, "DTTRADE")),
                        fit_id=_ft(invtran, "FITID"),
                        security_id=_ft(secid, "UNIQUEID"),
                        tran_type="INCOME",
                        total=float(_ft(income, "TOTAL") or "0"),
                        income_type=_ft(income, "INCOMETYPE"),
                    )
                )

            # Reinvestment transactions
            for reinvest in invtranlist.iter("REINVEST"):
                invtran = reinvest.find("INVTRAN")
                secid = reinvest.find("SECID")

                result.investment_transactions.append(
                    OfxInvestmentTransaction(
                        date=_parse_ofx_date(_ft(invtran, "DTTRADE")),
                        fit_id=_ft(invtran, "FITID"),
                        security_id=_ft(secid, "UNIQUEID"),
                        tran_type="REINVEST",
                        units=float(_ft(reinvest, "UNITS") or "0"),
                        unit_price=float(_ft(reinvest, "UNITPRICE") or "0"),
                        total=float(_ft(reinvest, "TOTAL") or "0"),
                        income_type=_ft(reinvest, "INCOMETYPE"),
                    )
                )

        # Investment positions
        invposlist = invstmtrs.find("INVPOSLIST")
        if invposlist is not None:
            for postag in ("POSSTOCK", "POSMF", "POSOTHER", "POSDEBT"):
                for pos in invposlist.iter(postag):
                    invpos = pos.find("INVPOS")
                    if invpos is None:
                        continue
                    secid = invpos.find("SECID")

                    sec_type_map = {
                        "POSSTOCK": "STOCK",
                        "POSMF": "MFUND",
                        "POSOTHER": "OTHER",
                        "POSDEBT": "BOND",
                    }

                    result.positions.append(
                        OfxPosition(
                            security_id=_ft(secid, "UNIQUEID"),
                            security_type=sec_type_map.get(postag, "OTHER"),
                            units=float(_ft(invpos, "UNITS") or "0"),
                            unit_price=float(_ft(invpos, "UNITPRICE") or "0"),
                            market_value=float(_ft(invpos, "MKTVAL") or "0"),
                        )
                    )


def _ft(parent: ET.Element | None, tag: str) -> str:
    """Find text in a child element, returning empty string if not found.

    Args:
        parent: Parent XML element.
        tag: Child tag name.

    Returns:
        Text content, or empty string.
    """
    if parent is None:
        return ""
    el = parent.find(tag)
    return (el.text or "").strip() if el is not None else ""


def _mask_account(acct_id: str) -> str:
    """Mask an account number, showing only last 4 digits.

    Args:
        acct_id: Full account number.

    Returns:
        Masked string like ``****1234``.
    """
    if not acct_id or len(acct_id) <= 4:
        return acct_id
    return "****" + acct_id[-4:]


# ── Main import function ──────────────────────────────────────────────


def import_ofx(path: str | Path) -> OfxImportResult:
    """Import an OFX or QFX file.

    Uses ``ofxtools`` if installed, otherwise falls back to the built-in parser.

    Args:
        path: Path to the OFX/QFX file.

    Returns:
        OfxImportResult with parsed data.
    """
    file_path = Path(path)
    if not file_path.exists():
        return OfxImportResult(
            source_path=str(file_path),
            warnings=[f"File not found: {file_path}"],
        )

    if file_path.suffix.lower() not in (".ofx", ".qfx"):
        return OfxImportResult(
            source_path=str(file_path),
            warnings=[f"Unexpected file extension: {file_path.suffix}. Expected .ofx or .qfx"],
        )

    if _ofxtools_available:
        logger.debug("Using ofxtools for %s", file_path.name)
        return _import_with_ofxtools(file_path)

    logger.debug("Using fallback parser for %s (install ofxtools for full support)", file_path.name)
    return _import_fallback(file_path)


def import_ofx_folder(
    folder: str | Path,
    *,
    recursive: bool = False,
) -> list[OfxImportResult]:
    """Import all OFX/QFX files from a folder.

    Args:
        folder: Path to the folder.
        recursive: Whether to scan subfolders.

    Returns:
        List of import results.
    """
    folder_path = Path(folder)
    if not folder_path.is_dir():
        logger.warning("Not a directory: %s", folder_path)
        return []

    results: list[OfxImportResult] = []
    for ext in ("*.ofx", "*.qfx"):
        pattern = f"**/{ext}" if recursive else ext
        for ofx_file in sorted(folder_path.glob(pattern)):
            if ofx_file.is_file():
                results.append(import_ofx(ofx_file))

    logger.info("Imported %d OFX/QFX files from %s", len(results), folder_path)
    return results
