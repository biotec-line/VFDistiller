# -*- coding: utf-8 -*-
"""HTTP-Retry-Session, FASTA/FAI-Zugriff, HGVS-/SPDI-/Indel-Helfer und StreamingFastaToGVCF."""
from __future__ import annotations

import datetime
import gzip
import os
import re
import shutil
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from pyfaidx import Faidx
    HAVE_PYFAIDX = True
except ImportError:
    Faidx = None
    HAVE_PYFAIDX = False


class _DefaultConverterConfig:
    MAX_RETRIES = 3


_CONVERTER_ENV = {
    "config_cls": _DefaultConverterConfig,
    "fasta_paths": {},
    "fasta_urls": {
        "GRCh37": "https://ftp.ensembl.org/pub/grch37/current/fasta/homo_sapiens/dna/Homo_sapiens.GRCh37.dna.primary_assembly.fa.gz",
        "GRCh38": "https://ftp.ensembl.org/pub/current_fasta/homo_sapiens/dna/Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz",
    },
}


def configure_converters_environment(config_cls=None, fasta_paths=None, fasta_urls=None) -> None:
    """Bindet Laufzeit-Config sowie FASTA-Pfade und -URLs ein."""
    if config_cls is not None:
        _CONVERTER_ENV["config_cls"] = config_cls
    if fasta_paths is not None:
        _CONVERTER_ENV["fasta_paths"] = fasta_paths
    if fasta_urls is not None:
        _CONVERTER_ENV["fasta_urls"] = fasta_urls


def get_robust_session(retries=None, backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504)):
    if retries is None:
        retries = getattr(_CONVERTER_ENV["config_cls"], "MAX_RETRIES", 3)
    """
    Erstellt eine requests.Session mit robuster Retry-Strategie.
    """
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def load_fai_index(fai_path):
    idx = {}
    with open(fai_path, "r", encoding="ascii") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) != 5:
                continue  # leere/abweichende .fai-Zeile überspringen statt ValueError
            chrom, length, offset, line_bases, line_width = parts
            idx[chrom] = (int(length), int(offset), int(line_bases), int(line_width))
    return idx


def fetch_base_from_fasta(fasta_path, fai_index, chrom, pos):
    """
    Random-access fetch of a single REF base using .fai index.
    """
    if chrom not in fai_index:
        return "N"
    length, offset, line_bases, line_width = fai_index[chrom]
    if pos < 1 or pos > length:
        return "N"
    line_num = (pos - 1) // line_bases
    col_num = (pos - 1) % line_bases
    byte_offset = offset + line_num * line_width + col_num
    with open(fasta_path, "rb") as f:
        f.seek(byte_offset)
        b = f.read(1)
    try:
        return b.decode("ascii").upper()
    except Exception:
        return "N"


def indel_ref_alt_from_spdi(chrom: str, pos1: int, deleted: str, inserted: str, fetch_ref_base) -> tuple[str, str] | None:
    """
    Baut REF/ALT-Sequenzen für ein Indel aus SPDI-Daten.

    Parameter:
        chrom        - Chromosom (z.B. "1", "X")
        pos1         - 1-basierte Position der Variation
        deleted      - SPDI deleted_sequence (kann leer sein)
        inserted     - SPDI inserted_sequence (kann leer sein)
        fetch_ref_base - Funktion(chrom, pos1) -> Referenzbase

    Rückgabe:
        (REF, ALT) oder None, falls nicht bestimmbar
    """
    # Hole die Ankerbase links der Variation
    anchor = fetch_ref_base(chrom, pos1)
    if not anchor or anchor in (".", "-", "N"):
        return None

    # REF = Anker + deleted, ALT = Anker + inserted
    ref_seq = anchor + deleted.upper() if deleted else anchor
    alt_seq = anchor + inserted.upper() if inserted else anchor

    # Validierung: nur ACGT erlaubt
    if not all(c in "ACGT" for c in ref_seq):
        return None
    if not all(c in "ACGT" for c in alt_seq):
        return None

    return ref_seq, alt_seq


