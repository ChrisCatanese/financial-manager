"""Import financial data from institution CSV/OFX/QFX exports.

Scans configured export folders (or command-line paths) for supported files,
auto-detects the format, parses and maps to tax-relevant structures, and
outputs a summary.

Usage::

    python scripts/import_financial_data.py
    python scripts/import_financial_data.py --path ~/Downloads/Fidelity
    python scripts/import_financial_data.py --config config/user-config.yaml --year 2025
    python scripts/import_financial_data.py --json  # Machine-readable output
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

from financial_manager.connectors.csv_importer import import_csv, import_csv_folder
from financial_manager.connectors.data_mapper import (
    ImportSummary,
    map_csv_results,
    map_ofx_results,
    merge_summaries,
)
from financial_manager.connectors.ofx_importer import import_ofx, import_ofx_folder
from financial_manager.user_config import load_user_config

logger = logging.getLogger(__name__)


def _scan_path(path: Path, *, recursive: bool = False) -> ImportSummary:
    """Scan a single path for CSV/OFX/QFX files and return mapped summary.

    Args:
        path: File or directory path.
        recursive: Whether to scan subdirectories.

    Returns:
        Aggregated ImportSummary.
    """
    csv_results = []
    ofx_results = []

    if path.is_file():
        ext = path.suffix.lower()
        if ext in (".csv", ".txt"):
            csv_results.append(import_csv(path))
        elif ext in (".ofx", ".qfx"):
            ofx_results.append(import_ofx(path))
        else:
            logger.warning("Unsupported file type: %s", path)
    elif path.is_dir():
        csv_results.extend(import_csv_folder(path, recursive=recursive))
        ofx_results.extend(import_ofx_folder(path, recursive=recursive))
    else:
        logger.warning("Path not found: %s", path)

    csv_summary = map_csv_results(csv_results) if csv_results else ImportSummary()
    ofx_summary = map_ofx_results(ofx_results) if ofx_results else ImportSummary()

    return merge_summaries(csv_summary, ofx_summary)


def _print_summary(summary: ImportSummary) -> None:
    """Print a human-readable summary of imported financial data.

    Args:
        summary: The import summary to display.
    """
    logger.info("=" * 70)
    logger.info("FINANCIAL DATA IMPORT SUMMARY")
    logger.info("=" * 70)
    logger.info("Sources imported: %d", summary.sources_imported)
    logger.info("")

    if summary.interest_income:
        logger.info("── Interest Income (→ 1099-INT) ──")
        for interest in summary.interest_income:
            logger.info(
                "  %s%s: $%.2f",
                interest.institution,
                f" ({interest.account_id})" if interest.account_id else "",
                interest.total_interest,
            )
        logger.info("  TOTAL: $%.2f", summary.total_interest)
        logger.info("")

    if summary.dividend_income:
        logger.info("── Dividend Income (→ 1099-DIV) ──")
        for div in summary.dividend_income:
            logger.info(
                "  %s: $%.2f ordinary, $%.2f qualified",
                div.institution,
                div.ordinary_dividends,
                div.qualified_dividends,
            )
        logger.info("  TOTAL ordinary: $%.2f", summary.total_ordinary_dividends)
        logger.info("")

    if summary.capital_gains:
        logger.info("── Capital Gains (→ Schedule D) ──")
        for gains in summary.capital_gains:
            logger.info(
                "  %s: $%.2f ST, $%.2f LT, $%.2f total (%d transactions)",
                gains.institution,
                gains.short_term_gain,
                gains.long_term_gain,
                gains.total_gain,
                len(gains.transactions),
            )
        logger.info("  TOTAL ST: $%.2f  LT: $%.2f", summary.total_short_term_gains, summary.total_long_term_gains)
        logger.info("")

    if summary.taxable_transactions:
        logger.info("── Tax-Relevant Transactions ──")
        by_category: dict[str, float] = {}
        for txn in summary.taxable_transactions:
            by_category[txn.category] = by_category.get(txn.category, 0) + txn.amount
        for cat, total in sorted(by_category.items()):
            logger.info("  %s: $%.2f", cat, total)
        logger.info("")

    if summary.warnings:
        logger.info("── Warnings ──")
        for w in summary.warnings:
            logger.info("  ⚠ %s", w)

    logger.info("=" * 70)


def main() -> None:
    """Entry point for the financial data import script."""
    parser = argparse.ArgumentParser(
        description="Import financial data from institution CSV/OFX/QFX exports.",
    )
    parser.add_argument(
        "--path",
        type=str,
        action="append",
        help="Path to a file or folder to import (can be repeated).",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to user-config.yaml (default: auto-detect).",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=0,
        help="Tax year to filter for.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON instead of human-readable text.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        default=True,
        help="Scan subdirectories (default: True).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
    )

    # Gather paths to scan
    paths: list[Path] = []

    if args.path:
        for p in args.path:
            paths.append(Path(p).expanduser().resolve())
    else:
        # Load from config
        config = load_user_config(args.config)

        # Use export_paths from accounts
        for acct in config.accounts:
            if acct.export_path:
                export_path = Path(acct.export_path).expanduser().resolve()
                if export_path.exists():
                    paths.append(export_path)
                    logger.info("Account '%s': scanning %s", acct.institution, export_path)
                else:
                    logger.warning("Account '%s': export path not found: %s", acct.institution, export_path)

        if not paths:
            logger.info("No export paths configured. Use --path or add export_path to accounts in config.")
            logger.info("")
            logger.info("Example:")
            logger.info("  python scripts/import_financial_data.py --path ~/Downloads/Fidelity")
            logger.info("")
            logger.info("Or add to config/user-config.yaml:")
            logger.info("  accounts:")
            logger.info("    - institution: Fidelity")
            logger.info("      export_path: ~/Downloads/Fidelity")
            sys.exit(0)

    if not paths:
        logger.error("No paths to scan.")
        sys.exit(1)

    # Scan all paths
    summaries: list[ImportSummary] = []
    for scan_path in paths:
        logger.info("Scanning: %s", scan_path)
        result = _scan_path(scan_path, recursive=args.recursive)
        if args.year:
            result.tax_year = args.year
        summaries.append(result)

    final = merge_summaries(*summaries)
    if args.year:
        final.tax_year = args.year

    # Output
    if args.json:
        output = json.dumps(asdict(final), indent=2, default=str)
        sys.stdout.write(output + "\n")
    else:
        _print_summary(final)


if __name__ == "__main__":
    main()
