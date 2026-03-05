# VFDistiller — Architektur-Dokumentation

Entwickler-Referenz fuer die interne Architektur von Variant Fusion Pro V17.

## Ueberblick

VFDistiller ist eine monolithische Single-File-Anwendung (`Variant_Fusion_pro_V17.py`, ~25.000 Zeilen) mit optionalen Cython-Modulen. Die Architektur folgt einem Manager-Pattern mit zentralen Koordinations-Klassen.

```
App (GUI, tkinter/ttkbootstrap)
 ├── Flag_and_Options_Manager .... Zentrale Settings-Verwaltung
 ├── MainFilterGate .............. Zentrale Filter-Entscheidungen
 │    ├── CodingFilter ........... Protein-Coding-Filter
 │    └── AfNoneTreatmentManager . AF-None-Policy
 ├── QualityManager .............. VCF-Record-Level-Filter
 ├── Distiller ................... Pipeline-Orchestrierung
 │    ├── AFFetchController ...... Multi-API-AF-Fetching
 │    ├── VCFBuffer .............. Gepufferte DB-Writes
 │    ├── PipelineProgress ....... Fortschritts-Tracking
 │    └── EmitQueue .............. GUI-Update-Queue
 ├── VariantDB ................... SQLite-Persistenz
 ├── GeneAnnotator ............... Gen-Symbol-Lookup
 ├── BackofficeCrawler ........... System-Tray + Hintergrund-Steuerung
 └── BackgroundMaintainer ........ Leerlauf-Annotation
```

## Datenfluss

```
GUI (tk.Vars)
  │
  ▼
Flag_and_Options_Manager.sync_from_gui()
  │
  ▼
FlagManager ──► MainFilterGate ──► Distiller Pipeline
                                        │
                                   VariantDB (SQLite)
                                        │
                                   _apply_af_filter_final()
                                        │
                                   Export (VCF / CSV / XLSX / PDF)
```

## Pipeline-Phasen

Die Hauptpipeline wird durch `Distiller.process_file()` gestartet und durchlaeuft folgende Phasen:

```
process_file(path, build)
  ├── _phase_vcf_scan
  │     Liest VCF/gVCF, wendet Quality-Filter an, sammelt Variant-Keys.
  │     Nutzt Cython vcf_parser (8x Speedup) falls verfuegbar.
  │     Pre-Filter: QUAL, FILTER=PASS, DP, HomRef.
  │
  ├── _start_streaming_pipeline
  │     Startet Pipeline-Thread fuer nachfolgende Phasen.
  │
  ├── _phase_af_fetch_streaming
  │     Holt Allele-Frequencies von mehreren APIs parallel:
  │     - gnomAD LightDB (lokal, bevorzugt)
  │     - MyVariant.info (async, batch)
  │     - gnomAD GraphQL API
  │     - Ensembl VEP
  │     - ALFA (NCBI)
  │     - TOPMed/BRAVO
  │     Gewichtete Verteilung via AFFetchController.
  │
  ├── _phase_full_annotation_streaming
  │     Volle Annotation via MyVariant.info:
  │     ClinVar, CADD, Consequence, Phenotypes, etc.
  │
  ├── _phase_gene_annotation_streaming
  │     Gen-Symbole via GeneAnnotator (lokaler GTF-Index).
  │
  ├── _phase_rsid_fill_streaming
  │     Fehlende RSIDs via NCBI Allele-Registry ergaenzen.
  │
  ├── _phase_missing_fill_streaming
  │     Fehlende ClinVar/Consequence-Felder nachfuellen.
  │
  └── _phase_alphagenome_streaming
        AlphaGenome Pathogenicity-Scores (erfordert API-Key).
```

## Klassen-Referenz

### Config

Zentrale Konfigurationskonstanten. Class-Level-Attribute, kein Instanziieren noetig.

- `get_fasta_path(build)` — FASTA-Pfad fuer GRCh37/38
- `validate()` — Prueft kritische Konfiguration
- `print_settings()` — Loggt aktuelle Settings