def make_hgvs_indel(chrom, pos, ref, alt):
    """
    Produce HGVS g.-notation for normalized indels.
    - Deletion:  chrN:g.start_enddel or chrN:g.posdel
    - Insertion: chrN:g.pos_pos+1insSEQ
    - DelIns:    chrN:g.start_enddelinsSEQ
    Assumes ref/alt are ACGT-only and left-normalized.
    """
    def _is_acgt(s: str) -> bool:
        return isinstance(s, str) and len(s) > 0 and all(c in "ACGT" for c in s)

    ch = str(chrom).replace("CHR", "").replace("chr", "")
    if not (_is_acgt(ref) and _is_acgt(alt)):
        return None

    # Trim common prefix
    i = 0
    while i < len(ref) and i < len(alt) and ref[i] == alt[i]:
        i += 1
    pos2 = pos + i
    ref2 = ref[i:]
    alt2 = alt[i:]

    # Trim common suffix
    j = 0
    while j < len(ref2) and j < len(alt2) and ref2[-1 - j] == alt2[-1 - j]:
        j += 1
    if j > 0:
        ref2 = ref2[:-j] if j < len(ref2) else ""
        alt2 = alt2[:-j] if j < len(alt2) else ""

    # Deletion
    if ref2 and not alt2:
        if len(ref2) == 1:
            return f"chr{ch}:g.{pos2}del"
        start = pos2
        end = pos2 + len(ref2) - 1
        return f"chr{ch}:g.{start}_{end}del"

    # Insertion
    if alt2 and not ref2:
        return f"chr{ch}:g.{pos2}_{pos2+1}ins{alt2}"

    # DelIns
    start = pos2
    end = pos2 + len(ref2) - 1
    return f"chr{ch}:g.{start}_{end}delins{alt2}"


def _is_pure_snv_key(key):
    chrom, pos, ref, alt, build = key
    return (
        isinstance(ref, str) and isinstance(alt, str) and
        len(ref) == 1 and len(alt) == 1 and
        all(c in "ACGT" for c in ref) and
        all(c in "ACGT" for c in alt) and
        ref != alt
    )


def _is_indel_key(key):
    chrom, pos, ref, alt, build = key
    if not (isinstance(ref, str) and isinstance(alt, str)):
        return False
    if not (all(c in "ACGT" for c in ref) and all(c in "ACGT" for c in alt)):
        return False
    return len(ref) != len(alt) or len(ref) > 1 or len(alt) > 1


def make_hgvs(chrom, pos, ref, alt):
    """
    HGVS g.-notation for SNVs and indels. Assumes VCF-normalized alleles.
    """
    key = (chrom, pos, ref, alt, None)
    if _is_pure_snv_key(key):
        ch = str(chrom).replace("CHR", "").replace("chr", "")
        return f"chr{ch}:g.{pos}{ref}>{alt}"
    if _is_indel_key(key):
        return make_hgvs_indel(chrom, pos, ref, alt)
    return None


HGVS_REGEX = re.compile(
    r"^chr[0-9XYM]+:g\.\d+(?:"
    r"[ACGT]>[ACGT]|"                    # SNV: g.123A>T
    r"del|"                               # Deletion: g.123del
    r"_\d+del|"                           # Range deletion: g.123_124del
    r"_\d+ins[ACGT]+|"                    # Range insertion: g.123_124insATG
    r"ins[ACGT]+|"                        # Simple insertion: g.123insATG
    r"_\d+delins[ACGT]+|"                 # Range delins: g.123_124delinsATG
    r"delins[ACGT]+"                      # Simple delins: g.123delinsATG
    r")$"
)


def is_valid_hgvs(hgvs: str) -> bool:
    """
    Validiert HGVS-Notation.
    FIX: Akzeptiert alle gueltigen HGVS-Formate inkl. Ranges
    """
    if not hgvs or not isinstance(hgvs, str):
        return False
    return bool(HGVS_REGEX.match(hgvs))


def normalize_variant(chrom, pos, ref, alt):
    while ref and alt and ref[0] == alt[0]:
        ref = ref[1:]
        alt = alt[1:]
        pos += 1
    while ref and alt and ref[-1] == alt[-1]:
        ref = ref[:-1]
        alt = alt[:-1]
    return chrom, pos, ref or "-", alt or "-"


