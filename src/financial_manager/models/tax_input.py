"""Pydantic model for tax calculation input."""

from __future__ import annotations

from pydantic import BaseModel, Field

from financial_manager.models.filing_status import FilingStatus


class TaxInput(BaseModel):
    """Input data for a federal income tax calculation.

    Attributes:
        gross_income: Total gross income before any deductions.
        filing_status: IRS filing status.
        tax_year: Tax year for bracket lookup (2024 or 2025).
        above_the_line_deductions: Deductions taken before AGI (e.g., IRA, student loan interest).
        itemized_deductions: Total itemized deductions; if 0, standard deduction is used.
        num_dependents: Number of qualifying dependents (for future credit calculations).
        num_qualifying_children: Number of qualifying children for CTC.
    """

    gross_income: float = Field(..., ge=0, description="Total gross income")
    filing_status: FilingStatus = Field(default=FilingStatus.SINGLE, description="IRS filing status")
    tax_year: int = Field(default=2024, ge=2024, le=2025, description="Tax year")
    above_the_line_deductions: float = Field(default=0.0, ge=0, description="Above-the-line deductions")
    itemized_deductions: float = Field(default=0.0, ge=0, description="Itemized deductions (0 = use standard)")
    num_dependents: int = Field(default=0, ge=0, description="Number of dependents")
    num_qualifying_children: int = Field(default=0, ge=0, description="Number of qualifying children for CTC")
