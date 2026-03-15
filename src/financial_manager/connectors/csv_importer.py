"""CSV importer for financial institution exports.

Supports auto-detection of institution-specific CSV formats:

- **Fidelity Positions**: Current holdings with cost basis, quantity, market value
- **Fidelity Activity**: Transactions (buys, sells, dividends, cap gains distributions)
- **Generic Bank CSV**: Transaction lists with date/description/amount columns

All parsing uses only the Python standard library (``csv`` module).
"""

from __future__ import annotations

import csv
import io
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Parsed record types ───────────────────────────────────────────────


@dataclass
class CsvHolding:
    """A single investment holding from a brokerage CSV export.

    Attributes:
        account: Account name or number.
        symbol: Ticker symbol.
        description: Security description.
        quantity: Number of shares/units.
        last_price: Most recent price per share.
        current_value: Current market value.
        cost_basis_total: Total cost basis.
        gain_loss: Unrealized gain/loss.
        holding_type: ``equity``, ``etf``, ``mutual_fund``, ``bond``, ``cash``, ``other``.
    """

    account: str = ""
    symbol: str = ""
    description: str = ""
    quantity: float = 0.0
    last_price: float = 0.0
    current_value: float = 0.0
    cost_basis_total: float = 0.0
    gain_loss: float = 0.0
    holding_type: str = "other"


@dataclass
class CsvTransaction:
    """A single financial transaction from a CSV export.

    Attributes:
        date: Transaction date string (ISO or institution format).
        account: Account name or number.
        description: Transaction description / merchant name.
        symbol: Ticker symbol (investment transactions).
        action: Transaction type (e.g. ``buy``, ``sell``, ``dividend``, ``deposit``).
        quantity: Shares transacted (investment transactions).
        price: Per-share price (investment transactions).
        amount: Dollar amount (positive = credit, negative = debit).
        fees: Commission or fees.
        category: Categorization from the institution (if provided).
    """

    date: str = ""
    account: str = ""
    description: str = ""
    symbol: str = ""
    action: str = ""
    quantity: float = 0.0
    price: float = 0.0
    amount: float = 0.0
    fees: float = 0.0
    category: str = ""


@dataclass
class CsvImportResult:
    """Result of importing one or more CSV files.

    Attributes:
        source_path: Path to the imported file.
        institution: Detected institution name (e.g. ``"Fidelity"``).
        format_type: Detected format (e.g. ``"fidelity_positions"``).
        holdings: Parsed holdings (if positions file).
        transactions: Parsed transactions (if activity/transactions file).
        warnings: Non-fatal issues encountered during parsing.
    """

    source_path: str = ""
    institution: str = ""
    format_type: str = ""
    holdings: list[CsvHolding] = field(default_factory=list)
    transactions: list[CsvTransaction] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ── Format detection ──────────────────────────────────────────────────

# Column signatures that identify specific CSV formats.
# Keys are frozensets of lowercase column names; values are (institution, format).
_FORMAT_SIGNATURES: list[tuple[frozenset[str], str, str]] = [
    # Fidelity Positions CSV
    (
        frozenset({"account name/number", "symbol", "description", "quantity",
                    "last price", "current value", "cost basis total"}),
        "Fidelity",
        "fidelity_positions",
    ),
    # Fidelity Positions (alternate headers)
    (
        frozenset({"account", "symbol", "description", "quantity",
                    "last price", "current value"}),
        "Fidelity",
        "fidelity_positions",
    ),
    # Fidelity Activity/History CSV
    (
        frozenset({"run date", "account", "action", "symbol", "description",
                    "quantity", "price ($)", "amount ($)"}),
        "Fidelity",
        "fidelity_activity",
    ),
    # Fidelity Activity (alternate headers)
    (
        frozenset({"date", "account", "action", "symbol", "description",
                    "quantity", "price", "amount"}),
        "Fidelity",
        "fidelity_activity",
    ),
    # Generic bank CSV (date, description, amount)
    (
        frozenset({"date", "description", "amount"}),
        "generic",
        "bank_transactions",
    ),
    # Generic with debit/credit columns
    (
        frozenset({"date", "description", "debit", "credit"}),
        "generic",
        "bank_transactions_split",
    ),
    # Wells Fargo CSV format
    (
        frozenset({"date", "amount", "balance"}),
        "Wells Fargo",
        "wells_fargo_transactions",
    ),
]


