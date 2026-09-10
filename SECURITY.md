# Security Policy — VFDistiller

[English](#english) | [Deutsch](#deutsch)

---

<a name="english"></a>
## English

### Supported Versions

| Version | Supported | Security Maintenance |
| ------- | --------- | -------------------- |
| 17.x / V17 | :white_check_mark: Yes | Active security support (current release: 17.0.1) |
| < 17.0  | :x: No | End of life; upgrade required |

Only the current major release series (`17.x`) receives active security patches. Users are strongly advised to run the latest available release.

### Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Use one of the following secure channels:

1. **GitHub Private Vulnerability Reporting (Preferred):**
   Navigate to [Security Advisories](https://github.com/biotec-line/VFDistiller/security/advisories) and click **"Report a vulnerability"**.
2. **Security Email:**
   - Primary: `security@open-bricks.org`
   - Organization: `security@biotec-line.org`
   - Maintainer: `lukas@open-bricks.org`
   - GitHub profile: [`@lukisch`](https://github.com/lukisch)

### Response Commitments & SLAs

- **Initial Response:** Within **48 hours** with an acknowledgment and issue reference.
- **Triage Assessment:** Within **5 business days** confirming validity, severity assessment, and reproduction steps.
- **Remediation & Advisory:** Coordinated release typically within **30–90 days**, depending on vulnerability complexity.

### Scope

The following areas are **in scope** for security reports:
- **Genomic parsers & file ingestion:** Memory corruption, path traversal, Zip-Slip, or unconstrained resource allocation in VCF, gVCF, 23andMe, and FASTA processing.
- **Local SQLite engine:** SQL injection vulnerabilities, unsafe deserialization, or local privilege/permission escalation.
- **External API connectors:** AlphaGenome, NCBI E-Utilities, Ensembl VEP, gnomAD, and MyVariant.info credential management, TLS enforcement, and secure deserialization.
- **Cython acceleration modules:** Buffer bounds checking, arithmetic overflow, and memory-safety regressions in `cython_hotpath`.
- **Packaging & Desktop Sandbox:** AppxManifest capability boundaries, MSIX isolation, and sandbox escape vectors.

The following areas are **out of scope**:
- **Biological / clinical annotations:** Discrepancies in third-party clinical significance classifications (ClinVar, gnomAD, Ensembl).
- **Regulatory claims:** VFDistiller is licensed and designated for **Research Use Only (RUO)**.
- **Upstream dependency issues:** Vulnerabilities in third-party libraries (`requests`, `Pillow`, `aiohttp`) without actionable impact on VFDistiller (though dependencies will be updated upon upstream release).
- **Self-inflicted credential leaks:** Committing private API keys into personal repositories or fork branches.

---

<a name="deutsch"></a>
## Deutsch

### Unterstützte Versionen

| Version | Unterstützt | Sicherheitswartung |
| ------- | ----------- | ------------------ |
| 17.x / V17 | :white_check_mark: Ja | Aktiver Sicherheitssupport (aktuelle Version: 17.0.1) |
| < 17.0  | :x: Nein | End of Life; Aktualisierung erforderlich |

### Sicherheitslücke melden

**Bitte melden Sie Sicherheitslücken niemals über öffentliche GitHub Issues.**

Nutzen Sie stattdessen:

1. **Private Vulnerability Reporting:**
   Über das GitHub-Menü [Security Advisories](https://github.com/biotec-line/VFDistiller/security/advisories) auf **"Report a vulnerability"** klicken.
2. **Sicherheits-E-Mail:**
   - Primär: `security@open-bricks.org`
   - Organisation: `security@biotec-line.org`
   - Maintainer: `lukas@open-bricks.org`
   - GitHub: [`@lukisch`](https://github.com/lukisch)

### Service-Level-Agreements (SLA)

- **Erstrückmeldung:** Innerhalb von **48 Stunden**.
- **Triage & Einstufung:** Verbindliche Einschätzung innerhalb von **5 Werktagen**.
- **Behebung:** Koordiniertes Release und Security Advisory in der Regel innerhalb von **30 bis 90 Tagen**.

### Geltungsbereich & Forschungshinweis

VFDistiller arbeitet nach dem **Local-First-Prinzip**. Es werden keine Telemetrie-, Analyse- oder Nutzungsdaten übertragen. Netzwerkanfragen erfolgen ausschließlich nach expliziter Nutzeraktion zur Konsultation wissenschaftlicher APIs über gesicherte HTTPS-Verbindungen. VFDistiller ist ausschließlich für Forschungszwecke bestimmt (**Research Use Only**).
