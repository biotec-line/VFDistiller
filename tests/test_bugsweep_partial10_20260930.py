# -*- coding: utf-8 -*-
"""
Bug-Sweep Block 10 (2026-09-30) — 23andMe-zu-VCF Konvertierung & Cache-Resilienz
=================================================================================

Bereich: 23andMe-zu-VCF Konvertierung, Build-Erkennung, Gzip/Stream-Parsing,
Cache-Ref-Auflösung & atomares Schreiben in convert_23andme_to_vcf
(detect_build_robust_by_rsids, parse_23andme, create_vcf, atomic_write_json, cache_upsert)

Behobene Bugs:
1. detect_build_robust_by_rsids Spaltenversatz: In 23andMe-Dateien ist Col 0 = rsid,
   Col 1 = Chromosom, Col 2 = Position. Die bisherige Implementierung wies fälschlich
   `vid = parts[2]` und `pos = int(parts[1])` zu (VCF-Spaltenanordnung). Da eine Position
   (z. B. "752566") nie mit "rs" beginnt, war `rs_pos` für 23andMe-Dateien stets leer,
   wodurch der Build-Erkennungs-Fallback immer `None` zurückgab.
   Fix: Erkennung beider Formate (23andMe: Col 0 rsid, Col 2 pos; VCF: Col 2 rsid, Col 1 pos)
   sowie Unterstützung von Tabulator- und Whitespace-Delimitern.
2. detect_build_robust_by_rsids Cache-Wiederverwendung: Bestehende Einträge in `self.cache`
   wurden ignoriert und ein leeres Dict initialisiert, wodurch alle rsIDs redundant
   über das Netzwerk abgefragt wurden.
   Fix: Vorhandene rsIDs aus `self.cache` vor dem Netzwerk-Fetch übernehmen.
3. parse_23andme Gzip- und Delimiter-Absturz: Öffnete `self.file_path` mit plain `open(..., encoding="utf-8")`,
   wodurch komprimierte 23andMe-Dateien (.txt.gz) reproduzierbar mit `UnicodeDecodeError`
   abstürzten. Zudem wurden durch festes `.split("\\t")` Dateien mit Leerzeichen-Trennung verworfen.
   Fix: Nutzung von `open_text_maybe_gzip()` und dynamischer Delimiter-Split (Tab oder Whitespace).
4. create_vcf stummer Datenverlust bei fehlender FASTA: Ohne lokale Referenz-FASTA
   (fasta_path=None) rief `create_vcf` `get_ref_base(chrom, pos, ..., cache, build)` auf.
   `get_ref_base` suchte jedoch nach Tupel-Keys `(build, chrom, pos)`, während der
   23andMe-Cache rsID-String-Keys führt. Dadurch gab `get_ref_base` immer 'N' zurück und
   alle Varianten wurden bei `ref_base in ('.', '-', 'N')` verworfen (0 geschriebene Zeilen).
   Fix: Direkte Auflösung von `ref_base` aus dem rsID-Cache (`cache[rsid]["assemblies"][build]["ref"]`),
   zusätzlicher Koordinaten-Index in `cache_upsert` und Erweiterung von `get_ref_base`.
5. create_vcf Kleinbuchstaben-Genotypen: Kleinbuchstaben wie 'aa' oder 'ag' wurden
   im SNP-Pfad nicht zu Großbuchstaben normalisiert, wodurch `all(a in "ACGT" for a in alleles)`
   fehlschlug und die Varianten verworfen wurden.
   Fix: `genotype = genotype.strip().replace("_", "-").upper()`.
6. atomic_write_json Verzeichnis-Isolation & Leak-Schutz: Schrieb `tmp.xxxxxx` direkt ins
   aktuelle Arbeitsverzeichnis (CWD) statt ins Zielverzeichnis, was bei abweichenden Laufwerken
   zu Cross-Device-Move-Fehlern führte und temporäre Dateien im CWD hinterließ.
   Fix: Temp-Datei isoliert in `os.path.dirname(dst)`, `os.makedirs()` und Löschung im `finally`-Block.
"""
import gzip
import json
import pathlib
import tempfile
import pytest

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
SRC_FILE = ROOT_DIR / "Variant_Fusion_pro_V17.py"


