"""Contract tests for repository metadata, configuration, and CI workflows.

These tests ensure repository-level standards, PEP 621 compliance,
security SLAs, and multi-agent hygiene invariants remain intact.
"""
from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_pyproject_toml_structure() -> None:
    """Verify pyproject.toml conforms to PEP 621 standards and ecosystem invariants."""
    pyproject_path = REPO_ROOT / "pyproject.toml"
    assert pyproject_path.exists(), "pyproject.toml must exist in repo root"

    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    # Project metadata
    project = data.get("project", {})
    assert project.get("name") == "vfdistiller"
    assert project.get("version") == "17.0.1"
    assert project.get("requires-python") == ">=3.10"
    assert project.get("license") == "AGPL-3.0-or-later"

    # URLs
    urls = project.get("urls", {})
    assert "Homepage" in urls
    assert "Repository" in urls
    assert "Documentation" in urls
    assert "Issues" in urls
    assert "Changelog" in urls
    assert "Security" in urls
    assert "Parent Organization" in urls
    assert "Umbrella Ecosystem" in urls

    assert urls["Repository"] == "https://github.com/biotec-line/VFDistiller"
    assert urls["Parent Organization"] == "https://github.com/biotec-line"
    assert urls["Umbrella Ecosystem"] == "https://github.com/open-bricks"

    # Core dependencies
    dependencies = project.get("dependencies", [])
    assert any(dep.startswith("requests") for dep in dependencies)
    assert any(dep.startswith("psutil") for dep in dependencies)
    assert any(dep.startswith("Pillow") for dep in dependencies)
    assert any(dep.startswith("intervaltree") for dep in dependencies)
    assert any(dep.startswith("ttkbootstrap") for dep in dependencies)

    # Tool configurations
    tools = data.get("tool", {})
    assert "pytest" in tools
    assert "ini_options" in tools["pytest"]
    assert "ruff" in tools
    assert "Variant_Fusion_pro_V17.py" in tools["ruff"].get("exclude", [])


def test_gitignore_hygiene_patterns() -> None:
    """Verify .gitignore contains necessary multi-host conflict and multi-agent lock patterns."""
    gitignore_path = REPO_ROOT / ".gitignore"
    assert gitignore_path.exists(), ".gitignore must exist in repo root"

    content = gitignore_path.read_text(encoding="utf-8")

    # Multi-host sync conflicts
    assert "*-conflict-*" in content
    assert "*.sync-conflict-*" in content
    assert "*-ASUS-GEI.*" in content
    assert "*-WORKSTATION-LG.*" in content

    # Multi-agent locks
    assert "LOCK" in content
    assert "LOCK.*" in content
    assert "*.lock" in content
    assert "LOCK*.txt" in content
    assert "LOCK.permissions.json" in content

    # Test & packaging caches
    assert ".ruff_cache/" in content
    assert "wheelhouse/" in content
    assert ".wheel-smoke/" in content
    assert "__pycache__/" in content


def test_security_policy_slas() -> None:
    """Verify SECURITY.md includes standard 48h SLA, 5-day triage, and direct security contacts."""
    security_path = REPO_ROOT / "SECURITY.md"
    assert security_path.exists(), "SECURITY.md must exist in repo root"

    content = security_path.read_text(encoding="utf-8")

    assert "48 hours" in content or "48 Stunden" in content
    assert "5 business days" in content or "5 Werktagen" in content
    assert "security@open-bricks.org" in content
    assert "security@biotec-line.org" in content
    assert "lukas@open-bricks.org" in content
    assert "@lukisch" in content
    assert "#english" in content
    assert "#deutsch" in content
    assert "17.0.1" in content


def test_llms_txt_integrity() -> None:
    """Verify llms.txt exists, contains valid documentation and links to project architecture."""
    llms_path = REPO_ROOT / "llms.txt"
    assert llms_path.exists(), "llms.txt must exist in repo root"

    content = llms_path.read_text(encoding="utf-8")
    assert "VFDistiller" in content
    assert "https://github.com/biotec-line/VFDistiller" in content
    assert "biotec-line" in content
    assert "open-bricks" in content


def test_changelog_release_section() -> None:
    """Verify CHANGELOG.md documents version 17.0.1 and follows Keep a Changelog formatting."""
    changelog_path = REPO_ROOT / "CHANGELOG.md"
    assert changelog_path.exists(), "CHANGELOG.md must exist in repo root"

    content = changelog_path.read_text(encoding="utf-8")
    assert "## [17.0.1]" in content
    assert "2026-09-10" in content


def test_ci_workflows_concurrency_and_matrix() -> None:
    """Verify CI workflows include concurrency cancellation and testing matrices."""
    workflows_dir = REPO_ROOT / ".github" / "workflows"
    assert workflows_dir.exists()

    tests_wf = workflows_dir / "tests.yml"
    assert tests_wf.exists(), "tests.yml workflow must exist"
    tests_content = tests_wf.read_text(encoding="utf-8")
    assert "cancel-in-progress: true" in tests_content
    assert "python-version" in tests_content
    assert "3.10" in tests_content
    assert "3.13" in tests_content
    assert "compileall" in tests_content
    assert "ruff check ." in tests_content

    smoke_wf = workflows_dir / "source-platform-smoke.yml"
    assert smoke_wf.exists(), "source-platform-smoke.yml must exist"
    smoke_content = smoke_wf.read_text(encoding="utf-8")
    assert "cancel-in-progress: true" in smoke_content


