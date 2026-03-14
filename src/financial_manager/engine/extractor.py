"""Document extractor — parses tax documents and extracts key financial data.

Uses pypdf for native PDF text extraction. Falls back gracefully if
optional dependencies (pdfplumber, PIL) are not available.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from financial_manager.models.tax_document import TaxDocumentType

logger = logging.getLogger(__name__)

# Lazy imports for optional dependencies
_pypdf_available = False
_pdfplumber_available = False

try:
    from pypdf import PdfReader  # noqa: F401

    _pypdf_available = True
except ImportError:
    pass

try:
    import pdfplumber  # noqa: F401

    _pdfplumber_available = True
except ImportError:
    pass


def _extract_pdf_text(file_path: Path) -> str:
    """Extract all text from a PDF file.

    Args:
        file_path: Path to the PDF.

    Returns:
        Concatenated text from all pages.

    Raises:
        RuntimeError: If no PDF library is available.
    """
    if _pdfplumber_available:
        import pdfplumber

        with pdfplumber.open(file_path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return "\n".join(pages)

    if _pypdf_available:
        from pypdf import PdfReader

        reader = PdfReader(str(file_path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)

    msg = "No PDF library available. Install pypdf or pdfplumber."
    raise RuntimeError(msg)


def _find_dollar_amount(text: str, pattern: str) -> float | None:
    """Search for a dollar amount near a label pattern.

    Args:
        text: Full document text.
        pattern: Regex pattern to match the label (case-insensitive).

    Returns:
        The first dollar amount found after the label, or None.
    """
    match = re.search(
        pattern + r"[:\s]*\$?([\d,]+\.?\d*)",
        text,
        re.IGNORECASE,
    )
    if match:
        try:
            return float(match.group(1).replace(",", ""))
        except ValueError:
            return None
    return None


def _extract_w2(text: str) -> dict[str, str | float | None]:
    """Extract key fields from a W-2.

    Args:
        text: Full text of the W-2 PDF.

    Returns:
        Dict with extracted W-2 box values.
    """
    data: dict[str, str | float | None] = {}

    # Box 1: Wages, tips, other compensation
    wages = _find_dollar_amount(text, r"(?:box\s*1|wages,?\s*tips)")
    if wages is not None:
        data["box_1_wages"] = wages

    # Box 2: Federal income tax withheld
    fed_withheld = _find_dollar_amount(text, r"(?:box\s*2|federal.*tax\s*withheld)")
    if fed_withheld is not None:
        data["box_2_federal_tax_withheld"] = fed_withheld

    # Box 3: Social Security wages
    ss_wages = _find_dollar_amount(text, r"(?:box\s*3|social\s*security\s*wages)")
    if ss_wages is not None:
        data["box_3_ss_wages"] = ss_wages

    # Box 5: Medicare wages
    medicare = _find_dollar_amount(text, r"(?:box\s*5|medicare\s*wages)")
    if medicare is not None:
        data["box_5_medicare_wages"] = medicare

    # Box 12: Retirement contributions (401k = code D)
    retirement = _find_dollar_amount(text, r"(?:box\s*12|12[a-d].*D)")
    if retirement is not None:
        data["box_12_retirement_contrib"] = retirement

    # Employer name
    emp_match = re.search(r"employer.*?name[:\s]*([\w\s&,.-]+)", text, re.IGNORECASE)
    if emp_match:
        data["employer_name"] = emp_match.group(1).strip()[:80]

    return data


def _extract_1099_int(text: str) -> dict[str, str | float | None]:
    """Extract key fields from a 1099-INT.

    Args:
        text: Full text of the 1099-INT PDF.

    Returns:
        Dict with interest income data.
    """
    data: dict[str, str | float | None] = {}

    interest = _find_dollar_amount(text, r"(?:box\s*1|interest\s*income)")
    if interest is not None:
        data["box_1_interest_income"] = interest

    penalty = _find_dollar_amount(text, r"(?:box\s*2|early\s*withdrawal\s*penalty)")
    if penalty is not None:
        data["box_2_early_withdrawal_penalty"] = penalty

    return data


def _extract_1099_div(text: str) -> dict[str, str | float | None]:
    """Extract key fields from a 1099-DIV.

    Args:
        text: Full text of the 1099-DIV PDF.

    Returns:
        Dict with dividend income data.
    """
    data: dict[str, str | float | None] = {}

    ordinary = _find_dollar_amount(text, r"(?:box\s*1a|ordinary\s*dividends)")
    if ordinary is not None:
        data["box_1a_ordinary_dividends"] = ordinary

    qualified = _find_dollar_amount(text, r"(?:box\s*1b|qualified\s*dividends)")
    if qualified is not None:
        data["box_1b_qualified_dividends"] = qualified

    cap_gains = _find_dollar_amount(text, r"(?:box\s*2a|total\s*capital\s*gain)")
    if cap_gains is not None:
        data["box_2a_capital_gain_distributions"] = cap_gains

    return data


def _extract_1099_r(text: str) -> dict[str, str | float | None]:
    """Extract key fields from a 1099-R.

    Args:
        text: Full text of the 1099-R PDF.

    Returns:
        Dict with retirement distribution data.
    """
    data: dict[str, str | float | None] = {}

    gross = _find_dollar_amount(text, r"(?:box\s*1|gross\s*distribution)")
    if gross is not None:
        data["box_1_gross_distribution"] = gross

    taxable = _find_dollar_amount(text, r"(?:box\s*2a|taxable\s*amount)")
    if taxable is not None:
        data["box_2a_taxable_amount"] = taxable

    fed_withheld = _find_dollar_amount(text, r"(?:box\s*4|federal.*tax\s*withheld)")
    if fed_withheld is not None:
        data["box_4_federal_tax_withheld"] = fed_withheld

    return data


def _extract_1098(text: str) -> dict[str, str | float | None]:
    """Extract key fields from a 1098 Mortgage Interest Statement.

    Args:
        text: Full text of the 1098 PDF.

    Returns:
        Dict with mortgage interest and property tax data.
    """
    data: dict[str, str | float | None] = {}

    interest = _find_dollar_amount(text, r"(?:box\s*1|mortgage\s*interest\s*received)")
    if interest is not None:
        data["box_1_mortgage_interest"] = interest

    points = _find_dollar_amount(text, r"(?:box\s*6|points\s*paid)")
    if points is not None:
        data["box_6_points"] = points

    prop_tax = _find_dollar_amount(text, r"(?:box\s*10|property\s*tax)")
    if prop_tax is not None:
        data["box_10_property_tax"] = prop_tax

    return data


def _extract_closing_disclosure(text: str) -> dict[str, str | float | None]:
    """Extract tax-relevant fields from a Closing Disclosure.

    Args:
        text: Full text of the Closing Disclosure PDF.

    Returns:
        Dict with points, prepaid interest, and property tax proration data.
    """
    data: dict[str, str | float | None] = {}

    loan_amount = _find_dollar_amount(text, r"loan\s*amount")
    if loan_amount is not None:
        data["loan_amount"] = loan_amount

    interest_rate = _find_dollar_amount(text, r"interest\s*rate")
    if interest_rate is not None:
        data["interest_rate"] = interest_rate

    points = _find_dollar_amount(text, r"(?:origination|points|discount)")
    if points is not None:
        data["origination_points"] = points

    prepaid_interest = _find_dollar_amount(text, r"prepaid\s*interest")
    if prepaid_interest is not None:
        data["prepaid_interest"] = prepaid_interest

    prop_tax = _find_dollar_amount(text, r"property\s*tax")
    if prop_tax is not None:
        data["property_tax_proration"] = prop_tax

    return data


# ── Router: doc_type → extractor function ─────────────────────────────
_EXTRACTORS: dict[
    TaxDocumentType,
    type[object] | None,  # placeholder type; actual callables assigned below
] = {}

_EXTRACTOR_MAP: dict[TaxDocumentType, object] = {
    TaxDocumentType.W2: _extract_w2,
    TaxDocumentType.W2_SPOUSE: _extract_w2,
    TaxDocumentType.FORM_1099_INT: _extract_1099_int,
    TaxDocumentType.FORM_1099_DIV: _extract_1099_div,
    TaxDocumentType.FORM_1099_R: _extract_1099_r,
    TaxDocumentType.FORM_1098: _extract_1098,
    TaxDocumentType.CLOSING_DISCLOSURE_PURCHASE: _extract_closing_disclosure,
    TaxDocumentType.CLOSING_DISCLOSURE_SALE: _extract_closing_disclosure,
}


def extract_document(
    file_path: str | Path,
    doc_type: TaxDocumentType,
) -> dict[str, str | float | None]:
    """Extract structured data from a tax document.

    Args:
        file_path: Path to the document file.
        doc_type: The classified document type.

    Returns:
        Dict of extracted key-value pairs. Empty dict if extraction
        is not supported for this document type or fails.
    """
    path = Path(file_path)

    if not path.exists():
        logger.warning("File not found: %s", path)
        return {}

    if path.suffix.lower() != ".pdf":
        logger.info("Skipping non-PDF file: %s", path.name)
        return {}

    if not (_pypdf_available or _pdfplumber_available):
        logger.warning("No PDF library installed; cannot extract from %s", path.name)
        return {}

    extractor = _EXTRACTOR_MAP.get(doc_type)
    if extractor is None:
        logger.info("No extractor for document type %s", doc_type.value)
        return {}

    try:
        text = _extract_pdf_text(path)
        if not text.strip():
            logger.warning("No text extracted from %s (may be scanned/image-based)", path.name)
            return {}
        result = extractor(text)  # type: ignore[operator]
        logger.info("Extracted %d fields from %s (%s)", len(result), path.name, doc_type.value)
        return result
    except Exception:
        logger.exception("Failed to extract data from %s", path.name)
        return {}
