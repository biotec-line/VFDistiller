# VFDistiller Web Companion

Status: geplant

Der Web Companion ist als lokaler/offlinefähiger Viewer für `vfdistiller-research-export-v1.json` geplant. Er ist kein Ersatz für die Desktop-App und führt keine Genom- oder API-Annotation selbst aus.

## Zweck

- exportierte Forschungsresultate auf Android, iOS, Web, Linux und macOS ansehen
- Filterparameter und Quellenstatus nachvollziehen
- RUO- und Nicht-Medizinprodukt-Hinweise sichtbar halten
- lokale Dateien ohne Cloud-Upload öffnen

## Nicht-Ziele

- keine öffentliche Upload-Webapp
- keine Verarbeitung vollständiger VCF-/gVCF-/FASTA-Rohdaten
- keine Speicherung von API-Keys
- keine klinische Diagnostik
- keine native Mobile-Analyse-Engine

## Nächste Schritte

1. JSON-Export in der Desktop-App implementieren.
2. Fixture-Datei für `vfdistiller-research-export-v1.json` anlegen.
3. Minimalen statischen Viewer bauen.
4. Offline- und Mobile-Smoke-Test dokumentieren.
