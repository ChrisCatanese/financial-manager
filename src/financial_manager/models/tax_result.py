"""Pydantic models for tax calculation results."""

from __future__ import annotations

from pydantic import BaseModel, Field

from financial_manager.models.filing_status import FilingStatus


class BracketResult(BaseModel):
    """Tax computed within a single bracket.

    Attributes:
        rate: Marginal tax rate for this bracket (e.g., 0.22).
        range_low: Lower bound of income taxed at this rate.
        range_high: Upper bound of income taxed at this rate.
        taxable_in_bracket: Amount of income taxed in this bracket.
        tax_in_bracket: Tax amount computed for this bracket.
    """

    rate: float = Field(..., description="Marginal rate (e.g., 0.22)")
    range_low: float = Field(..., description="Bracket floor")
    range_high: float = Field(..., description="Bracket ceiling (or taxable income if partial)")
    taxable_in_bracket: float = Field(..., description="Income taxed in this bracket")
    tax_in_bracket: float = Field(..., description="Tax from this bracket")


class TaxResult(BaseModel):
    """Complete result of a federal income tax calculation.

    Attributes:
        tax_year: The tax year used for the calculation.
        filing_status: The filing status used.
        gross_income: Original gross income.
        agi: Adjusted Gross Income.
        standard_deduction: Standard deduction amount for the filing status.
        deduction_used: Actual deduction applied (max of standard vs itemized).
        taxable_income: Income subject to tax (AGI - deduction).
        total_tax: Total federal income tax liability.
        effective_rate: Total tax / gross income.
        marginal_rate: Highest bracket rate that applies.
        brackets: Per-bracket breakdown of the calculation.
    """

    tax_year: int
    filing_status: FilingStatus
    gross_income: float
    agi: float
    standard_deduction: float
    deduction_used: float
    taxable_income: float
    total_tax: float
    effective_rate: float = Field(..., description="Effective tax rate (total_tax / gross_income)")
    marginal_rate: float = Field(..., description="Marginal (highest applicable) tax rate")
    brackets: list[BracketResult] = Field(default_factory=list, description="Per-bracket breakdown")
