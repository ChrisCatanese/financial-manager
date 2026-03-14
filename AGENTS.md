# AGENTS.md — Financial Manager (US Tax Calculator)

> **Enforcement:** strict | **Python:** ≥3.10 | **Linter:** ruff | **Types:** mypy | **Manifest:** dq-manifest.yaml

This is the Financial Manager project — a US federal tax calculator with a modern web frontend.

---

## Build & Test

```bash
# Backend
pip install -e ".[dev]"               # Install with dev dependencies
pytest tests/ -v                      # Run tests — MUST pass before commit
ruff check . --fix                    # Lint + auto-fix
mypy src/                             # Type check
pre-commit run --all-files            # All pre-commit hooks
python3 scripts/validate_change_log.py  # Change log validation

# Frontend
cd frontend && npm install            # Install frontend dependencies
npm run build                         # Build frontend
npm run test                          # Run frontend tests
```

## Project Structure

```
├── AGENTS.md                        ← AI agent instructions (this file)
├── .github/copilot-instructions.md  ← GitHub Copilot instructions
├── dq-manifest.yaml                 ← Structure enforcement contract
├── pyproject.toml                   ← Build config (ruff, mypy, pytest)
├── .pre-commit-config.yaml          ← Pre-commit hooks
├── docs/
│   ├── change-log.json              ← Defect tracking
│   └── requirements/
│       ├── business-requirements.md     ← Why (BR-NNN)
│       ├── functional-requirements.md   ← What (FR-NNN)
│       ├── technical-requirements.md    ← How (TR-NNN)
│       └── traceability-matrix.md       ← TR → FR → BR → Code → Tests
├── src/
│   └── financial_manager/           ← Core Python package
│       ├── __init__.py
│       ├── api/                     ← FastAPI REST endpoints
│       ├── engine/                  ← Tax calculation engine
│       ├── models/                  ← Pydantic data models
│       └── data/                    ← Tax brackets, rates, constants
├── frontend/                        ← React + Vite + TypeScript
│   ├── src/
│   │   ├── components/              ← React components
│   │   ├── hooks/                   ← Custom React hooks
│   │   ├── services/                ← API client layer
│   │   └── types/                   ← TypeScript type definitions
│   └── package.json
├── scripts/                         ← Pipeline & utility scripts
└── tests/                           ← Python tests
```

---

## 🚨 Mandatory Workflow: Validate → Fix → Revalidate

Every change follows this cycle — **no exceptions:**

1. **Identify or write a test** that covers the issue
2. **Confirm it fails** — this proves the test works
3. **Fix the code** — minimum necessary change
4. **Run the full test suite** — all tests must pass
5. **Run `pre-commit run --all-files`** — all hooks must pass

---

## Change Log Mandate

Before making **any** code change:

1. **Declare scope** — create an entry via CLI:
   ```bash
   python3 scripts/cl_new.py --type bug --severity minor \
     --component "<module>" --summary "<what you are about to change>" \
     --scope "src/module/" "scripts/helper.py"
   ```
2. **Edit within scope** — the gate only allows edits to files covered by an open entry's scope
3. Add or update at least one **test** that proves the fix
4. **Resolve the entry** via CLI:
   ```bash
   python3 scripts/cl_resolve.py CL-00001 \
     --requirement-refs BR-001 FR-002 \
     --test-refs "tests/test_module.py::test_function" \
     --requirement-change "Fixed validation logic" \
     --files "src/module/validator.py" "tests/test_module.py"
   ```
5. Run `python3 scripts/validate_change_log.py` — must pass

**Direct edits to `docs/change-log.json` are denied.** Use the CLI scripts only.

---

## Coding Standards

| Rule | Enforcement |
|------|-------------|
| **No `print()` in core code** | ruff T20 — use `logging` module |
| **No f-strings in logging** | ruff G — use `logging.info("msg %s", var)` |
| **Google-style docstrings** | ruff D — on all public functions/classes |
| **Type hints** | mypy — on all public function signatures |
| **Line length: 120** | ruff E501 |
| **Import order** | ruff I (isort) — stdlib → third-party → local |
| **Python ≥ 3.10** | pyproject.toml `requires-python` |

---

## Traceability Rules

- Every module in `src/` **MUST** appear in `docs/requirements/traceability-matrix.md`
- The matrix links: Technical Req → Functional Req → Business Req → Code → Tests
- `notebooks/` is an **exploratory carve-out** — exempt from traceability
- Code in `notebooks/` **MUST NOT** be imported by `src/` or `scripts/`

---

## Git Practices

```
feat(component): add new capability
fix(component): resolve specific issue
test(component): add/update tests
docs(component): update documentation
refactor(component): restructure without behavior change
```

Include `Co-Authored-By:` header when AI agents contribute to a commit.

---

## DO NOT

- ❌ Remove or skip failing tests to unblock yourself
- ❌ Declare a fix complete without running the full test suite
- ❌ Delete entries from `docs/change-log.json`
- ❌ Edit `docs/change-log.json` directly — use `cl_new.py` and `cl_resolve.py` only
- ❌ Commit directly to `main` branch
- ❌ Add dependencies without updating `pyproject.toml`
- ❌ Use `print()` in `src/` or `scripts/` — use `logging`
- ❌ Suppress errors or warnings — fail fast, fix forward