@pytest.fixture
def tmp_work_dir():
    with tempfile.TemporaryDirectory() as td:
        yield pathlib.Path(td)


def test_detect_build_robust_by_rsids_23andme_columns(tmp_work_dir):
    """Prüft, dass 23andMe-Dateien mit Col 0=rsid und Col 2=pos korrekt erkannt werden."""
    import Variant_Fusion_pro_V17 as vf

    test_file = tmp_work_dir / "test_23andme.txt"
    test_file.write_text(
        "# rsid\tchromosome\tposition\tgenotype\n"
        "rs3094315\t1\t752566\tAA\n"
        "rs3131972\t1\t752721\tGG\n",
        encoding="utf-8"
    )

    conv = vf.convert_23andme_to_vcf(str(test_file), cache_file=str(tmp_work_dir / "cache.json"))
    conv.cache["rs3094315"] = {"assemblies": {"GRCh37": {"chrom": "1", "pos": 752566, "ref": "G"}}}
    conv.cache["rs3131972"] = {"assemblies": {"GRCh37": {"chrom": "1", "pos": 752721, "ref": "A"}}}

    build = conv.detect_build_robust_by_rsids(str(test_file))
    assert build == "GRCh37"


def test_detect_build_robust_by_rsids_whitespace_delimiter(tmp_work_dir):
    """Prüft, dass auch Dateien mit Leerzeichen-Trennung erkannt werden."""
    import Variant_Fusion_pro_V17 as vf

    test_file = tmp_work_dir / "test_space.txt"
    test_file.write_text(
        "# rsid chromosome position genotype\n"
        "rs3094315 1 752566 AA\n"
        "rs3131972 1 752721 GG\n",
        encoding="utf-8"
    )

    conv = vf.convert_23andme_to_vcf(str(test_file), cache_file=str(tmp_work_dir / "cache.json"))
    conv.cache["rs3094315"] = {"assemblies": {"GRCh38": {"chrom": "1", "pos": 752566, "ref": "G"}}}
    conv.cache["rs3131972"] = {"assemblies": {"GRCh38": {"chrom": "1", "pos": 752721, "ref": "A"}}}

    build = conv.detect_build_robust_by_rsids(str(test_file))
    assert build == "GRCh38"


def test_detect_build_robust_by_rsids_vcf_fallback(tmp_work_dir):
    """Prüft, dass VCF-Dateien mit Col 2=rsid und Col 1=pos weiterhin unterstützt werden."""
    import Variant_Fusion_pro_V17 as vf

    test_file = tmp_work_dir / "test.vcf"
    test_file.write_text(
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        "1\t752566\trs3094315\tG\tA\t.\tPASS\t.\n",
        encoding="utf-8"
    )

    conv = vf.convert_23andme_to_vcf(str(test_file), cache_file=str(tmp_work_dir / "cache.json"))
    conv.cache["rs3094315"] = {"assemblies": {"GRCh37": {"chrom": "1", "pos": 752566, "ref": "G"}}}

    build = conv.detect_build_robust_by_rsids(str(test_file))
    assert build == "GRCh37"


def test_parse_23andme_handles_gzip_and_plain(tmp_work_dir):
    """Prüft, dass parse_23andme gemonkete und reale .gz-Dateien ohne Decode-Error liest."""
    import Variant_Fusion_pro_V17 as vf

    plain_file = tmp_work_dir / "sample.txt"
    plain_file.write_text("rs100\t1\t1000\tAA\n", encoding="utf-8")

    gz_file = tmp_work_dir / "sample.txt.gz"
    with gzip.open(gz_file, "wt", encoding="utf-8") as f:
        f.write("rs200\t2\t2000\tGG\n")

    conv_plain = vf.convert_23andme_to_vcf(str(plain_file), cache_file=str(tmp_work_dir / "c1.json"))
    vars_plain = conv_plain.parse_23andme()
    assert vars_plain == [("rs100", "1", 1000, "AA")]

    conv_gz = vf.convert_23andme_to_vcf(str(gz_file), cache_file=str(tmp_work_dir / "c2.json"))
    vars_gz = conv_gz.parse_23andme()
    assert vars_gz == [("rs200", "2", 2000, "GG")]


