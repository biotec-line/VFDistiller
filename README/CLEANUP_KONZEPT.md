# VFDistiller - Verzeichnis-Aufräum-Konzept

**Stand:** 20.01.2026
**Autor:** Claude (Code-Analyse)
**Ziel:** Root-Verzeichnis aufräumen, klare Struktur schaffen

---

## 1. Ist-Zustand Analyse

### Root-Verzeichnis (~11 GB, 40+ Einträge)

```
B2 VFDistiller/
├── __pycache__/                    # Python Cache
├── .claude/                        # Claude IDE Config
├── _alt/                           # Alte Versionen (V3-V12)
├── _OUTPUT EXE/                    # Build-Artefakte
├── _persönlich/                    # Persönliche Daten
├── _WARTUNG/                       # Wartungs-Tools + alte Versionen
├── converted_23andme_vcfs/         # Konvertierte VCFs (~75 MB)
├── cython_hotpath/                 # Cython-Module
├── data/                           # Datenbanken (~100 GB!)
├── FASTQ zu FASTA/                 # Konverter-Tools
├── ICO/                            # Icons
├── locales/                        # Übersetzungen
├── logs/                           # Log-Dateien
├── README/                         # Dokumentation
│
├── Homo_sapiens.GRCh37.dna...fa    # 3.0 GB - FASTA Referenz
├── Homo_sapiens.GRCh38.dna...fa    # 3.0 GB - FASTA Referenz
├── variant_fusion.sqlite           # 4.6 GB - Haupt-Datenbank
├── dbnsfp_light.db                 # 0 Bytes (leer)
├── cache.json                      # 1 MB
├── COMPLETE_PROJECT_CONTEXT.txt    # 87 MB (!)
│
├── Variant_Fusion_pro_V14.py       # 900 KB - AKTUELLE Version
├── Variant_Fusion_pro_V15.py       # 925 KB - NEUESTE Version
├── translator.py                   # 484 B
├── translator_patch.py             # 620 B
├── manage_translations.py          # 2.5 KB
├── lightdb_index_worker.py         # 3.3 KB
├── test_performance.py             # 12 KB
├── Get gnomAD DB light.py          # 2.6 KB
│
├── AUFGABEN.txt                    # Aufgaben-Liste
├── START.bat                       # Starter
├── VFDistiller.spec                # PyInstaller Spec
├── lightdb_config.json             # DB Config
├── variant_fusion_settings.json    # App Settings
├── distiller_debug.log             # Debug Log (610 KB)
└── variant_fusion.log              # Log
```

### Probleme

1. **Riesige Dateien im Root:**
   - 2x FASTA-Referenzen (je 3 GB) → gehören in `data/reference/`
   - variant_fusion.sqlite (4.6 GB) → gehört in `data/`
   - COMPLETE_PROJECT_CONTEXT.txt (87 MB) → sollte archiviert werden

2. **Verstreute Python-Dateien:**
   - `translator.py`, `translator_patch.py` → gehören in `locales/` oder `lib/`
   - `lightdb_index_worker.py` → gehört in `data/` oder `tools/`
   - `test_performance.py` → Duplikat von `cython_hotpath/test_performance.py`

3. **Unklare Ordner-Namen:**
   - `_alt` vs `_WARTUNG` → beide enthalten alte Versionen
   - `FASTQ zu FASTA` → Leerzeichen im Namen

4. **Duplizierte Dateien:**
   - `Get gnomAD DB light.py` existiert in Root UND in `data/`
   - `lightdb_config.json` existiert in Root UND in `data/`
   - `lightdb_index_worker.py` existiert in Root UND in `data/`

5. **Logs verstreut:**
   - `distiller_debug.log` im Root
   - `variant_fusion.log` im Root
   - `logs/` Ordner existiert auch

---

## 2. Soll-Struktur (Vorschlag)

