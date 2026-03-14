"""Long-term capital gains and qualified dividends rate thresholds.

Source: IRS Revenue Procedures for tax years 2024 and 2025.
Qualified dividends and net long-term capital gains are taxed at
preferential rates: 0%, 15%, or 20%.

The thresholds define the maximum taxable income for each preferential rate.
"""

from __future__ import annotations

from financial_manager.models.filing_status import FilingStatus

# Type alias: list of (rate, threshold) tuples
# Threshold = max taxable income at this preferential rate
CapGainsSchedule = list[tuple[float, float]]


def get_capital_gains_thresholds(
    tax_year: int,
    filing_status: FilingStatus,
) -> CapGainsSchedule:
    """Return the capital gains rate thresholds for the given year and status.

    Args:
        tax_year: 2024 or 2025.
        filing_status: IRS filing status enum.

    Returns:
        Ordered list of (rate, threshold) tuples. The last rate applies
        to income above the highest threshold.

    Raises:
        ValueError: If tax_year or filing_status is not supported.
    """
    key = (tax_year, filing_status)
    if key not in CAP_GAINS_THRESHOLDS:
        msg = f"No capital gains data for year={tax_year}, status={filing_status.value}"
        raise ValueError(msg)
    return CAP_GAINS_THRESHOLDS[key]


# ── 2024 Capital Gains Rate Thresholds ──────────────────────────────
# Source: IRS Rev. Proc. 2023-34
#
# The 0% rate applies up to the threshold; 15% applies up to the next
# threshold; 20% applies above that.

CAP_GAINS_THRESHOLDS: dict[tuple[int, FilingStatus], CapGainsSchedule] = {
    # ── 2024 ─────────────────────────────────────────────────────────
    (2024, FilingStatus.SINGLE): [
        (0.00, 47_025),
        (0.15, 518_900),
        (0.20, float("inf")),
    ],
    (2024, FilingStatus.MARRIED_FILING_JOINTLY): [
        (0.00, 94_050),
        (0.15, 583_750),
        (0.20, float("inf")),
    ],
    (2024, FilingStatus.QUALIFYING_SURVIVING_SPOUSE): [
        (0.00, 94_050),
        (0.15, 583_750),
        (0.20, float("inf")),
    ],
    (2024, FilingStatus.MARRIED_FILING_SEPARATELY): [
        (0.00, 47_025),
        (0.15, 291_850),
        (0.20, float("inf")),
    ],
    (2024, FilingStatus.HEAD_OF_HOUSEHOLD): [
        (0.00, 63_000),
        (0.15, 551_350),
        (0.20, float("inf")),
    ],
    # ── 2025 ─────────────────────────────────────────────────────────
    # Source: IRS Rev. Proc. 2024-40
    (2025, FilingStatus.SINGLE): [
        (0.00, 48_350),
        (0.15, 533_400),
        (0.20, float("inf")),
    ],
    (2025, FilingStatus.MARRIED_FILING_JOINTLY): [
        (0.00, 96_700),
        (0.15, 600_050),
        (0.20, float("inf")),
    ],
    (2025, FilingStatus.QUALIFYING_SURVIVING_SPOUSE): [
        (0.00, 96_700),
        (0.15, 600_050),
        (0.20, float("inf")),
    ],
    (2025, FilingStatus.MARRIED_FILING_SEPARATELY): [
        (0.00, 48_350),
        (0.15, 300_000),
        (0.20, float("inf")),
    ],
    (2025, FilingStatus.HEAD_OF_HOUSEHOLD): [
        (0.00, 64_750),
        (0.15, 566_700),
        (0.20, float("inf")),
    ],
}
