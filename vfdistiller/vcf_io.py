# -*- coding: utf-8 -*-
"""VCF/gVCF-I/O, Record-Parser, FORMAT/DP-Extraktion und Genotyp-Normalisierung."""
from __future__ import annotations

from contextlib import contextmanager
import gzip
import io
import os
import re
from typing import Optional


def is_gzipped(path: str) -> bool:
    """Prüft, ob der Pfad gzip- oder bgzip-komprimiert ist."""
    return path.lower().endswith((".gz", ".bgz"))


@contextmanager
def open_text_maybe_gzip(path: str):
    """
    Context manager for opening text files (gzipped or plain).
    Properly handles resource cleanup on exceptions.

    Args:
        path: File path (supports .gz, .bgz extensions)

    Yields:
        TextIO: Text stream

    Raises:
        RuntimeError: If file cannot be opened
    """
    bufsize = 1 << 20  # 1 MiB buffer

    file_obj = None
    buffered = None
    text_wrapper = None

    try:
        if is_gzipped(path):
            file_obj = gzip.GzipFile(filename=path, mode="rb")
            buffered = io.BufferedReader(file_obj, buffer_size=bufsize)
            text_wrapper = io.TextIOWrapper(
                buffered,
                encoding="utf-8",
                errors="replace",
                newline=""
            )
            yield text_wrapper
        else:
            file_obj = open(
                path,
                mode="r",
                encoding="utf-8",
                errors="replace",
                newline="",
                buffering=bufsize
            )
            yield file_obj

    except OSError as e:
        raise RuntimeError(f"Error opening {path}: {e}") from e

    finally:
        # Proper cleanup in reverse order
        if text_wrapper:
            try:
                text_wrapper.close()
            except Exception:
                pass
        if buffered:
            try:
                buffered.close()
            except Exception:
                pass
        if file_obj:
            try:
                file_obj.close()
            except Exception:
                pass


def is_vcf(path: str) -> bool:
    """Prüft, ob der Pfad wie eine VCF-Datei aussieht (plain oder gzipped)."""
    return path.lower().endswith((".vcf", ".vcf.gz"))


def _normalize_chrom_vcf(chrom: str) -> str:
    """
    Normalisiert Chromosom-Namen für konsistente Verarbeitung.

    V16 FIX: Zentrale Funktion für alle VCF-Parser.

    Transformationen:
    - chr1 -> 1
    - CHR1 -> 1
    - chrX -> X
    - chrM -> MT (VCF-Standard für Mitochondrien)
    - M -> MT

    Args:
        chrom: Rohes Chromosom aus VCF

    Returns:
        Normalisiertes Chromosom (ohne chr-Präfix, uppercase, M->MT)
    """
    c = str(chrom).replace("chr", "").replace("CHR", "").upper()
    # Mitochondrien-Normalisierung: M -> MT (Standard)
    if c == "M":
        c = "MT"
    return c


def _limit_vcf_line_to_alt(line: str, selected_alt: str) -> str:
    """
    Reduziert eine VCF-Zeile für den gefilterten Export auf eine sichtbare ALT.
    """
    if not selected_alt:
        return line

    line_body = line.rstrip("\r\n")
    newline = line[len(line_body):]
    parts = line_body.split("\t")
    if len(parts) < 5:
        return line

    selected_alt_norm = str(selected_alt).upper()
    for original_alt in parts[4].split(","):
        if original_alt.upper() == selected_alt_norm:
            parts[4] = original_alt
            return "\t".join(parts) + newline

    return line


def parse_vcf_records(path):
    """
    Streamt VCF-Records effizient:
    - Header wird genau einmal via 'header' am ersten Record mitgegeben.
    - INFO wird parsimoniously geparst; use split with maxsplit to reduce allocations.
    - Erzeugt fuer jede ALT nur ein schlankes key-tuple + minimalen record-dict.
    - Ziel: moeglichst wenig temporaere Listen/Dicts in inner loop.
    """
    header = []
    header_attached = False

    with open_text_maybe_gzip(path) as f:
        for line in f:
            if not line:
                continue
            if line[0] == "#":
                header.append(line.rstrip("\n"))
                continue
            if not line.strip():
                continue

            # --- Nur Python-Parsing hier ---
            parts = line.rstrip("\r\n").split("\t")
            if len(parts) < 8:
                continue

            chrom, pos_str, vid, ref, alt_str, qual, flt, info_str = parts[:8]
            fmt = parts[8] if len(parts) > 8 else None
            samples = parts[9:] if len(parts) > 9 else []

            try:
                pos = int(pos_str)
            except Exception:
                continue

            chrom_norm = _normalize_chrom_vcf(chrom)
            qual_norm = qual if qual not in (".", "") else None
            flt_norm = flt if flt not in (".", "") else None

            info_map = None
            if info_str and info_str != ".":
                info_map = {}
                for kv in info_str.split(";"):
                    if not kv:
                        continue
                    if "=" in kv:
                        k, v = kv.split("=", 1)
                        info_map[k] = v
                    else:
                        info_map[kv] = True

            alts = alt_str.split(",")
            for alt in alts:
                rec = {
                    "header": (header if not header_attached else None),
                    "chrom": chrom_norm,
                    "pos": pos,
                    "id": vid if vid != "." else None,
                    "ref": ref,
                    "alt": alt,
                    "qual": qual_norm,
                    "filter": flt_norm,
                    "info": info_str if info_map is None else info_map,
                    "fmt": fmt,
                    "samples": samples
                }
                yield rec

            header_attached = True


