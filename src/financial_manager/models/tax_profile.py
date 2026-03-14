"""Tax profile model — captures the filer's situation to drive checklist generation."""

from __future__ import annotations

import enum

from pydantic import BaseModel, Field

from financial_manager.models.filing_status import FilingStatus


class EmploymentType(str, enum.Enum):
    """How the filer earns income."""

    W2_EMPLOYEE = "w2_employee"
    SELF_EMPLOYED = "self_employed"
    RETIRED = "retired"
    UNEMPLOYED = "unemployed"


class InvestmentAccountType(str, enum.Enum):
    """Types of investment/retirement accounts held."""

    BROKERAGE = "brokerage"
    TRADITIONAL_IRA = "traditional_ira"
    ROTH_IRA = "roth_ira"
    FOUR_01K = "401k"
    HSA = "hsa"
    FIVE_29 = "529"
    CRYPTO = "crypto"


class TaxProfile(BaseModel):
    """Describes the filer's overall tax situation.

    Used by the checklist engine to determine which documents are needed.

    Attributes:
        tax_year: The filing year.
        filing_status: IRS filing status.
        filer_name: Primary filer's name.
        spouse_name: Spouse's name (if MFJ/MFS).
        filer_employment: How the primary filer earns income.
        spouse_employment: How the spouse earns income (if applicable).
        num_dependents: Number of qualifying dependents.
        num_qualifying_children: Children qualifying for CTC.
        has_mortgage: Whether the filer has a mortgage (1098).
        purchased_home: Whether a home was purchased during the tax year.
        sold_home: Whether a home was sold during the tax year.
        has_property_tax: Whether filer pays property tax.
        has_solar: Whether filer installed solar panels (Residential Clean Energy Credit).
        investment_accounts: Types of investment/retirement accounts.
        has_capital_gains: Whether the filer realized capital gains or losses.
        has_bank_interest: Whether the filer earned bank interest (1099-INT).
        has_dividends: Whether the filer received dividends (1099-DIV).
        has_retirement_distributions: Whether there were retirement distributions (1099-R).
        has_freelance_income: Whether there is 1099-NEC/MISC income.
        has_marketplace_income: Whether there is 1099-K income.
        has_unemployment: Whether unemployment benefits were received (1099-G).
        has_social_security: Whether Social Security benefits were received.
        has_student_loans: Whether student loan interest was paid (1098-E).
        has_education_expenses: Whether tuition was paid (1098-T).
        has_charitable_donations: Whether charitable donations were made.
        has_medical_expenses: Whether there were significant medical expenses.
        has_prior_year_return: Whether the filer has access to last year's return.
        document_source_path: Local path to folder of tax documents (e.g., iCloud).
    """

    tax_year: int = Field(default=2025, ge=2024, le=2025, description="Filing year")
    filing_status: FilingStatus = Field(
        default=FilingStatus.MARRIED_FILING_JOINTLY,
        description="IRS filing status",
    )
    filer_name: str = Field(default="", description="Primary filer name")
    spouse_name: str = Field(default="", description="Spouse name")

    # Employment
    filer_employment: EmploymentType = Field(default=EmploymentType.W2_EMPLOYEE)
    spouse_employment: EmploymentType | None = Field(default=None)

    # Dependents
    num_dependents: int = Field(default=0, ge=0)
    num_qualifying_children: int = Field(default=0, ge=0)

    # Real estate
    has_mortgage: bool = Field(default=False)
    purchased_home: bool = Field(default=False)
    sold_home: bool = Field(default=False)
    has_property_tax: bool = Field(default=False)
    has_solar: bool = Field(default=False)

    # Investments
    investment_accounts: list[InvestmentAccountType] = Field(default_factory=list)
    has_capital_gains: bool = Field(default=False)
    has_bank_interest: bool = Field(default=False)
    has_dividends: bool = Field(default=False)
    has_retirement_distributions: bool = Field(default=False)

    # Other income
    has_freelance_income: bool = Field(default=False)
    has_marketplace_income: bool = Field(default=False)
    has_unemployment: bool = Field(default=False)
    has_social_security: bool = Field(default=False)

    # Deductions
    has_student_loans: bool = Field(default=False)
    has_education_expenses: bool = Field(default=False)
    has_charitable_donations: bool = Field(default=False)
    has_medical_expenses: bool = Field(default=False)

    # Supporting
    has_prior_year_return: bool = Field(default=False)

    # Document source
    document_source_path: str | None = Field(
        default=None,
        description="Local filesystem path to tax document folder (e.g., iCloud)",
    )

    @property
    def is_joint(self) -> bool:
        """Whether this is a joint filing with a spouse."""
        return self.filing_status in (
            FilingStatus.MARRIED_FILING_JOINTLY,
            FilingStatus.MARRIED_FILING_SEPARATELY,
        )