def detect_csv_format(
    header_row: list[str],
) -> tuple[str, str]:
    """Detect the CSV format from header column names.

    Args:
        header_row: List of column header strings.

    Returns:
        Tuple of ``(institution, format_type)``.  Returns ``("unknown", "unknown")``
        if no format is recognized.
    """
    normalized = frozenset(h.strip().lower() for h in header_row if h.strip())

    for signature, institution, fmt in _FORMAT_SIGNATURES:
        if signature.issubset(normalized):
            return institution, fmt

    return "unknown", "unknown"


# ── Monetary value parsing ────────────────────────────────────────────

_MONEY_RE = re.compile(r"[^\d.\-+]")


def _parse_money(raw: str) -> float:
    """Parse a monetary string into a float, stripping currency symbols and commas.

    Args:
        raw: Raw string like ``"$1,234.56"`` or ``"($100.00)"`` or ``"-100.00"``.

    Returns:
        Float value.  Returns 0.0 for empty or unparseable strings.
    """
    if not raw or not raw.strip():
        return 0.0

    cleaned = raw.strip()

    # Handle parenthetical negatives: ($100.00) → -100.00
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]

    # Remove everything except digits, dots, minus, plus
    cleaned = _MONEY_RE.sub("", cleaned)

    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse_quantity(raw: str) -> float:
    """Parse a quantity string (shares, units).

    Args:
        raw: Raw quantity string.

    Returns:
        Float value.
    """
    return _parse_money(raw)


# ── File reader helper ────────────────────────────────────────────────


def _read_csv_lines(path: Path) -> list[str]:
    """Read a CSV file, skipping common preamble lines.

    Some exports (e.g. Fidelity) include title lines, date ranges, or blank
    lines before the actual CSV headers.  This function skips those.

    Args:
        path: Path to the CSV file.

    Returns:
        List of content lines starting from the header row.
    """
    raw_lines = path.read_text(encoding="utf-8-sig").splitlines()

    # Skip blank lines and common preamble patterns at the top
    content_lines: list[str] = []
    header_found = False
    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            if header_found:
                content_lines.append(line)
            continue

        # Once we find a line with commas that looks like a CSV header, start
        if not header_found:
            if "," in stripped:
                header_found = True
                content_lines.append(line)
        else:
            content_lines.append(line)

    return content_lines


# ── Fidelity parsers ──────────────────────────────────────────────────


def _parse_fidelity_positions(rows: list[dict[str, str]]) -> tuple[list[CsvHolding], list[str]]:
    """Parse Fidelity positions CSV rows.

    Args:
        rows: List of row dicts from csv.DictReader.

    Returns:
        Tuple of (holdings, warnings).
    """
    holdings: list[CsvHolding] = []
    warnings: list[str] = []

    for row in rows:
        # Normalize keys to lowercase
        r = {k.strip().lower(): v.strip() if v else "" for k, v in row.items() if k}

        symbol = r.get("symbol", "")
        if not symbol or symbol.lower() in ("", "pending activity"):
            continue

        # Skip footer/summary rows
        desc = r.get("description", "")
        if desc.lower().startswith("account total") or desc.lower().startswith("total"):
            continue

        account = r.get("account name/number", "") or r.get("account", "")
        quantity = _parse_quantity(r.get("quantity", "0"))
        last_price = _parse_money(r.get("last price", "0") or r.get("last price ($)", "0"))
        current_value = _parse_money(r.get("current value", "0") or r.get("current value ($)", "0"))
        cost_basis = _parse_money(r.get("cost basis total", "0") or r.get("cost basis total ($)", "0"))
        gain_loss = _parse_money(r.get("gain/loss dollar", "0") or r.get("gain/loss ($)", "0"))

        # Infer holding type from description
        holding_type = _infer_holding_type(desc, symbol)

        holdings.append(
            CsvHolding(
                account=account,
                symbol=symbol,
                description=desc,
                quantity=quantity,
                last_price=last_price,
                current_value=current_value,
                cost_basis_total=cost_basis,
                gain_loss=gain_loss,
                holding_type=holding_type,
            )
        )

    logger.info("Parsed %d Fidelity holdings", len(holdings))
    return holdings, warnings