def parse_vcf_records_mmap(path: str):
    """
    MEMORY-MAPPED VCF PARSER für grosse unkomprimierte Dateien.
    FIX: Entfernt blockierende sys.stderr Aufrufe.
    """
    import mmap

    header = []
    header_attached = False

    try:
        with open(path, 'rb') as f:
            # Access=READ ist wichtig für Windows File-Locking Koexistenz
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                current_pos = 0
                file_size = mm.size()

                while current_pos < file_size:
                    newline_pos = mm.find(b'\n', current_pos)

                    if newline_pos == -1:
                        # Letzte Zeile ohne Newline am Ende
                        line_bytes = mm[current_pos:]
                        current_pos = file_size
                    else:
                        # Zeile bis Newline
                        line_bytes = mm[current_pos:newline_pos]
                        current_pos = newline_pos + 1

                    # Leere Zeilen überspringen
                    if not line_bytes or len(line_bytes) == 0:
                        continue

                    # Win-Kompatibilität: \r entfernen falls vorhanden
                    if line_bytes.endswith(b'\r'):
                        line_bytes = line_bytes[:-1]

                    try:
                        line = line_bytes.decode('utf-8', errors='replace')
                    except Exception:
                        continue

                    if line.startswith('#'):
                        header.append(line)
                        continue
                    if not line.strip():
                        continue

                    # --- Parsing Logic ---
                    # (Identisch zum Standard-Parser, aber optimiert)
                    parts = line.split('\t')
                    if len(parts) < 8:
                        continue

                    chrom, pos_str, vid, ref, alt_str, qual, flt, info_str = parts[:8]
                    fmt = parts[8] if len(parts) > 8 else None
                    samples = parts[9:] if len(parts) > 9 else []

                    try:
                        pos = int(pos_str)
                    except ValueError:
                        continue

                    chrom_norm = _normalize_chrom_vcf(chrom)
                    qual_norm = qual if qual not in (".", "") else None
                    flt_norm = flt if flt not in (".", "") else None

                    info_map = None
                    if info_str and info_str != ".":
                        # Quick-Parse für INFO (vermeidet overhead)
                        info_map = {}
                        for kv in info_str.split(";"):
                            if not kv:
                                continue
                            if "=" in kv:
                                k, v = kv.split("=", 1)
                                info_map[k] = v
                            else:
                                info_map[kv] = True

                    alts = alt_str.split(",")
                    for alt in alts:
                        rec = {
                            "header": (header if not header_attached else None),
                            "chrom": chrom_norm,
                            "pos": pos,
                            "id": vid if vid != "." else None,
                            "ref": ref,
                            "alt": alt,
                            "qual": qual_norm,
                            "filter": flt_norm,
                            "info": info_str if info_map is None else info_map,
                            "fmt": fmt,
                            "samples": samples
                        }
                        yield rec

                    header_attached = True

    except Exception:
        # Fallback auf Standard-Parser bei mmap-Fehlern (z.B. 0-Byte Dateien)
        # Keine blockierenden Prints hier!
        yield from parse_vcf_records(path)


def parse_vcf_records_smart(path: str):
    """
    INTELLIGENTER VCF PARSER: Waehlt beste Methode automatisch.
    FIX: Entfernt blockierende sys.stderr Aufrufe.
    """
    try:
        file_size = os.path.getsize(path)
        file_size_mb = file_size / (1024 * 1024)

        # Nutze mmap nur für große, unkomprimierte Dateien
        # mmap lohnt sich meist erst ab >50MB, darunter ist overhead höher
        use_mmap = (
            not is_gzipped(path) and
            file_size_mb > 50
        )

        if use_mmap:
            yield from parse_vcf_records_mmap(path)
        else:
            yield from parse_vcf_records(path)

    except Exception:
        # Fallback bei jeglichem Fehler in der Smart-Selection
        yield from parse_vcf_records(path)


