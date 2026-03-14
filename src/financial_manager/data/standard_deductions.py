"""Standard deduction amounts by year and filing status.

Source: IRS Revenue Procedures for tax years 2023-2025.
"""

from __future__ import annotations

from financial_manager.models.filing_status import FilingStatus

# Keyed by (tax_year, filing_status) → standard deduction amount
STANDARD_DEDUCTIONS: dict[tuple[int, FilingStatus], float] = {
    # ── 2023 ─────────────────────────────────────────────────────────
    # Source: IRS Rev. Proc. 2022-38
    (2023, FilingStatus.SINGLE): 13_850,
    (2023, FilingStatus.MARRIED_FILING_JOINTLY): 27_700,
    (2023, FilingStatus.MARRIED_FILING_SEPARATELY): 13_850,
    (2023, FilingStatus.HEAD_OF_HOUSEHOLD): 20_800,
    (2023, FilingStatus.QUALIFYING_SURVIVING_SPOUSE): 27_700,
    # ── 2024 ─────────────────────────────────────────────────────────
    (2024, FilingStatus.SINGLE): 14_600,
    (2024, FilingStatus.MARRIED_FILING_JOINTLY): 29_200,
    (2024, FilingStatus.MARRIED_FILING_SEPARATELY): 14_600,
    (2024, FilingStatus.HEAD_OF_HOUSEHOLD): 21_900,
    (2024, FilingStatus.QUALIFYING_SURVIVING_SPOUSE): 29_200,
    # ── 2025 ─────────────────────────────────────────────────────────
    # Source: IRS Rev. Proc. 2024-40, updated per Pub. L. 119-2 (TCJA extension)
    (2025, FilingStatus.SINGLE): 15_750,
    (2025, FilingStatus.MARRIED_FILING_JOINTLY): 31_500,
    (2025, FilingStatus.MARRIED_FILING_SEPARATELY): 15_750,
    (2025, FilingStatus.HEAD_OF_HOUSEHOLD): 23_625,
    (2025, FilingStatus.QUALIFYING_SURVIVING_SPOUSE): 31_500,
}


def get_standard_deduction(tax_year: int, filing_status: FilingStatus) -> float:
    """Return the standard deduction for the given year and filing status.

    Args:
        tax_year: 2023, 2024, or 2025.
        filing_status: IRS filing status.

    Returns:
        Standard deduction amount in dollars.

    Raises:
        ValueError: If year/status combination is not supported.
    """
    key = (tax_year, filing_status)
    if key not in STANDARD_DEDUCTIONS:
        msg = f"No standard deduction data for year={tax_year}, status={filing_status.value}"
        raise ValueError(msg)
    return STANDARD_DEDUCTIONS[key]