def _parse_fidelity_activity(rows: list[dict[str, str]]) -> tuple[list[CsvTransaction], list[str]]:
    """Parse Fidelity activity/history CSV rows.

    Args:
        rows: List of row dicts from csv.DictReader.

    Returns:
        Tuple of (transactions, warnings).
    """
    txns: list[CsvTransaction] = []
    warnings: list[str] = []

    for row in rows:
        r = {k.strip().lower(): v.strip() if v else "" for k, v in row.items() if k}

        txn_date = r.get("run date", "") or r.get("date", "")
        if not txn_date:
            continue

        action = r.get("action", "").strip()
        if not action:
            continue

        account = r.get("account", "")
        symbol = r.get("symbol", "")
        description = r.get("description", "")
        quantity = _parse_quantity(r.get("quantity", "0"))
        price = _parse_money(r.get("price ($)", "0") or r.get("price", "0"))
        amount = _parse_money(r.get("amount ($)", "0") or r.get("amount", "0"))
        fees = _parse_money(r.get("commission ($)", "0") or r.get("fees ($)", "0") or r.get("fees", "0"))

        # Normalize action to standard categories
        normalized_action = _normalize_action(action)

        txns.append(
            CsvTransaction(
                date=txn_date,
                account=account,
                description=description,
                symbol=symbol,
                action=normalized_action,
                quantity=quantity,
                price=price,
                amount=amount,
                fees=fees,
            )
        )

    logger.info("Parsed %d Fidelity transactions", len(txns))
    return txns, warnings


# ── Generic bank parsers ──────────────────────────────────────────────


def _parse_bank_transactions(
    rows: list[dict[str, str]],
    *,
    split_columns: bool = False,
) -> tuple[list[CsvTransaction], list[str]]:
    """Parse generic bank CSV rows.

    Args:
        rows: List of row dicts from csv.DictReader.
        split_columns: If True, expect separate ``debit`` and ``credit`` columns.

    Returns:
        Tuple of (transactions, warnings).
    """
    txns: list[CsvTransaction] = []
    warnings: list[str] = []

    for row in rows:
        r = {k.strip().lower(): v.strip() if v else "" for k, v in row.items() if k}

        txn_date = r.get("date", "")
        if not txn_date:
            continue

        description = r.get("description", "") or r.get("memo", "") or r.get("name", "")

        if split_columns:
            debit = _parse_money(r.get("debit", "0"))
            credit = _parse_money(r.get("credit", "0"))
            amount = credit - debit
        else:
            amount = _parse_money(r.get("amount", "0"))

        category = r.get("category", "") or r.get("type", "")

        # Determine action from amount or category
        if "interest" in description.lower() or "interest" in category.lower():
            action = "interest"
        elif amount > 0:
            action = "credit"
        else:
            action = "debit"

        txns.append(
            CsvTransaction(
                date=txn_date,
                description=description,
                amount=amount,
                category=category,
                action=action,
            )
        )

    logger.info("Parsed %d bank transactions", len(txns))
    return txns, warnings


def _parse_wells_fargo(rows: list[dict[str, str]]) -> tuple[list[CsvTransaction], list[str]]:
    """Parse Wells Fargo CSV export.

    Wells Fargo CSVs sometimes lack headers, with columns:
    date, amount, *, *, description.

    Args:
        rows: List of row dicts from csv.DictReader.

    Returns:
        Tuple of (transactions, warnings).
    """
    txns: list[CsvTransaction] = []
    warnings: list[str] = []

    for row in rows:
        r = {k.strip().lower(): v.strip() if v else "" for k, v in row.items() if k}

        txn_date = r.get("date", "")
        if not txn_date:
            continue

        amount = _parse_money(r.get("amount", "0"))
        description = r.get("description", "") or r.get("memo", "")

        if "interest" in description.lower():
            action = "interest"
        elif amount > 0:
            action = "credit"
        else:
            action = "debit"

        txns.append(
            CsvTransaction(
                date=txn_date,
                description=description,
                amount=amount,
                action=action,
            )
        )

    logger.info("Parsed %d Wells Fargo transactions", len(txns))
    return txns, warnings


# ── Action / type normalization ───────────────────────────────────────

_ACTION_MAP: dict[str, str] = {
    # Fidelity action strings → normalized
    "you bought": "buy",
    "bought": "buy",
    "you sold": "sell",
    "sold": "sell",
    "reinvestment": "reinvestment",
    "dividend received": "dividend",
    "dividend": "dividend",
    "short-term cap gain": "short_term_gain",
    "long-term cap gain": "long_term_gain",
    "capital gain": "capital_gain",
    "interest earned": "interest",
    "interest": "interest",
    "transfer": "transfer",
    "contribution": "contribution",
    "distribution": "distribution",
    "fee charged": "fee",
    "fee": "fee",
    "tax withheld": "tax_withheld",
    "foreign tax paid": "foreign_tax",
    "return of capital": "return_of_capital",
}


