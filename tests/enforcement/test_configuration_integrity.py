"""Configuration integrity enforcement.

Criteria enforced:
  CFG-01: dq-manifest.yaml is valid YAML with required keys
  CFG-02: All JSON files in config/ are parseable
  CFG-03: docs/change-log.json is valid with required _meta structure
  CFG-04: pyproject.toml is parseable with required sections
  CFG-05: .pre-commit-config.yaml is valid YAML
  CFG-06: Paths declared in dq-manifest.yaml exist on disk

Run with:  pytest tests/enforcement/test_configuration_integrity.py -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from .conftest import CONFIG_DIR, MANIFEST, ROOT


class TestManifestIntegrity:
    """CFG-01: dq-manifest.yaml must be valid YAML with required structure."""

    def test_manifest_exists(self):
        """Manifest file must exist."""
        assert MANIFEST.exists(), "CFG-01: dq-manifest.yaml missing"

    def test_manifest_is_valid_yaml(self):
        """Manifest must parse as YAML."""
        data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
        assert isinstance(data, dict), "CFG-01: dq-manifest.yaml is not a mapping"

    def test_manifest_has_core_paths(self):
        """Manifest must declare core_paths."""
        data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
        assert "core_paths" in data, "CFG-01: dq-manifest.yaml missing 'core_paths'"

    def test_manifest_has_enforcement(self):
        """Manifest must declare enforcement level."""
        data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
        assert "enforcement" in data, "CFG-01: dq-manifest.yaml missing 'enforcement'"

    def test_manifest_has_test_paths(self):
        """Manifest must declare test_paths."""
        data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
        assert "test_paths" in data, "CFG-01: dq-manifest.yaml missing 'test_paths'"


class TestJsonConfigsParseable:
    """CFG-02: Every .json in config/ must be valid JSON."""

    @staticmethod
    def _config_json_files() -> list[Path]:
        if not CONFIG_DIR.exists():
            return []
        return sorted(CONFIG_DIR.rglob("*.json"))

    @pytest.mark.parametrize(
        "json_file",
        _config_json_files.__func__(),
        ids=[f.name for f in _config_json_files.__func__()],
    )
    def test_json_is_valid(self, json_file: Path):
        """Each JSON config file must parse without error."""
        try:
            json.loads(json_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            pytest.fail(f"CFG-02: {json_file.name} is invalid JSON: {e}")


class TestChangeLogIntegrity:
    """CFG-03: docs/change-log.json must be valid with required structure."""

    CL_PATH = ROOT / "docs" / "change-log.json"

    def test_change_log_exists(self):
        """Change log must exist."""
        assert self.CL_PATH.exists(), "CFG-03: docs/change-log.json missing"

    def test_change_log_is_valid_json(self):
        """Change log must parse as JSON."""
        try:
            json.loads(self.CL_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            pytest.fail(f"CFG-03: change-log.json invalid: {e}")

    def test_change_log_has_meta(self):
        """Change log must have _meta section."""
        data = json.loads(self.CL_PATH.read_text(encoding="utf-8"))
        assert "_meta" in data, "CFG-03: change-log.json missing '_meta'"

    def test_change_log_has_items(self):
        """Change log must have items array."""
        data = json.loads(self.CL_PATH.read_text(encoding="utf-8"))
        assert "items" in data, "CFG-03: change-log.json missing 'items'"
        assert isinstance(data["items"], list), "CFG-03: 'items' must be an array"


class TestPyprojectIntegrity:
    """CFG-04: pyproject.toml must be parseable with required sections."""

    PYPROJECT = ROOT / "pyproject.toml"

    def test_pyproject_exists(self):
        """pyproject.toml must exist."""
        assert self.PYPROJECT.exists(), "CFG-04: pyproject.toml missing"

    def test_pyproject_parseable(self):
        """pyproject.toml must be parseable."""
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore[no-redef]
            except ImportError:
                pytest.skip("No TOML parser available (need Python 3.11+ or tomli)")

        data = tomllib.loads(self.PYPROJECT.read_text(encoding="utf-8"))
        assert "project" in data, "CFG-04: pyproject.toml missing [project] section"
        assert "name" in data["project"], "CFG-04: pyproject.toml missing project.name"


class TestPrecommitConfig:
    """CFG-05: .pre-commit-config.yaml must be valid YAML."""

    PC_PATH = ROOT / ".pre-commit-config.yaml"

    def test_precommit_config_exists(self):
        """Pre-commit config must exist."""
        assert self.PC_PATH.exists(), "CFG-05: .pre-commit-config.yaml missing"

    def test_precommit_config_is_valid_yaml(self):
        """Pre-commit config must parse as YAML."""
        data = yaml.safe_load(self.PC_PATH.read_text(encoding="utf-8"))
        assert isinstance(data, dict), "CFG-05: .pre-commit-config.yaml is not a mapping"
        assert "repos" in data, "CFG-05: .pre-commit-config.yaml missing 'repos'"


class TestManifestPathsExist:
    """CFG-06: Paths declared in dq-manifest.yaml must exist on disk."""

    RUNTIME_PATHS = frozenset({"inputs", "outputs", "cache", "inbox"})

    def test_core_paths_exist(self):
        """Core paths in manifest must exist."""
        data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
        core = data.get("core_paths", [])
        if isinstance(core, list):
            missing = [
                p for p in core if isinstance(p, str) and p not in self.RUNTIME_PATHS and not (ROOT / p).exists()
            ]
        else:
            missing = []
        assert not missing, "CFG-06: Core paths in manifest missing from disk:\n" + "\n".join(f"  {m}" for m in missing)

    def test_test_paths_exist(self):
        """Test paths in manifest must exist."""
        data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
        test_paths = data.get("test_paths", [])
        if isinstance(test_paths, list):
            missing = [p for p in test_paths if isinstance(p, str) and not (ROOT / p).exists()]
        else:
            missing = []
        assert not missing, "CFG-06: Test paths in manifest missing from disk:\n" + "\n".join(f"  {m}" for m in missing)
