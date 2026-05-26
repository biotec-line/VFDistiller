# Portierungsplan - VFDistiller

Stand: 2026-05-26

## Kurzentscheidung

VFDistiller bleibt ein lokales Desktop-Forschungswerkzeug mit GitHub als Hauptvertrieb. Eine erneute Windows-Store-Veröffentlichung wird nicht aktiv verfolgt, weil das Store-Listing am 2026-04-12 nach IVDR-Risikoabwägung zurückgezogen wurde. Plattformübergreifende Nutzung ist trotzdem sinnvoll, aber nur als getrennte Linie: Desktop verarbeitet große lokale Genomdateien, Web/PWA/Android/iOS dienen höchstens als lokaler, datensparsamer Resultat-Viewer.

## Warum plattformübergreifend sinnvoll ist

- Bioinformatik-Nutzer arbeiten nicht ausschließlich auf Windows; Linux und macOS sind in Forschung und Lehre üblich.
- Große VCF-, gVCF-, FASTA- und LightDB-Dateien passen fachlich besser zu Desktop-/Workstation-Systemen als zu mobilen Sandboxes.
- Mobile Nutzung hat trotzdem Nachfrage: Ergebnisse, Filtersets und Forschungsnotizen sollen unterwegs geprüft, geteilt oder in Seminaren gezeigt werden können.
- Genetische Rohdaten sind besonders sensibel. Ein öffentlicher Cloud-Upload oder eine SaaS-Version wäre rechtlich, lizenzseitig und datenschutzfachlich deutlich riskanter als ein lokaler Export-/Viewer-Ansatz.

## Zielbild

1. Windows bleibt die primär getestete Desktop-Plattform.
2. Linux und macOS werden als Source-/Build-Smoke-Ziele geführt, nicht als separate Produktlinien.
3. Web/PWA wird nur als lokaler Companion für exportierte Ergebnisdateien geplant.
4. Android und iOS verwenden denselben PWA-/Viewer-Kern, keine native Analyse-Engine.
5. Raw-Genomdaten, FASTA-Referenzen, LightDB und API-Keys bleiben ausschließlich in der Desktop-App.
6. Jeder plattformübergreifende Pfad trägt den RUO-Hinweis: Research Use Only, kein Medizinprodukt, keine klinische Diagnostik.

## Plattformabwägung

| Ziel | Entscheidung | Begründung |
|---|---|---|
| Windows Store | Nicht erneut aktiv verfolgen | Das Listing wurde am 2026-04-12 bewusst zurückgezogen. Eine neue Store-Linie würde die IVDR-/Consumer-Genomik-Nähe wieder erhöhen. Store-Artefakte bleiben nur als historische Verpackungsbasis und für private Builds dokumentiert. |
| Android | Kein nativer Clone, nur PWA-Viewer | Mobile Geräte eignen sich für Ergebnisansicht, Filtervergleich und Notizen, aber nicht für große lokale Referenzdaten, LightDB und lange Annotierungsjobs. |
| Webapp | Ja, aber lokal/offline und exportbasiert | Sinnvoll als statischer oder lokal gehosteter Viewer für `vfdistiller-research-export-v1.json`. Keine öffentliche Upload-Webapp. |
| iOS | Kein nativer Clone, nur PWA-Viewer | Gleicher Kern wie Android; Datenschutz und Dateisandbox sprechen gegen eine native Analyse-Engine. |
| Mac App | P3 Source-/PyInstaller-Smoke | Forschungspublikum nutzt macOS; eine notarized App ist erst sinnvoll, wenn reproduzierbare Builds und Nachfrage vorliegen. |
| Linux Version | P2 Source-Smoke, später optional AppImage | Linux ist für Bioinformatik relevant. Wegen optionaler Cython-Module und großer Ressourcen zuerst Source- und CLI-/GUI-Smokes statt eigener Release-Kanal. |

## Umsetzungslinie

### P0 - Austauschformat definieren

`vfdistiller-research-export-v1.json` wird als portabler Resultat-Export geplant. Es enthält Metadaten, RUO-Hinweis, Filterparameter, Quellenstatus und eine reduzierte Variantenliste. Raw-Sequenzen, vollständige VCF-Rohdaten, FASTA-Referenzen, lokale Datenbankpfade und API-Keys werden nicht exportiert.

### P1 - Desktop-Export implementieren

Die Desktop-App soll zusätzlich zu CSV/Excel/PDF/annotiertem VCF einen JSON-Export erzeugen. Der Export muss UTF-8 nutzen, Schema-Version und App-Version enthalten und ohne lokale absolute Pfade auskommen.

### P2 - Lokaler Web/PWA-Viewer

Ein kleiner `web_companion/`-Viewer liest ausschließlich lokale Exportdateien und zeigt Varianten, Filter, Quellenstatus und RUO-Hinweise. Er darf keine Upload-URL und keine externe Telemetrie enthalten.

### P3 - Linux/macOS-Smokes

Linux und macOS werden mit Source-Start, optionalem Cython-Fallback, GUI-Import und einem kleinen Fixture-Export geprüft. PyInstaller-/AppImage-/notarized-Builds folgen nur bei stabilem Bedarf.

## Status

- Kein vorheriger `PORTIERUNGSPLAN.md` vorhanden.
- Windows Store historisch erledigt, aber am 2026-04-12 zurückgezogen.
- GitHub-only-Vertrieb ist bereits in README/README.de und `releases.json` dokumentiert.
- Projekt hat bestehende Exporte: CSV, Excel, PDF, annotiertes VCF.
- Neuer offener Transfer-Baustein: `vfdistiller-research-export-v1.json` plus lokaler Viewer.

## Nicht-Ziele

- Keine öffentliche Webapp für genetische Uploads.
- Keine klinische Entscheidungsunterstützung.
- Keine native Android-/iOS-Analyse-Engine.
- Keine erneute Store-Einreichung ohne neue Rechts- und Zweckbestimmungsprüfung.
- Keine Synchronisation von API-Keys, lokalen Datenbanken oder Genomreferenzen.
