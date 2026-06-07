# CROSSCHECK — Externe Dependencies

> Vorlage: `_TEMPLATES/CROSSCHECK_TEMPLATE.md` | Konvention: GUIDE.md §Toolchain-Standards
> Pfad: `_sources/CROSSCHECK.md` im jeweiligen Projektordner
> Stand: 2026-06-07

## Verwendete Pakete mit Major-Version-Pinning

### Core (required)

| Paket | Gepinnte Version | Aktuelle Version | Letzte Prüfung |
|---|---|---|---|
| requests | `>=2.31.0` | 2.33.1 | 2026-06-07 |
| psutil | `>=5.9.0` | 7.0.0 | 2026-06-07 |
| Pillow | `>=10.0.0` | 12.2.0 | 2026-06-07 |
| intervaltree | `>=3.1.0` | 3.1.0 | 2026-06-07 |
| ttkbootstrap | `>=1.10.0` | 1.19.2 | 2026-06-07 |
| pystray | `>=0.19.0` | 0.19.5 | 2026-06-07 |
| aiohttp | `>=3.9.0` | 3.13.5 | 2026-06-07 |
| scipy | `>=1.11.0` | 1.16.0 | 2026-06-07 |

### Export (optional but recommended)

| Paket | Gepinnte Version | Aktuelle Version | Letzte Prüfung |
|---|---|---|---|
| openpyxl | `>=3.1.0` | 3.1.5 | 2026-06-07 |
| reportlab | `>=4.0.0` | 4.4.5 | 2026-06-07 |

### Extended analysis (optional)

| Paket | Gepinnte Version | Aktuelle Version | Letzte Prüfung |
|---|---|---|---|
| numpy | `>=1.24.0` | 2.3.1 | 2026-06-07 |
| biopython | `>=1.81` | 1.85 | 2026-06-07 |
| pyfaidx | `>=0.7.0` | 0.9.0.3 | 2026-06-07 |

Aktuelle Version prüfen: `python -m uv pip list --outdated` oder `pip list --outdated`

---

## P0 — Sicherheit / CVEs (blockiert Release)

| # | Paket | Problem | Status | Behoben in |
|---|---|---|---|---|
| — | — | — | — | — |

Quellen: [PyPI Safety DB](https://pypi.org/), [CVE MITRE](https://cve.mitre.org/), `safety check`

---

## P1 — Breaking Changes bei Major-Update (dokumentieren vor Update)

| # | Paket | Von | Nach | Breaking Change | Aufwand |
|---|---|---|---|---|---|
| — | — | — | — | — | — |

---

## P2 — Deprecation-Warnings

| # | Paket | Warnung | Deadline | Maßnahme |
|---|---|---|---|---|
| — | — | — | — | — |

---

## P3 — Nice-to-have Features / Performance

| # | Paket | Neue Funktion | Nützlich für | Priorität |
|---|---|---|---|---|
| — | — | — | — | niedrig |

---

## Workflow

1. **Vor jedem Release:** Alle P0-Einträge abarbeiten; P1 dokumentiert und im CHANGELOG vermerkt.
2. **Quartalsmäßig:** `uv pip list --outdated` laufen lassen, Tabelle aktualisieren.
3. **Neue Deps:** Direkt beim Hinzufügen einen P2/P3-Eintrag anlegen, falls relevante Breaking-Change-Noten im Changelog.
