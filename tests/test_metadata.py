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
