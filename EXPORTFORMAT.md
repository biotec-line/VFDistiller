# Exportformat - vfdistiller-research-export-v1.json

Stand: 2026-05-26

Dieses Dokument definiert das geplante Austauschformat für den VFDistiller-Web/PWA-Companion. Es ist noch kein implementierter Codepfad, sondern die verbindliche Zielstruktur für den nächsten Portierungsschritt.

## Zweck

`vfdistiller-research-export-v1.json` soll Ergebnisdaten aus der Desktop-App in einen lokalen Web-/Mobile-Viewer übertragen. Das Format ist für Forschung, Lehre und Softwareentwicklung gedacht. Es ist nicht für klinische Diagnostik, Therapieentscheidungen oder öffentliche Cloud-Verarbeitung bestimmt.

## Datenschutzgrenzen

Der Export soll standardmäßig enthalten:

- Schema- und App-Metadaten
- RUO-/Nicht-Medizinprodukt-Hinweis
- gewählte Filterparameter
- Quellenstatus pro Annotation
- reduzierte Ergebnisvarianten
- optionale Notizen und Tags

Der Export soll standardmäßig nicht enthalten:

- vollständige Roh-VCF- oder gVCF-Dateien
- FASTA-Sequenzen oder Genomreferenzen
- gnomAD-LightDB-Inhalte
- API-Keys
- lokale absolute Dateipfade
- unnötige Personen-, Patienten- oder Identitätsdaten

## Schema-Skizze

```json
{
  "schema_version": "vfdistiller-research-export-v1",
  "app": {
    "name": "VFDistiller",
    "version": "17.0",
    "generated_at": "2026-05-26T00:00:00Z"
  },
  "legal": {
    "research_use_only": true,
    "not_for_clinical_use": true,
    "not_a_medical_device": true,
    "license": "AGPL-3.0-or-later"
  },
  "analysis": {
    "build": "GRCh38",
    "source_type": "VCF",
    "variant_count": 0,
    "filters": {
      "af_threshold": 0.007,
      "include_none": false,
      "filter_pass_only": true,
      "cadd_highlight_threshold": 22.0
    }
  },
  "variants": [
    {
      "chrom": "1",
      "pos": 123456,
      "ref": "A",
      "alt": "G",
      "gene": "GENE",
      "rsid": "rs000000",
      "af": 0.0001,
      "clin_sig": "uncertain_significance",
      "consequence": "missense_variant",
      "cadd": 12.3,
      "sources": {
        "gnomad": "hit",
        "clinvar": "hit",
        "vep": "hit",
        "alphagenome": "not_requested"
      },
      "notes": []
    }
  ]
}
```

## Kompatibilitätsregeln

- Reader müssen unbekannte Felder ignorieren.
- Neue Pflichtfelder erfordern eine neue Schema-Version.
- Zeitstempel werden als ISO-8601-Strings gespeichert.
- Text ist UTF-8.
- Exportdateien dürfen ohne Internetzugang lesbar bleiben.
- Der Web/PWA-Viewer darf keine Telemetrie und keinen externen Upload auslösen.
