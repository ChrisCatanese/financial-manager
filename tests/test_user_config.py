"""Tests for user configuration loading and helpers."""

from __future__ import annotations

import textwrap
from pathlib import Path

from financial_manager.user_config import (
    FilerInfo,
    FinancialAccount,
    KnownFacts,
    UserConfig,
    _resolve_path,
    build_brokerage_patterns,
    build_spouse_w2_patterns,
    load_user_config,
)


class TestResolvedPath:
    """Test path resolution with ~ and env vars."""

    def test_resolves_tilde(self) -> None:
        """Tilde expands to home directory."""
        result = _resolve_path("~/some_test_dir")
        assert result == Path.home() / "some_test_dir"

    def test_resolves_absolute(self) -> None:
        """Absolute paths pass through (resolved)."""
        result = _resolve_path("/tmp/test")
        assert result == Path("/tmp/test").resolve()


class TestLoadUserConfig:
    """Test YAML config loading."""

    def test_returns_defaults_when_no_config(self, tmp_path: Path) -> None:
        """Returns empty UserConfig when no config file exists."""
        result = load_user_config(tmp_path / "nonexistent.yaml")
        assert result.tax_year == 2025
        assert result.primary_filer.first_name == ""

    def test_loads_yaml_config(self, tmp_path: Path) -> None:
        """Loads a complete YAML config."""
        config_path = tmp_path / "test-config.yaml"
        config_path.write_text(textwrap.dedent("""\
            tax_year: 2026
            filing_status: single
            primary_filer:
              first_name: Alice
              last_name: Smith
            spouse:
              first_name: Bob
              last_name: Smith
            folders:
              - path: /tmp/tax
                label: "Tax Docs"
                context: tax
                tax_year_filter: 2026
            known_facts:
              solar_installed_date: "06/15/2026"
              children_count: 2
              children_ages: [5, 8]
            brokerage_names:
              - Schwab
              - Vanguard
            employer_names:
              - Acme Corp
            bank_names:
              - First National
            mortgage_servicer: BigBank Mortgage
            title_company: Secure Title LLC
            municipality: Springfield
        """))
        result = load_user_config(config_path)
        assert result.tax_year == 2026
        assert result.filing_status == "single"
        assert result.primary_filer.first_name == "Alice"
        assert result.spouse.first_name == "Bob"
        assert len(result.folders) == 1
        assert result.folders[0].label == "Tax Docs"
        assert result.folders[0].context == "tax"
        # Legacy fields are migrated into hierarchical model
        assert len(result.solar_installations) == 1
        assert result.solar_installations[0].installed_date == "06/15/2026"
        assert result.children_count == 2
        assert result.brokerage_names == ["Schwab", "Vanguard"]
        assert result.employer_names == ["Acme Corp"]
        assert result.bank_names == ["First National"]
        assert result.mortgage_servicers == ["BigBank Mortgage"]
        assert result.title_companies == ["Secure Title LLC"]
        assert result.municipalities == ["Springfield"]

    def test_handles_empty_yaml(self, tmp_path: Path) -> None:
        """Empty YAML returns defaults."""
        config_path = tmp_path / "empty.yaml"
        config_path.write_text("")
        result = load_user_config(config_path)
        assert result.tax_year == 2025

    def test_handles_minimal_yaml(self, tmp_path: Path) -> None:
        """Minimal config fills in defaults."""
        config_path = tmp_path / "minimal.yaml"
        config_path.write_text("tax_year: 2024\n")
        result = load_user_config(config_path)
        assert result.tax_year == 2024
        assert result.primary_filer.first_name == ""
        assert result.folders == []


class TestBuildSpousePatterns:
    """Test dynamic spouse W-2 pattern building."""

    def test_no_spouse_returns_empty(self) -> None:
        """No spouse name → no patterns."""
        config = UserConfig()
        assert build_spouse_w2_patterns(config) == []

    def test_builds_patterns_from_name(self) -> None:
        """Spouse first name creates bidirectional W-2 patterns."""
        config = UserConfig(spouse=FilerInfo(first_name="Alice"))
        patterns = build_spouse_w2_patterns(config)
        assert len(patterns) >= 2
        # Should match "alice_w2.pdf" and "w2_alice.pdf"
        assert any(p.search("alice_w2_2025") for p in patterns)
        assert any(p.search("w2_alice_2025") for p in patterns)

    def test_includes_extra_patterns(self) -> None:
        """Extra name_patterns from config are included."""
        config = UserConfig(
            spouse=FilerInfo(first_name="Alice", name_patterns=[r"allie.*w[\-\s]?2"])
        )
        patterns = build_spouse_w2_patterns(config)
        assert len(patterns) >= 3
        assert any(p.search("allie_w2_2025") for p in patterns)


class TestBuildBrokeragePatterns:
    """Test dynamic brokerage 1099 pattern building."""

    def test_no_brokerages_returns_empty(self) -> None:
        """No brokerage names → no patterns."""
        config = UserConfig()
        assert build_brokerage_patterns(config) == []

    def test_builds_patterns_from_names(self) -> None:
        """Brokerage accounts create 1099 matching patterns."""
        config = UserConfig(accounts=[
            FinancialAccount(institution="Schwab", account_type="brokerage"),
            FinancialAccount(institution="Vanguard", account_type="brokerage"),
        ])
        patterns = build_brokerage_patterns(config)
        assert len(patterns) == 2
        assert any(p.search("Schwab_1099_2025") for p in patterns)
        assert any(p.search("1099_Vanguard") for p in patterns)


class TestUserConfigDataclass:
    """Test UserConfig defaults and structure."""

    def test_defaults(self) -> None:
        """Default UserConfig has sensible empty values."""
        config = UserConfig()
        assert config.tax_year == 2025
        assert config.filing_status == "married_filing_jointly"
        assert config.primary_filer.first_name == ""
        assert config.spouse.first_name == ""
        assert config.folders == []
        assert config.solar_installations == []
        assert config.brokerage_names == []
        assert config.employer_names == []
        assert config.bank_names == []
        assert config.children_count == 0

    def test_known_facts_defaults(self) -> None:
        """KnownFacts has all zeros/empty defaults."""
        kf = KnownFacts()
        assert kf.estimated_tax_payments == 0.0
        assert kf.charitable_cash == 0.0
        assert kf.charitable_noncash == 0.0
        assert kf.medical_expenses == 0.0
        assert kf.educator_expenses == 0.0
        assert kf.student_loan_interest == 0.0
        assert kf.ira_contributions == 0.0
        assert kf.hsa_contributions == 0.0
        assert kf.notes == []
