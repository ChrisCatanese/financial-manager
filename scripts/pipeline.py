"""Pipeline launcher — single entry point for the core deliverable.

All core source modules must be reachable (directly or transitively)
from this file.

Usage:
    python -m scripts.pipeline
    uvicorn financial_manager.api.main:app --reload
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def run() -> None:
    """Execute the full pipeline — start the API server."""
    import uvicorn

    from financial_manager.api.main import app  # noqa: F401

    logger.info("Starting Financial Manager API server")
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    run()
