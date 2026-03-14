# Traceability Standard

> Every line of core production code must trace to a requirement.

---

## Core Boundary

The **core boundary** is defined by `dq-manifest.yaml`:

```yaml
core_paths:
  - src/
```

Everything under `core_paths` is **core production code** and must:

1. Map to a Technical Requirement (TR) in `docs/requirements/technical-requirements.md`
2. Appear in the traceability matrix at `docs/requirements/traceability-matrix.md`
3. Have a corresponding test

## Exploratory Carve-Out

The following directories are **exploratory** and exempt from traceability:

| Directory | Purpose | Import Restriction |
|-----------|---------|-------------------|
| `notebooks/` | Jupyter analysis, prototyping | Cannot be imported by `src/` |
| `scripts/` | Pipeline launchers, utilities | May import from `src/` |
| `config/` | Configuration files | Not Python code |
| `frontend/` | React frontend (separate test suite) | Not Python code |

**Rule:** `src/` code must never `import` from `notebooks/`.

## Pre-Commit Enforcement

Structure enforcement runs automatically at commit time:

| Check | Gate |
|-------|------|
| Every `src/` module in traceability matrix | ❌ Commit blocked |
| `notebooks/` not imported by `src/` | ❌ Commit blocked |
| `dq-manifest.yaml` present and valid | ❌ Commit blocked |
