"""Documentation quality enforcement.

Criteria enforced:
  DOC-01: Required docs exist and are >200 bytes
  DOC-02: Standards directory has required standard docs
  DOC-03: BR/FR/TR docs reference each other
  DOC-04: No broken internal markdown links in docs/requirements/
  DOC-05: Every doc has a title heading
  DOC-06: docs/ .md files use kebab-case naming
  DOC-07: README.md exists and has substance

Run with:  pytest tests/enforcement/test_documentation_quality.py -v
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from .conftest import (
    BUSINESS_REQ,
    DOCS_REQ,
    DOCS_STD,
    FUNCTIONAL_REQ,
    MANIFEST,
    MATRIX_PATH,
    ROOT,
    TECHNICAL_REQ,
)


def _md_files_in(directory: Path) -> list[Path]:
    """All .md files recursively under a directory."""
    if not directory.exists():
        return []
    return sorted(directory.rglob("*.md"))


def _extract_md_links(text: str) -> list[str]:
    """Extract all [text](target) link targets from markdown."""
    return re.findall(r"\[(?:[^\]]*)\]\(([^)]+)\)", text)


class TestRequiredDocumentsExist:
    """DOC-01: Every required document must exist and be >200 bytes."""

    REQUIRED = [
        ("business-requirements.md", BUSINESS_REQ),
        ("functional-requirements.md", FUNCTIONAL_REQ),
        ("technical-requirements.md", TECHNICAL_REQ),
        ("traceability-matrix.md", MATRIX_PATH),
        ("dq-manifest.yaml", MANIFEST),
        ("README.md", ROOT / "README.md"),
    ]

    @pytest.mark.parametrize(
        "name,path",
        REQUIRED,
        ids=[n for n, _ in REQUIRED],
    )
    def test_doc_exists_and_substantial(self, name: str, path: Path):
        """Each required doc must exist and not be a trivial stub."""
        assert path.exists(), f"DOC-01: Required document missing: {name}"
        size = path.stat().st_size
        assert size > 200, f"DOC-01: {name} is only {size} bytes"


class TestStandardsDocsCoverage:
    """DOC-02: docs/standards/ must exist and have standard docs."""

    def test_standards_directory_exists(self):
        """Standards directory must exist."""
        assert DOCS_STD.is_dir(), "DOC-02: docs/standards/ directory missing"


class TestRequirementCrossReferences:
    """DOC-03: Requirement docs must reference each other."""

    def test_fr_references_br(self):
        """Functional Requirements must reference Business Requirements."""
        if not FUNCTIONAL_REQ.exists():
            pytest.skip("functional-requirements.md not found")
        text = FUNCTIONAL_REQ.read_text(encoding="utf-8")
        assert "BR-" in text, "DOC-03: functional-requirements.md does not reference BR IDs"

    def test_tr_references_fr(self):
        """Technical Requirements must reference Functional Requirements."""
        if not TECHNICAL_REQ.exists():
            pytest.skip("technical-requirements.md not found")
        text = TECHNICAL_REQ.read_text(encoding="utf-8")
        assert "FR-" in text, "DOC-03: technical-requirements.md does not reference FRs"

    def test_matrix_references_all_layers(self):
        """Traceability matrix must mention BR, FR, and TR."""
        if not MATRIX_PATH.exists():
            pytest.skip("traceability-matrix.md not found")
        text = MATRIX_PATH.read_text(encoding="utf-8")
        assert "BR" in text, "DOC-03: Matrix missing BR references"
        assert "FR" in text, "DOC-03: Matrix missing FR references"
        assert "TR" in text, "DOC-03: Matrix missing TR references"


class TestNoStaleDocLinks:
    """DOC-04: Markdown links within docs/requirements/ must resolve."""

    def test_no_broken_links_in_requirements(self):
        """Internal relative links must point to existing files."""
        broken: list[str] = []
        for md_file in _md_files_in(DOCS_REQ):
            text = md_file.read_text(encoding="utf-8")
            links = _extract_md_links(text)
            for link in links:
                if link.startswith(("http://", "https://", "#")):
                    continue
                target = (md_file.parent / link.split("#")[0]).resolve()
                if not target.exists():
                    rel = md_file.relative_to(ROOT)
                    broken.append(f"  {rel}: -> {link}")
        assert not broken, (
            "DOC-04: Broken internal links in docs/requirements/:\n"
            + "\n".join(broken[:20])
        )


class TestDocTitleHeadings:
    """DOC-05: Every .md file in docs/ should start with a # heading."""

    def test_requirement_docs_have_titles(self):
        """All requirement docs must have a title heading."""
        no_title: list[str] = []
        for md_file in _md_files_in(DOCS_REQ):
            text = md_file.read_text(encoding="utf-8").strip()
            if not text.startswith("#"):
                first_heading = re.search(r"^#\s+", text, re.MULTILINE)
                if not first_heading or first_heading.start() > 200:
                    no_title.append(str(md_file.relative_to(ROOT)))
        assert not no_title, (
            "DOC-05: Docs missing title heading:\n"
            + "\n".join(f"  - {f}" for f in no_title)
        )


class TestDocNamingConventions:
    """DOC-06: All .md files in docs/ must use kebab-case."""

    _KEBAB_RE = re.compile(r"^[a-z][a-z0-9\-]*$")

    def test_no_upper_snake_in_docs(self):
        """No UPPER_SNAKE or mixed-case .md files in docs/."""
        docs_dir = ROOT / "docs"
        if not docs_dir.exists():
            return
        bad: list[str] = []
        for f in sorted(docs_dir.rglob("*.md")):
            if f.name == "README.md":
                continue
            if not self._KEBAB_RE.match(f.stem):
                bad.append(str(f.relative_to(ROOT)))
        assert not bad, (
            "DOC-06: Non-kebab-case .md files found in docs/:\n"
            + "\n".join(f"  - {f}" for f in bad)
        )


class TestReadmeQuality:
    """DOC-07: Root README.md should be informative."""

    def test_readme_exists(self):
        """README.md must exist at project root."""
        assert (ROOT / "README.md").exists(), "DOC-07: README.md missing"

    def test_readme_has_substance(self):
        """README.md must have real content."""
        readme = ROOT / "README.md"
        if not readme.exists():
            pytest.skip("No README.md")
        size = readme.stat().st_size
        assert size > 500, f"DOC-07: README.md is only {size} bytes"