def _normalize_action(raw_action: str) -> str:
    """Normalize a transaction action string to a standard category.

    Args:
        raw_action: Raw action string from CSV.

    Returns:
        Normalized action string.
    """
    lower = raw_action.strip().lower()

    # Exact match first
    if lower in _ACTION_MAP:
        return _ACTION_MAP[lower]

    # Substring match
    for pattern, normalized in _ACTION_MAP.items():
        if pattern in lower:
            return normalized

    return raw_action.strip().lower()


def _infer_holding_type(description: str, symbol: str) -> str:
    """Infer the holding type from description and symbol.

    Args:
        description: Security description.
        symbol: Ticker symbol.

    Returns:
        One of ``equity``, ``etf``, ``mutual_fund``, ``bond``, ``cash``, ``other``.
    """
    desc_lower = description.lower()
    sym_lower = symbol.lower()

    if "cash" in desc_lower or sym_lower in ("spaxx", "fdrxx", "fcash", "core"):
        return "cash"
    if "etf" in desc_lower or "exchange traded" in desc_lower:
        return "etf"
    if any(x in desc_lower for x in ("mutual fund", "index fund", "fidelity")):
        return "mutual_fund"
    if any(x in desc_lower for x in ("bond", "treasury", "note", "t-bill")):
        return "bond"
    if symbol and not any(c.isdigit() for c in symbol):
        return "equity"

    return "other"


# ── Main import function ──────────────────────────────────────────────


def import_csv(path: str | Path) -> CsvImportResult:
    """Import a CSV file, auto-detecting the format.

    Args:
        path: Path to the CSV file.

    Returns:
        CsvImportResult with parsed data and detected format.
    """
    file_path = Path(path)
    if not file_path.exists():
        return CsvImportResult(
            source_path=str(file_path),
            warnings=[f"File not found: {file_path}"],
        )

    if file_path.suffix.lower() not in (".csv", ".txt"):
        return CsvImportResult(
            source_path=str(file_path),
            warnings=[f"Unexpected file extension: {file_path.suffix}"],
        )

    try:
        content_lines = _read_csv_lines(file_path)
        if not content_lines:
            return CsvImportResult(
                source_path=str(file_path),
                warnings=["File is empty or contains no CSV data"],
            )

        # Parse header
        reader = csv.DictReader(io.StringIO("\n".join(content_lines)))
        if reader.fieldnames is None:
            return CsvImportResult(
                source_path=str(file_path),
                warnings=["Could not parse CSV headers"],
            )

        institution, fmt = detect_csv_format(list(reader.fieldnames))
        rows = list(reader)

        result = CsvImportResult(
            source_path=str(file_path),
            institution=institution,
            format_type=fmt,
        )

        if fmt == "fidelity_positions":
            result.holdings, result.warnings = _parse_fidelity_positions(rows)
        elif fmt == "fidelity_activity":
            result.transactions, result.warnings = _parse_fidelity_activity(rows)
        elif fmt == "bank_transactions":
            result.transactions, result.warnings = _parse_bank_transactions(rows)
        elif fmt == "bank_transactions_split":
            result.transactions, result.warnings = _parse_bank_transactions(rows, split_columns=True)
        elif fmt == "wells_fargo_transactions":
            result.transactions, result.warnings = _parse_wells_fargo(rows)
        else:
            result.warnings.append(
                f"Unrecognized CSV format. Headers: {list(reader.fieldnames)}"
            )
            logger.warning("Unrecognized CSV format in %s", file_path)

        return result

    except Exception as exc:
        logger.error("Failed to import CSV %s: %s", file_path, exc)
        return CsvImportResult(
            source_path=str(file_path),
            warnings=[f"Parse error: {exc}"],
        )


def import_csv_folder(
    folder: str | Path,
    *,
    recursive: bool = False,
) -> list[CsvImportResult]:
    """Import all CSV files from a folder.

    Args:
        folder: Path to the folder.
        recursive: Whether to scan subfolders.

    Returns:
        List of import results (one per file).
    """
    folder_path = Path(folder)
    if not folder_path.is_dir():
        logger.warning("Not a directory: %s", folder_path)
        return []

    pattern = "**/*.csv" if recursive else "*.csv"
    results: list[CsvImportResult] = []

    for csv_file in sorted(folder_path.glob(pattern)):
        if csv_file.is_file():
            results.append(import_csv(csv_file))

    logger.info("Imported %d CSV files from %s", len(results), folder_path)
    return results
