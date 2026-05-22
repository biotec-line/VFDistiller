# VFDistiller -- Known Issues & TODOs

> Update 2026-05-09: Der Connection-Leak in `_lookup_lightdb` wurde behoben.

> Dieses Projekt wurde aus dem Microsoft Store zurückgezogen und wird über GitHub gepflegt. Änderungen nur nach sorgfältiger Prüfung!

## Bekannte Architektur-Schulden (vom Entwickler dokumentiert)
1. FLAG_AND_OPTIONS_MANAGER nicht vollständig integriert
2. EMIT_QUEUE-Direktzugriffe durch VCFBuffer (bewusste Entscheidung)
3. CODING_FILTER doppelt instanziiert (MainFilterGate und Distiller)

## Bugs

### [BEHOBEN 2026-05-09] Connection-Leak in `_lookup_lightdb` (AfFetcher, Zeile 7475)
- **Datei:** Variant_Fusion_pro_V17.py, Zeilen 7500-7567
- **Klasse:** AfFetcher (NICHT Distiller -- die Distiller-Kopie ab Zeile 16637 hat bereits ein korrektes `finally`-Pattern)
- **Problem:** `conn.close()` stand innerhalb des `try`-Blocks. Wenn eine Exception auftrat, die nicht vom inneren `except` gefangen wurde, sprang die Ausführung zum äußeren `except` und `conn.close()` wurde übersprungen.
- **Praxis-Risiko:** Moderat. SQLite-Connections werden vom GC irgendwann geschlossen, aber auf Windows halten offene Connections ein File-Lock auf die DB, was andere Zugriffe blockieren kann.
- **Fix-Vorschlag:** Identisches Pattern wie in der Distiller-Kopie (Zeile 16674-16761) einbauen:
  ```python
  conn = None
  try:
      conn = sqlite3.connect(db_path)
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

### [MITTEL] SQLite-Verbindungen ohne check_same_thread=False
- **Datei:** Variant_Fusion_pro_V17.py, Zeilen 7249, 10263, 16676
- **Problem:** sqlite3.connect() ohne check_same_thread=False in Methoden die aus Worker-Threads aufgerufen werden können
- **Fix-Vorschlag:** check_same_thread=False setzen oder sicherstellen dass Aufrufe immer im gleichen Thread erfolgen

### [NIEDRIG] Bare except: an 5 Stellen
- **Zeilen:** 329, 8315, 10338, 14419, 21589, 21606
- **Problem:** Fängt auch SystemExit und KeyboardInterrupt
- **Fix-Vorschlag:** except Exception: statt except:

## TODOs

### [NIEDRIG] stale_days Parameter aufteilen
- **Datei:** Variant_Fusion_pro_V17.py, Zeile 10910
- **Problem:** BackgroundMaintainer-Konstruktor hat noch einzelnen stale_days Parameter, obwohl intern bereits Config.STALE_DAYS_AF etc. genutzt werden
- **Status:** Semantisch erledigt, Konstruktor-Signatur noch nicht aktualisiert

## Kosmetisch
- Doppelter Alias HAVE_AIOHTTP / AIOHTTP_AVAILABLE (Zeile 107) -- bewusster Kompatibilitäts-Alias
- Irreführender Kommentar bei pickle-Import (Zeile 66)
