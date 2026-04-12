# VFDistiller — Variant Fusion Distiller

> ⚠️ **Research Use Only / Nicht für klinische Diagnostik / Not for Clinical Use**
>
> VFDistiller ist ein **Forschungs- und Bioinformatik-Werkzeug** für die Analyse
> von VCF-Dateien aus genetischen Tests. Es ist:
>
> - **Kein IVD-Medizinprodukt** im Sinne der IVDR (EU) 2017/746
> - **Nicht CE-IVD-zertifiziert**, nicht durch BfArM oder eine Benannte Stelle geprueft
> - **Nicht für klinische Diagnostik** oder die Interpretation klinischer
>   Testergebnisse (auch nicht im Consumer-Genomik-Kontext)
> - **Keine Gesundheitsempfehlung**, keine Diagnose, keine Prognose, keine
>   Therapieempfehlung
> - Die angezeigten `ClinSig`-Werte (ClinVar) und Variant-Impact-Werte (VEP,
>   AlphaGenome) sind **Datenbank-Annotationen zur Forschungsorientierung**,
>   keine klinische Bewertung
>
> Nutzung ausschliesslich für **Bioinformatik-Lehre, -Forschung und -Software-
> Entwicklung**. Für klinische Interpretation genetischer Befunde konsultieren
> Sie bitte qualifizierte humangenetische Fachstellen.
>
> Unentgeltliche Open-Source-Schenkung (§§ 516 ff. BGB). Haftung auf Vorsatz
> und grobe Fahrlaessigkeit beschraenkt (§ 521 BGB, AGPL-3.0 §§ 15–17).
> Nutzung auf eigenes Risiko.

Bioinformatisches Desktop-Tool zur Verarbeitung, Konvertierung und Annotation forschungsbezogener genetischer Variantendaten aus beliebigen Sequenzierungsquellen. Unterstuetzt VCF, gVCF, 23andMe-Rohformat und FASTA — ohne pysam/bcftools/samtools (Windows-kompatibel).

![Variant Fusion - Hauptansicht](README/screenshots/main_view.png)

## Vertriebsänderung (2026-04-12)

VFDistiller wurde am 2026-04-12 aus dem Microsoft Store entfernt und wird
seitdem **ausschließlich über GitHub** als reines Open-Source-Forschungs-
Tool unter AGPL-3.0-or-later vertrieben.

**Hintergrund:** Bei erneuter Prüfung gegen die IVDR (EU) 2017/746 (In-vitro-
Diagnostika-Verordnung) hätte die Kombination aus Store-Vertrieb und
Consumer-Genomik-nahen Features die App in die Nähe einer IVD-MDSW-
Einstufung gerückt. Der Projektverantwortliche hat sich für die sauberste
Lösung entschieden — vollständige Entfernung des Store-Listings — statt
für ein BfArM-Abgrenzungsverfahren (§ 6 MPDG) oder eine aufwendige
CE-IVD-Zertifizierung.

**Konsequenzen:**
- Bereits installierte Store-Versionen laufen lokal weiter; es gibt keine weiteren Updates über den Store.
- Neue Nutzer: Repository klonen, über PyInstaller/uv bauen oder das GitHub-Releases-Archiv verwenden.
- Die Lizenz bleibt unverändert (AGPL-3.0-or-later, eingeführt am 2026-04-12).
- Zweckbestimmung bleibt: **Research Use Only — Bioinformatik-Tool für VCF-Analyse. Kein Medizinprodukt.**

## Features

- **Multi-Format-Import** — VCF, gVCF, 23andMe-Rohformat (.txt), FASTA (.fa/.fasta)
- **Automatische Build-Erkennung** — GRCh37 / GRCh38 aus Header, Contigs oder RSID-Positionen
- **Multi-Source-Annotation** — gnomAD, MyVariant.info, Ensembl VEP, ALFA, TOPMed, AlphaGenome
- **INFO-Recycling** — Vorhandene VCF-Annotationen werden wiederverwendet
- **Filterung** — AF-Schwelle, CADD-Score, Variant Impact, ClinSig, Genlisten, FILTER=PASS, Read Depth
- **Export** — CSV, Excel, PDF, annotiertes VCF (gefiltert oder vollstaendig)
- **GUI** — ttkbootstrap-Oberflaeche mit System-Tray, Fortschrittsanzeige, Themes
- **Performance** — Optionaler Cython-Hotpath (5x Gesamt-Speedup), SQLite-Batch-Writes, async HTTP via aiohttp
- **Hintergrund-Wartung** — Automatisches Nachladen fehlender Annotationen im Leerlauf
- **Mehrsprachig** — Deutsch und Englisch (JSON-basierte Uebersetzungen)

## Voraussetzungen

- Python 3.10+
- Windows 10/11 (primaer getestet), Linux/macOS experimentell

### Installation

