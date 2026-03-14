"""Tests for the FastAPI REST API endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from financial_manager.api.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Test the health check endpoint."""

    def test_health_returns_ok(self):
        """GET /api/v1/health should return status ok."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestCalculateEndpoint:
    """Test the POST /api/v1/calculate endpoint."""

    def test_basic_calculation(self):
        """Basic tax calculation via API."""
        response = client.post(
            "/api/v1/calculate",
            json={
                "gross_income": 75_000,
                "filing_status": "single",
                "tax_year": 2024,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tax_year"] == 2024
        assert data["filing_status"] == "single"
        assert data["total_tax"] > 0
        assert "brackets" in data
        assert len(data["brackets"]) > 0

    def test_mfj_calculation(self):
        """MFJ tax calculation via API."""
        response = client.post(
            "/api/v1/calculate",
            json={
                "gross_income": 150_000,
                "filing_status": "married_filing_jointly",
                "tax_year": 2024,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["filing_status"] == "married_filing_jointly"
        assert data["standard_deduction"] == 29_200

    def test_with_itemized_deductions(self):
        """API should accept and apply itemized deductions."""
        response = client.post(
            "/api/v1/calculate",
            json={
                "gross_income": 100_000,
                "filing_status": "single",
                "tax_year": 2024,
                "itemized_deductions": 25_000,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["deduction_used"] == 25_000

    def test_invalid_filing_status(self):
        """Invalid filing status should return 422."""
        response = client.post(
            "/api/v1/calculate",
            json={
                "gross_income": 50_000,
                "filing_status": "invalid_status",
            },
        )
        assert response.status_code == 422

    def test_negative_income_rejected(self):
        """Negative income should return 422."""
        response = client.post(
            "/api/v1/calculate",
            json={
                "gross_income": -1000,
                "filing_status": "single",
            },
        )
        assert response.status_code == 422

    def test_2025_year(self):
        """2025 tax year should work correctly."""
        response = client.post(
            "/api/v1/calculate",
            json={
                "gross_income": 60_000,
                "filing_status": "single",
                "tax_year": 2025,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tax_year"] == 2025
        assert data["standard_deduction"] == 15_750
