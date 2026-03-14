"""US federal income tax brackets by year and filing status.

Source: IRS Revenue Procedures for tax years 2024 and 2025.
Each bracket is a tuple of (rate, upper_bound) where upper_bound is the
maximum taxable income taxed at that rate. The last bracket uses float('inf').
"""

from __future__ import annotations

from financial_manager.models.filing_status import FilingStatus

# Type alias: list of (rate, upper_bound) tuples — upper_bound is inclusive ceiling
BracketSchedule = list[tuple[float, float]]


def get_brackets(tax_year: int, filing_status: FilingStatus) -> BracketSchedule:
    """Return the progressive tax bracket schedule for the given year and status.

    Args:
        tax_year: 2024 or 2025.
        filing_status: IRS filing status enum.

    Returns:
        Ordered list of (marginal_rate, bracket_ceiling) tuples.

    Raises:
        ValueError: If tax_year or filing_status is not supported.
    """
    key = (tax_year, filing_status)
    if key not in TAX_BRACKETS:
        msg = f"No bracket data for year={tax_year}, status={filing_status.value}"
        raise ValueError(msg)
    return TAX_BRACKETS[key]


# ── 2024 Brackets ───────────────────────────────────────────────────
# Source: IRS Rev. Proc. 2023-34

TAX_BRACKETS: dict[tuple[int, FilingStatus], BracketSchedule] = {
    # ── 2024 Single ──────────────────────────────────────────────────
    (2024, FilingStatus.SINGLE): [
        (0.10, 11_600),
        (0.12, 47_150),
        (0.22, 100_525),
        (0.24, 191_950),
        (0.32, 243_725),
        (0.35, 609_350),
        (0.37, float("inf")),
    ],
    # ── 2024 Married Filing Jointly / QSS ────────────────────────────
    (2024, FilingStatus.MARRIED_FILING_JOINTLY): [
        (0.10, 23_200),
        (0.12, 94_300),
        (0.22, 201_050),
        (0.24, 383_900),
        (0.32, 487_450),
        (0.35, 731_200),
        (0.37, float("inf")),
    ],
    (2024, FilingStatus.QUALIFYING_SURVIVING_SPOUSE): [
        (0.10, 23_200),
        (0.12, 94_300),
        (0.22, 201_050),
        (0.24, 383_900),
        (0.32, 487_450),
        (0.35, 731_200),
        (0.37, float("inf")),
    ],
    # ── 2024 Married Filing Separately ───────────────────────────────
    (2024, FilingStatus.MARRIED_FILING_SEPARATELY): [
        (0.10, 11_600),
        (0.12, 47_150),
        (0.22, 100_525),
        (0.24, 191_950),
        (0.32, 243_725),
        (0.35, 365_600),
        (0.37, float("inf")),
    ],
    # ── 2024 Head of Household ───────────────────────────────────────
    (2024, FilingStatus.HEAD_OF_HOUSEHOLD): [
        (0.10, 16_550),
        (0.12, 63_100),
        (0.22, 100_500),
        (0.24, 191_950),
        (0.32, 243_700),
        (0.35, 609_350),
        (0.37, float("inf")),
    ],
    # ── 2025 Single ──────────────────────────────────────────────────
    # Source: IRS Rev. Proc. 2024-40
    (2025, FilingStatus.SINGLE): [
        (0.10, 11_925),
        (0.12, 48_475),
        (0.22, 103_350),
        (0.24, 197_300),
        (0.32, 250_525),
        (0.35, 626_350),
        (0.37, float("inf")),
    ],
    # ── 2025 Married Filing Jointly / QSS ────────────────────────────
    (2025, FilingStatus.MARRIED_FILING_JOINTLY): [
        (0.10, 23_850),
        (0.12, 96_950),
        (0.22, 206_700),
        (0.24, 394_600),
        (0.32, 501_050),
        (0.35, 751_600),
        (0.37, float("inf")),
    ],
    (2025, FilingStatus.QUALIFYING_SURVIVING_SPOUSE): [
        (0.10, 23_850),
        (0.12, 96_950),
        (0.22, 206_700),
        (0.24, 394_600),
        (0.32, 501_050),
        (0.35, 751_600),
        (0.37, float("inf")),
    ],
    # ── 2025 Married Filing Separately ───────────────────────────────
    (2025, FilingStatus.MARRIED_FILING_SEPARATELY): [
        (0.10, 11_925),
        (0.12, 48_475),
        (0.22, 103_350),
        (0.24, 197_300),
        (0.32, 250_525),
        (0.35, 375_800),
        (0.37, float("inf")),
    ],
    # ── 2025 Head of Household ───────────────────────────────────────
    (2025, FilingStatus.HEAD_OF_HOUSEHOLD): [
        (0.10, 17_000),
        (0.12, 64_850),
        (0.22, 103_350),
        (0.24, 197_300),
        (0.32, 250_500),
        (0.35, 626_350),
        (0.37, float("inf")),
    ],
}
