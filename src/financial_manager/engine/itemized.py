"""Itemized deduction breakdown and SALT cap logic.

Provides fine-grained tracking of individual itemized deduction categories
rather than treating itemized deductions as a single lump sum.
"""

from __future__ import annotations

import logging
from typing import NamedTuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── IRS Limits ────────────────────────────────────────────────────────
SALT_CAP = 10_000.0  # State & Local Tax deduction cap (per return, even MFJ)
SALT_CAP_MFS = 5_000.0  # SALT cap for Married Filing Separately
MEDICAL_AGI_THRESHOLD = 0.075  # Medical expenses deductible above 7.5% of AGI

# Residential Clean Energy Credit rate (30% through 2032)
SOLAR_CREDIT_RATE = 0.30


class ItemizedDeductionBreakdown(BaseModel):
    """Detailed breakdown of itemized deductions.

    Attributes:
        mortgage_interest: Mortgage interest from 1098 Box 1 and closing disclosure.
        mortgage_points: Points paid (1098 Box 6 or closing disclosure).
        state_local_income_tax: State/local income tax withheld (from W-2 Box 17).
        property_tax: Real property taxes paid.
        salt_total: Combined state/local + property tax (before cap).
        salt_deductible: SALT after $10K cap.
        charitable_cash: Cash charitable contributions.
        charitable_noncash: Non-cash charitable contributions.
        medical_total: Total unreimbursed medical expenses.
        medical_deductible: Medical expenses exceeding 7.5% of AGI.
        other_deductions: Other allowable deductions.
        total_itemized: Grand total of all itemized deductions.
    """

    mortgage_interest: float = Field(default=0.0, ge=0)
    mortgage_points: float = Field(default=0.0, ge=0)
    state_local_income_tax: float = Field(default=0.0, ge=0)
    property_tax: float = Field(default=0.0, ge=0)
    salt_total: float = Field(default=0.0, ge=0)
    salt_deductible: float = Field(default=0.0, ge=0)
    charitable_cash: float = Field(default=0.0, ge=0)
    charitable_noncash: float = Field(default=0.0, ge=0)
    medical_total: float = Field(default=0.0, ge=0)
    medical_deductible: float = Field(default=0.0, ge=0)
    other_deductions: float = Field(default=0.0, ge=0)
    total_itemized: float = Field(default=0.0, ge=0)


class EnergyCreditResult(NamedTuple):
    """Result of the Residential Clean Energy Credit calculation."""

    solar_cost: float
    credit_rate: float
    credit_amount: float


def compute_itemized_deductions(
    mortgage_interest: float = 0.0,
    mortgage_points: float = 0.0,
    state_local_income_tax: float = 0.0,
    property_tax: float = 0.0,
    charitable_cash: float = 0.0,
    charitable_noncash: float = 0.0,
    medical_total: float = 0.0,
    agi: float = 0.0,
    other_deductions: float = 0.0,
    is_mfs: bool = False,
) -> ItemizedDeductionBreakdown:
    """Compute a detailed itemized deduction breakdown with IRS limits applied.

    Args:
        mortgage_interest: Mortgage interest paid.
        mortgage_points: Points paid on the mortgage.
        state_local_income_tax: State and local income tax withheld.
        property_tax: Real property taxes paid.
        charitable_cash: Cash charitable donations.
        charitable_noncash: Non-cash charitable donations.
        medical_total: Total unreimbursed medical expenses.
        agi: Adjusted Gross Income (for medical expense threshold).
        other_deductions: Other itemized deductions.
        is_mfs: Whether filing status is Married Filing Separately.

    Returns:
        ItemizedDeductionBreakdown with all amounts and the total.
    """
    # SALT: combine state/local income tax + property tax, apply cap
    salt_total = state_local_income_tax + property_tax
    salt_cap = SALT_CAP_MFS if is_mfs else SALT_CAP
    salt_deductible = min(salt_total, salt_cap)

    # Medical: only deductible above 7.5% of AGI
    medical_threshold = agi * MEDICAL_AGI_THRESHOLD
    medical_deductible = max(0.0, medical_total - medical_threshold)

    # Total
    total = (
        mortgage_interest
        + mortgage_points
        + salt_deductible
        + charitable_cash
        + charitable_noncash
        + medical_deductible
        + other_deductions
    )

    result = ItemizedDeductionBreakdown(
        mortgage_interest=round(mortgage_interest, 2),
        mortgage_points=round(mortgage_points, 2),
        state_local_income_tax=round(state_local_income_tax, 2),
        property_tax=round(property_tax, 2),
        salt_total=round(salt_total, 2),
        salt_deductible=round(salt_deductible, 2),
        charitable_cash=round(charitable_cash, 2),
        charitable_noncash=round(charitable_noncash, 2),
        medical_total=round(medical_total, 2),
        medical_deductible=round(medical_deductible, 2),
        other_deductions=round(other_deductions, 2),
        total_itemized=round(total, 2),
    )

    logger.info("Itemized deductions total: $%.2f (SALT: $%.2f capped to $%.2f)", total, salt_total, salt_deductible)
    return result


def compute_solar_credit(solar_system_cost: float) -> EnergyCreditResult:
    """Compute the Residential Clean Energy Credit (Form 5695) for solar.

    The credit is 30% of the total cost of a qualified solar electric
    property system installed through 2032.

    Args:
        solar_system_cost: Total cost of the solar installation.

    Returns:
        EnergyCreditResult with the cost, rate, and credit amount.
    """
    credit = round(solar_system_cost * SOLAR_CREDIT_RATE, 2)
    logger.info("Solar credit: $%.2f (%.0f%% of $%.2f)", credit, SOLAR_CREDIT_RATE * 100, solar_system_cost)
    return EnergyCreditResult(
        solar_cost=solar_system_cost,
        credit_rate=SOLAR_CREDIT_RATE,
        credit_amount=credit,
    )
