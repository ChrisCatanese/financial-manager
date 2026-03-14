"""Filing status enum for US federal income tax."""

from __future__ import annotations

from enum import Enum


class FilingStatus(str, Enum):
    """IRS filing statuses for federal income tax.

    Each status corresponds to a different set of tax bracket thresholds
    and standard deduction amounts.
    """

    SINGLE = "single"
    MARRIED_FILING_JOINTLY = "married_filing_jointly"
    MARRIED_FILING_SEPARATELY = "married_filing_separately"
    HEAD_OF_HOUSEHOLD = "head_of_household"
    QUALIFYING_SURVIVING_SPOUSE = "qualifying_surviving_spouse"
