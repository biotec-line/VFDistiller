# Security Policy — VFDistiller

[English](#english) | [Deutsch](#deutsch)

---

<a name="english"></a>
## English

### Supported Versions

| Version | Supported | Security Maintenance |
| ------- | --------- | -------------------- |
| 17.x / V17 | :white_check_mark: Yes | Active security support (current release: 17.0.2) |
| < 17.0  | :x: No | End of life; upgrade required |

Only the current major release series (`17.x`) receives active security patches. Users are strongly advised to run the latest available release.

### Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Use one of the following secure channels:

1. **GitHub Private Vulnerability Reporting (Preferred):**
   Navigate to [Security Advisories](https://github.com/biotec-line/VFDistiller/security/advisories/new) and submit a private report.
2. **Security & Support Email:**
   - Organization: `security@biotec-line.org`
   - Ecosystem: `security@open-bricks.org`
   - Official Support: `support@lukasgeiger.com`
   - Maintainer: `lukas@open-bricks.org`
   - GitHub profile: [`@lukisch`](https://github.com/lukisch)

### Response Commitments & SLAs

- **Initial Response:** Within **48 hours** with an acknowledgment and issue reference.
- **Triage Assessment:** Within **5 business days** confirming validity, severity assessment, and reproduction steps.
- **Remediation & Advisory:** Coordinated release typically within **30–90 days**, depending on vulnerability complexity.

### Security & Architectural Invariants

- **Local processing and online annotation:** File processing and SQLite storage are local. Enabled annotation services receive variant identifiers, positions and reference/alternate alleles. Several sources are enabled by default; an analysis can issue requests automatically according to the API settings. Reference downloads also use the network. See [Privacy Policy](PRIVACY_POLICY.md).
- **Non-Elevation / Least Privilege:** VFDistiller operates entirely in unprivileged user-space and never requires or requests administrative (root or UAC) privilege elevation.

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
| 17.x / V17 | :white_check_mark: Ja | Aktiver Sicherheitssupport (aktuelle Version: 17.0.2) |
| < 17.0  | :x: Nein | End of Life; Aktualisierung erforderlich |

### Sicherheitslücke melden

**Bitte melden Sie Sicherheitslücken niemals über öffentliche GitHub Issues.**

Nutzen Sie stattdessen:

1. **Private Vulnerability Reporting (Bevorzugt):**
   Über das GitHub-Menü [Security Advisories](https://github.com/biotec-line/VFDistiller/security/advisories/new) eine vertrauliche Meldung einreichen.
2. **Sicherheits- & Support-E-Mail:**
   - Organisation: `security@biotec-line.org`
   - Ökosystem: `security@open-bricks.org`
   - Offizieller Support: `support@lukasgeiger.com`
   - Maintainer: `lukas@open-bricks.org`
   - GitHub: [`@lukisch`](https://github.com/lukisch)

### Service-Level-Agreements (SLA)

- **Erstrückmeldung:** Innerhalb von **48 Stunden** mit Empfangsbestätigung und Vorgangsnummer.
- **Triage & Einstufung:** Verbindliche Einschätzung innerhalb von **5 Werktagen**.
- **Behebung:** Koordiniertes Release und Security Advisory in der Regel innerhalb von **30 bis 90 Tagen**.

### Sicherheits- und Architektur-Invarianten

- **Lokale Verarbeitung und Online-Annotation:** Dateiverarbeitung und SQLite-Speicherung erfolgen lokal. Aktivierte Annotationsdienste erhalten Variantenkennungen, Positionen und Referenz-/Alternativallele. Mehrere Quellen sind standardmäßig aktiviert; eine Analyse kann entsprechend den API-Einstellungen automatisch Anfragen senden. Referenzdownloads verwenden ebenfalls das Netzwerk. Siehe [Datenschutzerklärung](PRIVACY_POLICY.md).
- **Non-Elevation / Minimale Rechtevergabe:** Die Anwendung läuft vollständig im unprivilegierten Benutzerkontext und erfordert oder beansprucht zu keinem Zeitpunkt Administrator- oder Root-Rechte (keine UAC-Elevation erforderlich).