```
B2 VFDistiller/
│
├── src/                            # NEU: Haupt-Quellcode
│   ├── Variant_Fusion_pro_V15.py   # Aktuelle Version
│   ├── af_none_treatment.py        # (falls existiert)
│   └── __init__.py
│
├── lib/                            # NEU: Hilfsmodule
│   ├── translator.py
│   ├── translator_patch.py
│   └── __init__.py
│
├── data/                           # Datenbanken (existiert)
│   ├── reference/                  # NEU: Referenz-Genome
│   │   ├── Homo_sapiens.GRCh37.dna.primary_assembly.fa
│   │   ├── Homo_sapiens.GRCh37.dna.primary_assembly.fa.fai
│   │   ├── Homo_sapiens.GRCh38.dna.primary_assembly.fa
│   │   └── Homo_sapiens.GRCh38.dna.primary_assembly.fa.fai
│   ├── gnomad_light.db             # (existiert)
│   ├── variant_fusion.sqlite       # Verschieben aus Root
│   └── annotations/                # (existiert)
│
├── tools/                          # NEU: Hilfsskripte
│   ├── Get_gnomAD_DB_light.py      # Umbenannt (keine Leerzeichen)
│   ├── lightdb_index_worker.py
│   ├── manage_translations.py
│   └── test_performance.py
│
├── config/                         # NEU: Konfiguration
│   ├── lightdb_config.json
│   ├── variant_fusion_settings.json
│   └── cache.json
│
├── logs/                           # Log-Dateien (existiert)
│   ├── distiller_debug.log         # Verschieben aus Root
│   └── variant_fusion.log          # Verschieben aus Root
│
├── locales/                        # Übersetzungen (existiert)
│   └── translations.json
│
├── assets/                         # NEU: Statische Ressourcen
│   └── ICO/                        # Icons verschieben
│       └── ICO.ico
│
├── cython_hotpath/                 # Cython-Module (existiert)
│
├── docs/                           # NEU: Dokumentation
│   ├── README.md
│   ├── README.de.md
│   ├── CHANGELOG_V12.md
│   └── ...
│
├── archive/                        # NEU: Archiv (statt _alt + _WARTUNG)
│   ├── versions/                   # Alte Versionen
│   │   ├── V3/
│   │   ├── V4/
│   │   └── ...
│   ├── wartung/                    # Wartungs-Tools
│   └── context/                    # Alte Context-Dateien
│       └── COMPLETE_PROJECT_CONTEXT.txt
│
├── output/                         # NEU: Ausgaben
│   ├── exe/                        # Build-Artefakte (von _OUTPUT EXE)
│   └── converted_vcfs/             # Konvertierte VCFs
│
├── AUFGABEN.txt                    # Bleibt im Root
├── START.bat                       # Bleibt im Root
├── VFDistiller.spec                # Bleibt im Root
└── .gitignore                      # NEU: Git-Ignore
```

---

## 3. Notwendige Code-Anpassungen

### 3.1 Import-Pfade in `Variant_Fusion_pro_V15.py`

```python
# ALT (Zeile ~9605):
from af_none_treatment import AfNoneTreatmentManager

# NEU:
from lib.af_none_treatment import AfNoneTreatmentManager
# ODER: sys.path.insert(0, 'lib') bevor Import
```

```python
# ALT (Zeile ~18932-18933):
from translator import Translator
from translator_patch import patch_widgets

# NEU:
from lib.translator import Translator
from lib.translator_patch import patch_widgets
```

### 3.2 Pfad-Konstanten anpassen

```python
# ALT (geschätzt basierend auf Dateistruktur):
FASTA_PATH_37 = "Homo_sapiens.GRCh37.dna.primary_assembly.fa"
FASTA_PATH_38 = "Homo_sapiens.GRCh38.dna.primary_assembly.fa"

# NEU:
FASTA_PATH_37 = "data/reference/Homo_sapiens.GRCh37.dna.primary_assembly.fa"
FASTA_PATH_38 = "data/reference/Homo_sapiens.GRCh38.dna.primary_assembly.fa"
```

```python
# ALT:
DB_PATH = "variant_fusion.sqlite"

# NEU:
DB_PATH = "data/variant_fusion.sqlite"
```

```python
# ALT:
LIGHTDB_CONFIG = "lightdb_config.json"

# NEU:
LIGHTDB_CONFIG = "config/lightdb_config.json"
```

### 3.3 Settings-Pfade

```python
# ALT:
SETTINGS_FILE = "variant_fusion_settings.json"

# NEU:
SETTINGS_FILE = "config/variant_fusion_settings.json"
```

