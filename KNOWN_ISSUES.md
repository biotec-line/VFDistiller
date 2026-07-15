# VFDistiller -- Known Issues & TODOs

> Update 2026-05-26: Die worker-sicheren SQLite-Verbindungen in den LightDB-/Migrationspfaden nutzen jetzt `check_same_thread=False`.

> Update 2026-05-23: Der Connection-Leak in `_lookup_lightdb` ist auf GitHub behoben.

> Dieses Projekt wurde aus dem Microsoft Store zurückgezogen und wird über GitHub gepflegt. Änderungen nur nach sorgfältiger Prüfung!

## Bekannte Architektur-Schulden (vom Entwickler dokumentiert)
1. FLAG_AND_OPTIONS_MANAGER nicht vollständig integriert
2. EMIT_QUEUE-Direktzugriffe durch VCFBuffer (bewusste Entscheidung)
3. CODING_FILTER doppelt instanziiert (MainFilterGate und Distiller)

## Bugs

### [BEHOBEN AUF GITHUB 2026-05-23] Connection-Leak in `_lookup_lightdb`
- **Datei:** `Variant_Fusion_pro_V17.py`, Zeilen 7504-7609
- **Klasse:** AfFetcher (NICHT Distiller -- die Distiller-Kopie ab Zeile 16685 hat bereits ein korrektes `finally`-Pattern)
- **Problem:** `conn.close()` stand innerhalb des `try`-Blocks. Wenn eine Exception auftrat, die nicht vom inneren `except` gefangen wurde, sprang die Ausführung zum äußeren `except` und `conn.close()` wurde übersprungen.
- **Praxis-Risiko:** Moderat. SQLite-Connections werden vom GC irgendwann geschlossen, aber auf Windows halten offene Connections ein File-Lock auf die DB, was andere Zugriffe blockieren kann.
- **Umgesetztes Muster:** Connection vor dem `try` initialisieren und im `finally` schließen:
  ```python
  conn = None
  try:
      conn = sqlite3.connect(db_path, check_same_thread=False)
      ...
  except Exception as e:
      self.logger.log(...)
  finally:
      if conn:
          try:
              conn.close()
          except Exception:
              pass
  ```

### [BEHOBEN AUF GITHUB 2026-05-26] SQLite-Verbindungen ohne `check_same_thread=False`
- **Datei:** `Variant_Fusion_pro_V17.py`, Zeilen 7278, 7531, 10297, 16724
- **Problem:** sqlite3.connect() ohne check_same_thread=False in Methoden die aus Worker-Threads aufgerufen werden können
- **Fix:** Die betroffenen Background-/Worker-Pfade setzen jetzt `check_same_thread=False` beim Erzeugen der SQLite-Verbindungen.

### [BEHOBEN AUF GITHUB 2026-03-16; VERIFIZIERT 2026-07-15] Bare `except:` an sechs Stellen im Hauptprogramm
- **Datei:** `Variant_Fusion_pro_V17.py`; ehemalige Zeilen 329, 8315, 10338, 14419, 21589, 21606
- **Problem:** Fängt auch SystemExit und KeyboardInterrupt
- **Fix:** Commit `7665133` ersetzte die Bare-`except:`-Stellen, ist ein verifizierter Vorfahr von `origin/main`, und das Hauptprogramm enthält dort keinen Treffer mehr.
- **Abgrenzung:** `cython_hotpath/test_performance.py` enthält weiterhin sechs Bare-`except:`-Stellen in einem optionalen Benchmarkskript. Dieser separate Befund gehörte nicht zu den in diesem Issue dokumentierten Hauptprogramm-Zeilen.

## TODOs

### [NIEDRIG] stale_days Parameter aufteilen
- **Datei:** `Variant_Fusion_pro_V17.py`, Zeilen 10926, 10944, 10958
- **Problem:** BackgroundMaintainer-Konstruktor hat noch einzelnen stale_days Parameter, obwohl intern bereits Config.STALE_DAYS_AF etc. genutzt werden
- **Status:** Semantisch erledigt, Konstruktor-Signatur noch nicht aktualisiert

## Kosmetisch
- Doppelter Alias `HAVE_AIOHTTP` / `AIOHTTP_AVAILABLE` (Zeilen 107-112) -- bewusster Kompatibilitäts-Alias
