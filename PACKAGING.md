# Packaging Guide — VFDistiller

Dieses Dokument beschreibt alle Build- und Packaging-Optionen für VFDistiller.

---

## Windows — EXE-Release (Empfohlen für Endnutzer)

**Script:** `build_release.py`

Erstellt eine selbstständige Windows-EXE via PyInstaller und verpackt sie als Release-ZIP.

```bash
# Vollständiger Build (EXE + ZIP)
python build_release.py

# Nur ZIP aus bestehendem dist/
python build_release.py --skip-exe

# Build-Artefakte aufräumen
python build_release.py --clean
```

**Ausgabe:** `releases/VFDistiller_<Version>_<Datum>.zip`

**Enthält:** EXE, README, Konfigurationsvorlage, Lizenzen, Übersetzungen, Annotationsdaten (GTF), gnomAD-Download-Tool.

**Voraussetzungen:**
- Python 3.10+
- `pip install pyinstaller`
- `VFDistiller.spec` muss vorhanden sein

---

## Linux / macOS — Source-ZIP

**Script:** `make_source_zip.py`

Erstellt ein Source-ZIP mit allen Python-Quellen, Dokumentation und optionalem Cython-Hotpath.

```bash
# Source-ZIP erstellen
python make_source_zip.py

# Vorhandene Source-ZIPs entfernen
python make_source_zip.py --clean
```

**Ausgabe:** `releases/VFDistiller_<Version>_source_<Datum>.zip`

### Inhalt des Source-ZIP

| Kategorie | Dateien |
|---|---|
| Python-Quellen | `Variant_Fusion_pro_V17.py`, `translator.py`, `translator_patch.py`, `manage_translations.py`, `lightdb_index_worker.py` |
| Abhängigkeiten | `requirements.txt` |
| Übersetzungen | `locales/translations.json` |
| Cython-Hotpath | `cython_hotpath/*.pyx`, `cython_hotpath/setup.py` (falls vorhanden) |
| Tests | `tests/` (alle) |
| Dokumentation | `README.md`, `README.de.md`, `ARCHITECTURE.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `PRIVACY_POLICY.md`, `llms.txt` |
| Lizenzen | `LICENSE`, `NOTICE`, `THIRD_PARTY_LICENSES.txt` |
| Konfiguration | `variant_fusion_settings.json.example` |
| Hilfsprogramme | `Get gnomAD DB light.py`, `VFDistiller.ico` |
| Build-Skripte | `make_source_zip.py`, `build_release.py` |

### Nicht enthalten (und warum)

| Ausgeschlossen | Grund |
|---|---|
| `*.pyd` | Windows-spezifische Cython-Binaries, nicht portierbar |
| `*.exe` | Windows-Executables |
| `*_index.pkl` | Generierte Annotations-Caches (werden zur Laufzeit erzeugt) |
| `data/annotations/*.gtf.gz` | Referenzgenome (~85 MB), separat beziehen (siehe unten) |
| `Homo_sapiens.GRCh3*.fa*` | FASTA-Referenzgenome (sehr groß), lokal bereitstellen |
| `variant_fusion.sqlite`, `cache.json` | Nutzerdaten |
| `variant_fusion_settings.json` | Nutzerkonfiguration (`.example`-Vorlage ist enthalten) |
| `.vf_instance.lock`, `distiller_debug.log` | Laufzeit-Artefakte |
| `KNOWN_ISSUES.md`, `RELEASE_PLAN.md` u. a. | Interne Entwicklungsdateien |
| `START.bat` | Windows-spezifisches Startskript |

### Installation aus Source-ZIP (Linux / macOS)

```bash
# 1. ZIP entpacken
unzip VFDistiller_V17_source_*.zip
cd VFDistiller_V17_source/

# 2. Virtuelle Umgebung anlegen
python3 -m venv .venv
source .venv/bin/activate

# 3. Abhängigkeiten installieren
pip install -r requirements.txt

# 4. Annotationsdaten beziehen (optional, für Annotations-Feature)
#    Aus dem Windows-Release-ZIP extrahieren:  data/annotations/GRCh37.gtf.gz und GRCh38.gtf.gz
#    oder vom gnomAD-Download-Tool herunterladen:
python "Get gnomAD DB light.py"

# 5. Starten
python Variant_Fusion_pro_V17.py
```

### Optionaler Cython-Hotpath (Linux / macOS)

Der `cython_hotpath/`-Ordner enthält optionale `.pyx`-Quellen für Performance-kritische Codepfade.
Falls vorhanden, kann der Hotpath lokal gebaut werden:

```bash
# Cython installieren
pip install cython

# Hotpath bauen (erzeugt .so auf Linux/macOS statt .pyd auf Windows)
cd cython_hotpath/
python setup.py build_ext --inplace
```

Ohne Cython-Build läuft VFDistiller vollständig in reinem Python (automatischer Fallback).

### Tests ausführen

```bash
pip install pytest
pytest tests/ -v
```

---

## Optionen-Matrix

| Option | Windows EXE | Source-ZIP |
|---|---|---|
| Endnutzer (keine Python-Kenntnisse) | ✅ | ❌ |
| Entwickler / Power-User | — | ✅ |
| Linux | ❌ | ✅ |
| macOS | ❌ | ✅ |
| Cython-Hotpath nutzbar | ✅ (vorgebaut) | ✅ (selbst bauen) |
| Annotationsdaten enthalten | ✅ | ❌ (separat) |
| Größe | ~80 MB | ~1 MB |
| Selbstständig (kein Python nötig) | ✅ | ❌ |

---

## Cython-Fallback-Dokumentation

VFDistiller verwendet einen optionalen Cython-Hotpath für performance-kritische Operationen.
Der Fallback-Mechanismus ist vollständig transparent:

1. **Beim Start** versucht VFDistiller, die kompilierte Cython-Extension zu importieren.
2. **Falls nicht vorhanden**, wird automatisch die reine Python-Implementierung geladen.
3. **Kein Benutzereingriff nötig** — alle Features sind in beiden Modi verfügbar.

```python
# Internes Fallback-Muster (vereinfacht)
try:
    from cython_hotpath import vcf_parser  # schnell
except ImportError:
    from vcf_parser_pure import vcf_parser  # reines Python
```

Der Unterschied ist nur bei sehr großen VCF-Dateien (>1 GB) spürbar.

---

*Letzte Aktualisierung: 2026-06-14*
