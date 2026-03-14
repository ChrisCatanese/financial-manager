"""FastAPI application — US Federal Tax Calculator API."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from financial_manager.engine.calculator import TaxCalculator
from financial_manager.models.tax_input import TaxInput
from financial_manager.models.tax_result import TaxResult

logger = logging.getLogger(__name__)

app = FastAPI(
    title="US Federal Tax Calculator",
    description="Calculate US federal income tax with progressive brackets, deductions, and credits.",
    version="0.1.0",
)

# CORS — allow the Vite dev server and production frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_calculator = TaxCalculator()


@app.get("/api/v1/health")
def health_check() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Simple status dict.
    """
    return {"status": "ok"}


@app.post("/api/v1/calculate", response_model=TaxResult)
def calculate_tax(tax_input: TaxInput) -> TaxResult:
    """Calculate federal income tax for the given input.

    Args:
        tax_input: Income, filing status, deductions, and other parameters.

    Returns:
        Complete tax calculation result with bracket breakdown.
    """
    logger.info("API: /api/v1/calculate called")
    return _calculator.calculate(tax_input)