def parse_vcf_keys(path, limit=None):
    """
    Streamt nur die Schlüssel (chrom, pos, ref, alt) aus einem VCF.
    - Header wird übersprungen.
    - ALT-Spalten werden gesplittet → pro ALT ein Key.
    - Keine INFO/QUAL/SAMPLES geparst.
    - Optionales Limit: bricht nach N Keys ab.
    """
    count = 0
    with open_text_maybe_gzip(path) as f:
        for line in f:
            if not line or line[0] == "#":
                continue

            parts = line.rstrip("\n").split("\t", 5)
            if len(parts) < 5:
                continue

            chrom, pos_str, vid, ref, alt_str = parts[:5]
            try:
                pos = int(pos_str)
            except Exception:
                continue

            chrom_norm = _normalize_chrom_vcf(chrom)
            for alt in alt_str.split(","):
                yield (chrom_norm, pos, ref.upper(), alt.upper())
                count += 1
                if limit and count >= limit:
                    return


def count_variants_exact(vcf_path: str) -> int:
    """
    Zählt exakt die Anzahl der Varianten in einer VCF.
    Dabei werden Multi-ALT-Zeilen korrekt berücksichtigt,
    indem jede ALT als eigene Variante gezählt wird.
    """
    total = 0
    with open_text_maybe_gzip(vcf_path) as f:
        for line in f:
            if not line or line[0] == "#":
                continue
            # ALT-Spalte extrahieren (5. Spalte, Index 4)
            parts = line.split("\t", 6)
            if len(parts) > 4:
                alt_str = parts[4]
                total += len(alt_str.split(","))
    return total


def get_genotype_label(fmt, samples, sample_index=0):
    """
    ✅ AKTUALISIERT: Unterstützt hemizygous Genotypen (X/Y/MT).

    VCF-Standard:
    - Autosomen: 0/0, 0/1, 1/1 (diploid)
    - chrX non-PAR (männlich): 0, 1 (hemizygous)
    - chrY (männlich): 0, 1 (hemizygous)
    - chrM/MT: 0, 1 (haploid)

    Args:
        fmt: FORMAT-String aus VCF
        samples: Sample-Werte aus VCF
        sample_index: Index des Samples (default: 0)

    Returns:
        "het" | "hom" | "ref" | "hemi" | "."
    """
    if not fmt or not samples:
        return "."

    fmt_keys = fmt.split(":")
    try:
        gt_idx = fmt_keys.index("GT")
    except ValueError:
        return "."

    if sample_index >= len(samples):
        return "."

    vals = samples[sample_index].split(":")
    if gt_idx >= len(vals):
        return "."

    gt = vals[gt_idx].strip()
    gt = gt.replace("|", "/")

    # ✅ KRITISCH: Hemizygous Check ZUERST (vor Diploid)
    if "/" not in gt:
        # Hemizygous/Haploid: chrX, chrY, MT
        if gt == ".":
            return "."
        try:
            allele = int(gt)
            if allele == 0:
                return "ref"  # 0 = Referenz
            else:
                return "hemi"  # 1, 2, etc. = hemizygous alternativ
        except (ValueError, TypeError):
            return "."

    # Diploid Mapping
    GENOTYPE_MAP = {
        "0/1": "het", "1/0": "het",
        "0/2": "het", "2/0": "het",
        "1/2": "het", "2/1": "het",
        "1/1": "hom", "2/2": "hom", "3/3": "hom",
        "0/0": "ref",
        "./.": ".", "./0": ".", "0/.": ".",
    }

    normalized = GENOTYPE_MAP.get(gt)
    if normalized:
        return normalized

    # Fallback
    alleles = gt.split("/")
    if len(alleles) != 2:
        return "."

    try:
        if "." in alleles:
            return "."
        a1_int = int(alleles[0])
        a2_int = int(alleles[1])

        if a1_int == 0 and a2_int == 0:
            return "ref"
        elif a1_int == a2_int:
            return "hom"
        else:
            return "het"
    except (ValueError, TypeError):
        return "."


def normalize_genotype_display(genotype_str: str) -> str:
    """
    Normalisiert bereits gespeicherte Genotypen für konsistente Anzeige.

    Args:
        genotype_str: Genotyp aus DB/Cache

    Returns:
        Normalisierter Genotyp ("het" | "hom" | "ref" | "hemi" | ".")
    """
    if not genotype_str:
        return "."

    gt = str(genotype_str).strip().lower()

    # Bereits normalisiert?
    if gt in ("het", "hom", "ref", "hemi", "."):
        return gt

    # VCF-Format → durchleiten via get_genotype_label
    if "/" in gt or "|" in gt:
        # Simuliere FMT/Sample-Format
        return get_genotype_label("GT", [gt], 0)

    # Unbekanntes Format → .
    return "."


