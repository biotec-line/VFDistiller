# Privacy Policy — VFDistiller

**Last updated:** October 15, 2026
**Publisher:** Lukas Geiger
**Distribution:** GitHub only; the former Microsoft Store listing was withdrawn on April 12, 2026.

## Overview

VFDistiller is a desktop application for research-grade genetic variant analysis. This privacy policy explains how the application handles your data.

## Data Collection

**VFDistiller does not collect, store, or transmit any personal data to the developer.**

Local file processing and SQLite storage run on your device. Online annotation makes separate requests to external services as described below; local-first does not mean that every feature operates without network traffic.

## Data Processing

The application processes genetic data files (VCF, gVCF, 23andMe raw data, FASTA) that you choose to open. File ingestion, filtering and local database operations run on your machine. Enabled annotation features send variant-level query data to external services. Keeping the input file locally does not keep every variant field off the network.

## External Services

VFDistiller can connect to the following external services when configured annotation or lookup features run. Several sources are enabled by default in `Config.DEFAULT_API_SETTINGS`; starting an analysis can therefore issue requests automatically:

- **Ensembl VEP API** (ensembl.org) — for variant effect prediction
- **gnomAD** (gnomad.broadinstitute.org) — for population allele frequencies
- **MyVariant.info** (myvariant.info) — for variant annotations and allele frequencies
- **NCBI E-Utilities / ClinVar** (ncbi.nlm.nih.gov) — for allele and clinical-annotation lookups
- **Google AlphaGenome API** (googleapis.com) — for variant impact prediction; this also requires the optional client and a configured API key

These requests can contain variant identifiers, chromosome positions, reference/alternate alleles and the genome assembly. AlphaGenome calls also specify a genomic interval. Configured provider credentials may be used for authentication. Each external service has its own privacy policy; omitting a full input-file upload does not eliminate variant-level data transmission.

Review the API settings and enabled sources before processing your files. Requests and retries can run as part of the analysis; this policy does not promise a separate confirmation for every request. Reference-dataset downloads also require network access.

## Local Storage

The application stores user preferences and settings locally on your device. Local storage is separate from the external annotation and download requests described above.

## Children's Privacy

Variant Fusion does not knowingly collect any data from children or any other users.

## Changes to This Policy

Updates to this privacy policy will be posted on this page with an updated revision date.

## Contact

For questions about this privacy policy:
- GitHub: [github.com/biotec-line/VFDistiller](https://github.com/biotec-line/VFDistiller)
- ORCID: [0009-0005-7296-1534](https://orcid.org/0009-0005-7296-1534)
