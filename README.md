# VFDistiller — Variant Fusion Distiller

> ⚠️ **Research Use Only / Nicht für klinische Diagnostik / Not for Clinical Use**
>
> VFDistiller ist ein **Forschungs- und Bioinformatik-Werkzeug** für die Analyse
> von VCF-Dateien aus genetischen Tests. Es ist:
>
> - **Kein IVD-Medizinprodukt** im Sinne der IVDR (EU) 2017/746
> - **Nicht CE-IVD-zertifiziert**, nicht durch BfArM oder eine Benannte Stelle geprüft
> - **Nicht für klinische Diagnostik** oder die Interpretation klinischer
>   Testergebnisse (auch nicht im Consumer-Genomik-Kontext)
> - **Keine Gesundheitsempfehlung**, keine Diagnose, keine Prognose, keine
>   Therapieempfehlung
> - Die angezeigten `ClinSig`-Werte (ClinVar) und Variant-Impact-Werte (VEP,
>   AlphaGenome) sind **Datenbank-Annotationen zur Forschungsorientierung**,
>   keine klinische Bewertung
>
> Nutzung ausschließlich für **Bioinformatik-Lehre, -Forschung und -Software-
> Entwicklung**. Für klinische Interpretation genetischer Befunde konsultieren
> Sie bitte qualifizierte humangenetische Fachstellen.
>
> Unentgeltliche Open-Source-Schenkung (§§ 516 ff. BGB). Haftung auf Vorsatz
> und grobe Fahrlässigkeit beschränkt (§ 521 BGB, AGPL-3.0 §§ 15–17).
> Nutzung auf eigenes Risiko.
>
> ---
>
> **English summary:** VFDistiller is a bioinformatics research tool. It is
> NOT an in-vitro diagnostic medical device (IVDR (EU) 2017/746), NOT
> CE-marked, NOT reviewed by BfArM or any notified body and NOT intended for
> clinical diagnosis, prognosis or therapy decisions. ClinSig / variant-impact
> values shown are third-party research database annotations, not medical
> assessments. Use for bioinformatics research, teaching and software
> development only. Free open-source donation; liability limited to intent
> and gross negligence (§ 521 BGB, AGPL-3.0 §§ 15–17). Use at your own risk.

A bioinformatics desktop tool for processing, converting, and annotating research-grade genetic variant data from any sequencing source. Supports VCF, gVCF, 23andMe raw format, and FASTA — without pysam/bcftools/samtools (Windows-compatible).

![Variant Fusion - Main View](README/screenshots/main_view.png)

## Distribution Change (2026-04-12)

VFDistiller was **withdrawn from the Microsoft Store** on 2026-04-12 (listing set
to "unavailable" — Microsoft Partner Center does not support hard delete) and is
now distributed **exclusively via GitHub** as a pure open-source research tool
under AGPL-3.0-or-later. The Store listing is no longer publicly searchable and
no new installations can be acquired through the Store. Existing local
installations continue to run but will receive no further updates.

**Why:** On re-evaluation against the IVDR (EU) 2017/746 (in-vitro diagnostic
regulation), the combination of Store distribution + consumer-genomics-
adjacent features would have placed the app close to IVD-MDSW classification.
The project lead chose the cleanest mitigation — withdrawing the Store listing
entirely — rather than pursuing a BfArM delimitation procedure (§ 6 MPDG)
or expensive CE-IVD certification.

**Consequences:**
- Existing Store installations keep working locally; no further updates via Store.
- New users: clone the repo, build via PyInstaller/uv, or use the GitHub Releases archive.
- No change to the license (AGPL-3.0-or-later, as introduced on 2026-04-12).
- Zweckbestimmung / Intended purpose remains: **Research Use Only — Bioinformatics tool for VCF analysis. Not a medical device.**

**Repository status (2026-05-01):**
- Git tracks source code, documentation, tests, workflow metadata, packaging templates, and the application icon.
- Genome references, downloaded gene annotations, local settings, SQLite caches/databases, logs, build outputs, release archives, and Store binaries are excluded by `.gitignore` and must remain local.
- API keys are never committed; use the generated `variant_fusion_settings.json` or environment-specific local configuration.

## Features

- **Multi-Format Import** — VCF, gVCF, 23andMe raw text format (.txt), FASTA (.fa/.fasta)
- **Automatic Build Detection** — GRCh37 / GRCh38 from header, contigs, or RSID positions
- **Multi-Source Annotation** — gnomAD, MyVariant.info, Ensembl VEP, ALFA, TOPMed, AlphaGenome
- **INFO Recycling** — Existing VCF annotations are reused
- **Filtering** — AF threshold, CADD score, Variant Impact, ClinSig, gene lists, FILTER=PASS, Read Depth
- **Export** — CSV, Excel, PDF, annotated VCF (filtered or complete)
- **GUI** — ttkbootstrap interface with System Tray, progress indicator, themes
- **Performance** — Optional Cython hot-path (5x overall speedup), SQLite batch writes, async HTTP via aiohttp
- **Background Maintenance** — Automatic re-fetching of missing annotations during idle
- **Multilingual** — German and English (JSON-based translations)