### ResourceManager (Singleton)

Verwaltet externe Ressourcen-Pfade (FASTA, GTF, Datenbanken). Persistiert in `resources_config.json`.

- `get(key, absolute=True)` — Ressourcen-Pfad abrufen
- `get_fasta_path(build)` — FASTA fuer Build
- `register(key, path)` — Neue Ressource registrieren
- `refresh()` — Alle Pfade neu pruefen
- `heal(key)` — Fehlende Ressource suchen/reparieren

### Flag_and_Options_Manager

Speichert alle GUI-Einstellungen thread-safe. Wird vor Pipeline-Start mit `sync_from_gui(app)` synchronisiert.

**Getter:** `get_af_threshold()`, `get_include_none()`, `get_filter_pass_only()`, `get_qual_threshold()`, `get_only_protein_coding()`, `get_stale_days()`, `get_alphagenome_key()`, `get_af_none_policy()`, `get_cadd_highlight_threshold()`

**Setter:** `set_af_threshold(val)`, `set_include_none(val)`, `set_only_protein_coding(val)`, `set_af_none_policy(policy)`, `set_stale_days(days)`, `set_alphagenome_key(key)`

**Batch:** `get_all_flags()`, `set_from_dict(flags)`

### MainFilterGate

Zentrale Filterlogik. Entscheidet ob eine Variante angezeigt wird.

- `check_variant(key, af_value, fetch_status)` — Gibt `(passed: bool, reason: str, data: dict)` zurueck
- `check_batch(variants)` — Batch-Pruefung
- `passes(key, af_value)` — Schnellpruefung (bool)

**SubGates:**
- `CodingFilter` — Filtert auf Protein-Coding-Gene via GeneAnnotator
- `AfNoneTreatmentManager` — Policy fuer Varianten ohne AF-Wert (Presets: strict, moderate, permissive, research)

### QualityManager

VCF-Record-Level-Filter (unabhaengig von MainFilterGate).

- `passes(record)` — Prueft QUAL, FILTER, DP, HomRef
- `set_preset(name)` — Vordefinierte Presets laden
- `set_custom_settings(...)` — Individuelle Schwellen

Presets: strict, moderate, permissive, lenient, custom.

### Distiller

Pipeline-Orchestrierung. Kernklasse fuer die Variantenverarbeitung.

**Entry Points:**
- `process_file(path, build, ...)` — Haupteinstieg, erkennt Format automatisch
- `_distill_vcf(vcf_path, build, ...)` — Direkte VCF-Verarbeitung

**Format-Handler:**
- `_process_23andme(path, build)` — 23andMe-Rohdaten via Converter
- `_process_fasta(path, build)` — FASTA via StreamingFastaToGVCF
- `_process_fastq(path, build)` — FASTQ (experimentell)

**Filter:**
- `_apply_af_filter_final(key, val, af_threshold, include_none)` — Finale AF-Entscheidung
- `_validate_af_in_cache(key, row)` — AF-Pruefung gegen DB-Cache

**Properties:**
- `display_keys` — Set der aktuell angezeigten Variant-Keys
- `done_variants` / `total_variants` — Fortschrittszaehler

### AFFetchController

Multi-API AF-Fetching mit adaptiver Lastverteilung.

- `job_collector_and_distributor(keys, build, workers)` — Verteilt Keys auf APIs
- `result_collector_and_merger(keys, results)` — Fusioniert Ergebnisse
- `_compute_weights()` — Gewichte basierend auf API-Performance
- `apply_success_reward(api)` / `apply_timeout_penalty(api)` — Adaptive Gewichtung

**Circuit Breaker:** Jede API hat einen eigenen CircuitBreaker der nach mehreren Fehlern die API temporaer deaktiviert.

**ThroughputTuner:** Passt Worker-Anzahl dynamisch an CPU-Last an.

### VariantDB

SQLite-Persistenz fuer Varianten-Daten.

**Schema:** `variants` Tabelle mit Composite-Key `(chrom, pos, ref, alt, build)`.

