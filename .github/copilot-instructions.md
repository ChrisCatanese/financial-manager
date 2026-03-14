# Copilot Instructions — Financial Manager (US Tax Calculator)

> See **AGENTS.md** for the complete project standards and coding conventions.
> This file provides GitHub Copilot–specific guidance.

---

## Mandatory Workflow

Every change follows: **Validate → Fix → Revalidate**

1. Write or identify a test that covers the issue
2. Confirm it fails — proves the test works
3. Fix the code — minimum necessary change
4. Run the full test suite — all must pass
5. Run `pre-commit run --all-files` — all hooks must pass

## Build & Test

```bash
# Backend
pytest tests/ -v                        # Tests — MUST pass
ruff check . --fix                      # Lint
mypy src/                               # Type check
python3 scripts/validate_change_log.py  # Defect log
pre-commit run --all-files              # All hooks

# Frontend
cd frontend && npm test                 # Frontend tests
cd frontend && npm run build            # Build check
```

## Key Rules

- **No `print()` in `src/` or `scripts/`** — use `logging` module (enforced by ruff T20)
- **Google-style docstrings** on all public functions and classes
- **Type hints** on all public function signatures
- Every `src/` module must appear in `docs/requirements/traceability-matrix.md`
- Log defects in `docs/change-log.json` **before** applying fixes
- Never remove tests to make failures pass

## Domain Context

This project is a **US Federal Tax Calculator** supporting:
- 2024 and 2025 tax years
- All filing statuses (Single, MFJ, MFS, HoH, QSS)
- Progressive bracket calculations
- Standard and itemized deductions
- Common tax credits (Child Tax Credit, EITC, etc.)
- AMT calculations
- Capital gains tax rates

## Coding Conventions

- Python ≥ 3.10, line length 120
- FastAPI for REST API, Pydantic for models
- React + Vite + TypeScript for frontend
- Conventional commits: `feat(scope):`, `fix(scope):`, `test(scope):`, `docs(scope):`
