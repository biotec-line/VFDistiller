# Changelog / Änderungsprotokoll

Alle wesentlichen Änderungen an diesem Projekt werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [Unreleased]

### Hinzugefügt / Added
- `CODE_OF_CONDUCT.md` and `CONTRIBUTING.md` added as repository community files.
- Root application icon added for packaging and repository metadata.
- `PORTIERUNGSPLAN.md` added for the GitHub-only Linux/macOS desktop portability strategy.

### Entfernt / Removed
- Removed the planned Web/PWA companion track from the active porting strategy.

### Geändert / Changed
- README files now document the current GitHub-only distribution and repository privacy/ignore policy.
- README test instructions now clarify the split between deterministic pytest coverage and manual benchmark scripts.
- `.gitignore` now covers internal test locks, secrets, private keys, installer artifacts, and LLM control files.
- `SECURITY.md` and `PRIVACY_POLICY.md` updated after the Microsoft Store withdrawal.
- `pytest.ini` now limits automated test collection to the maintained `tests/` suite.
- Downloaded Ensembl GTF annotation archives are no longer tracked and remain local via `.gitignore`.
- `START.bat` now prefers the local `dist\VFDistiller.exe` and falls back to the Python source entry point.
- German README/UI wording now uses real umlauts for touched end-user text.
- `.gitattributes` added for stable line endings and binary asset handling.

### Behoben / Fixed
- Removed stale contributing-template placeholders and replaced the missing CLA reference with DCO guidance.
- Performance benchmark scripts no longer expose a `test_correctness()` function that pytest can miscollect as a fixture-based test.
- Cython accelerator console logging no longer crashes benchmark scripts on Windows cp1252 terminals.
- Performance benchmark scripts now tolerate Windows console encodings for their own status output.
- LightDB lookups now close SQLite connections in a `finally` block, preventing file-lock leaks on cursor or setup failures.
- LightDB lookup setup also handles `sqlite3.connect()` failures without masking the original fallback result.

### Entfernt / Removed
- Removed stale internal cleanup concept notes from the public README documentation tree.

## [1.0.0] - YYYY-MM-DD

### Hinzugefügt / Added
- Erstveröffentlichung / Initial release
