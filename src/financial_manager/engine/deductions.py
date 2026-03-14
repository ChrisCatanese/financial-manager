"""Deduction logic for federal income tax."""

from __future__ import annotations

from financial_manager.data.standard_deductions import get_standard_deduction
from financial_manager.models.filing_status import FilingStatus


def apply_deductions(
    agi: float,
    tax_year: int,
    filing_status: FilingStatus,
    itemized_deductions: float = 0.0,
) -> tuple[float, float, float]:
    """Compute taxable income after applying the larger of standard or itemized deduction.

    Args:
        agi: Adjusted Gross Income.
        tax_year: Tax year for standard deduction lookup.
        filing_status: IRS filing status.
        itemized_deductions: Total itemized deductions claimed.

    Returns:
        Tuple of (taxable_income, standard_deduction, deduction_used) where
        deduction_used is whichever deduction was actually applied.
    """
    standard = get_standard_deduction(tax_year, filing_status)
    deduction_used = max(standard, itemized_deductions)
    taxable_income = max(0.0, agi - deduction_used)
    return taxable_income, standard, deduction_used