def normalize_indel(chrom, pos, ref, alt, get_ref_base):
    """
    Links-normalisiert eine Indel und fügt ggf. Ankerbase hinzu.
    """
    if ref is None or alt is None:
        return None

    ref = ref.replace("-", "").replace(".", "")
    alt = alt.replace("-", "").replace(".", "")

    i = 0
    while i < len(ref) and i < len(alt) and ref[i] == alt[i]:
        i += 1
    pos += i
    ref = ref[i:]
    alt = alt[i:]

    j = 0
    while j < len(ref) and j < len(alt) and ref[-1 - j] == alt[-1 - j]:
        j += 1
    if j > 0:
        ref = ref[:-j] if j < len(ref) else ""
        alt = alt[:-j] if j < len(alt) else ""

    if ref == "" or alt == "":
        anchor_pos = max(1, pos - 1)
        anchor_base = get_ref_base(chrom, anchor_pos)
        if not anchor_base or anchor_base not in "ACGT":
            return None
        if ref == "":
            ref = anchor_base
            alt = anchor_base + alt
            pos = anchor_pos
        elif alt == "":
            alt = anchor_base
            ref = anchor_base + ref
            pos = anchor_pos

    if not (all(c in "ACGT" for c in ref) and all(c in "ACGT" for c in alt)):
        return None

    return chrom, pos, ref, alt


def get_ref_base(chrom, pos, fasta_path=None, fai_index=None, cache=None, build=None):
    """
    Liefert die Referenzbase (ACGT) für eine gegebene Chromosomenposition.
    Nutzt, falls vorhanden:
      - FASTA + FAI-Index
      - ansonsten Assembly-Cache (falls übergeben)
    Gibt 'N' zurück, wenn keine Base ermittelt werden kann.
    """
    # FASTA + FAI
    if fasta_path and fai_index:
        try:
            base = fetch_base_from_fasta(fasta_path, fai_index, chrom, pos).upper()
            if base in "ACGT":
                return base
        except Exception:
            pass

    # Cache (falls vorhanden)
    if cache and build:
        c_norm = str(chrom).replace("chr", "").upper()
        try:
            p_norm = int(pos)
        except (ValueError, TypeError):
            p_norm = pos
        for k in [
            (build, c_norm, p_norm),
            (build, chrom, pos),
            (c_norm, p_norm, build),
            (chrom, pos, build),
            f"{build}:{c_norm}:{p_norm}",
        ]:
            if k in cache:
                base = cache[k]
                if isinstance(base, str) and base.upper() in "ACGT":
                    return base.upper()
                elif isinstance(base, dict) and "ref" in base and str(base["ref"]).upper() in "ACGT":
                    return str(base["ref"]).upper()

    return "N"


