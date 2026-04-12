# Store Listing — VFDistiller

> **Kopfnotiz für den Partner-Center-Upload:**
> Diese Datei enthält den Listing-Text für den Microsoft Store. Der Upload
> erfolgt manuell im Partner Center durch den Entwickler (Lukas Geiger).
>
> **Research Use Only — Not for Clinical Use — Kein Medizinprodukt.**
>
> Empfohlene Store-Kategorie: **Entwickler-Tools** (bzw. Developer tools /
> Bioinformatics). Die App darf nicht in einer „Medizin"-, „Gesundheit"-
> oder „Diagnose"-Kategorie gelistet werden.

---

## Deutsch

### Kurzbeschreibung (max 100 Zeichen)
Bioinformatik-Tool für VCF-Analyse und -Annotation (Research Use Only)

### Beschreibung (max 10.000 Zeichen)

**Research Use Only — Not for Clinical Use — Kein Medizinprodukt.**

VFDistiller (Variant Fusion Distiller) ist ein bioinformatisches Desktop-Tool
für die technische Verarbeitung, Format-Konvertierung und Annotation
forschungsbezogener genetischer Variantendaten. Es richtet sich an
Bioinformatiker, Forschende und Entwickler, die mit VCF-Dateien arbeiten.

VFDistiller ist **ausschließlich für Forschung, Lehre und Software-Entwicklung
bestimmt**. Es ist **kein In-vitro-Diagnostikum** (IVDR (EU) 2017/746),
**nicht CE-IVD-zertifiziert**, **nicht durch BfArM oder eine Benannte Stelle
geprüft** und **nicht für klinische Diagnostik, Prognose oder
Therapie-Entscheidungen bestimmt**.

FEATURES:
- Multi-Format-Import: VCF, gVCF, 23andMe-Rohformat (.txt), FASTA (.fa/.fasta)
- Automatische Build-Erkennung: GRCh37 und GRCh38 aus Header, Contigs oder RSID-Positionen
- Multi-Source-Annotation: gnomAD, MyVariant.info, Ensembl VEP, ALFA, TOPMed, AlphaGenome
- INFO-Recycling: Vorhandene VCF-Annotationen werden wiederverwendet
- Technische Filterung: AF-Schwelle, CADD-Score, Variant Impact, ClinSig, Genlisten, FILTER=PASS, Read Depth
- Vielseitiger Export: CSV, Excel, PDF, annotiertes VCF (gefiltert oder vollständig)
- Moderne GUI: ttkbootstrap-Oberfläche mit System-Tray, Fortschrittsanzeige und Themes
- Performance: Optionaler Cython-Hotpath (5x Gesamt-Speedup), SQLite-Batch-Writes, async HTTP
- Hintergrund-Wartung: Automatisches Nachladen fehlender Annotationen im Leerlauf
- Mehrsprachig: Deutsch und Englisch

FÜR WEN:
- Bioinformatiker, die VCF-Dateien aus Forschungs-Sequenzierungen effizient verarbeiten möchten
- Forschende in Humangenetik, Populationsgenetik und Grundlagenforschung
- Software-Entwickler, die Annotationspipelines bauen oder Referenz-Tools benötigen
- Lehrende im Bereich Bioinformatik, die eine Windows-native Alternative zu pysam/bcftools/samtools suchen

VORTEILE:
- Keine pysam/bcftools/samtools nötig — läuft nativ unter Windows
- Offline-fähig dank gnomAD LightDB für schnelle Allele-Frequency-Lookups
- Automatischer Download fehlender Genomreferenzen und Datenbanken
- Transparente Ergebnisse: Tabellenansicht mit sortierbaren Spalten, Doppelklick öffnet externe Datenbanken

HINWEISE ZUR VERWENDUNG:
- Die angezeigten ClinSig-Werte (ClinVar) und Variant-Impact-Werte (VEP,
  AlphaGenome) sind Datenbank-Annotationen aus Drittquellen zur
  Forschungsorientierung. Sie sind keine klinische Bewertung.
- Für die klinische Interpretation genetischer Befunde müssen
  qualifizierte humangenetische Fachstellen konsultiert werden.
- Der Anbieter übernimmt keine Haftung für die klinische Richtigkeit der
  annotierten Werte; diese liegt bei den jeweiligen Quell-Datenbanken.

KOSTENLOS
VFDistiller ist und bleibt kostenlos. Der vollständige Quellcode steht unter
der GNU Affero General Public License v3.0-or-later (AGPL-3.0-or-later) bereit.
Quellcode-Repository: https://github.com/biotec-line/VFDistiller

RECHTLICHER HINWEIS
Unentgeltliche Open-Source-Schenkung (§§ 516 ff. BGB). Haftung auf Vorsatz
und grobe Fahrlässigkeit beschränkt (§ 521 BGB, AGPL-3.0 §§ 15–17).
Nutzung auf eigenes Risiko.

### Schlüsselwörter

