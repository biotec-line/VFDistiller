# Variant Fusion -- Store Issues & Versionsverlauf

> Policy: Siehe `.SOFTWARE/WINDOWS_STORE_BUGFIX_POLICY.md`

## Store-Informationen

| Feld | Wert |
|------|------|
| **Store-Name** | Variant Fusion |
| **Store-ID** | 9MWRG32ZLDRM |
| **Store-Link** | https://apps.microsoft.com/detail/9MWRG32ZLDRM |
| **Herausgeber** | Geiger |
| **Kategorie** | Bildung |
| **Preis** | Kostenlos |
| **Sprachen** | Deutsch, Englisch |
| **Min. OS** | Windows 10 v17763.0 |

---

## Aktuelle Store-Version: 17.0.1.0

Veröffentlicht: 2026-03-10 (ca.)

---

## Issue-Register

| # | Severity | Beschreibung | Datei:Zeile | Gefunden | Status |
|---|----------|-------------|-------------|----------|--------|
| 1 | P2 | Connection-Leak in `_lookup_lightdb` (AfFetcher) -- kein `finally`-Block, `conn.close()` wird bei Exception übersprungen. Auf Windows hält offene Connection File-Lock auf DB. | V17.py:7500-7567 | 2026-03-13 | BEHOBEN 2026-05-23 |
| 2 | P2 | SQLite-Verbindungen ohne `check_same_thread=False` in Methoden die aus Worker-Threads aufgerufen werden können | V17.py:7249,10263,16676 | 2026-03-13 | BEHOBEN 2026-05-23 |
| 3 | P3 | Bare `except:` an 6 Stellen -- fängt auch SystemExit und KeyboardInterrupt | V17.py:329,8315,10338,14419,21589,21606 | 2026-03-13 | OFFEN |
| 4 | P3 | TODO: `stale_days` Parameter im BackgroundMaintainer-Konstruktor aufteilen (semantisch erledigt, Signatur nicht aktualisiert) | V17.py:10861 | 2026-03-13 | BEHOBEN 2026-07-28 |
| 5 | P3 | Doppelter Alias HAVE_AIOHTTP / AIOHTTP_AVAILABLE (bewusster Compat-Alias) | V17.py:107 | 2026-03-13 | WONTFIX |
| 6 | P3 | Irreführender Kommentar bei pickle-Import | V17.py:66 | 2026-03-13 | BEHOBEN 2026-06-12 |

**Release-Trigger-Status:** 0x P0, 0x P1, 0x P2, 1x P3 → Kein Release-Trigger (P0 oder 3x P1 nötig, P3 sammeln bis 10+)

---

## Bekannte Architektur-Schulden (vom Entwickler dokumentiert, kein Issue)

1. FLAG_AND_OPTIONS_MANAGER nicht vollstaendig integriert
2. EMIT_QUEUE-Direktzugriffe durch VCFBuffer (bewusste Entscheidung)
3. CODING_FILTER doppelt instanziiert (MainFilterGate und Distiller)

---

## Geplanter naechster Release: 17.0.2.0

**Trigger:** Noch nicht erreicht -- sammeln bis P0, 3x P1, oder 10+ P2/P3
**Enthaelt bisher:** --

---

## Versionsverlauf

### v17.0.1.0 (2026-03-10) -- Store (aktuell)
- Initialer Windows Store Release
- MSIX: `releases/windowsstore/v17.0.1.0/VariantFusion_17.0.1.0.msix`
- CWD-Unabhaengigkeit (alle Pfade absolut via BASE_DIR)
- HTTPS fuer alle API-Calls
- WACK bestanden