class StreamingFastaToGVCF:
    def detect_build_from_fasta(self, fasta_path):
        """Versucht, den Build aus den ersten Headerzeilen der FASTA zu erkennen."""
        try:
            with open(fasta_path, "r", encoding="utf-8") as f:
                for _ in range(200):
                    line = f.readline()
                    if not line:
                        break
                    if line.startswith(">"):
                        low = line.lower()
                        if "grch38" in low or "hg38" in low:
                            return "GRCh38"
                        if "grch37" in low or "hg19" in low or "b37" in low:
                            return "GRCh37"
        except Exception as e:
            print(f"[WARN] Build-Erkennung fehlgeschlagen: {e}")
        return "GRCh38"  # Fallback

    def build_fasta_index(self, fasta_path):
        """
        Build a .fai using pyfaidx (samtools-compatible).
        """
        fai_path = fasta_path + ".fai"
        if os.path.exists(fai_path):
            print(f"[INFO] Index {fai_path} existiert bereits – überspringe.")
            return fai_path
        if not HAVE_PYFAIDX:
            raise RuntimeError("pyfaidx ist nicht installiert, kann FAI nicht erzeugen.")
        print(f"[INFO] Erstelle Index für {fasta_path} ...")
        Faidx(fasta_path)
        print(f"[INFO] Index erstellt: {fai_path}")
        return fai_path

    def ensure_fasta(self, build):
        fasta_path = _CONVERTER_ENV["fasta_paths"][build]
        if os.path.exists(fasta_path) and os.path.exists(fasta_path + ".fai"):
            return fasta_path
        url = _CONVERTER_ENV["fasta_urls"][build]
        gz_path = fasta_path + ".gz"
        print(f"[INFO] Lade Referenz {build} herunter...")
        with get_robust_session() as session:
            with session.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(gz_path, "wb") as f:
                    shutil.copyfileobj(r.raw, f)
        print("[INFO] Entpacke...")
        with gzip.open(gz_path, "rb") as f_in, open(fasta_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        os.remove(gz_path)
        self.build_fasta_index(fasta_path)
        return fasta_path

    def convert_streaming_gvcf(self, sample_fasta, build, out_vcf):
        if not build:
            build = self.detect_build_from_fasta(sample_fasta)
            print(f"[INFO] Automatisch ermittelter Build: {build}")

        ref_fasta = self.ensure_fasta(build)
        fai_index = load_fai_index(ref_fasta + ".fai")

        with open(sample_fasta, "r", encoding="utf-8") as sf, open(out_vcf, "w", encoding="utf-8") as vcf:
            vcf.write("##fileformat=VCFv4.2\n")
            vcf.write(f"##reference={build}\n")
            vcf.write("##source=StreamingFastaToGVCF\n")
            vcf.write(f"##reference_file={os.path.abspath(ref_fasta)}\n")
            vcf.write(f"##fileDate={datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d')}\n")
            vcf.write("##INFO=<ID=END,Number=1,Type=Integer,Description=\"End position of the block\">\n")
            vcf.write("##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">\n")
            vcf.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\n")

            chrom = None
            pos = 0
            block_start = None
            block_ref_base = None
            in_ref_block = False

            def flush_block(end_pos):
                nonlocal block_start, in_ref_block
                if in_ref_block and block_start is not None:
                    vcf.write(f"{chrom}\t{block_start}\t.\t{block_ref_base}\t.\t.\tPASS\tEND={end_pos}\tGT\t0/0\n")
                block_start = None
                in_ref_block = False

            for line in sf:
                if line.startswith(">"):
                    if in_ref_block:
                        flush_block(pos)
                    chrom = line[1:].strip().split()[0]
                    pos = 0
                    continue
                for base in line.strip().upper():
                    pos += 1
                    ref_base = fetch_base_from_fasta(ref_fasta, fai_index, chrom, pos)
                    if base not in ("A", "C", "G", "T", "N") or ref_base == "N":
                        continue
                    if base != ref_base:
                        if in_ref_block:
                            flush_block(pos - 1)
                        vcf.write(f"{chrom}\t{pos}\t.\t{ref_base}\t{base}\t100\tPASS\t.\tGT\t1/1\n")
                    else:
                        if not in_ref_block:
                            block_start = pos
                            block_ref_base = ref_base
                            in_ref_block = True
            if in_ref_block:
                flush_block(pos)
        print(f"[INFO] gVCF geschrieben: {out_vcf}")

    def convert_streaming_variants_only(self, sample_fasta, build, out_vcf):
        """
        Stream through sample FASTA and emit only variant positions vs. reference.
        No gVCF blocks, only ALT sites with a dummy homozygous alt genotype (1/1).
        """
        if not build:
            build = self.detect_build_from_fasta(sample_fasta)
            print(f"[INFO] Automatisch ermittelter Build: {build}")

        ref_fasta = self.ensure_fasta(build)
        fai_index = load_fai_index(ref_fasta + ".fai")

        with open(sample_fasta, "r", encoding="utf-8") as sf, open(out_vcf, "w", encoding="utf-8") as vcf:
            vcf.write("##fileformat=VCFv4.2\n")
            vcf.write(f"##reference={build}\n")
            vcf.write("##source=StreamingFastaToVCF\n")
            vcf.write(f"##reference_file={os.path.abspath(ref_fasta)}\n")
            vcf.write(f"##fileDate={datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d')}\n")
            vcf.write("##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">\n")
            vcf.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\n")

            chrom = None
            pos = 0
            for line in sf:
                if line.startswith(">"):
                    chrom = line[1:].strip().split()[0]
                    pos = 0
                    continue
                for base in line.strip().upper():
                    pos += 1
                    if base not in ("A", "C", "G", "T", "N"):
                        continue
                    ref_base = fetch_base_from_fasta(ref_fasta, fai_index, chrom, pos)
                    if ref_base == "N" or base == "N":
                        continue
                    if base != ref_base:
                        vcf.write(f"{chrom}\t{pos}\t.\t{ref_base}\t{base}\t100\tPASS\t.\tGT\t1/1\n")
