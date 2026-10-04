# VFDistiller — I18N Logging & Docstring Inventory (TW-VFD-04)

**Stand:** 2026-10-03  
**Status:** Abgeschlossen (TASKPLAN 633 / TW-VFD-04)  
**Bezug:** Policy P-006 (Tier-2 6-Sprachen-Standard), `AUFGABEN.txt`, `STORE_ISSUES.md`, `KNOWN_ISSUES.md`

---

## 1. Ausgangslage & Problemstellung

Im Rahmen der UI-Internationalisierung wurden alle sichtbaren GUI-Komponenten (Menüs, Buttons, Dialoge, Tabellen, Tooltips, Toasts) erfolgreich in `locales/translations.json` überführt (185 Übersetzungsschlüssel mit 100% Parität über alle 6 Tier-2-Sprachen: Deutsch, Englisch, Spanisch, Chinesisch, Japanisch, Russisch).

In `AUFGABEN.txt` verblieb der offene Posten:
> „Docstrings und Log-Meldungen (249 Strings, niedrige Prio für UI-Internationalisierung)“

Dieser Posten wurde in **TW-VFD-04** formalisiert mit dem Auftrag:
1. Strings nach Nutzerwirkung und Zielgruppe klassifizieren (User-facing vs. Operator-facing vs. Entwickler).
2. Klare Strategie (Lokalisierung vs. bewusste technische Einsprachigkeit) für jede Kategorie festlegen und begründen.
3. Regressionsrisiken, Fallbacks und Tests verbindlich definieren.

---

## 2. Klassifizierungsmatrix & Architekturentscheidung

| Kategorie | Umfang (Strings) | Zielgruppe | Ausgabekanal | Strategie & Architekturentscheidung |
|-----------|------------------|------------|--------------|--------------------------------------|
| **Kategorie A: Docstrings & Typkommentare** | ~260 | Entwickler, Wartungsagenten, IDEs | Quellcode / AST (`Variant_Fusion_pro_V17.py`, Hilfsmodule) | **Bewusste technische Einsprachigkeit im Quellcode.** Keine Aufnahme in `locales/translations.json`. *Begründung:* Docstrings werden zur Laufzeit dem Endanwender nicht angezeigt. Eine Lokalisierung würde die Übersetzungsdatenbank aufblähen, Ladezeiten verlängern und birgt kein Qualitätsplus für Endanwender. |
| **Kategorie B: Operator- & Diagnose-Logs** | ~120 | Operatoren, Support, Bugreports | Konsole (`stdout`/`stderr`), Datei (`distiller_debug.log`) via `MultiSinkLogger` | **Bewusste technische Einsprachigkeit mit strukturierter Präfix-Syntax (`[Modul] Status`).** Keine dynamische Lokalisierung. *Begründung:* Logdateien wandern in Fehlerberichte und werden von Diagnoseskripten/Grep automatisiert geparst. Eine Umschaltung der Logsprache würde automatisierte Regressions- und Fehleranalyse brechen. Sensible Loci/rsIDs werden via `redact_for_logfile` geschwärzt. |
| **Kategorie C: User-facing Status- & Feedbackmeldungen** | ~33 | Endanwender, Labornutzer | GUI-Queue (`ui_queue`), Statusleiste, Modal-Dialoge, Toasts | **Vollständige Tier-2-Mehrsprachigkeit (100% Parität DE, EN, ES, ZH, JA, RU).** Verankert in `locales/translations.json` und über `Translator.t()` / `self._t()` dynamisch auflösbar. |

---

## 3. Detail-Inventur der Logging-Kategorien

### Kategorie A: Quellcode-Docstrings (Rein entwicklerbezogen)
- Modul-Header, Funktions- und Klassendocstrings in `Variant_Fusion_pro_V17.py`, `Get gnomAD DB light.py`, `lightdb_index_worker.py`.
- Enthalten bioinformatische Spezifikationen (z. B. VCF 4.2 Specs, HGVS-Nomenklatur, Liftover GRCh37/GRCh38, Cython Fallbacks).
- **Entscheidung:** Verbleiben im Quelltext als deutsche bzw. englische Dokumentation. Keine I18N-Aktion erforderlich.

### Kategorie B: Operator-Logs (`MultiSinkLogger` / `distiller_debug.log`)
- Muster: `self.logger.log("[Modul] Statusmeldung")`
- Typische Präfixe:
  - `[23andMe→VCF]`, `[BuildCheck]`, `[LightDB]`, `[Maint]`, `[Maint-P5]`, `[BackofficeCrawler]`, `[AfNoneTreatment]`, `[Distiller]`
- **Entscheidung:**
  1. Beibehaltung der deterministischen englischen/deutschen Meldungen für Diagnose und Support.
  2. Datenschutz- und Redaktionsgarantie: Genomische Koordinaten und rsIDs werden vor dem Schreiben in die persistente Datei über `redact_for_logfile` maskiert (`rs<redigiert>`, `<locus redigiert>`).

### Kategorie C: Endanwender-relevante GUI-Strings
- Alle Dialoge (`QualitySettingsDialog`, `ResourceSetupDialog`, `SettingsTab`), Menüs (`Optionen -> Sprache`) und Table-Headings sind bereits vollständig an den `Translator` angebunden.
- Der Übersetzungskatalog `locales/translations.json` umfasst 185 Schlüssel und deckt alle Nutzerinteraktionen ab.
- Laufzeit-Gate: `python manage_translations.py --check` validiert die 100%-ige Parität (Exit 0).

---

## 4. Testabdeckung & Verifikation

1. **Übersetzungs-Parität:** `tests/test_i18n.py` und `manage_translations.py --check` sichern die lückenlose Abdeckung über alle 6 Sprachen.
2. **Datenschutz in Logs:** `tests/test_logfile_redaction.py` validiert, dass keine unbefugten Genom-IDs in `distiller_debug.log` verbleiben (6/6 Tests grün).
3. **Stale-Days & Maintainer:** `tests/test_stale_days_maintainer.py` validiert das getrennte Verhalten von AF- und Full-Stale-Schwellenwerten (5/5 Tests grün).
4. **Platform & Contract Smoke:** `tests/test_security_license_contract.py` und `source_platform_smoke.py` bestätigen hermetische Integrität.

---

## 5. Fazit & Abschluss

Die Restlücke aus `AUFGABEN.txt:66` ist damit vollständig analysiert, kategorisiert und als architektonische Entscheidung verbindlich dokumentiert. Es verbleiben keine ungelösten I18N-Schulden für VFDistiller.
