# Changelog / Änderungsprotokoll

Alle wesentlichen Änderungen an diesem Projekt werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [17.0.2] - 2026-09-19

### Repository-Hygiene, CI-Härtung & PEP 621 Standardisierung (Pfad A)
- **CI/Workflow Timeout- & Concurrency-Härtung**: Timeout-Grenzen für alle GitHub Actions Workflows verbindlich definiert: `.github/workflows/tests.yml` (`timeout-minutes: 15`), `.github/workflows/source-platform-smoke.yml` (`timeout-minutes: 15`), `.github/workflows/stale.yml` (`timeout-minutes: 10`) und `.github/workflows/welcome.yml` (`timeout-minutes: 5`). Concurrency-Cancellation (`group: ${{ github.workflow }}-${{ github.ref }}`, `cancel-in-progress: true`) in `welcome.yml` nachgerüstet.
- **PEP 621 Standard-Lizenzmetadaten**: `pyproject.toml` mit standardisiertem `license-files = ["LICENSE", "NOTICE", "THIRD_PARTY_LICENSES.md", "THIRD_PARTY_LICENSES.txt"]` gemäß modernem Packaging-Standard ausgestattet.
- **Multi-Host Cloud-Sync- & Fail-Closed Lock-Schutz**: `.gitignore` erweitert um Cloud-Konfliktmuster (`*conflicted copy*`, `* (Kopie)*`, `* (Copy)*`, `*-WORKSTATION*`, `*-LAPTOP*`, `*-ASUS*`, `*-Mac Studio*`, `*-MacBook*`), Fail-Closed Lock-Sperren (`LOCK.user.*`, `LOCK.until.*`, `LOCK.condition.*`, `.automation-lock`, `!package-lock.json`) und zusätzliche Tool-Caches (`.hypothesis/`, `.turbo/`, `.tox/`).
- **Synchronisierte Versionsanhebung (17.0.2)**: Durchgängige Versionsharmonisierung auf `17.0.2` in `pyproject.toml`, Windows Store AppX-Metadaten `store_package.json` (`17.0.2.0`), `store_package/AppxManifest.xml` (`17.0.2.0`), `SECURITY.md`, `llms.txt` und `MARKETING-LOG.txt`.
- **Drittanbieter-SBOM & Lizenzaudit**: Re-Audit der Third-Party-Lizenzdokumentation `THIRD_PARTY_LICENSES.md` mit Stempel `2026-09-19 (v17.0.2)`, Bestätigung von Zero-Copyleft für genomische Forschungsdaten und `RunAsInvoker`-Laufzeitgarantie.
- **Automatisierte Vertragstests**: `tests/test_metadata.py` erweitert um Validierung von CI-Timeouts, Workflow-Concurrency, PEP 621 `license-files`, `.gitignore`-Ausschlussmustern und Release-Dokumentation.

## [17.0.1] - 2026-09-10

### Repository-Hygiene & CI-Matrix-Härtung (Pfad A)
- **PEP 621 Standard-Metadaten**: `pyproject.toml` mit standardisierter Paketkonfiguration für `vfdistiller` v17.0.1 angelegt (AGPL-3.0-or-later, Python >=3.10, vollständige Ökosystem- und Repository-URLs für biotec-line und open-bricks, standardisierte Classifiers, optionale Dev-/Test-Dependencies sowie `[tool.pytest.ini_options]` und `[tool.ruff]`).
- **CI-Matrix & Concurrency-Härtung**: Neue GitHub Actions Workflow-Matrix `.github/workflows/tests.yml` für Python 3.10 bis 3.13 unter `ubuntu-latest` mit Bytecode-Kompilierungsgate (`python -m compileall -q .`), Linter-Gate (`ruff check .`) und Pytest-Ausführung. Concurrency-Cancellation (`cancel-in-progress: true`) in `source-platform-smoke.yml` und `tests.yml` nachgerüstet.
- **Git-Hygiene & Lock-Schutz**: `.gitignore` erweitert um Schutz vor Multi-Host-Synchronisationskonflikten (`*-conflict-*`, `*.sync-conflict-*`, etc.), Multi-Agent Locks (`LOCK`, `LOCK.*`, etc.) sowie `.ruff_cache/`, `wheelhouse/` und Build-Caches.
- **Sicherheitsrichtlinie & SLAs**: `SECURITY.md` zweisprachig überarbeitet mit verbindlicher 48-Stunden-Erstrückmeldung (SLA), 5-Werktage-Triage und offiziellen Sicherheitskontakten (`security@open-bricks.org`, `security@biotec-line.org`, `lukas@open-bricks.org`).
- **Code-Qualität & Bugfixes**: Unbenutzte Imports in `tests/` bereinigt, ungebundene `DIST_DIR`-Variable in `build_release.py` behoben, Benchmark-Schleifen in `test_performance.py` an Ruff-Konventionen angepasst.
- **Vertragstestsuite**: `tests/test_metadata.py` hinzugefügt, um PEP 621 Metadaten, `.gitignore`-Muster, Sicherheits-SLAs, `llms.txt`, `CHANGELOG.md` und CI-Workflows automatisiert im Testzyklus abzusichern.