def test_bilingual_readme_18_point_navigation_parity() -> None:
    """Verify that README.md and README.de.md both define the 18-point navigation with reciprocal anchors."""
    readme_en_path = REPO_ROOT / "README.md"
    readme_de_path = REPO_ROOT / "README.de.md"
    assert readme_en_path.exists(), "README.md must exist"
    assert readme_de_path.exists(), "README.de.md must exist"

    en_content = readme_en_path.read_text(encoding="utf-8")
    de_content = readme_de_path.read_text(encoding="utf-8")

    for point in range(1, 19):
        assert f"(#{point}-" in en_content, f"README.md missing navigation link for section #{point}"
        assert f"(#{point}-" in de_content, f"README.de.md missing navigation link for section #{point}"
        assert f'id="{point}-' in en_content, f"README.md missing anchor id for section #{point}"
        assert f'id="{point}-' in de_content, f"README.de.md missing anchor id for section #{point}"


def test_target_personas_and_high_intent_queries() -> None:
    """Verify target personas [PERSONA-01] through [PERSONA-04] and high-intent SEO queries."""
    readme_en = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (REPO_ROOT / "README.de.md").read_text(encoding="utf-8")
    marketing_log = (REPO_ROOT / "MARKETING-LOG.txt").read_text(encoding="utf-8")
    llms_txt = (REPO_ROOT / "llms.txt").read_text(encoding="utf-8")

    personas = ["[PERSONA-01]", "[PERSONA-02]", "[PERSONA-03]", "[PERSONA-04]"]
    for p in personas:
        assert p in readme_en, f"{p} missing from README.md"
        assert p in readme_de, f"{p} missing from README.de.md"
        assert p in marketing_log, f"{p} missing from MARKETING-LOG.txt"
        assert p in llms_txt, f"{p} missing from llms.txt"


def test_comparative_matrix_and_governance_invariants() -> None:
    """Verify 10-dimension comparative matrix and invariants INV-LOCAL-01 through INV-SLA-10."""
    readme_en = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (REPO_ROOT / "README.de.md").read_text(encoding="utf-8")
    licenses_md = (REPO_ROOT / "THIRD_PARTY_LICENSES.md").read_text(encoding="utf-8")
    marketing_log = (REPO_ROOT / "MARKETING-LOG.txt").read_text(encoding="utf-8")

    invariants = [
        "INV-LOCAL-01", "INV-PRIVACY-02", "INV-INSPECT-03", "INV-CONVERT-04",
        "INV-OFFLINE-05", "INV-ACCEL-06", "INV-EXPORT-07", "INV-UNPRIV-08",
        "INV-COMPLY-09", "INV-SLA-10",
    ]

    for inv in invariants:
        assert inv in readme_en, f"{inv} missing from README.md"
        assert inv in readme_de, f"{inv} missing from README.de.md"
        assert inv in licenses_md, f"{inv} missing from THIRD_PARTY_LICENSES.md"
        assert inv in marketing_log, f"{inv} missing from MARKETING-LOG.txt"

    for alt in ["bcftools", "BaseSpace", "IGV", "VEP"]:
        assert alt in readme_en, f"Alternative {alt} missing from README.md matrix"
        assert alt in readme_de, f"Alternative {alt} missing from README.de.md matrix"


def test_third_party_licenses_audit_markdown() -> None:
    """Verify THIRD_PARTY_LICENSES.md includes SPDX audit, LGPL statement, and Zero-Copyleft guarantee."""
    lic_md_path = REPO_ROOT / "THIRD_PARTY_LICENSES.md"
    assert lic_md_path.exists(), "THIRD_PARTY_LICENSES.md must exist in repo root"

    content = lic_md_path.read_text(encoding="utf-8")
    assert "AGPL-3.0-or-later" in content
    assert "LGPL-3.0-or-later" in content
    assert "Apache-2.0" in content
    assert "MIT" in content
    assert "BSD-3-Clause" in content
    assert "HPND" in content
    assert "pystray" in content
    assert "RunAsInvoker" in content
    assert "Zero-Copyleft" in content
    assert "Research Use Only" in content


def test_marketing_log_audit_record() -> None:
    """Verify MARKETING-LOG.txt documents Pfad A and Pfad B runs."""
    m_log = REPO_ROOT / "MARKETING-LOG.txt"
    assert m_log.exists(), "MARKETING-LOG.txt must exist"

    content = m_log.read_text(encoding="utf-8")
    assert "2026-09-10" in content
    assert "Pfad A" in content
    assert "2026-09-16" in content
    assert "Pfad B" in content
    assert "biotec-line/VFDistiller" in content


def test_pyproject_marketing_and_license_urls() -> None:
    """Verify pyproject.toml defines Marketing Log and Third-Party Licenses URLs."""
    pyproject_path = REPO_ROOT / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    urls = data.get("project", {}).get("urls", {})

    assert "Marketing Log" in urls
    assert "Third-Party Licenses" in urls
    assert "LLM Ready" in urls
    assert urls["Marketing Log"] == "https://github.com/biotec-line/VFDistiller/blob/main/MARKETING-LOG.txt"
    assert urls["Third-Party Licenses"] == "https://github.com/biotec-line/VFDistiller/blob/main/THIRD_PARTY_LICENSES.md"