**Wichtige Methoden:**
- `upsert_variant(key, fields)` — Einzelnes Upsert
- `upsert_variants_bulk(records)` — Batch-Upsert (10x schneller)
- `get_variant(key)` — Einzelnes Lookup
- `get_variants_bulk(keys)` — Batch-Lookup
- `select_for_export(build, af_threshold, include_none)` — Export-Query
- `for_background_priorities(...)` — Keys fuer Hintergrund-Wartung

**Thread-Safety:** Jeder Thread erhaelt eigene Connection via `threading.local()`.

### VCFBuffer

Gepufferte Batch-Writes in die VariantDB.

- `add(key, update, priority)` — Variant in Buffer aufnehmen
- `flush(force_priority)` — Buffer in DB schreiben
- Priority-Queue: Hoch-priorisierte Updates werden bevorzugt geflusht

### EmitQueue

GUI-Update-Queue mit Batch-Flush und Throttling.

- `add(key)` — Key fuer GUI-Update vormerken
- `flush()` — Alle ausstehenden Updates an GUI senden
- `discard(key)` — Key aus Queue entfernen

### GeneAnnotator

Lokaler Gen-Symbol-Lookup via GTF-Annotationsdaten.

- `annotate_variant(chrom, pos, build)` — Gen-Symbol fuer Position
- `annotate_batch(variants)` — Batch-Annotation
- Verwendet `IntervalTree` fuer schnelle Positionssuche
- Cache: Vorberechneter Index wird als `.pkl` gespeichert

### FetchStatusManager (Static)

Kodiert den API-Fetch-Status als Integer (3-Bit-Encoding: gnomAD, ExAC, 1KG).

- `status_label(code)` — Menschenlesbares Label
- `is_success(code)` / `is_failure(code)` — Status-Pruefung
- `classify_af_status(af, last_fetch, fetch_status, stale_days)` — AF-Klassifikation

### LightDBGnomADManager

Verwaltet die lokale gnomAD LightDB (SQLite, ~2 GB).

- `ensure_lightdb(auto_download)` — Download/Update pruefen
- `lookup_variants_bulk(keys, batch_size)` — Schnelle AF-Lookups
- `start_index_worker()` — Hintergrund-Indexierung starten

### FastaValidator

Validiert Varianten gegen Genomreferenz (FASTA).

- `validate_variant(chrom, pos, ref, alt, build)` — Einzelvalidierung
- `validate_batch(variants, build)` — Batch mit Shift-Detection
- `needs_validation(ref, alt)` — Prueft ob Validierung noetig (SNVs werden uebersprungen im non-strict Modus)

**Shift-Detection:** Erkennt systematische +1/-1 Positionsverschiebungen zwischen Builds.

### BackgroundMaintainer

Laedt fehlende Annotationen im Leerlauf nach.

- `start()` / `stop()` / `pause()` / `resume()` — Lifecycle
- `run_forever()` — Endlosschleife fuer Hintergrund-Tasks
- `automatic_fetch_decission_and_processing_unit(...)` — Entscheidet welche Varianten nachgeladen werden

Pausiert automatisch wenn die Hauptpipeline aktiv ist.

### BackofficeCrawler

System-Tray-Integration und Steuerung des BackgroundMaintainer.

- Zeigt Tray-Icon mit Status (gruen/gelb/rot)
- Kontextmenue: Pause, Resume, Open App

### Konverter

**convert_23andme_to_vcf** — Konvertiert 23andMe-Rohdaten zu VCF:
- Automatische Build-Erkennung
- RSID-Lookup via NCBI mit adaptivem Parallel-Fetch
- PAR-Region-Handling (Pseudoautosomale Regionen)

**StreamingFastaToGVCF** — Konvertiert FASTA zu gVCF:
- Build-Erkennung aus FASTA-Header
- Streaming-Modus fuer grosse Dateien

**FASTQmap** — FASTQ-Mapping (experimentell):
- k-mer-basiertes Alignment
- Indel-Detection via Smith-Waterman

### PipelineProgress

Tracking fuer alle Pipeline-Phasen mit ETA-Berechnung.

