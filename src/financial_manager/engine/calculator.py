"""Core tax calculation engine for US federal income tax."""

from __future__ import annotations

import logging

from financial_manager.data.capital_gains_rates import get_capital_gains_thresholds
from financial_manager.data.tax_brackets import get_brackets
from financial_manager.engine.deductions import apply_deductions
from financial_manager.models.filing_status import FilingStatus
from financial_manager.models.tax_input import TaxInput
from financial_manager.models.tax_result import BracketResult, TaxResult

logger = logging.getLogger(__name__)

# Additional Medicare Tax thresholds by filing status (IRS Form 8959)
_ADDITIONAL_MEDICARE_THRESHOLDS: dict[FilingStatus, float] = {
    FilingStatus.SINGLE: 200_000,
    FilingStatus.MARRIED_FILING_JOINTLY: 250_000,
    FilingStatus.QUALIFYING_SURVIVING_SPOUSE: 250_000,
    FilingStatus.MARRIED_FILING_SEPARATELY: 125_000,
    FilingStatus.HEAD_OF_HOUSEHOLD: 200_000,
}

_ADDITIONAL_MEDICARE_RATE = 0.009  # 0.9%


class TaxCalculator:
    """Calculates US federal income tax using progressive brackets.

    Supports the Qualified Dividends and Capital Gain Tax Worksheet
    for preferential 0%/15%/20% rates on qualified dividends and
    net long-term capital gains. Also computes Additional Medicare Tax.

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

    def compute_qdcg_tax(
        self,
        taxable_income: float,
        qualified_dividends: float,
        net_capital_gains: float,
        tax_year: int,
        filing_status: FilingStatus,
    ) -> tuple[float, float, list[BracketResult]]:
        """Compute tax using the Qualified Dividends and Capital Gain Tax Worksheet.

        This implements the IRS worksheet (Form 1040 instructions) that applies
        preferential 0%/15%/20% rates to qualified dividends and net LTCG,
        while taxing remaining ordinary income at progressive rates.

        Args:
            taxable_income: Total taxable income (line 15).
            qualified_dividends: Qualified dividends (line 3a).
            net_capital_gains: Net capital gain from Schedule D (or line 7 if positive).
            tax_year: Tax year.
            filing_status: Filing status.

        Returns:
            Tuple of (total_tax, marginal_rate, bracket_breakdown).
        """
        # Worksheet line references from IRS Form 1040 Instructions
        # Line 1: taxable income
        ws_line1 = taxable_income

        # Line 2: qualified dividends
        # Line 3: net capital gain (Schedule D line 15 or line 7 if > 0)
        # Line 4: line 2 + line 3
        preferential_income = min(qualified_dividends + net_capital_gains, ws_line1)

        # Line 5: taxable income minus preferential income = ordinary income
        ordinary_income = max(0.0, ws_line1 - preferential_income)

        # If there's no preferential income, just use progressive brackets
        if preferential_income <= 0:
            return self.compute_progressive_tax(taxable_income, tax_year, filing_status)

        # Tax on ordinary income at progressive rates (IRS worksheet line 24)
        ordinary_tax_raw, marginal_rate, brackets = self.compute_progressive_tax(
            ordinary_income, tax_year, filing_status
        )
        # IRS worksheet uses whole-dollar amounts
        ordinary_tax = round(ordinary_tax_raw)

        # Apply preferential rates to the qualified dividends + net LTCG
        cap_gains_brackets = get_capital_gains_thresholds(tax_year, filing_status)

        # The preferential rates apply based on where the income falls
        # in the taxable income stack. Ordinary income fills from the bottom,
        # then preferential income sits on top.
        preferential_tax = 0.0
        income_so_far = ordinary_income  # ordinary income already "used" the lower brackets

        remaining_pref = preferential_income
        for rate, threshold in cap_gains_brackets:
            if remaining_pref <= 0:
                break

            # How much room is left in this rate bracket?
            room = max(0.0, threshold - income_so_far)
            taxed_at_rate = min(remaining_pref, room)

            if taxed_at_rate > 0:
                tax_amount = round(taxed_at_rate * rate)
                preferential_tax += tax_amount
                brackets.append(
                    BracketResult(
                        rate=rate,
                        range_low=income_so_far,
                        range_high=income_so_far + taxed_at_rate,
                        taxable_in_bracket=taxed_at_rate,
                        tax_in_bracket=float(tax_amount),
                    )
                )
                income_so_far += taxed_at_rate
                remaining_pref -= taxed_at_rate

        # IRS worksheet line 25: sum of ordinary + preferential components
        total_tax = float(ordinary_tax + preferential_tax)

        # IRS worksheet line 26: full progressive tax for comparison
        full_progressive_raw, _, _ = self.compute_progressive_tax(
            taxable_income, tax_year, filing_status
        )
        full_progressive = float(round(full_progressive_raw))

        # IRS worksheet line 27: tax = min(QDCG worksheet tax, regular tax)
        if full_progressive < total_tax:
            return full_progressive, marginal_rate, brackets

        return total_tax, marginal_rate, brackets

    def compute_additional_medicare_tax(
        self,
        w2_medicare_wages: float,
        filing_status: FilingStatus,
    ) -> float:
        """Compute Additional Medicare Tax (Form 8959).

        The 0.9% Additional Medicare Tax applies to Medicare wages (W-2 Box 5)
        exceeding the threshold for the filing status.

        Args:
            w2_medicare_wages: Total Medicare wages from all W-2 Box 5.
            filing_status: Filing status for threshold lookup.

        Returns:
            Additional Medicare Tax amount.
        """
        threshold = _ADDITIONAL_MEDICARE_THRESHOLDS[filing_status]
        excess = max(0.0, w2_medicare_wages - threshold)
        # IRS Form 8959 uses whole-dollar amounts
        return float(round(excess * _ADDITIONAL_MEDICARE_RATE))

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
        taxable_before_qbi, standard_deduction, deduction_used = apply_deductions(
            agi=agi,
            tax_year=tax_input.tax_year,
            filing_status=tax_input.filing_status,
            itemized_deductions=tax_input.itemized_deductions,
        )

        # Step 3: Apply QBI deduction
        qbi = tax_input.qbi_deduction
        taxable_income = max(0.0, taxable_before_qbi - qbi)

        # Step 4: Compute income tax (line 16)
        has_preferential = (tax_input.qualified_dividends > 0 or tax_input.net_capital_gains > 0)

        if has_preferential:
            income_tax, marginal_rate, brackets = self.compute_qdcg_tax(
                taxable_income=taxable_income,
                qualified_dividends=tax_input.qualified_dividends,
                net_capital_gains=tax_input.net_capital_gains,
                tax_year=tax_input.tax_year,
                filing_status=tax_input.filing_status,
            )
        else:
            income_tax, marginal_rate, brackets = self.compute_progressive_tax(
                taxable_income=taxable_income,
                tax_year=tax_input.tax_year,
                filing_status=tax_input.filing_status,
            )

        # Step 5: Additional Medicare Tax
        additional_medicare = self.compute_additional_medicare_tax(
            w2_medicare_wages=tax_input.w2_medicare_wages,
            filing_status=tax_input.filing_status,
        )

        # Step 6: Total tax
        total_tax = round(income_tax + additional_medicare, 2)

        # Step 7: Compute effective rate
        effective_rate = round(total_tax / tax_input.gross_income, 6) if tax_input.gross_income > 0 else 0.0

        # Step 8: Refund or amount owed
        refund_or_owed = round(tax_input.total_withholding - total_tax, 2)

        return TaxResult(
            tax_year=tax_input.tax_year,
            filing_status=tax_input.filing_status,
            gross_income=tax_input.gross_income,
            agi=agi,
            standard_deduction=standard_deduction,
            deduction_used=deduction_used,
            qbi_deduction=qbi,
            taxable_income=taxable_income,
            income_tax=income_tax,
            additional_medicare_tax=additional_medicare,
            total_tax=total_tax,
            total_withholding=tax_input.total_withholding,
            refund_or_owed=refund_or_owed,
            effective_rate=effective_rate,
            marginal_rate=marginal_rate,
            brackets=brackets,
        )