## [Unreleased]

### Internationalisierung (Tier-2 Policy P-006 Standard — 2026-09-23)
- **Vollständige 6-Sprachen-Erweiterung (Tier-2 Parität)**: `locales/translations.json` auf 158 Schlüssel mit 100% Abdeckung für Deutsch (`de`), Englisch (`en`), Spanisch (`es`), Chinesisch (`zh`), Japanisch (`ja`) und Russisch (`ru`) erweitert (948 Übersetzungen, 0 Lücken).
- **Modernisierte i18n-Engine (`translator.py`)**: Deterministische 4-stufige Fallback-Kette (`target -> en -> de -> key`), System-Locale-Erkennung (`detect_system_language`), kwargs-String-Interpolation, thread-sicherer Singleton-Zugriff (`get_translator`, `t`, `set_language`) und vollständige Rückwärtskompatibilität für PyInstaller (`sys._MEIPASS`) und JSONDecodeError-Regressionswächter.
- **CI & Validierungs-CLI (`manage_translations.py`)**: Neuer CLI-Schalter `--check` zur automatisierten Validierung der 100%igen Übersetzungsparität aller 6 Sprachen im CI-Workflow; UTF-8-Encoding-Härtung für Windows-Konsolen.
- **GUI-Sprachmenü & Persistenz (`Variant_Fusion_pro_V17.py`)**: Sprachauswahl-Menü auf alle 6 Sprachen (`Deutsch`, `English`, `Español`, `简体中文`, `日本語`, `Русский`) erweitert; die gewählte Sprache wird in `variant_fusion_settings.json` persistent gespeichert und beim App-Start automatisch wiederhergestellt.
- **Umfassende Vertragstest-Suite (`tests/test_i18n.py`)**: 10 neue automatisierte Tests zur Überprüfung von Sprachkonstanten, 100% Katalog-Parität, 4-Ebenen-Fallback, Format-Interpolation, Singleton-Funktionen, System-Locale-Erkennung, CLI-Prüflauf und UTF-8/Umlaut-Integrität.

