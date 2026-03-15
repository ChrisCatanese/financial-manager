"""Tests for the pipeline API routes."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from financial_manager.api.main import app
from financial_manager.connectors.data_mapper import ImportSummary
from financial_manager.engine.assembler import (
    CreditSection,
    DeductionSection,
    IncomeSection,
    RealEstateSection,
    TaxPicture,
    WithholdingSection,
)

client = TestClient(app)


def _make_picture(**overrides: object) -> TaxPicture:
    """Build a minimal TaxPicture for testing."""
    defaults: dict[str, object] = {
        "tax_year": 2025,
        "filing_status": "married_filing_jointly",
        "income": IncomeSection(wages=200_000, taxable_interest=500, qualified_dividends=1_000),
        "deductions": DeductionSection(mortgage_interest=15_000, salt_deduction=10_000),
        "credits": CreditSection(),
        "withholding": WithholdingSection(w2_withholding=40_000, total_medicare_wages=200_000),
        "real_estate": RealEstateSection(),
        "documents": [],
        "gaps": [],
    }
    defaults.update(overrides)
    return TaxPicture(**defaults)  # type: ignore[arg-type]


def _make_import_summary() -> ImportSummary:
    """Build a minimal ImportSummary for testing."""
    return ImportSummary(
        tax_year=2025,
        total_interest=200.0,
        total_ordinary_dividends=300.0,
        total_qualified_dividends=150.0,
        total_short_term_gains=0.0,
        total_long_term_gains=500.0,
        sources_imported=2,
    )


@pytest.fixture()
def _mock_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch assembler and importer for fast unit tests."""
    picture = _make_picture()
    import_summary = _make_import_summary()

    monkeypatch.setattr(
        "financial_manager.api.pipeline_routes.load_user_config",
        lambda: MagicMock(tax_year=2025),
    )
    monkeypatch.setattr(
        "financial_manager.api.pipeline_routes.get_folder_configs",
        lambda c: [],
    )
    monkeypatch.setattr(
        "financial_manager.api.pipeline_routes.scan_multiple_folders",
        lambda configs: [],
    )
    monkeypatch.setattr(
        "financial_manager.api.pipeline_routes.assemble_tax_picture",
        lambda scanned, config: picture,
    )
    monkeypatch.setattr(
        "financial_manager.api.pipeline_routes._run_imports",
        lambda config: import_summary,
    )


class TestAssembleEndpoint:
    """Tests for POST /api/v1/pipeline/assemble."""

    @pytest.mark.usefixtures("_mock_pipeline")
    def test_assemble_returns_tax_picture(self) -> None:
        """Assemble endpoint returns structured tax picture."""
        resp = client.post("/api/v1/pipeline/assemble")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tax_year"] == 2025
        assert data["filing_status"] == "married_filing_jointly"
        assert "income" in data
        assert data["income"]["wages"] == 200_000

    @pytest.mark.usefixtures("_mock_pipeline")
    def test_assemble_returns_deductions(self) -> None:
        """Assemble includes deduction data."""
        data = client.post("/api/v1/pipeline/assemble").json()
        assert data["deductions"]["mortgage_interest"] == 15_000
        assert data["deductions"]["salt_deduction"] == 10_000

    @pytest.mark.usefixtures("_mock_pipeline")
    def test_assemble_returns_documents_list(self) -> None:
        """Assemble includes documents and gaps."""
        data = client.post("/api/v1/pipeline/assemble").json()
        assert "documents" in data
        assert "gaps" in data
        assert isinstance(data["documents"], list)


class TestCalculateEndpoint:
    """Tests for POST /api/v1/pipeline/calculate."""

    @pytest.mark.usefixtures("_mock_pipeline")
    def test_calculate_returns_result(self) -> None:
        """Calculate endpoint returns tax computation."""
        resp = client.post("/api/v1/pipeline/calculate")
        assert resp.status_code == 200
        data = resp.json()
        assert "result" in data
        assert "tax_input" in data
        assert data["result"]["tax_year"] == 2025

    @pytest.mark.usefixtures("_mock_pipeline")
    def test_calculate_result_has_brackets(self) -> None:
        """Calculation includes bracket breakdown."""
        data = client.post("/api/v1/pipeline/calculate").json()
        assert "brackets" in data["result"]
        assert len(data["result"]["brackets"]) > 0

    @pytest.mark.usefixtures("_mock_pipeline")
    def test_calculate_merges_imports(self) -> None:
        """Calculation includes data from financial imports."""
        data = client.post("/api/v1/pipeline/calculate").json()
        # The import summary adds $200 interest + $300 dividends + $500 lt gains
        # So gross should be > wages alone
        assert data["tax_input"]["gross_income"] > 200_000


