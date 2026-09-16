# Third-Party Licenses & Transparency Notice

> **Project:** `biotec-line/VFDistiller` (Variant Fusion Distiller — Local-First VCF & Genetic Variant Annotation)<br>
> **Audited:** 2026-09-16<br>
> **Repository License:** [AGPL-3.0-or-later](LICENSE)<br>
> **Architecture & Privacy:** 100% Local-First, Zero-Egress by default, Unprivileged User-Mode (`RunAsInvoker`)<br>
> **Intended Use:** Research Use Only (RUO) — Bioinformatics tool. Not an IVD medical device under IVDR (EU) 2017/746.

---

## Executive Summary & Compliance Assurance

`VFDistiller` (Variant Fusion Distiller) is a local-first bioinformatics desktop application designed for processing, converting, filtering, and annotating research-grade genetic variant data (VCF, gVCF, 23andMe raw text, and FASTA). The software is licensed under the [GNU Affero General Public License Version 3 or later](LICENSE) (AGPL-3.0-or-later).

The core runtime operates on an uncompromising local-first privacy model: all genomic sequencing files, converted VCFs, genome references, SQLite database caches (gnomAD LightDB), and local configuration remain strictly on the user's local workstation. External network calls to scientific APIs (such as Ensembl VEP or MyVariant.info) are strictly user-initiated, transmitting only public locus coordinates over encrypted HTTPS connections—never patient or sample identities.

All third-party libraries and runtime components utilized by `VFDistiller` are distributed under widely recognized, OSI-approved open-source licenses (MIT, BSD-3-Clause, Apache-2.0, HPND, and LGPL-3.0-or-later):

- **Zero-Copyleft Contagion for Genomic Data:** The user's input files (VCF, gVCF, 23andMe, FASTA), processed variant tables, exported annotated VCFs, and generated reports (CSV, Excel `.xlsx`, PDF) are user-generated scientific research data. They remain 100% the intellectual property of the researcher/institution and are never subject to AGPL copyleft obligations.
- **`pystray` (LGPL-3.0-or-later):** The system tray indicator uses `pystray`, linked dynamically via standard PyPI wheel distribution. In accordance with **LGPLv3 Section 4**, users retain full rights to inspect, modify, and dynamically relink this dependency in their Python environment. The application retains full GUI functionality even if `pystray` is omitted.
- **Unprivileged User-Mode (`RunAsInvoker`):** The application runs entirely within unprivileged user space, requiring zero administrative elevation, root privileges, or UAC prompts.
- **Research Use Only (RUO):** The software is designated strictly for bioinformatics research, education, and software development. It is not an in-vitro diagnostic medical device under IVDR (EU) 2017/746 and is not certified for clinical diagnostic or therapeutic decision-making.

---

## Governance & Runtime Invariants

`VFDistiller` strictly enforces ten foundational governance and runtime invariants:

1. **`INV-LOCAL-01` (100% Local-First & Zero Egress):** All genomic sequencing files, converted VCFs, genome references, SQLite databases, and local settings reside solely on the local workstation. Zero telemetry, zero analytics, zero automated cloud egress.
2. **`INV-PRIVACY-02` (Automated Locus & rsID Log Redaction):** Sensitive genomic coordinates and rsIDs are automatically stripped from persistent logs via `redact_for_logfile`, strictly protecting genetic privacy according to GDPR/DSGVO Art. 9 and GenDG.
3. **`INV-INSPECT-03` (Accessible Desktop GUI & Transparent Filtering):** Full visual inspection of variant records via ttkbootstrap desktop GUI and Web Companion PWA; filter criteria (AF thresholds, CADD score, ClinSig, read depth) are completely auditable and user-configurable.
4. **`INV-CONVERT-04` (Multi-Format Ingestion & Standards Parity):** Seamless conversion and ingestion of VCF v4.2, gVCF, 23andMe raw text, and FASTA files without requiring Unix-only toolchains (`bcftools`, `samtools`, `pysam`).
5. **`INV-OFFLINE-05` (Offline Allele Frequency & Annotation Capability):** Fast local annotation using offline SQLite LightDB (gnomAD) without mandatory internet connectivity, supplemented by optional async REST endpoints (VEP, MyVariant.info).
6. **`INV-ACCEL-06` (Optional Cython Hotpath with Graceful Fallback):** Optional compiled Cython extensions provide up to 5x end-to-end acceleration for VCF parsing and AF validation, falling back gracefully to pure Python when no C compiler is available.
7. **`INV-EXPORT-07` (Format Preservation & Multi-Report Generation):** VCF exports preserve original sample FORMAT metrics (DP, GQ, AD, PL) and multi-sample integrity, with flexible export to CSV, Excel (.xlsx), and PDF reports.
8. **`INV-UNPRIV-08` (Unprivileged User-Mode Operation — `RunAsInvoker`):** The application runs entirely within unprivileged user space, requiring zero administrative elevation, root rights, or UAC elevation.
9. **`INV-COMPLY-09` (Strict Research Use Only Boundary — RUO):** Clear and explicit legal boundaries affirming the application is a research and bioinformatics tool, NOT an in-vitro diagnostic medical device under IVDR (EU) 2017/746 and NOT certified for clinical diagnosis.
10. **`INV-SLA-10` (Open-Source Governance, 48h Security SLA & Test Coverage):** Free open-source distribution under AGPL-3.0-or-later, comprehensive third-party license audit, committed 48-hour security response SLA, and automated regression test suites.

