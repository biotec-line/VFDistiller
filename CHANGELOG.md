# Changelog / Änderungsprotokoll

Alle wesentlichen Änderungen an diesem Projekt werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [Unreleased]

### Hinzugefügt / Added
- `pyproject.toml`: Standardisierter PEP 621-Projekt-Manifest mit Abhängigkeiten, Meta-Informationen, URLs, Keywords und Pytest-Konfiguration.
- Shields.io-Badges für Lizenz (AGPL-3.0-or-later), Python-Versionen, Testsuite-Status (42 bestanden), Plattform-Matrix und Research Use Only-Status in `README.md` und `README.de.md`.
- Mermaid-Systemarchitekturdiagramm zur Visualisierung der lokalen Datenfluss-Pipeline (Eingaben -> Lokaler Verarbeitungs-Kern & Cython Hotpath -> Multi-Source Annotations-Engine -> GUI & Export-Oberfläche) in `README.md` und `README.de.md`.
- GFM `> [!NOTE]`-Callout zur klaren Abgrenzung lokaler KI- und Datenschutzgrenzen für genetische Variantendaten.
- `MARKETING-LOG.txt`: Dokumentation der Sichtbarkeits- und Marketingmaßnahmen, Empfehlungen für EDAM-Katalogisierung (bio.tools) und Repositoriendaten.
- `make_source_zip.py`: Source-ZIP-Builder für Linux und macOS. Erstellt ein portables Quellcode-Archiv mit allen Python-Quellen, Übersetzungen, optionalem Cython-Hotpath (.pyx), Tests und Dokumentation. Schließt Windows-Binaries (.pyd, .exe), generierte Caches und FASTA-Referenzgenome aus.
- `PACKAGING.md`: Vollständige Packaging-Dokumentation mit Optionen-Matrix (Windows EXE vs. Source-ZIP), Schritt-für-Schritt-Installationsanleitung für Linux/macOS, Cython-Fallback-Erläuterung und Hinweisen zu Annotationsdaten.
- `tests/test_source_packaging.py`: 14 automatisierte Tests für `make_source_zip.py` — Ausschlusslogik (.pyd/.exe/_index.pkl), Inklusionslogik (.pyx/.py/.json/.md), Versionslesung, ZIP-Erzeugung und ZIP-Inhalt.
- `tests/source_platform_smoke.py`: Plattform-Smoke für Linux und macOS — 7 Checks (Python-Version, Pflicht-Deps real importierbar, tkinter headless-safe, ttkbootstrap headless-tolerant, Hauptmodul mit Mocks ladbar, safe_float-Logik, VCF-Erkennung mit Fixture).
- `.github/workflows/source-platform-smoke.yml`: CI-Workflow für ubuntu-latest und macos-latest; installiert Kern-Deps (pip) und python3-tk (apt); führt Smoke explizit aus.
- `CODE_OF_CONDUCT.md` and `CONTRIBUTING.md` added as repository community files.
- Root application icon added for packaging and repository metadata.
- `llms.txt` added with machine-readable project context, search phrases, important files, and Research Use Only boundaries.

### Geändert / Changed
- `llms.txt`: Timestamp auf `2026-07-27` und Testergebnisse verifiziert (42/42 Pytest-Tests grün). [G 2026-07-27]
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
- `BackgroundMaintainer` verwendet getrennte AF- und Vollannotations-
  Staleness-Schwellen aus `Config.STALE_DAYS_AF` und `Config.STALE_DAYS_FULL`.
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
