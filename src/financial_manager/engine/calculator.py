"""Core tax calculation engine for US federal income tax."""

from __future__ import annotations

import logging

from financial_manager.data.tax_brackets import get_brackets
from financial_manager.engine.deductions import apply_deductions
from financial_manager.models.filing_status import FilingStatus
from financial_manager.models.tax_input import TaxInput
from financial_manager.models.tax_result import BracketResult, TaxResult

logger = logging.getLogger(__name__)


class TaxCalculator:
    """Calculates US federal income tax using progressive brackets.

    Usage:
        calc = TaxCalculator()
        result = calc.calculate(TaxInput(gross_income=100_000))
    """

    def compute_agi(self, gross_income: float, above_the_line_deductions: float) -> float:
        """Compute Adjusted Gross Income.

        Args:
            gross_income: Total gross income.
            above_the_line_deductions: Deductions taken before AGI.

        Returns:
            AGI (floored at 0).
        """
        return max(0.0, gross_income - above_the_line_deductions)

    def compute_progressive_tax(
        self,
        taxable_income: float,
        tax_year: int,
        filing_status: FilingStatus,
    ) -> tuple[float, float, list[BracketResult]]:
        """Calculate tax using progressive brackets.

        Args:
            taxable_income: Income subject to tax.
            tax_year: Tax year for bracket lookup.
            filing_status: IRS filing status.

        Returns:
            Tuple of (total_tax, marginal_rate, bracket_breakdown).
        """
        brackets = get_brackets(tax_year, filing_status)
        total_tax = 0.0
        marginal_rate = 0.0
        breakdown: list[BracketResult] = []
        prev_ceiling = 0.0

        for rate, ceiling in brackets:
            if taxable_income <= prev_ceiling:
                break

            bracket_low = prev_ceiling
            bracket_high = min(taxable_income, ceiling)
            income_in_bracket = bracket_high - bracket_low
            tax_in_bracket = income_in_bracket * rate

            if income_in_bracket > 0:
                breakdown.append(
                    BracketResult(
                        rate=rate,
                        range_low=bracket_low,
                        range_high=bracket_high,
                        taxable_in_bracket=income_in_bracket,
                        tax_in_bracket=round(tax_in_bracket, 2),
                    )
                )
                total_tax += tax_in_bracket
                marginal_rate = rate

            prev_ceiling = ceiling

        return round(total_tax, 2), marginal_rate, breakdown

    def calculate(self, tax_input: TaxInput) -> TaxResult:
        """Perform a complete federal income tax calculation.

        Args:
            tax_input: All inputs needed for the calculation.

        Returns:
            Complete TaxResult with bracket breakdown.
        """
        logger.info(
            "Calculating tax: year=%d, status=%s, income=%.2f",
            tax_input.tax_year,
            tax_input.filing_status.value,
            tax_input.gross_income,
        )

        # Step 1: Compute AGI
        agi = self.compute_agi(tax_input.gross_income, tax_input.above_the_line_deductions)

        # Step 2: Apply deductions
        taxable_income, standard_deduction, deduction_used = apply_deductions(
            agi=agi,
            tax_year=tax_input.tax_year,
            filing_status=tax_input.filing_status,
            itemized_deductions=tax_input.itemized_deductions,
        )

        # Step 3: Progressive tax calculation
        total_tax, marginal_rate, brackets = self.compute_progressive_tax(
            taxable_income=taxable_income,
            tax_year=tax_input.tax_year,
            filing_status=tax_input.filing_status,
        )

        # Step 4: Compute effective rate
        effective_rate = round(total_tax / tax_input.gross_income, 6) if tax_input.gross_income > 0 else 0.0

        return TaxResult(
            tax_year=tax_input.tax_year,
            filing_status=tax_input.filing_status,
            gross_income=tax_input.gross_income,
            agi=agi,
            standard_deduction=standard_deduction,
            deduction_used=deduction_used,
            taxable_income=taxable_income,
            total_tax=total_tax,
            effective_rate=effective_rate,
            marginal_rate=marginal_rate,
            brackets=brackets,
        )