---

## Runtime Dependency Matrix

| Package | Version Floor | Functional Role | License (SPDX) | Upstream Repository | Compliance Mechanism |
|:---|:---|:---|:---|:---|:---|
| **`requests`** | `>=2.32.3` | Synchronous HTTP calls to NCBI / gnomAD REST | [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) | [psf/requests](https://github.com/psf/requests) | Permissive Apache-2.0, patched against CVE-2024-35195 |
| **`aiohttp`** | `>=3.10.11` | Asynchronous REST calls to Ensembl VEP | [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) | [aio-libs/aiohttp](https://github.com/aio-libs/aiohttp) | Permissive Apache-2.0, patched against CVE-2024-52304 |
| **`psutil`** | `>=5.9.0` | Memory and CPU resource monitoring | [BSD-3-Clause](https://opensource.org/licenses/BSD-3-Clause) | [giampaolo/psutil](https://github.com/giampaolo/psutil) | Permissive BSD-3-Clause |
| **`Pillow`** | `>=10.3.0` | Desktop icon rendering and image processing | [HPND](https://opensource.org/licenses/HPND) | [python-pillow/Pillow](https://github.com/python-pillow/Pillow) | Permissive Historical Permission Notice, patched against CVE-2024-28219 |
| **`intervaltree`** | `>=3.1.0` | Genomic coordinate interval queries | [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) | [chaimleib/intervaltree](https://github.com/chaimleib/intervaltree) | Permissive Apache-2.0 |
| **`sortedcontainers`** | `>=2.4.0` | Sorted collection data structures for intervals | [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) | [grantjenks/python-sortedcontainers](https://github.com/grantjenks/python-sortedcontainers) | Permissive Apache-2.0 |
| **`ttkbootstrap`** | `>=1.10.0` | Modern theme engine for Tkinter desktop GUI | [MIT](https://opensource.org/licenses/MIT) | [israel-dryer/ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap) | Permissive MIT |
| **`pystray`** | `>=0.19.0` | Windows / cross-platform System Tray icon | [LGPL-3.0-or-later](https://www.gnu.org/licenses/lgpl-3.0.html) | [moses-palmer/pystray](https://github.com/moses-palmer/pystray) | Dynamic linking via PyPI wheel, LGPLv3 § 4 compliant |
| **`scipy`** | `>=1.11.0` | Scientific statistics and distribution calculations | [BSD-3-Clause](https://opensource.org/licenses/BSD-3-Clause) | [scipy/scipy](https://github.com/scipy/scipy) | Permissive BSD-3-Clause |

---

## Optional & Extended Dependencies

| Package | Version Floor | Functional Role | License (SPDX) | Upstream Repository | Compliance Mechanism |
|:---|:---|:---|:---|:---|:---|
| **`openpyxl`** | `>=3.1.3` | Exporting variant analysis tables to Excel (.xlsx) | [MIT](https://opensource.org/licenses/MIT) | [openpyxl/openpyxl](https://foss.heptapod.net/openpyxl/openpyxl) | Permissive MIT, patched against CVE-2024-24576 |
| **`et_xmlfile`** | `>=1.1.0` | Low-memory XML generator for openpyxl | [MIT](https://opensource.org/licenses/MIT) | [openpyxl/et_xmlfile](https://foss.heptapod.net/openpyxl/et_xmlfile) | Permissive MIT |
| **`reportlab`** | `>=4.0.0` | Generating PDF summary research reports | [BSD-3-Clause](https://opensource.org/licenses/BSD-3-Clause) | [reportlab/reportlab](https://www.reportlab.com/) | Permissive BSD-3-Clause |
| **`numpy`** | `>=1.24.0` | High-performance numerical arrays | [BSD-3-Clause](https://opensource.org/licenses/BSD-3-Clause) | [numpy/numpy](https://github.com/numpy/numpy) | Permissive BSD-3-Clause |
| **`biopython`** | `>=1.81` | Sequence parsing and alignment helpers | [BSD-3-Clause / Biopython License](https://biopython.org/wiki/Biopython_License) | [biopython/biopython](https://github.com/biopython/biopython) | Permissive Biopython / BSD-3-Clause license |
| **`pyfaidx`** | `>=0.7.0` | Fast random access to FASTA reference files | [BSD-3-Clause](https://opensource.org/licenses/BSD-3-Clause) | [mdshw5/pyfaidx](https://github.com/mdshw5/pyfaidx) | Permissive BSD-3-Clause |
| **`cython`** | `>=3.0.0` | C-compilation for parsing and AF hotpaths | [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) | [cython/cython](https://github.com/cython/cython) | Permissive Apache-2.0 |

---

## Development, Testing & Packaging Tooling

| Package | Role & Scope | License (SPDX) | Upstream Repository |
|:---|:---|:---|:---|
| **`pytest`** | Test framework, contract test suites, unit & regression tests | [MIT](https://opensource.org/licenses/MIT) | [pytest-dev/pytest](https://github.com/pytest-dev/pytest) |
| **`pluggy`** | Plugin management mechanism for pytest | [MIT](https://opensource.org/licenses/MIT) | [pytest-dev/pluggy](https://github.com/pytest-dev/pluggy) |
| **`iniconfig`** | Brain-dead simple configuration parser used by pytest | [MIT](https://opensource.org/licenses/MIT) | [pytest-dev/iniconfig](https://github.com/pytest-dev/iniconfig) |
| **`ruff`** | High-performance Python linter and code style enforcement | [MIT OR Apache-2.0](https://github.com/astral-sh/ruff) | [astral-sh/ruff](https://github.com/astral-sh/ruff) |
| **`packaging`** | Core utilities for Python packages and version comparison | [Apache-2.0 OR BSD-2-Clause](https://github.com/pypa/packaging) | [pypa/packaging](https://github.com/pypa/packaging) |
| **`PyInstaller`** | Windows standalone executable bundling | [GPL-2.0-or-later WITH Bootloader-exception](https://www.pyinstaller.org/) | [pyinstaller/pyinstaller](https://github.com/pyinstaller/pyinstaller) |
| **`altgraph`** | Abstract graph analysis package used by PyInstaller | [MIT](https://opensource.org/licenses/MIT) | [ronaldoussoren/altgraph](https://github.com/ronaldoussoren/altgraph) |

---

## LGPL Dynamic Linking Compliance Statement

`pystray` is licensed under the GNU Lesser General Public License Version 3 or later (LGPL-3.0-or-later). `VFDistiller` complies with LGPLv3 Section 4:

1. **Dynamic Linking:** `VFDistiller` imports and links dynamically to unmodified `pystray` packages distributed through official Python Package Index (PyPI) wheels.
2. **User Relinking & Modification Rights:** Integrators and end users are entitled to inspect, modify, upgrade, or replace the `pystray` package in their Python runtime environment without restriction.
3. **No Proprietary Modifications:** No modifications have been made to the `pystray` codebase.
4. **Graceful Fallback:** If `pystray` is uninstalled or fails to initialize, `VFDistiller` continues running normally in standard desktop window mode without tray minimization.

---

## Data Privacy & Zero-Copyleft Affirmation

- **Operator Data Ownership:** Variant Call Format (VCF) files, genomic sequences, SQLite databases, and exported summaries created or processed by `VFDistiller` constitute user data. The AGPL-3.0 license covers the software source code, not the data processed through it.
- **Zero Telemetry:** The application contains zero commercial telemetry, zero analytics tracking scripts, and zero advertising libraries.
- **Log Hygiene:** Through the `redact_for_logfile` architecture, private genomic identifiers (including rsIDs, chromosome positions, and sample filepaths) are scrubbed prior to writing to persistent disk logs, preventing inadvertent privacy leaks.

---

## License Texts & Excerpts

### GNU Affero General Public License Version 3 (AGPL-3.0-or-later)
VFDistiller is distributed under AGPL-3.0-or-later. Full license text is available in the root [LICENSE](LICENSE) file.

### MIT License
Used for `ttkbootstrap`, `openpyxl`, `et_xmlfile`, `pytest`, `pluggy`, `iniconfig`, and `altgraph`.
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
> The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

### Apache License Version 2.0 (Apache-2.0)
Used for `requests`, `aiohttp`, `intervaltree`, `sortedcontainers`, `cython`, and co-licensed `ruff`.
> Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

### BSD-3-Clause License
Used for `psutil`, `scipy`, `reportlab`, `numpy`, `biopython`, and `pyfaidx`.
> Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
> 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
> 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
> 3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
