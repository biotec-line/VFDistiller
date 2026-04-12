# Security Policy — VFDistiller

Thank you for helping to keep VFDistiller safe. This document describes how
to report security vulnerabilities and which parts of the project are in
scope.

## Supported Versions

| Version | Supported                       |
| ------- | ------------------------------- |
| V17.x   | :white_check_mark: (current)    |
| < V17   | :x: (no further security fixes) |

Only the current major version is supplied with security updates. Older
versions are not patched; users are expected to upgrade to V17.x.

## How to Report a Vulnerability

**Do not open a public GitHub issue for security reports.**

Please use GitHub's **Private Vulnerability Reporting** feature:

1. Go to <https://github.com/biotec-line/VFDistiller/security/advisories>.
2. Click **Report a vulnerability**.
3. Provide a description, a minimal reproducer if possible, and the version
   / build you tested against.

Alternatively you can reach the maintainer via the contact methods listed
in the repository profile (GitHub: `@lukisch`).

You can expect:

- An acknowledgement within **7 days** of your report.
- A triage decision (accepted / duplicate / not in scope) within **14 days**.
- Coordinated disclosure: we aim to publish a fix and an advisory within
  **90 days**. If a fix cannot be delivered in that time window, we will
  communicate openly about it.

Please do **not** perform destructive testing against third-party services
or other people's data while researching VFDistiller. Use your own sample
files, a local SQLite database and your own API keys.

## Scope

VFDistiller is a desktop application. The following areas are **in scope**
for security reports:

- **VCF / gVCF / 23andMe / FASTA parsers** — memory-unsafe handling,
  path-traversal, ZIP-slip-style issues, resource-exhaustion through
  maliciously crafted input files.
- **SQLite storage** — SQL-injection, file-permission issues, data-loss
  bugs that can be triggered remotely (e.g. through a crafted import file).
- **Third-party API integrations** — credential leakage (AlphaGenome,
  NCBI, Ensembl VEP, gnomAD, MyVariant.info), unsanitised data sent over
  HTTPS, TLS downgrade, unsafe handling of API responses.
- **Cython hot-path modules** — buffer overflows, out-of-bounds reads,
  use-after-free.
- **Store-packaging / AppxManifest** — capability requests that exceed
  what the documentation claims; path-escalation out of the sandbox.
- **Update / background workers** — privilege escalation, arbitrary file
  writes outside the user-data directory.

The following areas are **out of scope**:

- **Clinical correctness or clinical validity of the displayed ClinVar
  (ClinSig) / VEP / AlphaGenome / gnomAD annotations.** These values are
  reproduced as-is from the underlying third-party research databases.
  Reports about „pathogenic" / „benign" / allele-frequency mis-classifications
  should be directed to the respective upstream sources
  (ClinVar/NCBI, Ensembl, Google DeepMind, gnomAD / Broad Institute).
- **Regulatory status.** VFDistiller is Research Use Only (see NOTICE).
  Issues such as „the tool should have been CE-IVD certified" are not
  security reports; please contact the maintainer directly for regulatory
  correspondence.
- **Third-party Python packages.** Vulnerabilities in `requests`,
  `aiohttp`, `Pillow`, `reportlab`, `openpyxl`, etc. should be reported to
  the respective upstream projects. We will, however, bump the pinned
  version in `requirements.txt` once an upstream fix is published.
- **User's own API-key leakage via their own misuse** (e.g. committing a
  configuration file to a public repository).

## Handling of User Data

VFDistiller processes data locally. See `PRIVACY_POLICY.md` for the
full privacy statement. No telemetry, analytics or crash reporting is
included. Outbound network traffic only occurs when the user explicitly
triggers an annotation or lookup feature.

## Coordinated Disclosure

Once a fix is available, we will:

1. Publish a GitHub Security Advisory with a CVE request where applicable.
2. Ship a patched release to the Microsoft Store and update the
   `CHANGELOG.md`.
3. Credit the reporter (unless anonymity was requested).

Thank you for responsible disclosure.
