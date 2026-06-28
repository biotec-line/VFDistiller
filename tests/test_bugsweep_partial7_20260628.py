# -*- coding: utf-8 -*-
"""
Bugsweep Block 7 (2026-06-28) — FASTA open() Encoding-Konsistenz
=================================================================

Echte Bugs: open() ohne encoding= in StreamingFastaToGVCF und load_fasta.

Kontext: convert_streaming_gvcf / convert_streaming_variants_only schreiben
eine temporäre VCF-Datei. _process_fasta liest sie mit encoding="utf-8"
(bereits in Block 5b gesichert). Das cp1252-Standardencoding auf Windows
erzeugt einen UnicodeDecodeError, wenn der Pfad oder ##reference-Header
Nicht-ASCII enthält (z.B. C:\\Users\\Müller\\...).

Teststrategie: Statische Quelltext-Assertions (SRC = Dateitext), da die
StreamingFastaToGVCF-Methoden FASTA-Dateien + FAI-Index + externe
Subprocess-Calls voraussetzen und keinen leichten Mock-Seam bieten.
"""
import pathlib
import re

SRC_FILE = (
    pathlib.Path(__file__).parent.parent / "Variant_Fusion_pro_V17.py"
)


def _src() -> str:
    return SRC_FILE.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# A1: detect_build_from_fasta — liest FASTA-Header
# ---------------------------------------------------------------------------

def test_detect_build_encoding():
    """detect_build_from_fasta öffnet die FASTA-Datei mit encoding='utf-8'."""
    src = _src()
    # Suche innerhalb der detect_build_from_fasta-Funktion
    fn_start = src.index("def detect_build_from_fasta(")
    fn_block = src[fn_start : fn_start + 800]
    assert 'open(fasta_path, "r", encoding="utf-8")' in fn_block, (
        "detect_build_from_fasta: open(fasta_path, 'r') fehlt encoding='utf-8'; "
        "auf Windows würde cp1252 für nicht-ASCII-FASTA-Header verwendet."
    )


# ---------------------------------------------------------------------------
# A2: load_fasta — liest gesamte FASTA-Sequenz in Speicher
# ---------------------------------------------------------------------------

def test_load_fasta_encoding():
    """load_fasta öffnet die FASTA-Datei mit encoding='utf-8'."""
    src = _src()
    fn_start = src.index("def load_fasta(self, fasta_path")
    fn_block = src[fn_start : fn_start + 400]
    assert 'open(fasta_path, "r", encoding="utf-8")' in fn_block, (
        "load_fasta: open(fasta_path, 'r') fehlt encoding='utf-8'; "
        "FASTA-Dateien mit Nicht-ASCII-Headern würden auf Windows scheitern."
    )


# ---------------------------------------------------------------------------
# B1: convert_streaming_gvcf — Writer der temporären VCF-Datei
# ---------------------------------------------------------------------------

def test_convert_streaming_gvcf_encoding():
    """
    convert_streaming_gvcf öffnet sample_fasta und out_vcf mit encoding='utf-8'.

    Kritisch: _process_fasta (Block 5b) liest out_vcf mit encoding='utf-8'.
    Fehlende Angabe auf Schreib-Seite → UnicodeDecodeError auf Read-Seite.
    """
    src = _src()
    fn_start = src.index("def convert_streaming_gvcf(")
    fn_block = src[fn_start : fn_start + 1200]
    assert (
        'open(sample_fasta, "r", encoding="utf-8") as sf, '
        'open(out_vcf, "w", encoding="utf-8") as vcf'
    ) in fn_block, (
        "convert_streaming_gvcf: fehlende encoding='utf-8' beim Öffnen von "
        "sample_fasta/out_vcf. Write/Read-Asymmetrie mit _process_fasta."
    )


# ---------------------------------------------------------------------------
# B2: convert_streaming_variants_only — Write-Seite des Variant-only-Pfads
# ---------------------------------------------------------------------------

def test_convert_streaming_variants_only_encoding():
    """
    convert_streaming_variants_only öffnet sample_fasta/out_vcf mit encoding='utf-8'.
    """
    src = _src()
    fn_start = src.index("def convert_streaming_variants_only(")
    fn_block = src[fn_start : fn_start + 1200]
    assert (
        'open(sample_fasta, "r", encoding="utf-8") as sf, '
        'open(out_vcf, "w", encoding="utf-8") as vcf'
    ) in fn_block, (
        "convert_streaming_variants_only: fehlende encoding='utf-8'; "
        "VCF-Output wäre auf Windows in cp1252 kodiert."
    )


# ---------------------------------------------------------------------------
# C1: Kein verbleibender open(sample_fasta) ohne encoding im gesamten Quelltext
# ---------------------------------------------------------------------------

def test_no_sample_fasta_open_without_encoding():
    """
    Sicherstellt, dass kein weiteres open(sample_fasta, "r") ohne encoding= existiert.
    """
    src = _src()
    bad_pattern = re.compile(r'open\(sample_fasta,\s*"r"\)')
    matches = bad_pattern.findall(src)
    assert not matches, (
        f"Noch {len(matches)} open(sample_fasta, 'r') ohne encoding= gefunden: {matches}"
    )


# ---------------------------------------------------------------------------
# C2: Kein verbleibender open(fasta_path, "r") ohne encoding in FASTA-Funktionen
# ---------------------------------------------------------------------------

def test_no_fasta_path_open_without_encoding():
    """
    Sicherstellt, dass kein open(fasta_path, "r") ohne encoding= verbleibt.
    """
    src = _src()
    bad_pattern = re.compile(r'open\(fasta_path,\s*"r"\)')
    matches = bad_pattern.findall(src)
    assert not matches, (
        f"Noch {len(matches)} open(fasta_path, 'r') ohne encoding= gefunden: {matches}"
    )