- `start_pipeline(total)` / `complete_pipeline()` — Lifecycle
- `start_phase(name)` / `update_phase(name, count)` / `complete_phase(name)` — Phasen-Tracking
- `percent()` — Gesamtfortschritt
- `eta()` — Geschaetzte Restzeit

### AlphaGenomeScorer

Integration mit Google AlphaGenome API fuer Pathogenicity-Scores.

- `score_batch(variants, logger)` — Batch-Scoring
- Erfordert API-Key und `numpy` + `alphagenome` Package

## Performance-Architektur

### Cython Hot-Path

Optionale C-kompilierte Module in `cython_hotpath/`:

| Modul | Funktion | Speedup |
|---|---|---|
| `vcf_parser.pyx` | Tab-Splitting mit `strchr()`, atoi/atof | 8x |
| `af_validator.pyx` | Direct C-float Casts | 100x |
| `key_normalizer.pyx` | chr-Stripping, Case-Normalisierung | 25x |
| `fasta_lookup.pyx` | mmap + C-Level String-Suche | 100x |

**Fallback-Logik:** `CythonAccelerator` in `cython_hotpath/__init__.py` probiert Cython-Import, faellt auf Python zurueck.

### SQLite-Optimierungen

- Batch-Inserts via `upsert_variants_bulk()` (bis zu 500 pro Batch)
- WAL-Modus fuer parallele Reads/Writes
- Thread-lokale Connections
- Annotation-Cache mit deferred Flush

### Async HTTP

- `aiohttp` fuer paralleles API-Fetching (bis zu 8 Worker)
- Adaptive Gewichtung: Schnelle APIs bekommen mehr Keys
- Circuit Breaker pro API (3 Failures = 60s Pause)
- Rate-Limiting per API konfigurierbar

### Threading-Modell

```
Main Thread (GUI)
  ├── Pipeline Thread (Distiller._start_streaming_pipeline)
  │    ├── AF-Fetch Workers (asyncio event loop)
  │    └── VCFBuffer Flush Thread
  ├── BackgroundMaintainer Thread
  ├── LightDB Index Worker (subprocess)
  └── Log Drain Timer
```

GUI-Updates via `EmitQueue` mit Throttling (max. alle 100ms).

## Bekannte Architektur-Schulden

1. **Flag_and_Options_Manager nicht vollstaendig integriert** — App verwendet parallel tk.BooleanVar neben dem FlagManager
2. **EmitQueue Direktzugriffe** — VCFBuffer greift direkt auf emit_queue zu statt drain_live_enqueue (bewusste Designentscheidung fuer Single-Key-Updates)
3. **CodingFilter doppelt instanziiert** — Separate Instanzen in MainFilterGate und Distiller

### Erledigt (2026-03)

- **AFFetchController** — Einzelinstanz in App, wird per Referenz an Distiller und BackgroundMaintainer uebergeben
- **STALE_DAYS Refactoring** — Config.STALE_DAYS_AF=365, Config.STALE_DAYS_FULL=30, separate Getter/Setter, UI-Integration

## Konfigurationsdateien

| Datei | Zweck | Git-tracked |
|---|---|---|
| `variant_fusion_settings.json` | Nutzer-Settings + API-Keys | Nein (.gitignore) |
| `variant_fusion_settings.json.example` | Vorlage ohne Credentials | Ja |
| `resources_config.json` | Lokale Ressourcen-Pfade | Nein (.gitignore) |
| `data/lightdb_config.json` | gnomAD LightDB Timestamps | Nein (.gitignore) |
| `locales/translations.json` | UI-Uebersetzungen | Ja |

## Build & Distribution

### PyInstaller

```bash
pyinstaller VFDistiller.spec
```

Erzeugt Standalone-EXE in `dist/`. Die Spec-Datei verwendet relative Pfade.

### Cython kompilieren

```bash
cd cython_hotpath
python setup.py build_ext --inplace
```

Erzeugt `.pyd` (Windows) oder `.so` (Linux) Module.
