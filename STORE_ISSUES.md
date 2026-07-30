# Variant Fusion -- Store Issues & Versionsverlauf

> Lokale Steuer-Policy (nicht Teil dieses GitHub-Repositories): `../../_STORE/WINDOWS_STORE_BUGFIX_POLICY.md`

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
| 1 | P2 | Connection-Leak in `_lookup_lightdb` (AfFetcher) -- kein `finally`-Block, `conn.close()` wird bei Exception übersprungen. Auf Windows hält eine offene Connection einen File-Lock auf der DB. | `Variant_Fusion_pro_V17.py:7504-7609` | 2026-03-13 | GEFIXT (GitHub) 2026-05-23, `9d54dee` |
| 2 | P2 | SQLite-Verbindungen ohne `check_same_thread=False` in Methoden, die aus Worker-Threads aufgerufen werden können | `Variant_Fusion_pro_V17.py:7278,7531,10297,16724` | 2026-03-13 | GEFIXT (GitHub) 2026-05-26, `9cb6141` |
| 3 | P3 | Bare `except:` an den sechs ursprünglich dokumentierten Stellen im Hauptprogramm -- fängt auch SystemExit und KeyboardInterrupt | `Variant_Fusion_pro_V17.py` (ehemals 329, 8315, 10338, 14419, 21589, 21606) | 2026-03-13 | GEFIXT (GitHub) 2026-03-16, `7665133`; Remote-Readback 2026-07-15 ohne Treffer |
| 4 | P3 | TODO: `stale_days`-Parameter im BackgroundMaintainer-Konstruktor aufteilen (semantisch erledigt, Signatur nicht aktualisiert) | `Variant_Fusion_pro_V17.py:10926,10944,10958` | 2026-03-13 | OFFEN |
| 5 | P3 | Doppelter Alias `HAVE_AIOHTTP` / `AIOHTTP_AVAILABLE` (bewusster Compat-Alias) | `Variant_Fusion_pro_V17.py:107-112` | 2026-03-13 | WONTFIX |
| 6 | P3 | Irreführender Kommentar beim `pickle`-Import | `Variant_Fusion_pro_V17.py:67` | 2026-03-13 | GEFIXT (GitHub) 2026-06-12, `cad96f8` |

**Statusaufschlüsselung:** 1x OFFEN (#4, P3), 1x WONTFIX (#5, P3), 4x GEFIXT (GitHub) (#1, #2, #3, #6), 0x GEFIXT (Store).

**Release-Trigger-Status:** 0x P0, 0x P1; 5x P2/P3 noch nicht als Store-Fix belegt (2x P2 + 3x P3: vier GitHub-Fixes und ein offenes Issue). WONTFIX wird nicht gezählt. Damit bleibt die Policy-Schwelle von 10x P2/P3 unterschritten und es besteht kein Store-Release-Trigger.

**Scope-Hinweis zu #3:** Der Nulltreffer gilt für das veröffentlichte Hauptprogramm `Variant_Fusion_pro_V17.py` auf `origin/main`; Fix-Commit `7665133` ist ein verifizierter Vorfahr dieses Stands. Das optionale Benchmarkskript `cython_hotpath/test_performance.py` enthält weiterhin sechs Bare-`except:`-Stellen; diese gehörten nicht zu den sechs in #3 dokumentierten Hauptprogramm-Fundstellen und sind kein stillschweigend geschlossener projektweiter Befund.

---

## Bekannte Architektur-Schulden (vom Entwickler dokumentiert, kein Issue)

1. FLAG_AND_OPTIONS_MANAGER nicht vollstaendig integriert
2. EMIT_QUEUE-Direktzugriffe durch VCFBuffer (bewusste Entscheidung)
3. CODING_FILTER doppelt instanziiert (MainFilterGate und Distiller)

---

## Geplanter naechster Release: 17.0.2.0

**Trigger:** Nicht erreicht -- 5x P2/P3 noch nicht als Store-Fix belegt; Schwelle 10, kein P0/P1
**GitHub-Fixes seit dem Store-Stand:** #1, #2, #3 und #6; #4 bleibt offen, #5 bleibt WONTFIX

---

## Versionsverlauf

### v17.0.1.0 (2026-03-10) -- Store (aktuell)
- Initialer Windows Store Release
- MSIX: `releases/windowsstore/v17.0.1.0/VariantFusion_17.0.1.0.msix`
- CWD-Unabhaengigkeit (alle Pfade absolut via BASE_DIR)
- HTTPS fuer alle API-Calls
- WACK bestanden
