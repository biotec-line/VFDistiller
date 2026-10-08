"""Automated security, dependency floor, and third-party license contract tests for VFDistiller."""

from __future__ import annotations

import re
import subprocess
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

    # Build optional dependencies
    assert "build = [" in pyproject_text, "pyproject.toml must define build optional dependencies"
    assert "pyinstaller>=6.10.0" in pyproject_text, "build dependencies must require pyinstaller>=6.10.0"
    assert "altgraph>=0.17.4" in pyproject_text, "build dependencies must require altgraph>=0.17.4"
    assert "packaging>=24.0" in pyproject_text, "build dependencies must require packaging>=24.0"

    # Pytest minversion hardening
    assert 'minversion = "9.1.1"' in pyproject_text, "pyproject.toml must specify pytest minversion 9.1.1"
    pytest_ini = (ROOT / "pytest.ini").read_text(encoding="utf-8")
    assert "minversion = 9.1.1" in pytest_ini, "pytest.ini must specify minversion = 9.1.1"

    # requirements-dev.txt presence and floors
    req_dev_file = ROOT / "requirements-dev.txt"
    assert req_dev_file.is_file(), "requirements-dev.txt must exist"
    req_dev_text = req_dev_file.read_text(encoding="utf-8")
    assert "pytest>=9.1.1" in req_dev_text
    assert "ruff>=0.9.0" in req_dev_text
    assert "pyinstaller>=6.10.0" in req_dev_text
    assert "altgraph>=0.17.4" in req_dev_text
    assert "packaging>=24.0" in req_dev_text

    # Check author contact email and project URLs
    assert "support@lukasgeiger.com" in pyproject_text, "pyproject.toml must use official support email"
    assert "Third-Party Licenses" in pyproject_text, "pyproject.toml must reference Third-Party Licenses URL"
    assert "Security Advisories" in pyproject_text, "pyproject.toml must reference Security Advisories URL"


def test_third_party_licenses_complete_and_accurate() -> None:
    """Verify THIRD_PARTY_LICENSES.txt comprehensively covers runtime, packaging, and test packages in 5-field schema."""
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
        assert f"Package: {pkg}" in content, f"Package entry for {pkg} missing from THIRD_PARTY_LICENSES.txt"
        assert spdx in content, f"SPDX identifier {spdx} for {pkg} missing from THIRD_PARTY_LICENSES.txt"

    # Ensure 5-field structured schema fields exist
    assert "Package:" in content, "Package: field missing in THIRD_PARTY_LICENSES.txt"
    assert "License:" in content, "License: field missing in THIRD_PARTY_LICENSES.txt"
    assert "URL:" in content, "URL: field missing in THIRD_PARTY_LICENSES.txt"
    assert "SPDX:" in content, "SPDX: field missing in THIRD_PARTY_LICENSES.txt"
    assert "Notice:" in content, "Notice: field missing in THIRD_PARTY_LICENSES.txt"

    # Audit recency confirmation
    assert "Stand: 2026-09-29" in content, "Historical audit anchor missing"
    assert "Stand: 2026-10-09" in content, "Current re-audit timestamp missing"


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

    # Test artifact patterns
    assert "pytest_out.txt" in content, "pytest_out.txt pattern missing in .gitignore"
    assert "pytest*.txt" in content, "pytest*.txt pattern missing in .gitignore"

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


def test_no_plaintext_secrets_or_credentials() -> None:
    """Verify absence of plaintext API tokens, private keys, or credentials across tracked non-test files."""
    tracked_output = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()

    secret_patterns = [
        re.compile(r"""(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36}"""),
        re.compile(r"""-----BEGIN (?:RSA|OPENSSH|DSA|EC|PGP)? PRIVATE KEY-----"""),
        re.compile(r"""(?i)(?:bearer|token|apikey|api_key)\s*[:=]\s*['"][A-Za-z0-9_\-\.]{16,}['"]"""),
    ]

    suspicious_findings: list[str] = []
    for rel_path in tracked_output:
        file_path = ROOT / rel_path
        if not file_path.is_file():
            continue
        if "test" in rel_path.lower() or file_path.suffix.lower() in [".png", ".ico", ".jpg", ".svg", ".pyd"]:
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            continue
        for line_num, line in enumerate(content.splitlines(), 1):
            for pat in secret_patterns:
                if pat.search(line):
                    suspicious_findings.append(f"{rel_path}:{line_num}: {line.strip()[:80]}")

    assert not suspicious_findings, "Potential plaintext secrets detected in tracked files:\n" + "\n".join(suspicious_findings)


def test_security_policy_bilingual_and_sla() -> None:
    """Verify SECURITY.md provides bilingual policy, security contact addresses, 48h SLA, and advisory URL."""
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

    # Direct private advisory URL
    assert "https://github.com/biotec-line/VFDistiller/security/advisories/new" in sec_text, (
        "SECURITY.md must direct reporters to /security/advisories/new"
    )

    # SLA commitment
    assert "48 Stunden" in sec_text, "SECURITY.md must define 48h SLA in German"
    assert "48 hours" in sec_text, "SECURITY.md must define 48h SLA in English"
    assert "5 Werktagen" in sec_text or "5 business days" in sec_text, "SECURITY.md must define triage window"
    assert "Local-First & Zero-Egress" in sec_text, "SECURITY.md must document Local-First commitment"
    assert "Non-Elevation" in sec_text, "SECURITY.md must document Non-Elevation guarantee"


def test_license_parity_across_manifests() -> None:
    """Verify license AGPL-3.0-or-later parity across all repository manifests."""
    pyproject_text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'license = "AGPL-3.0-or-later"' in pyproject_text

    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in license_text
    assert "Version 3" in license_text

    notice_text = (ROOT / "NOTICE").read_text(encoding="utf-8")
    assert "AGPL-3.0-or-later" in notice_text

    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "AGPL-3.0-or-later" in readme_text


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


def test_user_assets_zero_copyleft_and_linking() -> None:
    """Verify zero-copyleft guarantee for research data and dynamic linking for LGPL dependencies."""
    tpl_text = (ROOT / "THIRD_PARTY_LICENSES.txt").read_text(encoding="utf-8")
    assert "Zero-Copyleft Contagion for Genomic Research Data" in tpl_text
    assert "LGPL Dynamic Linking Compliance Statement" in tpl_text
    assert "pystray" in tpl_text

    tpl_md = (ROOT / "THIRD_PARTY_LICENSES.md").read_text(encoding="utf-8")
    assert "Zero-Copyleft" in tpl_md
    assert "LGPL-3.0-or-later" in tpl_md
