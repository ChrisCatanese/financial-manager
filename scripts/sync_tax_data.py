#!/usr/bin/env python3
"""Sync tax data from PSLmodels/Tax-Calculator.

Downloads policy_current_law.json from the Tax-Calculator project and
auto-generates the Python data modules used by our tax engine.

Usage:
    python scripts/sync_tax_data.py generate     # Download and regenerate data files
    python scripts/sync_tax_data.py check         # Validate current files match upstream
    python scripts/sync_tax_data.py download      # Just download/refresh the cached JSON

Generated files:
    src/financial_manager/data/tax_brackets.py
    src/financial_manager/data/standard_deductions.py
    src/financial_manager/data/capital_gains_rates.py

Source: https://github.com/PSLmodels/Tax-Calculator (CC0 public domain)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger("sync_tax_data")

# ── Paths ────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / ".cache" / "reference"
SRC_DATA = ROOT / "src" / "financial_manager" / "data"
OVERRIDES_PATH = ROOT / "scripts" / "tax_data_overrides.json"

# ── Configuration ────────────────────────────────────────────────────
TC_RAW_URL = (
    "https://raw.githubusercontent.com/PSLmodels/Tax-Calculator"
    "/master/taxcalc/policy_current_law.json"
)
SUPPORTED_YEARS: list[int] = [2023, 2024, 2025]
REV_PROC_SOURCES: dict[int, str] = {
    2023: "IRS Rev. Proc. 2022-38",
    2024: "IRS Rev. Proc. 2023-34",
    2025: "IRS Rev. Proc. 2024-40",
}

# Ordered (tc_mars, our_filing_status_name) — controls output ordering
FILING_STATUS_ORDER: list[tuple[str, str]] = [
    ("single", "SINGLE"),
    ("mjoint", "MARRIED_FILING_JOINTLY"),
    ("widow", "QUALIFYING_SURVIVING_SPOUSE"),
    ("mseparate", "MARRIED_FILING_SEPARATELY"),
    ("headhh", "HEAD_OF_HOUSEHOLD"),
]


# ── Download / Cache ─────────────────────────────────────────────────


def _download_policy_json(*, force: bool = False) -> dict[str, Any]:
    """Download policy_current_law.json, caching to .cache/reference/.

    Args:
        force: Re-download even if cached file exists.

    Returns:
        Parsed JSON as a dict.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached = CACHE_DIR / "policy_current_law.json"
    hash_file = CACHE_DIR / "policy_current_law.sha256"

    if cached.exists() and not force:
        logger.info("Using cached %s", cached)
        with open(cached) as f:
            return json.load(f)

    logger.info("Downloading Tax-Calculator policy JSON from %s", TC_RAW_URL)
    req = urllib.request.Request(TC_RAW_URL, headers={"User-Agent": "financial-manager-sync/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()

    new_hash = hashlib.sha256(raw).hexdigest()
    old_hash = hash_file.read_text().strip() if hash_file.exists() else ""

    if new_hash != old_hash:
        logger.info("Upstream data changed (hash %s -> %s)", old_hash[:12] or "none", new_hash[:12])
    else:
        logger.info("Upstream data unchanged (hash %s)", new_hash[:12])

    cached.write_bytes(raw)
    hash_file.write_text(new_hash + "\n")
    return json.loads(raw)


# ── TC Data Extraction ───────────────────────────────────────────────


def _load_overrides() -> dict[str, Any]:
    """Load known corrections from tax_data_overrides.json."""
    if not OVERRIDES_PATH.exists():
        return {}
    with open(OVERRIDES_PATH) as f:
        data = json.load(f)
    return data.get("overrides", {})


def _get_tc_values_by_mars(
    policy: dict[str, Any],
    param: str,
    year: int,
) -> dict[str, float]:
    """Extract all MARS-keyed values for a parameter and year.

    Args:
        policy: The full TC policy JSON dict.
        param: Parameter name (e.g. 'II_brk1', 'STD').
        year: Tax year.

    Returns:
        Dict mapping TC MARS string to float value.
    """
    result: dict[str, float] = {}
    for entry in policy[param]["value"]:
        if entry["year"] == year:
            mars = entry.get("MARS")
            if mars:
                result[mars] = float(entry["value"])
    return result


def _get_tc_scalar(policy: dict[str, Any], param: str, year: int) -> float | None:
    """Extract a non-MARS scalar value for a parameter and year.

    Tax-Calculator uses "last value wins" semantics: if a year isn't
    explicitly listed, the most recent prior year's value applies.

    Args:
        policy: The full TC policy JSON dict.
        param: Parameter name (e.g. 'II_rt1').
        year: Tax year.

    Returns:
        The float value, or None if no data exists at or before the year.
    """
    best: float | None = None
    best_year = -1
    for entry in policy[param]["value"]:
        entry_year = entry["year"]
        if entry_year <= year and entry_year > best_year:
            best = float(entry["value"])
            best_year = entry_year
    return best


def _apply_overrides(
    overrides: dict[str, Any],
    param: str,
    year: int,
    mars: str,
    tc_value: float,
) -> float:
    """Apply override if one exists for this parameter/year/mars combo.

    Args:
        overrides: The loaded overrides dict.
        param: TC parameter name.
        year: Tax year.
        mars: TC MARS string.
        tc_value: Original value from Tax-Calculator.

    Returns:
        Corrected value if override exists, otherwise original tc_value.
    """
    key = f"{param}:{year}:{mars}"
    if key in overrides:
        corrected = overrides[key]["value"]
        logger.info(
            "Override applied: %s = %s -> %s (%s)",
            key,
            tc_value,
            corrected,
            overrides[key].get("note", ""),
        )
        return float(corrected)
    return tc_value


# ── Number Formatting ────────────────────────────────────────────────


def _fmt_int(v: float) -> str:
    """Format a dollar amount as an underscore-separated integer literal.

    Args:
        v: Dollar amount (e.g. 11000.0).

    Returns:
        Formatted string (e.g. '11_000').
    """
    return f"{int(v):_}"


def _fmt_rate(v: float) -> str:
    """Format a tax rate as a 2-decimal float literal.

    Args:
        v: Rate as a decimal (e.g. 0.10).

    Returns:
        Formatted string (e.g. '0.10').
    """
    return f"{v:.2f}"


# ── Code Generation ──────────────────────────────────────────────────


def _generate_brackets_py(
    policy: dict[str, Any],
    years: list[int],
    overrides: dict[str, Any],
) -> str:
    """Generate the complete source code for tax_brackets.py.

    Args:
        policy: TC policy JSON.
        years: Tax years to include.
        overrides: Known corrections dict.

    Returns:
        Complete Python source as a string.
    """
    lines: list[str] = [
        '"""US federal income tax brackets by year and filing status.',
        "",
        "Auto-generated by scripts/sync_tax_data.py from PSLmodels/Tax-Calculator.",
        "Source: https://github.com/PSLmodels/Tax-Calculator (policy_current_law.json)",
        "Do not edit manually - run ``python scripts/sync_tax_data.py generate`` to update.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from financial_manager.models.filing_status import FilingStatus",
        "",
        "# Type alias: list of (rate, upper_bound) tuples - upper_bound is inclusive ceiling",
        "BracketSchedule = list[tuple[float, float]]",
        "",
        "",
        "def get_brackets(tax_year: int, filing_status: FilingStatus) -> BracketSchedule:",
        '    """Return the progressive tax bracket schedule for the given year and status.',
        "",
        "    Args:",
        "        tax_year: Tax year (e.g. 2023, 2024, 2025).",
        "        filing_status: IRS filing status enum.",
        "",
        "    Returns:",
        "        Ordered list of (marginal_rate, bracket_ceiling) tuples.",
        "",
        "    Raises:",
        "        ValueError: If tax_year or filing_status is not supported.",
        '    """',
        "    key = (tax_year, filing_status)",
        "    if key not in TAX_BRACKETS:",
        '        msg = f"No bracket data for year={tax_year}, status={filing_status.value}"',
        "        raise ValueError(msg)",
        "    return TAX_BRACKETS[key]",
        "",
        "",
        "TAX_BRACKETS: dict[tuple[int, FilingStatus], BracketSchedule] = {",
    ]

    brk_params = [f"II_brk{i}" for i in range(1, 7)]
    rt_params = [f"II_rt{i}" for i in range(1, 8)]

    for year in years:
        source = REV_PROC_SOURCES.get(year, "IRS")
        lines.append(f"    # -- {year} -- {source} {'--' * 25}")

        # Rates are not MARS-keyed — same for all filing statuses
        rates: list[float] = []
        for rt_param in rt_params:
            rate = _get_tc_scalar(policy, rt_param, year)
            if rate is None:
                msg = f"Missing rate {rt_param} for year {year}"
                raise ValueError(msg)
            rates.append(rate)

        for tc_mars, fs_name in FILING_STATUS_ORDER:
            brk_values = _get_tc_values_by_mars(policy, brk_params[0], year)
            if tc_mars not in brk_values:
                logger.warning("No bracket data for %s/%s, skipping", year, tc_mars)
                continue

            thresholds: list[float] = []
            for brk_param in brk_params:
                vals = _get_tc_values_by_mars(policy, brk_param, year)
                raw_val = vals[tc_mars]
                val = _apply_overrides(overrides, brk_param, year, tc_mars, raw_val)
                thresholds.append(val)

            lines.append(f"    ({year}, FilingStatus.{fs_name}): [")
            for rate, threshold in zip(rates[:6], thresholds, strict=True):
                lines.append(f"        ({_fmt_rate(rate)}, {_fmt_int(threshold)}),")
            # Last bracket extends to infinity
            lines.append(f'        ({_fmt_rate(rates[6])}, float("inf")),')
            lines.append("    ],")

    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def _generate_deductions_py(
    policy: dict[str, Any],
    years: list[int],
    overrides: dict[str, Any],
) -> str:
    """Generate the complete source code for standard_deductions.py.

    Args:
        policy: TC policy JSON.
        years: Tax years to include.
        overrides: Known corrections dict.

    Returns:
        Complete Python source as a string.
    """
    lines: list[str] = [
        '"""Standard deduction amounts by year and filing status.',
        "",
        "Auto-generated by scripts/sync_tax_data.py from PSLmodels/Tax-Calculator.",
        "Source: https://github.com/PSLmodels/Tax-Calculator (policy_current_law.json)",
        "Do not edit manually - run ``python scripts/sync_tax_data.py generate`` to update.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from financial_manager.models.filing_status import FilingStatus",
        "",
        "# Keyed by (tax_year, filing_status) -> standard deduction amount",
        "STANDARD_DEDUCTIONS: dict[tuple[int, FilingStatus], float] = {",
    ]

    for year in years:
        source = REV_PROC_SOURCES.get(year, "IRS")
        lines.append(f"    # -- {year} -- {source} {'--' * 25}")
        vals = _get_tc_values_by_mars(policy, "STD", year)
        for tc_mars, fs_name in FILING_STATUS_ORDER:
            if tc_mars not in vals:
                continue
            raw_val = vals[tc_mars]
            val = _apply_overrides(overrides, "STD", year, tc_mars, raw_val)
            lines.append(f"    ({year}, FilingStatus.{fs_name}): {_fmt_int(val)},")

    lines.extend(
        [
            "}",
            "",
            "",
            "def get_standard_deduction(tax_year: int, filing_status: FilingStatus) -> float:",
            '    """Return the standard deduction for the given year and filing status.',
            "",
            "    Args:",
            "        tax_year: Tax year (e.g. 2023, 2024, 2025).",
            "        filing_status: IRS filing status.",
            "",
            "    Returns:",
            "        Standard deduction amount in dollars.",
            "",
            "    Raises:",
            "        ValueError: If year/status combination is not supported.",
            '    """',
            "    key = (tax_year, filing_status)",
            "    if key not in STANDARD_DEDUCTIONS:",
            '        msg = f"No standard deduction data for year={tax_year}, status={filing_status.value}"',
            "        raise ValueError(msg)",
            "    return STANDARD_DEDUCTIONS[key]",
            "",
        ]
    )

    return "\n".join(lines)


def _generate_cap_gains_py(
    policy: dict[str, Any],
    years: list[int],
    overrides: dict[str, Any],
) -> str:
    """Generate the complete source code for capital_gains_rates.py.

    Args:
        policy: TC policy JSON.
        years: Tax years to include.
        overrides: Known corrections dict.

    Returns:
        Complete Python source as a string.
    """
    lines: list[str] = [
        '"""Long-term capital gains and qualified dividends rate thresholds.',
        "",
        "Auto-generated by scripts/sync_tax_data.py from PSLmodels/Tax-Calculator.",
        "Source: https://github.com/PSLmodels/Tax-Calculator (policy_current_law.json)",
        "Do not edit manually - run ``python scripts/sync_tax_data.py generate`` to update.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from financial_manager.models.filing_status import FilingStatus",
        "",
        "# Type alias: list of (rate, threshold) tuples",
        "CapGainsSchedule = list[tuple[float, float]]",
        "",
        "",
        "def get_capital_gains_thresholds(",
        "    tax_year: int,",
        "    filing_status: FilingStatus,",
        ") -> CapGainsSchedule:",
        '    """Return the capital gains rate thresholds for the given year and status.',
        "",
        "    Args:",
        "        tax_year: Tax year (e.g. 2023, 2024, 2025).",
        "        filing_status: IRS filing status enum.",
        "",
        "    Returns:",
        "        Ordered list of (rate, threshold) tuples. The last rate applies",
        "        to income above the highest threshold.",
        "",
        "    Raises:",
        "        ValueError: If tax_year or filing_status is not supported.",
        '    """',
        "    key = (tax_year, filing_status)",
        "    if key not in CAP_GAINS_THRESHOLDS:",
        '        msg = f"No capital gains data for year={tax_year}, status={filing_status.value}"',
        "        raise ValueError(msg)",
        "    return CAP_GAINS_THRESHOLDS[key]",
        "",
        "",
        "CAP_GAINS_THRESHOLDS: dict[tuple[int, FilingStatus], CapGainsSchedule] = {",
    ]

    for year in years:
        source = REV_PROC_SOURCES.get(year, "IRS")
        lines.append(f"    # -- {year} -- {source} {'--' * 25}")

        # CG rates are not MARS-keyed (same for all statuses)
        cg_rates: list[float] = []
        for i in range(1, 4):
            rate = _get_tc_scalar(policy, f"CG_rt{i}", year)
            if rate is None:
                msg = f"Missing CG_rt{i} for year {year}"
                raise ValueError(msg)
            cg_rates.append(rate)

        for tc_mars, fs_name in FILING_STATUS_ORDER:
            brk1_vals = _get_tc_values_by_mars(policy, "CG_brk1", year)
            if tc_mars not in brk1_vals:
                continue

            t1_raw = brk1_vals[tc_mars]
            t1 = _apply_overrides(overrides, "CG_brk1", year, tc_mars, t1_raw)

            brk2_vals = _get_tc_values_by_mars(policy, "CG_brk2", year)
            t2_raw = brk2_vals[tc_mars]
            t2 = _apply_overrides(overrides, "CG_brk2", year, tc_mars, t2_raw)

            lines.append(f"    ({year}, FilingStatus.{fs_name}): [")
            lines.append(f"        ({_fmt_rate(cg_rates[0])}, {_fmt_int(t1)}),")
            lines.append(f"        ({_fmt_rate(cg_rates[1])}, {_fmt_int(t2)}),")
            lines.append(f'        ({_fmt_rate(cg_rates[2])}, float("inf")),')
            lines.append("    ],")

    lines.append("}")
    lines.append("")
    return "\n".join(lines)


# ── Commands ─────────────────────────────────────────────────────────


def _cmd_download(args: argparse.Namespace) -> int:
    """Download/refresh the cached TC JSON."""
    _download_policy_json(force=args.force)
    logger.info("Policy JSON cached at %s", CACHE_DIR / "policy_current_law.json")
    return 0


def _cmd_generate(args: argparse.Namespace) -> int:
    """Download TC data and regenerate all Python data files."""
    policy = _download_policy_json(force=args.force)
    overrides = _load_overrides()
    years = args.years or SUPPORTED_YEARS

    files = {
        SRC_DATA / "tax_brackets.py": _generate_brackets_py(policy, years, overrides),
        SRC_DATA / "standard_deductions.py": _generate_deductions_py(policy, years, overrides),
        SRC_DATA / "capital_gains_rates.py": _generate_cap_gains_py(policy, years, overrides),
    }

    for path, content in files.items():
        path.write_text(content)
        logger.info("Generated %s", path.relative_to(ROOT))

    logger.info("Done. Run 'pytest tests/' to validate, then 'ruff format src/' to finalize.")
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    """Validate that current data files match what upstream would generate."""
    policy = _download_policy_json(force=args.force)
    overrides = _load_overrides()
    years = args.years or SUPPORTED_YEARS

    generators = {
        SRC_DATA / "tax_brackets.py": _generate_brackets_py,
        SRC_DATA / "standard_deductions.py": _generate_deductions_py,
        SRC_DATA / "capital_gains_rates.py": _generate_cap_gains_py,
    }

    mismatches = 0
    for path, gen_fn in generators.items():
        expected = gen_fn(policy, years, overrides)
        if not path.exists():
            logger.error("MISSING: %s", path.relative_to(ROOT))
            mismatches += 1
            continue
        actual = path.read_text()
        if actual != expected:
            logger.error("MISMATCH: %s differs from upstream", path.relative_to(ROOT))
            mismatches += 1
        else:
            logger.info("OK: %s matches upstream", path.relative_to(ROOT))

    if mismatches:
        logger.error(
            "%d file(s) out of sync. Run 'python scripts/sync_tax_data.py generate' to fix.",
            mismatches,
        )
        return 1
    logger.info("All data files match upstream Tax-Calculator data.")
    return 0


# ── CLI ──────────────────────────────────────────────────────────────


def main() -> int:
    """Entry point for the sync script."""
    parser = argparse.ArgumentParser(
        description="Sync tax data from PSLmodels/Tax-Calculator.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if cached",
    )
    parser.add_argument(
        "--years",
        type=int,
        nargs="+",
        default=None,
        help=f"Tax years to include (default: {SUPPORTED_YEARS})",
    )

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("download", help="Download/refresh the cached TC JSON")
    sub.add_parser("generate", help="Download TC data and regenerate data files")
    sub.add_parser("check", help="Validate current files match upstream")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    handlers = {
        "download": _cmd_download,
        "generate": _cmd_generate,
        "check": _cmd_check,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