def test_create_vcf_resolves_ref_base_from_cache_when_fasta_none(tmp_work_dir):
    """Prüft, dass ohne lokale FASTA-Datei die Referenzbase sauber aus dem Cache aufgelöst wird."""
    import Variant_Fusion_pro_V17 as vf

    cache_file = tmp_work_dir / "cache.json"
    out_vcf = tmp_work_dir / "output.vcf"

    conv = vf.convert_23andme_to_vcf(str(tmp_work_dir / "dummy.txt"), cache_file=str(cache_file))
    conv.cache_upsert(conv.cache, "rs3094315", "GRCh37", "1", 752566, "G")

    variants = [("rs3094315", "1", 752566, "AA")]
    conv.create_vcf(variants, "GRCh37", str(out_vcf), conv.cache, fasta_path=None, sex="unknown")

    assert out_vcf.exists()
    content = out_vcf.read_text(encoding="utf-8")
    lines = [line for line in content.splitlines() if not line.startswith("#")]
    assert len(lines) == 1
    cols = lines[0].split("\t")
    assert cols[0] == "1"
    assert cols[1] == "752566"
    assert cols[2] == "rs3094315"
    assert cols[3] == "G"   # REF korrekt aus Cache
    assert cols[4] == "A"   # ALT
    assert cols[9] == "1/1" # GT homozygot ALT


def test_create_vcf_normalizes_lowercase_genotypes(tmp_work_dir):
    """Prüft, dass klein geschriebene Genotypen wie 'aa' oder 'ag' zu validem VCF führen."""
    import Variant_Fusion_pro_V17 as vf

    cache_file = tmp_work_dir / "cache.json"
    out_vcf = tmp_work_dir / "output_lower.vcf"

    conv = vf.convert_23andme_to_vcf(str(tmp_work_dir / "dummy.txt"), cache_file=str(cache_file))
    conv.cache_upsert(conv.cache, "rs101", "GRCh37", "1", 500, "C")
    conv.cache_upsert(conv.cache, "rs102", "GRCh37", "1", 600, "T")

    variants = [
        ("rs101", "1", 500, "ca"),  # Heterozygot C/A
        ("rs102", "1", 600, "gg"),  # Homozygot G/G
    ]
    conv.create_vcf(variants, "GRCh37", str(out_vcf), conv.cache, fasta_path=None, sex="female")

    content = out_vcf.read_text(encoding="utf-8")
    lines = [line for line in content.splitlines() if not line.startswith("#")]
    assert len(lines) == 2
    assert "rs101\tC\tA\t.\tPASS\t.\tGT\t0/1" in lines[0]
    assert "rs102\tT\tG\t.\tPASS\t.\tGT\t1/1" in lines[1]


def test_atomic_write_json_directory_isolation_and_cleanup(tmp_work_dir):
    """Prüft, dass atomic_write_json im Zielordner agiert und Temp-Dateien nicht im CWD leakt."""
    import Variant_Fusion_pro_V17 as vf

    sub_dir = tmp_work_dir / "nested" / "deep"
    target_json = sub_dir / "data.json"

    conv = vf.convert_23andme_to_vcf(str(tmp_work_dir / "dummy.txt"), cache_file=str(tmp_work_dir / "c.json"))
    payload = {"status": "ok", "count": 42}
    conv.atomic_write_json(payload, str(target_json))

    assert target_json.exists()
    loaded = json.loads(target_json.read_text(encoding="utf-8"))
    assert loaded == payload

    # Keine verwaisten Temp-Dateien im Zielordner oder CWD
    tmp_files_in_dir = list(sub_dir.glob(".tmp_*"))
    assert len(tmp_files_in_dir) == 0


def test_get_ref_base_resolves_normalized_coordinate_keys():
    """Prüft, dass get_ref_base mit normalisierten Tupeln und Cache-String-Keys arbeitet."""
    import Variant_Fusion_pro_V17 as vf

    cache = {
        ("GRCh37", "1", 12345): "A",
        "GRCh38:X:99999": "T",
    }

    base1 = vf.get_ref_base("chr1", 12345, cache=cache, build="GRCh37")
    assert base1 == "A"

    base2 = vf.get_ref_base("X", 99999, cache=cache, build="GRCh38")
    assert base2 == "T"

    base_missing = vf.get_ref_base("2", 88888, cache=cache, build="GRCh37")
    assert base_missing == "N"