### Dokumentation & Auffindbarkeit / Discoverability (Pfad B — 2026-09-16)
- **Zweisprachige 18-Punkte-Schnellnavigation**: Vollständige Strukturierung von `README.md` und `README.de.md` mit 18 durchnummerierten Hauptabschnitten und 100% wechselseitiger Anker-Parität (#1 bis #18 inklusive Alias-Ankern).
- **Zielgruppen & High-Intent SEO Keywords**: 4 definierte Zielgruppen (`[PERSONA-01]` bis `[PERSONA-04]`: Klinische Genetiker, Bioinformatik-Core-Facility-Entwickler, Seltene-Krankheiten-Forscher, Datenschutzbeauftragte & Offline-Labor-IT) mit spezifischen High-Intent-Suchbegriffen in Englisch und Deutsch.
- **10-Dimensionen-Vergleichsmatrix**: Detaillierte Gegenüberstellung von VFDistiller mit 4 Branchen-Alternativen (Unix Shell Pipelines, Cloud-Varianten-Portale, Desktop-Browser IGV, CLI-Annotations-Engines) gemappt auf die 10 Governance- und Laufzeit-Invarianten `INV-LOCAL-01` bis `INV-SLA-10`.
- **Governance & Laufzeit-Invarianten**: Verbindliche Verankerung der 10 Invarianten (`INV-LOCAL-01` Local-First Zero-Egress, `INV-PRIVACY-02` Locus/rsID Log-Redaktion, `INV-INSPECT-03` Desktop GUI, `INV-CONVERT-04` Multi-Format Ingestion, `INV-OFFLINE-05` Offline gnomAD SQLite, `INV-ACCEL-06` Cython Hotpaths, `INV-EXPORT-07` FORMAT-Erhalt & Reports, `INV-UNPRIV-08` RunAsInvoker, `INV-COMPLY-09` RUO-Grenze, `INV-SLA-10` 48h SLA) in beiden READMEs, `THIRD_PARTY_LICENSES.md` und `MARKETING-LOG.txt`.
- **Drittanbieter-Lizenzaudit (`THIRD_PARTY_LICENSES.md`)**: Vollständiges Markdown-Inventar aller Laufzeit-, Optional- und Entwicklungs-Dependencies mit SPDX-Bezeichnern, Bestätigung der Zero-Copyleft-Freiheit für genomische Forschungsdaten, unprivilegierter `RunAsInvoker`-Laufzeit sowie LGPLv3 § 4 Transparenzerklärung für dynamisch verlinktes `pystray`.
- **Lokales Marketing- und Audit-Logbuch (`MARKETING-LOG.txt`)**: Lokales Register zur Erfassung von Pfad A (2026-09-10) und Pfad B (2026-09-16) mit Zielgruppen, Suchbegriffen, Vergleichsmatrix und Ökosystem-Synergien.
- **PEP 621 URL-Erweiterung**: URLs in `pyproject.toml` um `Marketing Log`, `Third-Party Licenses` (Markdown) und `LLM Ready` erweitert.
- **LLM-Kontext & Shields.io Badges**: `llms.txt` aktualisiert (Stand: 2026-09-16, 148 bestandene Tests, 10 Subtests); Badges für Teststand, Local-First Zero-Egress, RunAsInvoker, Third-Party Audited und Marketing-Log nachgezogen.
- **Automatisierte Vertragstests**: Neue Contract-Tests in `tests/test_metadata.py` zur Validierung von 18-Punkte-Navigationsparität, Zielgruppen, Vergleichsmatrix, Invarianten, Lizenzaudit und Marketing-Log.

### Hinzugefügt / Added (2026-09-13)
- **Web Companion & Mobile PWA Suite**: `web_companion/` mit responsivem HTML-Interface, Web-App-Manifest (`manifest.json`, `manifest.webmanifest`), Touch-Icons und Vektor-/Favicon-Assets für lokale Web-Vorschau und PWA-Unterstützung integriert.

### Dokumentation & Metadaten (2026-09-13)
- **Test-Badges & LLM-Kontext**: Test-Badge in `README.md` und `README.de.md` auf 134 bestandene Tests (inkl. Regressionstestsuite `test_bugsweep_partial8_20260910.py`) aktualisiert; Prüfdatum in `llms.txt` auf 2026-09-13 nachgezogen.

### Behoben / Fixed (2026-09-10 - Bug-Sweep Block 8)
- **VCF FORMAT-Metriken im Export (`_extract_format_field` & `_build_format_fields`)**: `_extract_format_field` unterstützt nun neben geparsten Datensätzen mit `samples`-Liste auch `orig_records`-Einträge mit `sample`-String (Singular). Zuvor wurden beim VCF-Export alle Qualitäts-Metriken (DP, GQ, AD, PL) stillschweigend verworfen.
- **Multi-Sample VCF Parsing**: In `parse_vcf_records` und `parse_vcf_records_mmap` wurde die fehlerhafte Begrenzung `split('\t', 9)` entfernt, wodurch Multi-Sample-Spalten nicht mehr in ein einziges Feld konkateniert werden.
- **QualityManager Sample-Namen & DP-Priorisierung**: `QualityManager` stellt nun die Methode `get_vcf_sample_names` bereit, die von `Distiller.process_vcf` aufgerufen wird (verhindert stumme `AttributeError`-Fehler). Zudem priorisiert `QualityManager._extract_dp` nun sample-spezifische FORMAT-DP-Werte vor aggregierten INFO-DP-Werten.

### Dokumentation & Sichtbarkeit / Discoverability (2026-08-14)
- **Badges & Header-Politur**: Shields.io-Badges für Organisation (`biotec-line`), Dach-Ökosystem (`open-bricks`), Lizenz (`AGPL-3.0`), Python-Version (`3.10+`), Bioinformatik-Standards (`VCF 4.2 | gVCF`), Genom-Builds (`GRCh37 | GRCh38`), Teststatus (`115 passed`) und LLM-Kontext in englische und deutsche README integriert.
- **Pipeline-Architekturdiagramm**: Interaktives Mermaid-Flowchart in `README.md` und `README.de.md` ergänzt, das die 5 Stufen (Eingabe, Ingestion/Build-Erkennung, Multi-Source-Annotation, Quality Gate, Export) visualisiert.
- **LLM-Discoverability**: GFM Callout (`> [!TIP]`) für `llms.txt` in beiden READMEs verankert; `llms.txt` Prüfstempel auf `2026-08-14` und Ökosystem-Metadaten synchronisiert.

### Sicherheit / Security (2026-08-06)
- **Die Logdatei trägt keine Variantenkennungen mehr.** `MultiSinkLogger` schrieb
  jede Zeile wörtlich in `logfile_path` — also auch
  `[Cache] rs1801133 @ hg38 → chr1:11796321`. Auf der Konsole ist das richtig,
  dort sitzt die Person, deren Genom es ist; die Datei dagegen überlebt die
  Sitzung und geht in Bugreports mit. rsIDs und genomische Loci werden jetzt
  beim Schreiben redigiert (`redact_for_logfile`), Konsole und UI bleiben
  vollständig. Der Dateikopf weist auf die Redaktion hin.
  Bewusst eng gefasst: keine Entropie-Heuristik, die Zähler, Prozentwerte,
  Zeitstempel oder Pfade mitschwärzen und das Log unlesbar machen würde —
  `tests/test_logfile_redaction.py` prüft beide Richtungen. Schließt CodeQL
  `py/clear-text-logging-sensitive-data` (#2) und
  `py/clear-text-storage-sensitive-data` (#3).

### Hinzugefügt / Added
- `make_source_zip.py`: Source-ZIP-Builder für Linux und macOS. Erstellt ein portables Quellcode-Archiv mit allen Python-Quellen, Übersetzungen, optionalem Cython-Hotpath (.pyx), Tests und Dokumentation. Schließt Windows-Binaries (.pyd, .exe), generierte Caches und FASTA-Referenzgenome aus.
- `PACKAGING.md`: Vollständige Packaging-Dokumentation mit Optionen-Matrix (Windows EXE vs. Source-ZIP), Schritt-für-Schritt-Installationsanleitung für Linux/macOS, Cython-Fallback-Erläuterung und Hinweisen zu Annotationsdaten.
- `tests/test_source_packaging.py`: 14 automatisierte Tests für `make_source_zip.py` — Ausschlusslogik (.pyd/.exe/_index.pkl), Inklusionslogik (.pyx/.py/.json/.md), Versionslesung, ZIP-Erzeugung und ZIP-Inhalt.
- `tests/source_platform_smoke.py`: Plattform-Smoke für Linux und macOS — 7 Checks (Python-Version, Pflicht-Deps real importierbar, tkinter headless-safe, ttkbootstrap headless-tolerant, Hauptmodul mit Mocks ladbar, safe_float-Logik, VCF-Erkennung mit Fixture).
- `.github/workflows/source-platform-smoke.yml`: CI-Workflow für ubuntu-latest und macos-latest; installiert Kern-Deps (pip) und python3-tk (apt); führt Smoke explizit aus.
- `CODE_OF_CONDUCT.md` and `CONTRIBUTING.md` added as repository community files.
- Root application icon added for packaging and repository metadata.
- `llms.txt` added with machine-readable project context, search phrases, important files, and Research Use Only boundaries.

### Geändert / Changed
- `build_release.py` now builds via PyInstaller in `C:\_Local_DEV\codex_build\vfdistiller`, mirrors the finished EXE back to `dist\VFDistiller.exe`, and produces the versioned release ZIP from that local artifact.
- `build_exe.bat` added as a Windows build entrypoint so the project follows the current `.SOFTWARE` local-build workflow more directly.
- Source Platform Smoke CI now uses `actions/checkout@v6` and `actions/setup-python@v6`.
- `llms.txt` now records the 2026-06-11 hygiene check and audience context.
- README files now document the current GitHub-only distribution and repository privacy/ignore policy.
- README files now lead with clearer VCF/gVCF/23andMe/FASTA discoverability language, screenshot gallery entries, and local-first bioinformatics search phrases.
- README test instructions now clarify the split between deterministic pytest coverage and manual benchmark scripts.
- `.gitignore` now covers internal test locks, secrets, private keys, installer artifacts, and LLM control files.
- `.gitignore` now also covers active `LOCK*.txt` files and agent-internal `docs/superpowers/` implementation plans so coordination files stay local.
- Internal planning files such as `PORTIERUNGSPLAN.md`, `DECISIONS.md`, `TODO.md`, and `DONE.md` now stay local-only.
- `SECURITY.md` and `PRIVACY_POLICY.md` updated after the Microsoft Store withdrawal.
- `pytest.ini` now limits automated test collection to the maintained `tests/` suite.
- Downloaded Ensembl GTF annotation archives are no longer tracked and remain local via `.gitignore`.
- `START.bat` now prefers the local `dist\VFDistiller.exe` and falls back to the Python source entry point.
- German README/UI wording now uses real umlauts for touched end-user text.
- `.gitattributes` added for stable line endings and binary asset handling.
- Community workflows now use current `actions/stale@v10` and `actions/first-interaction@v3` actions.

### Behoben / Fixed
- Die primäre Arbeitsleiste verwendet für Start/Stop jetzt übersetzbare
  deutsche Aktionslabels und gibt Dateipfad, Dateiauswahl, AF-Schwelle,
  Start/Stop und CADD-Hervorhebung per fokussierbaren Tooltips Kontext.
- AF-Fetch-Endentscheidung nutzt jetzt das angereicherte Fetch-Ergebnis mit `meanAF_fetch_success`, damit validierte AF-None-Treffer nicht als ungeprüft klassifiziert und aus der Anzeige gefiltert werden.
- Die kompakten Symbolbuttons für `⟳` sowie die `📂`-Genlistenlader exponieren jetzt Tooltip-Kontext auch bei Tastaturfokus, statt sich fast nur auf das Icon zu verlassen. Die Haupt-UI bleibt kompakt; Screenreader-nahe und keyboard-orientierte Nutzung bekommt jedoch klarere Hilfetexte.
- `StreamingFastaToGVCF.convert_streaming_gvcf` und `convert_streaming_variants_only`: Fehlende `encoding="utf-8"`-Parameter beim Öffnen von FASTA-Eingabe und VCF-Ausgabe. Auf Windows wurde der cp1252-Standard verwendet, was zu `UnicodeDecodeError` führte, wenn Dateipfade oder `##reference`-Header Nicht-ASCII-Zeichen (z.B. Umlaute) enthielten. Betroffen war die Write-Seite eines Lese/Schreib-Paars, dessen Read-Seite bereits in Block 5b auf `encoding="utf-8"` gesichert wurde.
- `StreamingFastaToGVCF.detect_build_from_fasta` und `load_fasta`: Fehlende `encoding="utf-8"`-Parameter beim Lesen von FASTA-Dateien auf denselben Codepfaden.
- Technisches Issue-Register auf den aktuellen GitHub-Stand synchronisiert: Die im Hauptprogramm dokumentierten Bare-`except:`-Stellen sind seit Commit `7665133` behoben; `origin/main` enthält in `Variant_Fusion_pro_V17.py` keinen Treffer. Bare-`except:`-Stellen im separaten optionalen Cython-Benchmark bleiben ausdrücklich außerhalb dieses Fix-Claims.
- Release packaging no longer references a non-existent `README/licenses/LICENSE.de.txt`; the documented license tree now matches the shipped files.
- Removed a stale inline comment that incorrectly suggested the top-level `pickle` import was missing or only local-only, even though cache serialization uses it.
- Removed stale contributing-template placeholders and replaced the missing CLA reference with DCO guidance.
- Performance benchmark scripts no longer expose a `test_correctness()` function that pytest can miscollect as a fixture-based test.
- Cython accelerator console logging no longer crashes benchmark scripts on Windows cp1252 terminals.
- Performance benchmark scripts now tolerate Windows console encodings for their own status output.
- LightDB lookups now close SQLite connections in a `finally` block, preventing file-lock leaks on cursor or setup failures.
- LightDB lookup setup also handles `sqlite3.connect()` failures without masking the original fallback result.

### Entfernt / Removed
- Removed `PORTIERUNGSPLAN.md` from the public repository index; the Linux/macOS desktop portability plan remains a local planning file.
- Removed the planned Web/PWA companion track from the active porting strategy.
- Removed stale internal cleanup concept notes from the public README documentation tree.

## [1.0.0] - YYYY-MM-DD

### Hinzugefügt / Added
- Erstveröffentlichung / Initial release