VCF, Varianten, Bioinformatik, Forschung, Annotation, gnomAD, Ensembl, VEP,
FASTA, Genom-Pipeline, Research Use Only, Developer-Tool, Windows-Bioinformatik

### Kategorie

**Entwickler-Tools** (Developer tools).
**Nicht** „Medizin", „Gesundheit & Fitness" oder „Medical" — VFDistiller ist
kein Medizinprodukt.

### Altersfreigabe

USK / ESRB: alle Altersgruppen (keine jugendgefährdenden Inhalte, reines
Entwickler-Tool).

---

## English

### Short Description (max 100 chars)
Bioinformatics tool for VCF annotation and analysis (Research Use Only)

### Description (max 10,000 chars)

**Research Use Only — Not for Clinical Use — Not a Medical Device.**

VFDistiller (Variant Fusion Distiller) is a bioinformatics desktop tool for
the technical processing, format conversion and annotation of research-grade
genetic variant data. It is intended for bioinformaticians, researchers and
software developers working with VCF files.

VFDistiller is **strictly for research, teaching and software development**.
It is **not an in-vitro diagnostic medical device** (IVDR (EU) 2017/746),
**not CE-IVD certified**, **not reviewed by BfArM or any notified body** and
**not intended for clinical diagnosis, prognosis or therapeutic decisions**.

FEATURES:
- Multi-Format Import: VCF, gVCF, 23andMe raw text format (.txt), FASTA (.fa/.fasta)
- Automatic Build Detection: GRCh37 and GRCh38 from header, contigs or RSID positions
- Multi-Source Annotation: gnomAD, MyVariant.info, Ensembl VEP, ALFA, TOPMed, AlphaGenome
- INFO Recycling: Existing VCF annotations are reused
- Technical Filtering: AF threshold, CADD score, variant impact, ClinSig, gene lists, FILTER=PASS, read depth
- Versatile Export: CSV, Excel, PDF, annotated VCF (filtered or complete)
- Modern GUI: ttkbootstrap interface with system tray, progress indicators and themes
- Performance: Optional Cython hot-path (5x overall speedup), SQLite batch writes, async HTTP
- Background Maintenance: Automatic re-fetching of missing annotations during idle time
- Multilingual: German and English

FOR WHOM:
- Bioinformaticians working with VCF files from research sequencing runs
- Researchers in human genetics, population genetics and basic research
- Software developers building annotation pipelines or needing a reference tool
- Bioinformatics teachers looking for a Windows-native alternative to pysam/bcftools/samtools

BENEFITS:
- No pysam/bcftools/samtools required — runs natively on Windows
- Offline-capable with gnomAD LightDB for fast allele frequency lookups
- Automatic download of missing genome references and databases
- Transparent results: sortable table view, double-click opens external databases

USAGE NOTES:
- ClinSig values (ClinVar), variant-impact values (VEP, AlphaGenome) and
  allele-frequency annotations (gnomAD, ALFA, TOPMed) are third-party
  research database annotations shown for scientific orientation. They
  are not clinical assessments.
- For the clinical interpretation of genetic findings please consult
  qualified human-genetics professionals.
- The publisher accepts no liability for the clinical correctness of the
  annotated values; that responsibility rests with the source databases.

FREE
VFDistiller is free and will remain free. The full source code is available
under the GNU Affero General Public License v3.0-or-later
(AGPL-3.0-or-later).
Source repository: https://github.com/biotec-line/VFDistiller

LEGAL NOTICE
Unpaid open-source donation under §§ 516 et seq. German Civil Code.
Liability limited to intent and gross negligence (§ 521 German Civil Code,
AGPL-3.0 §§ 15–17). Use at your own risk.

### Keywords

VCF, variants, bioinformatics, research, annotation, gnomAD, Ensembl, VEP,
FASTA, genome pipeline, research use only, developer tool, windows bioinformatics

### Category

**Developer tools**.
**Not** "Medical", "Health & fitness" or "Medical" — VFDistiller is not a
medical device.

### Age Rating

USK / ESRB: all ages (no harmful content; pure developer tool).

---

## Changelog dieser Listing-Datei

- 2026-04-12: RUO-Umstellung im Rahmen des IVDR-Gutachtens umgesetzt.
  - DTC-Zielgruppenformulierungen entfernt („23andMe/AncestryDNA-Nutzer, die
    ihre Rohdaten wissenschaftlich auswerten möchten" → ersetzt durch
    forschungs- und entwicklerorientierte Zielgruppe).
  - RUO-Kurzfassung an den Anfang der Beschreibung gesetzt.
  - Lizenz-Angabe von „VFDistiller License v1.0" auf AGPL-3.0-or-later
    aktualisiert.
  - Kategorie von „Photo & Video" auf „Entwickler-Tools / Developer tools"
    korrigiert (neue Kategorie muss im Partner Center manuell umgestellt
    werden).
  - Keyword „consumer genomics" / „Consumer-Genomik" entfernt; stattdessen
    Forschungs- und Entwicklungs-Terminologie.
  - Haftungshinweis und Source-Repository-Link ergänzt.
