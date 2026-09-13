"""Automated security, dependency floor, and third-party license contract tests for VFDistiller."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dependency_vulnerability_floors() -> None:
    """Verify requirements.txt and pyproject.toml enforce patched dependency floors against CVEs."""
    req_file = ROOT / "requirements.txt"
    assert req_file.is_file(), "requirements.txt must exist"
    req_text = req_file.read_text(encoding="utf-8")

    assert re.search(r"^requests\s*>=\s*2\.32\.3", req_text, re.MULTILINE), (
        "requirements.txt must enforce requests>=2.32.3 floor (CVE-2024-35195)"
    )
    assert re.search(r"^aiohttp\s*>=\s*3\.10\.11", req_text, re.MULTILINE), (
        "requirements.txt must enforce aiohttp>=3.10.11 floor"
    )
    assert re.search(r"^Pillow\s*>=\s*10\.3\.0", req_text, re.MULTILINE), (
        "requirements.txt must enforce Pillow>=10.3.0 floor"
    )
    assert re.search(r"^openpyxl\s*>=\s*3\.1\.3", req_text, re.MULTILINE), (
        "requirements.txt must enforce openpyxl>=3.1.3 floor (CVE-2024-24576)"
    )

    pyproject_file = ROOT / "pyproject.toml"
    assert pyproject_file.is_file(), "pyproject.toml must exist"
    pyproject_text = pyproject_file.read_text(encoding="utf-8")

    # PEP 621 dependencies section
    assert "dependencies = [" in pyproject_text, "pyproject.toml must define project.dependencies"
    assert "requests>=2.32.3" in pyproject_text, "pyproject.toml must specify requests>=2.32.3"
    assert "aiohttp>=3.10.11" in pyproject_text, "pyproject.toml must specify aiohttp>=3.10.11"
    assert "Pillow>=10.3.0" in pyproject_text, "pyproject.toml must specify Pillow>=10.3.0"

    # Dev optional dependencies floor (pytest >= 9.1.1 protects against CVE-2025-7117 / GHSA-6w46-j5rx-g56g)
    assert "[project.optional-dependencies]" in pyproject_text, "pyproject.toml must define optional-dependencies"
    assert "pytest>=9.1.1" in pyproject_text, "pyproject.toml dev dependencies must require pytest>=9.1.1"
    assert "ruff>=0.9.0" in pyproject_text, "pyproject.toml dev dependencies must require ruff>=0.9.0"
    assert "openpyxl>=3.1.3" in pyproject_text, "pyproject.toml export dependencies must require openpyxl>=3.1.3"

    # Check author contact email and project URLs
    assert "support@lukasgeiger.com" in pyproject_text, "pyproject.toml must use official support email"
    assert "Third-Party Licenses" in pyproject_text, "pyproject.toml must reference Third-Party Licenses URL"


def test_third_party_licenses_complete_and_accurate() -> None:
    """Verify THIRD_PARTY_LICENSES.txt comprehensively covers runtime, packaging, and test packages."""
    license_file = ROOT / "THIRD_PARTY_LICENSES.txt"
    assert license_file.is_file(), "THIRD_PARTY_LICENSES.txt must exist"
    content = license_file.read_text(encoding="utf-8")

    required_packages = [
        ("requests", "Apache-2.0"),
        ("psutil", "BSD-3-Clause"),
        ("Pillow", "HPND"),
        ("intervaltree", "Apache-2.0"),
        ("sortedcontainers", "Apache-2.0"),
        ("ttkbootstrap", "MIT"),
        ("pystray", "LGPL-3.0-or-later"),
        ("aiohttp", "Apache-2.0"),
        ("scipy", "BSD-3-Clause"),
        ("openpyxl", "MIT"),
        ("et_xmlfile", "MIT"),
        ("reportlab", "BSD-3-Clause"),
        ("numpy", "BSD-3-Clause"),
        ("biopython", "BSD-3-Clause"),
        ("pyfaidx", "BSD-3-Clause"),
        ("pytest", "MIT"),
        ("pluggy", "MIT"),
        ("iniconfig", "MIT"),
        ("ruff", "MIT OR Apache-2.0"),
        ("packaging", "Apache-2.0 OR BSD-2-Clause"),
        ("PyInstaller", "GPL-2.0-or-later WITH Bootloader-exception"),
        ("altgraph", "MIT"),
    ]

    for pkg, spdx in required_packages:
        assert pkg in content, f"Package {pkg} missing from THIRD_PARTY_LICENSES.txt"
        assert spdx in content, f"SPDX identifier {spdx} for {pkg} missing from THIRD_PARTY_LICENSES.txt"

    # Ensure structured schema fields exist
    assert "License:" in content, "License: field missing in THIRD_PARTY_LICENSES.txt"
    assert "URL:" in content, "URL: field missing in THIRD_PARTY_LICENSES.txt"
    assert "SPDX:" in content, "SPDX: field missing in THIRD_PARTY_LICENSES.txt"
    assert "Notice:" in content, "Notice: field missing in THIRD_PARTY_LICENSES.txt"


def test_gitignore_security_and_multi_host_hardening() -> None:
    """Verify .gitignore blocks private secrets, certificates, and multi-host conflict files."""
    gitignore_file = ROOT / ".gitignore"
    assert gitignore_file.is_file(), ".gitignore must exist"
    content = gitignore_file.read_text(encoding="utf-8")

    # Secrets and certificate protection
    for pat in ["credentials.json", "secrets.*", "*.pfx", "*.p12", "*.cer", "*.crt", "*.pem", "*.key", "keyring/"]:
        assert pat in content, f"Secret pattern {pat} missing in .gitignore"

    # Multi-host sync hardening
    for host_pat in ["*-WORKSTATION-LG*", "*-ASUS-GEI*", "*.sync-conflict-*", "*.conflict", "*-CONFLIT-*"]:
        assert host_pat in content, f"Sync conflict pattern {host_pat} missing in .gitignore"

    # Multi-agent lock system fail-closed patterns
    for lock_pat in ["LOCK", "LOCK.*", "*.lock", "LOCK*.txt", "LOCK.permissions.json"]:
        assert lock_pat in content, f"Lock pattern {lock_pat} missing in .gitignore"

    # Web companion / Node cache patterns
    assert "node_modules/" in content, "node_modules/ pattern missing in .gitignore"
    assert ".nyc_output/" in content, ".nyc_output/ pattern missing in .gitignore"


def test_no_hardcoded_user_paths_in_python_code() -> None:
    """Verify no hardcoded personal user profile paths exist in active Python source and tests."""
    disallowed_regex = re.compile(r"""(?i)C:[/\\]Users[/\\](?:lukas|admin|administrator)[/\\]""", re.VERBOSE)

    python_files = [
        p for p in ROOT.rglob("*.py")
        if not any(part in p.parts for part in [".git", ".pytest_cache", ".ruff_cache", "venv", ".venv", "build", "dist"])
    ]
    assert len(python_files) >= 15, f"Expected at least 15 Python files to scan, found {len(python_files)}"

    violating_lines = []
    for py_file in python_files:
        try:
            text = py_file.read_text(encoding="utf-8")
        except Exception:
            continue
        for idx, line in enumerate(text.splitlines(), 1):
            if disallowed_regex.search(line):
                violating_lines.append(f"{py_file.name}:{idx}: {line.strip()}")

    assert not violating_lines, "Found hardcoded user paths in Python code:\n" + "\n".join(violating_lines)


def test_security_policy_bilingual_and_sla() -> None:
    """Verify SECURITY.md provides bilingual policy, security contact addresses, and 48h SLA."""
    sec_file = ROOT / "SECURITY.md"
    assert sec_file.is_file(), "SECURITY.md must exist"
    sec_text = sec_file.read_text(encoding="utf-8")

    assert "## Deutsch" in sec_text, "SECURITY.md must contain German section"
    assert "## English" in sec_text, "SECURITY.md must contain English section"

    # Contact addresses
    assert "security@biotec-line.org" in sec_text, "SECURITY.md must list security@biotec-line.org"
    assert "security@open-bricks.org" in sec_text, "SECURITY.md must list security@open-bricks.org"
    assert "support@lukasgeiger.com" in sec_text, "SECURITY.md must list support@lukasgeiger.com"
    assert "lukas@open-bricks.org" in sec_text, "SECURITY.md must list lukas@open-bricks.org"

    # SLA commitment
    assert "48 Stunden" in sec_text, "SECURITY.md must define 48h SLA in German"
    assert "48 hours" in sec_text, "SECURITY.md must define 48h SLA in English"
    assert "5 Werktagen" in sec_text or "5 business days" in sec_text, "SECURITY.md must define triage window"
    assert "Local-First & Zero-Egress" in sec_text, "SECURITY.md must document Local-First commitment"
    assert "Non-Elevation" in sec_text, "SECURITY.md must document Non-Elevation guarantee"


def test_local_first_and_offline_invariants() -> None:
    """Verify absence of unapproved telemetry, analytics, and remote trackers in Python sources."""
    disallowed_patterns = [
        re.compile(r"google-analytics\.com", re.IGNORECASE),
        re.compile(r"mixpanel\.com", re.IGNORECASE),
        re.compile(r"segment\.io", re.IGNORECASE),
        re.compile(r"sentry\.io", re.IGNORECASE),
    ]

    source_files = [
        ROOT / "Variant_Fusion_pro_V17.py",
        ROOT / "lightdb_index_worker.py",
        ROOT / "translator.py",
    ]

    for src_file in source_files:
        if not src_file.is_file():
            continue
        text = src_file.read_text(encoding="utf-8")
        for pat in disallowed_patterns:
            assert not pat.search(text), f"Disallowed telemetry pattern {pat.pattern} found in {src_file.name}"