### 3.4 Log-Pfade

```python
# ALT:
LOG_FILE = "distiller_debug.log"

# NEU:
LOG_FILE = "logs/distiller_debug.log"
```

### 3.5 Icon-Pfad

```python
# ALT:
ICON_PATH = "ICO/ICO.ico"

# NEU:
ICON_PATH = "assets/ICO/ICO.ico"
```

---

## 4. Migrations-Strategie

### Phase 1: Vorbereitung (Risiko: Niedrig)
1. Neue Ordner erstellen (`src/`, `lib/`, `tools/`, `config/`, `assets/`, `docs/`, `archive/`, `output/`)
2. `.gitignore` erstellen (falls Git verwendet wird)
3. Backup der aktuellen Struktur

### Phase 2: Dateien verschieben (Risiko: Mittel)
1. FASTA-Dateien → `data/reference/`
2. Logs → `logs/`
3. Config-Dateien → `config/`
4. Icons → `assets/ICO/`
5. Dokumentation → `docs/`
6. Alte Versionen → `archive/versions/`
7. `_WARTUNG` Inhalte → `archive/wartung/`
8. `_alt` Inhalte → `archive/versions/`

### Phase 3: Code-Anpassungen (Risiko: Hoch)
1. Alle Pfad-Konstanten in V15 anpassen (siehe Abschnitt 3)
2. Import-Pfade anpassen
3. START.bat anpassen
4. VFDistiller.spec anpassen

### Phase 4: Test & Validierung
1. App starten und alle Funktionen testen
2. Prüfen ob alle Dateien gefunden werden
3. Prüfen ob Datenbank-Zugriff funktioniert
4. Prüfen ob FASTA-Lookup funktioniert

---

## 5. Risiko-Bewertung

| Aktion | Risiko | Auswirkung bei Fehler |
|--------|--------|----------------------|
| Ordner erstellen | Niedrig | Keine |
| Logs verschieben | Niedrig | Nur neue Logs betroffen |
| Icons verschieben | Niedrig | Icon fehlt (kosmetisch) |
| Config verschieben | Mittel | App startet nicht |
| FASTA verschieben | Hoch | Annotation bricht ab |
| DB verschieben | Hoch | App startet nicht |
| Import-Pfade ändern | Hoch | App startet nicht |

---

## 6. Empfehlung

**Priorität: NIEDRIG** - Aufräumen ist "nice to have", aber kein kritisches Problem.

### Option A: Minimales Aufräumen (Empfohlen)
Nur die offensichtlichsten Probleme lösen:
1. FASTA-Dateien → `data/reference/` verschieben
2. Logs → `logs/` verschieben
3. `COMPLETE_PROJECT_CONTEXT.txt` → archivieren oder löschen

**Aufwand:** ~1-2 Stunden
**Risiko:** Niedrig

### Option B: Vollständiges Refactoring
Komplette Umstrukturierung wie oben beschrieben.

**Aufwand:** ~4-8 Stunden + umfangreiches Testen
**Risiko:** Mittel-Hoch

### Option C: Nichts tun
Aktuelle Struktur beibehalten.

**Aufwand:** 0
**Risiko:** 0
**Nachteil:** Unübersichtlichkeit bleibt

---

## 7. Sofort löschbare Dateien

Diese Dateien können wahrscheinlich gelöscht werden:

| Datei | Größe | Grund |
|-------|-------|-------|
| `dbnsfp_light.db` | 0 B | Leer, nie befüllt |
| `cache.json` | 1 MB | Kann neu generiert werden |
| `COMPLETE_PROJECT_CONTEXT.txt` | 87 MB | Alter Context-Dump |
| `converted_23andme_vcfs/*.vcf` | ~75 MB | Test-Ausgaben (wenn nicht benötigt) |

**Potenzielle Ersparnis:** ~160 MB (ohne die 6 GB FASTA)

---

## 8. Nächste Schritte

1. [ ] Entscheidung: Option A, B oder C?
2. [ ] Backup erstellen
3. [ ] Änderungen durchführen
4. [ ] Testen
5. [ ] Alte Backups nach erfolgreichem Test löschen