def _extract_format_field(rec: dict, field_name: str) -> Optional[str]:
    """
    Extrahiert einen spezifischen Wert aus dem FORMAT-String eines VCF-Records.

    Args:
        rec: VCF-Record dict (unterstützt 'sample' aus orig_records oder 'samples' aus Parser)
        field_name: Name des FORMAT-Feldes (z.B. "DP", "GQ", "AD")

    Returns:
        Feld-Wert oder None

    Beispiele:
        _extract_format_field(rec, "DP")  # "45"
        _extract_format_field(rec, "GQ")  # "99"
    """
    fmt = rec.get("fmt")
    if not fmt or not isinstance(fmt, str):
        return None

    fmt_fields = fmt.split(":")
    if field_name not in fmt_fields:
        return None
    field_index = fmt_fields.index(field_name)

    # Sample-Werte: Unterstütze sowohl "sample" (String aus orig_records)
    # als auch "samples" (Liste aus VCF-Parser)
    sample_raw = rec.get("sample")
    if not sample_raw:
        samples_list = rec.get("samples")
        if samples_list and isinstance(samples_list, (list, tuple)) and len(samples_list) > 0:
            sample_raw = samples_list[0]

    if not sample_raw or not isinstance(sample_raw, str):
        return None

    # Multi-Sample Guard: falls sample_raw noch Tabulatoren enthält
    if "\t" in sample_raw:
        sample_raw = sample_raw.split("\t")[0]

    try:
        sample_fields = sample_raw.split(":")
        if len(sample_fields) > field_index:
            value = sample_fields[field_index].strip()
            if value and value != ".":
                return value
    except (IndexError, ValueError, AttributeError):
        pass

    return None


def _get_dp_value(rec: dict) -> Optional[str]:
    """
    ✅ KORRIGIERT: Extrahiert DP (Read Depth) NUR aus VCF-Record.

    ⚠️ WICHTIG: DP wird NICHT in der DB gespeichert!
              DP kommt ausschließlich aus dem Original-VCF-Record.

    Priorität:
    1. FORMAT-Feld DP (aus Sample)
    2. INFO-Feld DP (multi-sample)

    Args:
        rec: VCF-Record dict aus orig_records

    Returns:
        DP-Wert als String oder None

    V16 FIX: Unterstützt sowohl String- als auch Dict-Format für INFO.
    """
    # 1. FORMAT-Feld DP (bevorzugt - sample-spezifisch)
    dp_format = _extract_format_field(rec, "DP")
    if dp_format:
        return dp_format

    # 2. INFO-Feld DP (fallback - multi-sample gesamt)
    info = rec.get("info")
    if info:
        # V16 FIX: INFO kann Dict (vom Parser) oder String sein
        if isinstance(info, dict):
            dp_val = info.get("DP")
            if dp_val is not None:
                return str(dp_val)
        elif isinstance(info, str) and "DP=" in info:
            match = re.search(r'DP=(\d+)', info)
            if match:
                return match.group(1)

    # ❌ NICHT aus DB holen - DP wird dort nicht gespeichert!
    return None


def _build_format_fields(rec: dict, genotype: str) -> tuple:
    """
    ✅ KORRIGIERT: Konstruiert FORMAT-String und Sample-Werte für VCF-Export.

    Nutzt nur VCF-Record-Daten, keine DB-Felder.

    Args:
        rec: VCF-Record dict aus orig_records
        genotype: Normalisierter Genotyp ("het", "hom", "ref", "hemi")

    Returns:
        (format_string, sample_string)

    Beispiel:
        _build_format_fields(rec, "het")
        # → ("GT:DP:GQ:AD", "0/1:45:99:20,25")
    """
    format_fields = ["GT"]
    sample_values = [genotype]

    # DP
    dp_value = _get_dp_value(rec)
    if dp_value:
        format_fields.append("DP")
        sample_values.append(dp_value)

    # GQ (Genotype Quality)
    gq_value = _extract_format_field(rec, "GQ")
    if gq_value:
        format_fields.append("GQ")
        sample_values.append(gq_value)

    # AD (Allelic Depth)
    ad_value = _extract_format_field(rec, "AD")
    if ad_value:
        format_fields.append("AD")
        sample_values.append(ad_value)

    # PL (Phred-scaled Likelihoods)
    pl_value = _extract_format_field(rec, "PL")
    if pl_value:
        format_fields.append("PL")
        sample_values.append(pl_value)

    format_str = ":".join(format_fields)
    sample_str = ":".join(sample_values)

    return format_str, sample_str