VFDistiller wird **ausschließlich über GitHub** vertrieben (kein Microsoft
Store, kein Paketmanager). Empfohlene Installationswege:

1. **GitHub-Releases** — neuestes Paket-Archiv (falls verfuegbar) unter
   [Releases](https://github.com/biotec-line/VFDistiller/releases) herunterladen.
2. **Source-Build** — Repository klonen und Abhaengigkeiten installieren:

```bash
git clone https://github.com/biotec-line/VFDistiller.git
cd VFDistiller

# Abhaengigkeiten installieren
pip install -r requirements.txt

# Optional: Cython-Beschleunigung (erfordert C-Compiler)
pip install cython
cd cython_hotpath
python setup.py build_ext --inplace
cd ..
```

3. **PyInstaller / uv** — fuer einen Standalone-`.exe`-Build siehe
   `VFDistiller.spec` (PyInstaller-Konfiguration im Repo enthalten).

### Genomreferenzen (optional, fuer FASTA-Validierung)

Die Genomreferenzen (GRCh37/GRCh38) muessen separat heruntergeladen werden (~3 GB pro Build):

```bash
# GRCh37
wget https://ftp.ensembl.org/pub/grch37/current/fasta/homo_sapiens/dna/Homo_sapiens.GRCh37.dna.primary_assembly.fa.gz
gunzip Homo_sapiens.GRCh37.dna.primary_assembly.fa.gz

# GRCh38
wget https://ftp.ensembl.org/pub/release-112/fasta/homo_sapiens/dna/Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz
gunzip Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz
```

Die Dateien ins Projektverzeichnis legen. Beim ersten Start wird automatisch ein `.fai`-Index erzeugt.

### gnomAD LightDB (optional)

Fuer schnelle Offline-AF-Lookups kann die gnomAD LightDB heruntergeladen werden. Das Tool bietet beim ersten Start einen Download-Dialog an. Alternativ:

```bash
python "Get gnomAD DB light.py"
```

## Verwendung

### GUI starten

```bash
python Variant_Fusion_pro_V17.py
```

Oder unter Windows:

```
START.bat
```

### Workflow

1. **Datei oeffnen** — VCF, gVCF, 23andMe-Textdatei oder FASTA waehlen
2. **Build pruefen** — Wird automatisch erkannt, kann manuell ueberschrieben werden
3. **Pipeline laeuft** — Varianten werden geparst, annotiert und gefiltert
4. **Ergebnisse** — Tabellenansicht mit sortierbaren Spalten, Doppelklick oeffnet externe Datenbanken
5. **Export** — CSV, Excel, PDF oder annotiertes VCF exportieren

### Konfiguration

Beim ersten Start wird `variant_fusion_settings.json` aus der Vorlage `variant_fusion_settings.json.example` erstellt. Wichtige Einstellungen:

| Einstellung | Beschreibung | Standard |
|---|---|---|
| `af_threshold` | Allele-Frequency-Schwelle | 0.007 |
| `include_none` | Varianten ohne AF anzeigen | false |
| `cadd_highlight_threshold` | CADD-Score-Hervorhebung | 22.0 |
| `stale_days` | Tage bis AF-Refresh | 200 |
| `alphagenom_key` | Google AlphaGenome API-Key | (leer) |
| `quality_settings` | VCF-Record-Level Filter | siehe Example |

### API-Keys

- **AlphaGenome**: Erfordert einen Google AI API-Key. In `variant_fusion_settings.json` unter `alphagenom_key` und `api_settings.phase6_ag.alphagenom.api_key` eintragen.
- **NCBI**: Optional fuer hoehere Rate-Limits. Unter `api_settings.global.ncbi_api_key` eintragen.

## Dependencies

### Core (erforderlich)

| Paket | Lizenz | Zweck |
|---|---|---|
| requests | Apache 2.0 | HTTP-Requests |
| psutil | BSD | CPU/Memory-Monitoring |
| Pillow | PIL License | Icon/Image-Processing |
| intervaltree | Apache 2.0 | Genomische Intervalle |
| ttkbootstrap | MIT | Moderne GUI-Themes |
| pystray | MIT | System-Tray-Icon |
| aiohttp | Apache 2.0 | Async HTTP-Fetching |
| scipy | BSD | Statistik |

### Optional

| Paket | Lizenz | Zweck |
|---|---|---|
| openpyxl | MIT | Excel-Export |
| reportlab | BSD | PDF-Export |
| numpy | BSD | Array-Operationen |
| biopython | Biopython License | Sequenz-Alignment |
| pyfaidx | MIT | FASTA-Indexierung |
| cython | Apache 2.0 | Hot-Path-Kompilierung |

## Cython-Beschleunigung

Optionale C-kompilierte Hot-Paths fuer kritische Operationen:

| Modul | Speedup | Funktion |
|---|---|---|
| `vcf_parser.pyx` | 8x | VCF-Zeilen-Parsing |
| `af_validator.pyx` | 100x | AF-Validierung |
| `key_normalizer.pyx` | 25x | Variant-Key-Normalisierung |
| `fasta_lookup.pyx` | 100x | FASTA-Sequenz-Lookup |

Gesamt-Pipeline-Speedup: ~5x (50k Varianten: 15 min -> 3 min).

Wenn Cython nicht installiert ist, werden automatisch Python-Fallbacks verwendet.

## Projektstruktur

```
VFDistiller/
├── Variant_Fusion_pro_V17.py .... Hauptprogramm (GUI + Pipeline)
├── requirements.txt ............. Python-Abhaengigkeiten
├── variant_fusion_settings.json.example . Konfigurations-Vorlage
├── VFDistiller.spec ............. PyInstaller Build-Konfiguration
├── START.bat .................... Windows-Schnellstart
│
├── cython_hotpath/ .............. Optionale Cython-Module
│   ├── __init__.py .............. CythonAccelerator Hauptklasse
│   ├── vcf_parser.pyx .......... VCF-Parsing
│   ├── af_validator.pyx ......... AF-Validierung
│   ├── key_normalizer.pyx ....... Key-Normalisierung
│   ├── fasta_lookup.pyx ......... FASTA-Lookup
│   ├── setup.py ................. Build-Script
│   └── test_performance.py ...... Benchmarks
│
├── data/annotations/ ............ Gen-Annotationsdaten
│   ├── GRCh37.gtf.gz ........... Ensembl Gene-Annotationen
│   └── GRCh38.gtf.gz
│
├── locales/
│   └── translations.json ........ Uebersetzungen (de/en)
│
├── ICO/ICO.ico .................. App-Icon
│
├── lightdb_index_worker.py ...... gnomAD LightDB Hintergrund-Indexierung
├── translator.py ................ Uebersetzungs-Engine
├── translator_patch.py .......... Uebersetzungs-Patches
├── manage_translations.py ....... Uebersetzungs-Verwaltung
├── Get gnomAD DB light.py ....... gnomAD Download-Tool
├── test_performance.py .......... Performance-Tests
│
├── ARCHITECTURE.md .............. Entwickler-Dokumentation
└── README/ ...................... Erweiterte Dokumentation & Lizenzen
    └── licenses/
        ├── LICENSE.txt .......... Hauptlizenz (Englisch)
        ├── LICENSE.de.txt ....... Hauptlizenz (Deutsch)
        └── THIRD_PARTY_LICENSES.txt . Third-Party-Lizenzen
```

## Lizenz

**[AGPL-3.0-or-later](LICENSE)** (GNU Affero General Public License, Version 3
oder jede neuere Version). **Kostenlos. Dauerhaft.**

- Copyright (C) 2026 Lukas Geiger (c/o Um:bruch Think Tank)
- Volltext: [LICENSE](LICENSE), Haftungshinweise: [NOTICE](NOTICE)
- Vorgaengerlizenz: Die fruehere „VFDistiller License v1.0" wurde abgeloest
  und liegt zur Nachvollziehbarkeit in
  [`docs/archive/`](docs/archive/VFDistiller_License_v1_legacy.md).

Kurz gefasst:

- Nutzen, studieren, modifizieren, weitergeben: **erlaubt**, kostenlos.
- Weitergabe (einschliesslich Forks, Re-Packaging, kostenpflichtiger Support):
  **erlaubt**, aber abgeleitete Werke muessen unter AGPL-3.0-or-later bleiben.
- **Network-/SaaS-Nutzung (AGPL § 13):** Wer eine modifizierte Version auf
  einem Server betreibt, mit dem Nutzer ueber ein Netzwerk interagieren,
  muss diesen Nutzern den Quellcode zugaenglich machen.
- **Kein Weiterverkauf dieses Codes als Closed-Source-Produkt.** Jede
  abgeleitete Arbeit bleibt AGPL.
- Die Software ist **nicht medizinisch validiert** und darf nicht fuer
  klinische Diagnosen oder Therapieentscheidungen verwendet werden
  (siehe RUO-Banner oben und [NOTICE](NOTICE)).

Third-Party-Bibliotheken behalten ihre jeweiligen Lizenzen (MIT, BSD,
Apache 2.0, PIL License, Biopython License). Siehe
[`README/licenses/THIRD_PARTY_LICENSES.txt`](README/licenses/THIRD_PARTY_LICENSES.txt).

> **Vertrieb:** VFDistiller wird ausschliesslich ueber GitHub vertrieben
> (siehe [Vertriebsaenderung (2026-04-12)](#vertriebsaenderung-2026-04-12)
> oben). Das frühere Microsoft-Store-Listing wurde zurueckgezogen.

## Version

V17.0 — Aktuelle Produktionsversion (Maerz 2026).

---

🇬🇧 [English version](README.md)
