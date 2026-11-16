# -*- coding: utf-8 -*-
"""Headless-CLI für das Core-Paket `vfdistiller` (ohne GUI/tkinter)."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any, Optional, Sequence

from vfdistiller.quality import QualityManager
from vfdistiller.vcf_io import (
    _limit_vcf_line_to_alt,
    _normalize_chrom_vcf,
    open_text_maybe_gzip,
    parse_vcf_records,
)

__version__ = "17.0.2"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vfdistiller",
        description="VFDistiller headless core CLI (inspect, filter, db-stats)",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Zeigt die Paketversion an und beendet das Programm.",
    )
    subparsers = parser.add_subparsers(dest="command")

    p_inspect = subparsers.add_parser("inspect", help="VCF/gVCF zusammenfassen")
    p_inspect.add_argument("vcf", help="Pfad zur VCF- oder .vcf.gz-Datei")
    p_inspect.add_argument("--limit", type=int, default=None, help="Maximale Record-Anzahl")
    p_inspect.add_argument("--json", action="store_true", help="Ausgabe als JSON")

    p_filter = subparsers.add_parser("filter", help="QualityManager auf VCF anwenden")
    p_filter.add_argument("vcf", help="Pfad zur VCF- oder .vcf.gz-Datei")
    p_filter.add_argument("--out-vcf", default=None, help="Optionaler Ausgabepfad für bestandene Records")
    p_filter.add_argument(
        "--preset",
        default="clinical",
        choices=sorted(QualityManager.PRESETS.keys()),
        help="QualityManager-Preset (Default: clinical)",
    )
    p_filter.add_argument("--min-dp", type=int, default=None, help="Minimales DP überschreiben")
    p_filter.add_argument("--min-qual", type=float, default=None, help="Minimales QUAL überschreiben")
    p_filter.add_argument("--require-pass", action="store_true", default=None, help="Nur PASS/.-Records zulassen")
    p_filter.add_argument("--exclude-hom-ref", action="store_true", default=None, help="0/0-Genotypen ausfiltern")
    p_filter.add_argument("--keep-hom-ref", action="store_true", help="0/0-Genotypen behalten (z. B. RMA)")
    p_filter.add_argument("--sample-index", type=int, default=0, help="Sample-Spaltenindex (0-basiert)")
    p_filter.add_argument("--json", action="store_true", help="Ausgabe als JSON")

    p_db = subparsers.add_parser("db-stats", help="SQLite-VariantDB-Statistiken auslesen")
    p_db.add_argument("sqlite_path", help="Pfad zur SQLite-Datenbank")
    p_db.add_argument("--json", action="store_true", help="Ausgabe als JSON")

    return parser


def _cmd_inspect(args: argparse.Namespace) -> int:
    vcf_path = Path(args.vcf)
    if not vcf_path.is_file():
        print(f"Fehler: VCF-Datei nicht gefunden: {vcf_path}", file=sys.stderr)
        return 2
    if args.limit is not None and args.limit < 0:
        print("Fehler: --limit darf nicht negativ sein.", file=sys.stderr)
        return 2

    qm = QualityManager(preset="permissive")
    samples = qm.get_vcf_sample_names(str(vcf_path))
    total = 0
    pass_count = 0
    chroms: list[str] = []
    seen_chroms: set[str] = set()

    for rec in parse_vcf_records(str(vcf_path)):
        if args.limit is not None and total >= args.limit:
            break
        total += 1
        chrom = rec.get("chrom")
        if chrom and chrom not in seen_chroms:
            seen_chroms.add(chrom)
            chroms.append(chrom)
        if (rec.get("filter") or ".") in ("PASS", "."):
            pass_count += 1

    payload = {
        "file": str(vcf_path),
        "records": total,
        "pass_or_dot_records": pass_count,
        "samples": samples,
        "sample_count": len(samples),
        "chromosomes": chroms,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(
            f"{vcf_path.name}: {total} Records, {pass_count} PASS/., "
            f"{len(samples)} Samples, {len(chroms)} Chromosomen"
        )
    return 0


def _parse_line_for_quality(line: str, sample_index: int) -> tuple[list[dict[str, Any]], str]:
    body = line.rstrip("\r\n")
    parts = body.split("\t")
    if len(parts) < 8:
        return [], body
    chrom, pos_str, vid, ref, alt_str, qual, flt, info_str = parts[:8]
    fmt = parts[8] if len(parts) > 8 else None
    samples = parts[9:] if len(parts) > 9 else []
    try:
        pos = int(pos_str)
    except ValueError:
        return [], body

    selected_samples = (
        [samples[sample_index]] if 0 <= sample_index < len(samples) else []
    )
    info_map: Optional[dict[str, Any]] = None
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

    records: list[dict[str, Any]] = []
    for alt in alt_str.split(","):
        records.append(
            {
                "chrom": _normalize_chrom_vcf(chrom),
                "pos": pos,
                "id": vid if vid != "." else None,
                "ref": ref,
                "alt": alt,
                "qual": qual if qual not in (".", "") else None,
                "filter": flt if flt not in (".", "") else None,
                "info": info_str if info_map is None else info_map,
                "fmt": fmt,
                "samples": selected_samples,
            }
        )
    return records, body


def _cmd_filter(args: argparse.Namespace) -> int:
    vcf_path = Path(args.vcf)
    if not vcf_path.is_file():
        print(f"Fehler: VCF-Datei nicht gefunden: {vcf_path}", file=sys.stderr)
        return 2
    if args.sample_index < 0:
        print("Fehler: --sample-index darf nicht negativ sein.", file=sys.stderr)
        return 2

    qm = QualityManager(preset=args.preset)
    custom_kwargs: dict[str, Any] = {}
    if args.require_pass is True:
        custom_kwargs["filter_pass_only"] = True
    if args.min_qual is not None:
        custom_kwargs["qual_threshold"] = args.min_qual
    if args.min_dp is not None:
        custom_kwargs["min_dp"] = args.min_dp
        custom_kwargs["use_dp_filter"] = True
    if args.keep_hom_ref:
        custom_kwargs["filter_homref"] = False
    elif args.exclude_hom_ref is True:
        custom_kwargs["filter_homref"] = True

    if custom_kwargs:
        qm.set_custom_settings(**custom_kwargs)

    out_handle = None
    out_path_str: Optional[str] = None
    if args.out_vcf:
        out_path = Path(args.out_vcf)
        if out_path.parent:
            os.makedirs(out_path.parent, exist_ok=True)
        out_path_str = str(out_path)
        out_handle = open(out_path, "w", encoding="utf-8", newline="\n")

    passed_alts = 0
    try:
        with open_text_maybe_gzip(str(vcf_path)) as fh:
            for raw_line in fh:
                if not raw_line:
                    continue
                if raw_line.startswith("#"):
                    if out_handle is not None:
                        out_handle.write(raw_line.rstrip("\r\n") + "\n")
                    continue
                if not raw_line.strip():
                    continue

                line_records, body = _parse_line_for_quality(raw_line, args.sample_index)
                passing_for_line = [rec["alt"] for rec in line_records if qm.passes(rec)]
                passed_alts += len(passing_for_line)
                if out_handle is not None and passing_for_line:
                    if len(passing_for_line) == len(line_records):
                        out_handle.write(body + "\n")
                    else:
                        for alt in passing_for_line:
                            out_handle.write(_limit_vcf_line_to_alt(body, alt) + "\n")
    finally:
        if out_handle is not None:
            out_handle.close()

    stats = qm.get_stats()
    payload = {
        "input": str(vcf_path),
        "preset": qm.current_preset,
        "settings": qm.get_settings(),
        "total": stats["total_checked"],
        "passed": passed_alts,
        "rejected": stats["total_checked"] - passed_alts,
        "stats": stats,
        "out_vcf": out_path_str,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(
            f"Gefiltert ({qm.current_preset}): {passed_alts}/{stats['total_checked']} bestanden"
            + (f" -> {out_path_str}" if out_path_str else "")
        )
    return 0


def _cmd_db_stats(args: argparse.Namespace) -> int:
    db_path = Path(args.sqlite_path)
    if not db_path.is_file():
        print(f"Fehler: SQLite-Datenbank nicht gefunden: {db_path}", file=sys.stderr)
        return 2

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        print(f"Fehler beim Öffnen der Datenbank: {exc}", file=sys.stderr)
        return 2

    try:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        if "variants" not in tables:
            print("Fehler: Tabelle 'variants' fehlt in der Datenbank.", file=sys.stderr)
            return 2

        total_variants = int(conn.execute("SELECT COUNT(*) FROM variants").fetchone()[0])
        by_build = {
            (row[0] or "unknown"): int(row[1])
            for row in conn.execute("SELECT build, COUNT(*) FROM variants GROUP BY build").fetchall()
        }
        af_known = int(conn.execute("SELECT COUNT(*) FROM variants WHERE af_filter_mean IS NOT NULL").fetchone()[0])
        annotation_cache_count = (
            int(conn.execute("SELECT COUNT(*) FROM annotation_cache").fetchone()[0])
            if "annotation_cache" in tables
            else 0
        )
    finally:
        conn.close()

    payload = {
        "database": str(db_path),
        "total_variants": total_variants,
        "af_populated": af_known,
        "af_missing": total_variants - af_known,
        "by_build": by_build,
        "annotation_cache_entries": annotation_cache_count,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"{db_path.name}: {total_variants} Varianten ({af_known} mit AF), Cache={annotation_cache_count}")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Haupteinstiegspunkt der Headless-CLI."""
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2

    if getattr(args, "version", False):
        print(f"vfdistiller {__version__}")
        return 0

    if args.command == "inspect":
        return _cmd_inspect(args)
    if args.command == "filter":
        return _cmd_filter(args)
    if args.command == "db-stats":
        return _cmd_db_stats(args)

    parser.print_help()
    return 2
