"""Cross-validate tax data against PSLmodels/Tax-Calculator.

Downloads (or uses cached) policy_current_law.json and compares
every bracket, standard deduction, and capital gains threshold
against our data modules. Known TC bugs are handled via overrides.

Marked as integration tests — they require network access on first run.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from financial_manager.data.capital_gains_rates import get_capital_gains_thresholds
from financial_manager.data.standard_deductions import get_standard_deduction
from financial_manager.data.tax_brackets import get_brackets
from financial_manager.models.filing_status import FilingStatus

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / ".cache" / "reference"
POLICY_JSON = CACHE_DIR / "policy_current_law.json"
OVERRIDES_PATH = ROOT / "scripts" / "tax_data_overrides.json"

YEARS = [2023, 2024, 2025]

# TC MARS -> our FilingStatus
MARS_TO_STATUS: dict[str, FilingStatus] = {
    "single": FilingStatus.SINGLE,
    "mjoint": FilingStatus.MARRIED_FILING_JOINTLY,
    "mseparate": FilingStatus.MARRIED_FILING_SEPARATELY,
    "headhh": FilingStatus.HEAD_OF_HOUSEHOLD,
    "widow": FilingStatus.QUALIFYING_SURVIVING_SPOUSE,
}


def _load_policy() -> dict | None:
    """Load the cached TC policy JSON, or None if unavailable."""
    if not POLICY_JSON.exists():
        return None
    with open(POLICY_JSON) as f:
        return json.load(f)


def _load_overrides() -> dict:
    """Load known TC corrections."""
    if not OVERRIDES_PATH.exists():
        return {}
    with open(OVERRIDES_PATH) as f:
        data = json.load(f)
    return data.get("overrides", {})


def _is_overridden(overrides: dict, param: str, year: int, mars: str) -> bool:
    """Check if a parameter has a known override."""
    return f"{param}:{year}:{mars}" in overrides


def _get_tc_value(policy: dict, param: str, year: int, mars: str) -> float | None:
    """Extract a MARS-keyed value from TC policy JSON."""
    for entry in policy[param]["value"]:
        if entry["year"] == year and entry.get("MARS") == mars:
            return float(entry["value"])
    return None


@pytest.fixture(scope="module")
def policy_data() -> dict:
    """Load TC policy data, skip if not cached."""
    data = _load_policy()
    if data is None:
        pytest.skip(
            "Tax-Calculator policy JSON not cached. "
            "Run 'python scripts/sync_tax_data.py download' first."
        )
    return data


@pytest.fixture(scope="module")
def overrides() -> dict:
    """Load known TC corrections."""
    return _load_overrides()


class TestBracketsMatchTC:
    """Verify our bracket data matches Tax-Calculator."""

    @pytest.mark.parametrize("year", YEARS)
    @pytest.mark.parametrize("mars,status", list(MARS_TO_STATUS.items()))
    def test_bracket_thresholds(
        self,
        policy_data: dict,
        overrides: dict,
        year: int,
        mars: str,
        status: FilingStatus,
    ) -> None:
        """Each bracket threshold must match TC (or override)."""
        our_brackets = get_brackets(year, status)

        for i in range(6):
            param = f"II_brk{i + 1}"
            tc_val = _get_tc_value(policy_data, param, year, mars)
            if tc_val is None:
                pytest.skip(f"No TC data for {param}/{year}/{mars}")

            our_val = our_brackets[i][1]

            if _is_overridden(overrides, param, year, mars):
                # Verify our value matches the override, not TC
                override_val = overrides[f"{param}:{year}:{mars}"]["value"]
                assert our_val == override_val, (
                    f"{param} {year}/{mars}: ours={our_val} != override={override_val}"
                )
            else:
                assert our_val == tc_val, (
                    f"{param} {year}/{mars}: ours={our_val} != TC={tc_val}"
                )


class TestDeductionsMatchTC:
    """Verify our standard deduction data matches Tax-Calculator."""

    @pytest.mark.parametrize("year", YEARS)
    @pytest.mark.parametrize("mars,status", list(MARS_TO_STATUS.items()))
    def test_standard_deduction(
        self,
        policy_data: dict,
        overrides: dict,
        year: int,
        mars: str,
        status: FilingStatus,
    ) -> None:
        """Each standard deduction must match TC (or override)."""
        tc_val = _get_tc_value(policy_data, "STD", year, mars)
        if tc_val is None:
            pytest.skip(f"No TC data for STD/{year}/{mars}")

        our_val = get_standard_deduction(year, status)

        if _is_overridden(overrides, "STD", year, mars):
            override_val = overrides[f"STD:{year}:{mars}"]["value"]
            assert our_val == override_val
        else:
            assert our_val == tc_val, (
                f"STD {year}/{mars}: ours={our_val} != TC={tc_val}"
            )


class TestCapGainsMatchTC:
    """Verify our capital gains thresholds match Tax-Calculator."""

    @pytest.mark.parametrize("year", YEARS)
    @pytest.mark.parametrize("mars,status", list(MARS_TO_STATUS.items()))
    def test_cap_gains_thresholds(
        self,
        policy_data: dict,
        overrides: dict,
        year: int,
        mars: str,
        status: FilingStatus,
    ) -> None:
        """Each cap gains threshold must match TC (or override)."""
        our_cg = get_capital_gains_thresholds(year, status)

        for i, param in enumerate(["CG_brk1", "CG_brk2"]):
            tc_val = _get_tc_value(policy_data, param, year, mars)
            if tc_val is None:
                pytest.skip(f"No TC data for {param}/{year}/{mars}")

            our_val = our_cg[i][1]

            if _is_overridden(overrides, param, year, mars):
                override_val = overrides[f"{param}:{year}:{mars}"]["value"]
                assert our_val == override_val
            else:
                assert our_val == tc_val, (
                    f"{param} {year}/{mars}: ours={our_val} != TC={tc_val}"
                )
