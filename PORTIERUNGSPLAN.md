# Portierungsplan - VFDistiller

Stand: 2026-05-26

## Kurzentscheidung

VFDistiller bleibt ein lokales Desktop-Forschungswerkzeug mit GitHub als Hauptvertrieb. Eine erneute Windows-Store-Veröffentlichung wird nicht aktiv verfolgt, weil das Store-Listing am 2026-04-12 nach IVDR-Risikoabwägung zurückgezogen wurde. Eine Mobile-Version ist nicht sinnvoll und wird nicht geplant. Interessant sind nur macOS und Linux als zusätzliche Desktop-/Workstation-Ziele.

## Warum plattformübergreifend sinnvoll ist

- Bioinformatik-Nutzer arbeiten nicht ausschließlich auf Windows; Linux und macOS sind in Forschung und Lehre üblich.
- Große VCF-, gVCF-, FASTA- und LightDB-Dateien passen fachlich zu Desktop-/Workstation-Systemen.
- Die Analyse kann lange laufen, braucht lokale Dateien, optionale Cython-Module, SQLite-Caches und teils große Referenzdaten.
- macOS und Linux können Reichweite in Forschung, Lehre und Bioinformatik erhöhen, ohne die Zweckbestimmung in Richtung Consumer-Mobile-App zu verschieben.
- Genetische Rohdaten sind besonders sensibel. Mobile-, Web- oder SaaS-Linien würden mehr Datenschutz- und Zweckbestimmungsrisiko erzeugen als Nutzen.

## Zielbild

1. Windows bleibt die primär getestete Desktop-Plattform.
2. Linux wird als erstes Zusatzsystem geprüft, weil Bioinformatik dort besonders relevant ist.
3. macOS wird als zweites Zusatzsystem geprüft, primär über Source-Start und später optional über PyInstaller/notarized App.
4. Android, iOS, Webapp und PWA sind Nicht-Ziele.
5. Raw-Genomdaten, FASTA-Referenzen, LightDB und API-Keys bleiben ausschließlich lokal.
6. Jeder Desktop-Port trägt den RUO-Hinweis: Research Use Only, kein Medizinprodukt, keine klinische Diagnostik.

## Plattformabwägung

| Ziel | Entscheidung | Begründung |
|---|---|---|
| Windows Store | Nicht erneut aktiv verfolgen | Das Listing wurde am 2026-04-12 bewusst zurückgezogen. Eine neue Store-Linie würde die IVDR-/Consumer-Genomik-Nähe wieder erhöhen. Store-Artefakte bleiben nur als historische Verpackungsbasis und für private Builds dokumentiert. |
| Android | Nicht planen | Mobile Sandbox, Dateigrößen, sensible Rohdaten und lange Analysejobs passen nicht zum App-Zweck. |
| Webapp/PWA | Nicht planen | Kein Upload- oder Viewer-Pfad nötig; bestehende Desktop-Exporte reichen. Eine Weblinie würde Datenschutz- und Zweckbestimmungsrisiken erhöhen. |
| iOS | Nicht planen | Gleiche Gründe wie Android, zusätzlich stärkere Dateisandbox und kein klarer Usecase. |
| Mac App | Prüfen | macOS ist für Forschung und Lehre relevant. Erst Source-Smoke, dann optional PyInstaller-/notarized-Build bei Bedarf. |
| Linux Version | Prüfen | Linux ist für Bioinformatik besonders relevant. Erst Source-Smoke und Cython-Fallback, später optional AppImage oder anderes Paketformat. |

## Umsetzungslinie

### P0 - Linux-Smoke-Test

Source-Start auf Linux prüfen: Python-Abhängigkeiten, Tk/ttkbootstrap, optionaler Cython-Fallback, SQLite/LightDB-Zugriffe, kleiner VCF-Fixture-Import und bestehende Exporte. Ziel ist erst ein dokumentierter Startpfad, kein eigener Release-Kanal.

### P1 - macOS-Smoke-Test

Source-Start auf macOS prüfen: Python-Abhängigkeiten, Tk/ttkbootstrap-Darstellung, Dateidialoge, Cython-Fallback, SQLite/LightDB-Zugriffe und bestehende Exporte. Packaging erst danach bewerten.

### P2 - Build-/Packaging-Notizen

Falls Linux/macOS-Smokes stabil sind, Build-Optionen getrennt dokumentieren: AppImage oder tar/zip für Linux, PyInstaller und optional Notarisierung für macOS. Keine Plattform bekommt einen eigenen Feature-Fork.

### P3 - Dokumentation und Supportgrenzen

README/README.de sollen klar zwischen primär getesteter Windows-Version und experimentellen Linux/macOS-Pfaden unterscheiden. RUO-Hinweis, lokale Datenhaltung und fehlende klinische Zweckbestimmung bleiben überall sichtbar.

## Status

- Kein vorheriger `PORTIERUNGSPLAN.md` vorhanden.
- Windows Store historisch erledigt, aber am 2026-04-12 zurückgezogen.
- GitHub-only-Vertrieb ist bereits in README/README.de und `releases.json` dokumentiert.
- Projekt hat bestehende Exporte: CSV, Excel, PDF, annotiertes VCF.
- Neuer offener Portierungsbaustein: Linux-/macOS-Smoke-Protokolle.

## Nicht-Ziele

- Keine öffentliche Webapp für genetische Uploads.
- Kein Web-/PWA-Viewer.
- Keine klinische Entscheidungsunterstützung.
- Keine native Android-/iOS-Analyse-Engine.
- Keine erneute Store-Einreichung ohne neue Rechts- und Zweckbestimmungsprüfung.
- Keine Synchronisation von API-Keys, lokalen Datenbanken oder Genomreferenzen.
