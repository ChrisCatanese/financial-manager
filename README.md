# Financial Manager — US Federal Tax Calculator

A modern, web-based US federal income tax calculator with a Python/FastAPI backend
and React + TypeScript + Vite frontend.

**AI Agents:** See [.copilot-context.md](.copilot-context.md) for project context.

---

## Features

- **Progressive bracket calculation** — accurate 2024 and 2025 federal tax brackets
- **All filing statuses** — Single, MFJ, MFS, Head of Household, QSS
- **Deductions** — standard deduction auto-applied, itemized deduction override
- **Bracket breakdown** — see exactly how much is taxed at each rate
- **REST API** — FastAPI backend with OpenAPI documentation
- **Modern frontend** — React + TypeScript + Vite with Tailwind CSS

---

## Quick Start

### Backend

```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate    # macOS/Linux

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Run tests
pytest tests/ -v

# 4. Start the API server
uvicorn financial_manager.api.main:app --reload
```

The API will be available at `http://localhost:8000` with docs at `/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/calculate` | Calculate federal income tax |

### Example Request

```json
POST /api/v1/calculate
{
    "gross_income": 100000,
    "filing_status": "single",
    "tax_year": 2024,
    "itemized_deductions": 0
}
```

### Example Response

```json
{
    "tax_year": 2024,
    "filing_status": "single",
    "gross_income": 100000,
    "agi": 100000,
    "standard_deduction": 14600,
    "deduction_used": 14600,
    "taxable_income": 85400,
    "total_tax": 13841.0,
    "effective_rate": 0.13841,
    "marginal_rate": 0.22,
    "brackets": [
        {"rate": 0.10, "range_low": 0, "range_high": 11600, "taxable_in_bracket": 11600, "tax_in_bracket": 1160.0},
        {"rate": 0.12, "range_low": 11600, "range_high": 47150, "taxable_in_bracket": 35550, "tax_in_bracket": 4266.0},
        {"rate": 0.22, "range_low": 47150, "range_high": 85400, "taxable_in_bracket": 38250, "tax_in_bracket": 8415.0}
    ]
}
```

---

## Project Structure

```
financial-manager/
├── src/financial_manager/       # Python backend
│   ├── api/                     # FastAPI endpoints
│   ├── engine/                  # Tax calculation logic
│   ├── models/                  # Pydantic models
│   └── data/                    # Tax bracket data
├── frontend/                    # React + Vite + TypeScript
├── tests/                       # Python test suite
├── scripts/                     # Utility scripts
└── docs/                        # Requirements & traceability
```

---

## Development

```bash
# Run all checks
pytest tests/ -v                        # Tests
ruff check . --fix                      # Lint
mypy src/                               # Type check
python3 scripts/validate_change_log.py  # Change log
pre-commit run --all-files              # All hooks

# Frontend
cd frontend && npm test && npm run build
```

---

## Supported Tax Years & Filing Statuses

| Tax Year | Single | MFJ | MFS | HoH | QSS |
|----------|--------|-----|-----|-----|-----|
| 2024 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 2025 | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## Author

Chris Catanese