class TestFullPipelineEndpoint:
    """Tests for POST /api/v1/pipeline/full."""

    @pytest.mark.usefixtures("_mock_pipeline")
    def test_full_returns_all_sections(self) -> None:
        """Full pipeline returns income, deductions, credits, withholding, calculation."""
        resp = client.post("/api/v1/pipeline/full")
        assert resp.status_code == 200
        data = resp.json()
        expected_keys = (
            "income", "deductions", "credits", "withholding",
            "calculation", "real_estate", "documents", "gaps", "sources",
        )
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"

    @pytest.mark.usefixtures("_mock_pipeline")
    def test_full_income_merges_imports(self) -> None:
        """Income section combines document and import data."""
        data = client.post("/api/v1/pipeline/full").json()
        inc = data["income"]
        # Interest: 500 from docs + 200 from imports
        assert inc["interest"] == 700.0
        assert inc["interest_from_docs"] == 500.0
        assert inc["interest_from_imports"] == 200.0

    @pytest.mark.usefixtures("_mock_pipeline")
    def test_full_deduction_method(self) -> None:
        """Deduction method is reported."""
        data = client.post("/api/v1/pipeline/full").json()
        assert data["deductions"]["method"] in ("standard", "itemized")

    @pytest.mark.usefixtures("_mock_pipeline")
    def test_full_calculation_has_refund_or_owed(self) -> None:
        """Calculation includes refund_or_owed."""
        data = client.post("/api/v1/pipeline/full").json()
        calc = data["calculation"]
        assert "refund_or_owed" in calc
        assert "effective_rate" in calc
        assert "marginal_rate" in calc

    @pytest.mark.usefixtures("_mock_pipeline")
    def test_full_sources_metadata(self) -> None:
        """Sources metadata is correct."""
        data = client.post("/api/v1/pipeline/full").json()
        src = data["sources"]
        assert src["documents_scanned"] == 0
        assert src["documents_extracted"] == 0
        assert src["financial_files_imported"] == 2

    @pytest.mark.usefixtures("_mock_pipeline")
    def test_full_withholding_total(self) -> None:
        """Withholding totals are correct."""
        data = client.post("/api/v1/pipeline/full").json()
        wh = data["withholding"]
        assert wh["w2"] == 40_000
        assert wh["total"] == 40_000


class TestBuildTaxInput:
    """Tests for the internal _build_tax_input_from_picture function."""

    def test_basic_mapping(self) -> None:
        """Basic mapping from TaxPicture to TaxInput."""
        from financial_manager.api.pipeline_routes import _build_tax_input_from_picture

        picture = _make_picture()
        ti = _build_tax_input_from_picture(picture)
        assert ti.filing_status.value == "married_filing_jointly"
        assert ti.tax_year == 2025
        assert ti.w2_medicare_wages == 200_000

    def test_with_import_summary(self) -> None:
        """Import summary values get merged."""
        from financial_manager.api.pipeline_routes import _build_tax_input_from_picture

        picture = _make_picture()
        summary = _make_import_summary()
        ti = _build_tax_input_from_picture(picture, summary)
        # qualified_dividends = 1000 (docs) + 150 (imports)
        assert ti.qualified_dividends == 1_150.0
        # net_capital_gains = 500 lt from imports
        assert ti.net_capital_gains == 500.0

    def test_fallback_filing_status(self) -> None:
        """Invalid filing status defaults to MFJ."""
        from financial_manager.api.pipeline_routes import _build_tax_input_from_picture

        picture = _make_picture(filing_status="invalid_status")
        ti = _build_tax_input_from_picture(picture)
        assert ti.filing_status.value == "married_filing_jointly"