## Prerequisites

- Python 3.10+
- Windows 10/11 (primarily tested), Linux/macOS experimental

### Installation

VFDistiller is distributed **exclusively via GitHub** (no Microsoft Store,
no package manager). Recommended paths:

1. **GitHub Releases** — download the latest packaged archive (if available)
   from [Releases](https://github.com/biotec-line/VFDistiller/releases).
2. **Source build** — clone the repository and install dependencies:

```bash
git clone https://github.com/biotec-line/VFDistiller.git
cd VFDistiller

# Install dependencies
pip install -r requirements.txt

# Optional: Cython acceleration (requires C compiler)
pip install cython
cd cython_hotpath
python setup.py build_ext --inplace
cd ..
```

3. **PyInstaller / uv** — for a standalone `.exe` build, see
   `VFDistiller.spec` (PyInstaller configuration shipped with the repo).

### Tests

Run the maintained regression suite from the repository root:

```bash
python -m pytest -q
```

`pytest.ini` limits automated collection to `tests/`. The two
`test_performance.py` files are executable benchmark/correctness scripts and
are intentionally run directly:

```bash
python test_performance.py
python cython_hotpath/test_performance.py
```

This split keeps CI focused on deterministic regression coverage while the
benchmark scripts remain available for manual performance verification.

### Genome References (optional, for FASTA validation)

The genome references (GRCh37/GRCh38) must be downloaded separately (~3 GB per build):

```bash
# GRCh37
wget https://ftp.ensembl.org/pub/grch37/current/fasta/homo_sapiens/dna/Homo_sapiens.GRCh37.dna.primary_assembly.fa.gz
gunzip Homo_sapiens.GRCh37.dna.primary_assembly.fa.gz

# GRCh38
wget https://ftp.ensembl.org/pub/release-112/fasta/homo_sapiens/dna/Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz
gunzip Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz
```

Place the files in the project directory. On first launch, a `.fai` index is automatically generated.

### gnomAD LightDB (optional)

For fast offline AF lookups, the gnomAD LightDB can be downloaded. The tool offers a download dialog on first launch. Alternatively:

```bash
python "Get gnomAD DB light.py"
```

## Usage

### Launch GUI

```bash
python Variant_Fusion_pro_V17.py
```

Or on Windows:

```
START.bat
```

### Workflow

1. **Open file** — Select VCF, gVCF, 23andMe text file, or FASTA
2. **Check build** — Automatically detected, can be manually overridden
3. **Pipeline runs** — Variants are parsed, annotated, and filtered
4. **Results** — Table view with sortable columns, double-click opens external databases
5. **Export** — Export as CSV, Excel, PDF, or annotated VCF

### Configuration

On first launch, `variant_fusion_settings.json` is created from the template `variant_fusion_settings.json.example`. Key settings:

| Setting | Description | Default |
|---|---|---|
| `af_threshold` | Allele frequency threshold | 0.007 |
| `include_none` | Show variants without AF | false |
| `cadd_highlight_threshold` | CADD score highlighting | 22.0 |
| `stale_days` | Days until AF refresh | 200 |
| `alphagenom_key` | Google AlphaGenome API key | (empty) |
| `quality_settings` | VCF record-level filter | see example |

### API Keys

- **AlphaGenome**: Requires a Google AI API key. Enter in `variant_fusion_settings.json` under `alphagenom_key` and `api_settings.phase6_ag.alphagenom.api_key`.
- **NCBI**: Optional for higher rate limits. Enter under `api_settings.global.ncbi_api_key`.

## Dependencies

### Core (required)

| Package | License | Purpose |
|---|---|---|
| requests | Apache 2.0 | HTTP requests |
| psutil | BSD | CPU/Memory monitoring |
| Pillow | PIL License | Icon/Image processing |
| intervaltree | Apache 2.0 | Genomic intervals |
| ttkbootstrap | MIT | Modern GUI themes |
| pystray | MIT | System Tray icon |
| aiohttp | Apache 2.0 | Async HTTP fetching |
| scipy | BSD | Statistics |

### Optional

| Package | License | Purpose |
|---|---|---|
| openpyxl | MIT | Excel export |
| reportlab | BSD | PDF export |
| numpy | BSD | Array operations |
| biopython | Biopython License | Sequence alignment |
| pyfaidx | MIT | FASTA indexing |
| cython | Apache 2.0 | Hot-path compilation |

## Cython Acceleration

Optional C-compiled hot-paths for critical operations:

| Module | Speedup | Function |
|---|---|---|
| `vcf_parser.pyx` | 8x | VCF line parsing |
| `af_validator.pyx` | 100x | AF validation |
| `key_normalizer.pyx` | 25x | Variant key normalization |
| `fasta_lookup.pyx` | 100x | FASTA sequence lookup |

Overall pipeline speedup: ~5x (50k variants: 15 min -> 3 min).

If Cython is not installed, Python fallbacks are used automatically.

## Project Structure

```
VFDistiller/
├── Variant_Fusion_pro_V17.py .... Main program (GUI + Pipeline)
├── requirements.txt ............. Python dependencies
├── variant_fusion_settings.json.example . Configuration template
├── VFDistiller.spec ............. PyInstaller build configuration
├── START.bat .................... Windows quick-start
│
├── cython_hotpath/ .............. Optional Cython modules
│   ├── __init__.py .............. CythonAccelerator main class
│   ├── vcf_parser.pyx .......... VCF parsing
│   ├── af_validator.pyx ......... AF validation
│   ├── key_normalizer.pyx ....... Key normalization
│   ├── fasta_lookup.pyx ......... FASTA lookup
│   ├── setup.py ................. Build script
│   └── test_performance.py ...... Benchmarks
│
├── data/annotations/ ............ Runtime/downloaded gene annotation cache (ignored)
│
├── locales/
│   └── translations.json ........ Translations (de/en)
│
├── ICO/ICO.ico .................. App icon
│
├── lightdb_index_worker.py ...... gnomAD LightDB background indexing
├── translator.py ................ Translation engine
├── translator_patch.py .......... Translation patches
├── manage_translations.py ....... Translation management
├── Get gnomAD DB light.py ....... gnomAD download tool
├── test_performance.py .......... Performance tests
│
├── ARCHITECTURE.md .............. Developer documentation
└── README/ ...................... Extended documentation & licenses
    └── licenses/
        ├── LICENSE.txt .......... Main license (English)
        ├── LICENSE.de.txt ....... Main license (German)
        └── THIRD_PARTY_LICENSES.txt . Third-party licenses
```

## License

**[AGPL-3.0-or-later](LICENSE)** (GNU Affero General Public License, version 3
or any later version). **Free of charge. Forever.**

- Copyright (C) 2026 Lukas Geiger (c/o Um:bruch Think Tank)
- Full text: [LICENSE](LICENSE), disclaimers: [NOTICE](NOTICE)
- Superseded license: the former "VFDistiller License v1.0" has been retired
  and is kept for reference in
  [`docs/archive/`](docs/archive/VFDistiller_License_v1_legacy.md).

In short:

- Use, study, modify, share: **allowed**, at no cost.
- Redistribution (including forks, re-packaging, paid support): **allowed**,
  but derivative works must remain under AGPL-3.0-or-later.
- **Network / SaaS use (AGPL § 13):** If you run a modified version on a
  server that users interact with over a network, you must make the
  corresponding source code available to those users.
- **No resale of this code as a closed-source product.** Any downstream
  work must stay AGPL.
- The software is **not medically validated** and must not be used for
  clinical diagnoses or therapeutic decisions. See the RUO banner above
  and [NOTICE](NOTICE).

Third-party libraries retain their own licenses (MIT, BSD, Apache 2.0,
PIL License, Biopython License). See
[`README/licenses/THIRD_PARTY_LICENSES.txt`](README/licenses/THIRD_PARTY_LICENSES.txt).

> **Distribution:** VFDistiller is distributed exclusively via GitHub
> (see [Distribution Change (2026-04-12)](#distribution-change-2026-04-12)
> above). The former Microsoft Store listing has been retired.

## Version

V17.0 — Current production version (March 2026).

---

🇩🇪 [Deutsche Version](README.de.md)

> ⚠️ **Rechtlicher Hinweis / Legal Notice**
>
> Dieses Projekt ist **kein Medizinprodukt** im Sinne der MDR (EU) 2017/745 / IVDR (EU) 2017/746. Es ist **nicht klinisch validiert**, **nicht durch BfArM oder eine Benannte Stelle geprüft**, **nicht zertifiziert**. Es verarbeitet Daten ausschließlich zu Forschungs- und Softwareentwicklungszwecken. Eine klinische oder diagnostische Nutzung ist ausdrücklich **nicht** die Zweckbestimmung. Entscheidungen über Diagnose und Therapie bleiben qualifizierten Fachpersonen vorbehalten.
>
> This project is **not a medical device** within the meaning of MDR (EU) 2017/745 / IVDR (EU) 2017/746. It is **not clinically validated**, **not approved by BfArM or any Notified Body**, **not certified**. Data is processed exclusively for research and software development purposes. Clinical or diagnostic use is explicitly **not** the intended purpose. Decisions about diagnosis and therapy remain reserved for qualified professionals.
>
> Unentgeltliche Open-Source-Schenkung (§§ 516 ff. BGB). Haftung auf Vorsatz und grobe Fahrlässigkeit beschränkt (§ 521 BGB). Nutzung auf eigenes Risiko. / Unpaid open-source donation. Liability limited to intent and gross negligence. Use at own risk.

