"""Tests for expanded API endpoints — profile, checklist, scan, upload."""

from __future__ import annotations

from fastapi.testclient import TestClient

from financial_manager.api.main import app

client = TestClient(app)


class TestProfileEndpoints:
    """Tests for /api/v1/profile endpoints."""

    def test_get_profile_before_creation(self) -> None:
        """GET /profile should return error when no profile exists."""
        # Reset state
        from financial_manager.api import main

        main._current_profile = None
        main._current_checklist = None

        response = client.get("/api/v1/profile")
        assert response.status_code == 200
        assert "error" in response.json()

    def test_create_profile(self) -> None:
        """POST /profile should create a profile and return it."""
        payload = {
            "tax_year": 2025,
            "filing_status": "married_filing_jointly",
            "filer_name": "Chris",
            "spouse_name": "Sarah",
            "filer_employment": "w2_employee",
            "spouse_employment": "w2_employee",
            "has_mortgage": True,
            "purchased_home": True,
            "has_property_tax": True,
            "has_bank_interest": True,
            "investment_accounts": ["brokerage", "roth_ira"],
            "has_prior_year_return": True,
        }
        response = client.post("/api/v1/profile", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["filer_name"] == "Chris"
        assert data["filing_status"] == "married_filing_jointly"

    def test_get_profile_after_creation(self) -> None:
        """GET /profile should return the created profile."""
        # First create
        client.post(
            "/api/v1/profile",
            json={
                "tax_year": 2025,
                "filing_status": "single",
                "filer_employment": "w2_employee",
            },
        )
        response = client.get("/api/v1/profile")
        assert response.status_code == 200
        assert response.json()["filing_status"] == "single"


class TestChecklistEndpoints:
    """Tests for /api/v1/checklist endpoints."""

    def test_checklist_after_profile(self) -> None:
        """Checklist should be generated after profile creation."""
        client.post(
            "/api/v1/profile",
            json={
                "tax_year": 2025,
                "filing_status": "married_filing_jointly",
                "filer_employment": "w2_employee",
                "spouse_employment": "w2_employee",
                "has_mortgage": True,
                "has_bank_interest": True,
            },
        )
        response = client.get("/api/v1/checklist")
        assert response.status_code == 200
        data = response.json()
        assert data["tax_year"] == 2025
        assert len(data["items"]) > 0

        # Should include W-2, W-2 Spouse, 1098, 1099-INT
        types = [item["doc_type"] for item in data["items"]]
        assert "w2" in types
        assert "w2_spouse" in types
        assert "1098" in types
        assert "1099_int" in types

    def test_checklist_before_profile(self) -> None:
        """Checklist should error if no profile exists."""
        from financial_manager.api import main

        main._current_profile = None
        main._current_checklist = None

        response = client.get("/api/v1/checklist")
        data = response.json()
        assert "error" in data


class TestScanEndpoint:
    """Tests for /api/v1/documents/scan."""

    def test_scan_without_profile(self) -> None:
        """Scan should error without a profile."""
        from financial_manager.api import main

        main._current_profile = None
        main._current_checklist = None

        response = client.post("/api/v1/documents/scan")
        assert "error" in response.json()

    def test_scan_without_path(self) -> None:
        """Scan should error if no path provided and none in profile."""
        client.post(
            "/api/v1/profile",
            json={
                "tax_year": 2025,
                "filing_status": "single",
                "filer_employment": "w2_employee",
            },
        )
        response = client.post("/api/v1/documents/scan")
        assert "error" in response.json()


class TestExtractedDataEndpoint:
    """Tests for /api/v1/documents/extracted."""

    def test_extracted_data_empty(self) -> None:
        """Extracted data should be empty for a fresh checklist."""
        client.post(
            "/api/v1/profile",
            json={
                "tax_year": 2025,
                "filing_status": "single",
                "filer_employment": "w2_employee",
            },
        )
        response = client.get("/api/v1/documents/extracted")
        assert response.status_code == 200
        data = response.json()
        assert data["documents_with_data"] == 0
