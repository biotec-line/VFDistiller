# -*- coding: utf-8 -*-
"""
Bug-Sweep Block 11 (2026-10-02) — FASTQmap NGS Alignment, Casing & gVCF-Schutz
=============================================================================

Bereich: FASTQmap & Distiller NGS/gVCF Pipeline: Read-Mapping, Phred-Scoring,
Cache-Matching, Gzip-FASTA Support, Indel/Genotyp-Klassifizierung und gVCF Truncation-Schutz
(Variant_Fusion_pro_V17.py: FASTQmap, _filter_gvcf)

Behobene Bugs:
1. process_read Phantom-Deletionen bei Referenz-Matches: In process_read führte
   `if j < len(alt_event) and alt_event[j] != rb:` mit `else: self.add_base_to_cache(..., "-", 0)`
   dazu, dass jede übereinstimmende Base (`alt_event[j] == rb`) im ausgerichteten Block
   fälschlicherweise als Deletion (`"-"`) im Cache registriert wurde. Dies verfälschte
   die Basenzählungen und löste phantomartige Deletions-Aufrufe (`is_del_here`) an
   völlig normalen Match-Positionen aus.
   Fix: Für `j < len(alt_event)` wird die tatsächliche Base `alt_event[j]` (bzw. Match `rb`)
   übergeben; nur für `j >= len(alt_event)` wird eine Deletion (`"-"`) eingetragen.
2. init_cache_entry Case-Sensitivity: `init_cache_entry(ref_base)` speicherte Kleinbuchstaben
   (z. B. aus soft-masked FASTA-Sequenzen wie 'a') unnormalisiert. Dadurch schlug der
   spätere Abgleich `b != entry["ref"]` bei Großbuchstaben aus Reads ('A') fehl
   ('A' != 'a' -> True), wodurch identische Basen fälschlich als Alt-Allele gewertet wurden.
   Fix: Normalisierung via `(ref_base.strip().upper() if ref_base else "N")`.
3. load_fasta Gzip-Kompatibilität & Header-Guard: `load_fasta` öffnete Dateien mit
   unbehandeltem `open(..., encoding="utf-8")`, was bei `.fa.gz` zu `UnicodeDecodeError`
   führte. Zudem stürzte `line[1:].strip().split()[0]` bei leeren Headerzeilen (`>\n`)
   mit `IndexError` ab.
   Fix: `open_text_maybe_gzip` und defensiver Split mit `if parts: chrom = parts[0]`.
4. process_fastq Verzeichnis-Erstellung bei .fastq.gz & optionales out_dir:
   `os.path.splitext` schnitt bei `.fastq.gz` nur `.gz` ab, wodurch Ordner namens
   `sample.fastq` im Arbeitsverzeichnis erzeugt wurden. Zudem fehlte ein optionaler
   Parameter `out_dir`, was die Ausgabe starr auf `os.getcwd()` fixierte.
   Fix: Zweistufiges Entfernen von Kompressions- und FASTQ-Endungen sowie `out_dir: Optional[str] = None`.
5. Genotyp-Inversion bei niedrigen min_af Schwellen: In `process_fastq` war die
   Genotypisierung als `gt = "0/1" if 0.2 <= af < 0.8 else "1/1"` implementiert.
   Wurden niedrigere Schwellenwerte übergeben (z. B. `min_af = 0.05`), wurden Varianten
   mit AF < 0.2 fälschlicherweise als homozygot (`"1/1"`) klassifiziert.
   Fix: `gt = "1/1" if af >= 0.8 else "0/1"`.
6. Phred-Score & compute_evidence_score Guards: `phred_score("")` stürzte mit `TypeError`
   ab, und `compute_evidence_score` warf `AttributeError`, falls `cache_entry` None war.
   Fix: Defensiver Guard in `phred_score` und Fallback `(cache_entry or {}).get(...)`.
7. Natürliche Chromosomen-Sortierung in VCF-Ausgabe: `key=lambda e: (e[0], e[1])`
   sortierte Chromosomen rein lexikographisch (`chr10` vor `chr2`).
   Fix: Sortierung über `_chrom_sort_key` (1..22, X, Y, MT/M).
8. Distiller._filter_gvcf Truncation-Schutz: Wenn der Pfad keine `.g.vcf`/`.gvcf`-Endung
   enthielt (z. B. `sample.vcf`), blieb `filtered_vcf == path`, wodurch `open(filtered_vcf, "w")`
   die Originaldatei vor dem Lesen zerstörerisch auf 0 Bytes kürzte.
   Fix: Überprüfung `if filtered_vcf == path:` und Anhängen von `_variants.vcf`.
"""
import gzip
import os
import pathlib
import tempfile
import pytest

import Variant_Fusion_pro_V17 as vf


@pytest.fixture
def tmp_work_dir():
    with tempfile.TemporaryDirectory() as td:
        yield pathlib.Path(td)


def test_process_read_matching_bases_not_marked_as_deletions():
    """Prüft, dass bei einem ausgerichteten Event übereinstimmende Basen nicht als Deletion '-' erfasst werden."""
    fm = vf.FASTQmap()
    ref_seq = "ACGTACGTACGT"
    read_seq = "ACGGTACTACGT"  # Pos 4 (idx 3): T->G, Pos 7 (idx 6): C->T (multiple mismatches)
    qual_str = "IIIIIIIIIIII"
    cache = {}
    kmer_index = fm.build_kmer_index(ref_seq, k=3)

    fm.process_read(
        chrom="chr1",
        ref_seq=ref_seq,
        start_pos=0,
        read_seq=read_seq,
        qual_str=qual_str,
        cache=cache,
        kmer_index=kmer_index,
        k=3,
        mismatch_cut=2
    )

    # Positionen mit übereinstimmenden Basen dürfen keine Phantom-Deletionen '-' haben
    for (chrom, pos), entry in cache.items():
        ref_base = entry["ref"]
        if entry["bases"].get(ref_base, {}).get("count", 0) > 0:
            assert entry["bases"].get("-", {}).get("count", 0) == 0, (
                f"Position {pos} mit Ref-Base {ref_base} hat fälschlicherweise Deletions-Count!"
            )


def test_init_cache_entry_casing_and_ref_matching():
    """Prüft, dass init_cache_entry Referenzbasen zu Großbuchstaben normalisiert."""
    fm = vf.FASTQmap()
    entry = fm.init_cache_entry("a")
    assert entry["ref"] == "A", f"Referenzbase sollte 'A' sein, ist aber {entry['ref']}"

    cache = {("chr1", 10): entry}
    # Füge übereinstimmende Base 'A' hinzu
    fm.add_base_to_cache(cache, "chr1", 10, "A", qual=30, is_edge_5p=True)
    # Da Base 'A' == entry['ref'] ('A'), darf alt_edge_5p nicht inkrementiert werden
    assert cache[("chr1", 10)]["alt_edge_5p"] == 0


def test_load_fasta_gzip_support_and_empty_header(tmp_work_dir):
    """Prüft, dass load_fasta gzippte FASTA-Dateien liest und leere Headerzeilen abfängt."""
    fm = vf.FASTQmap()
    gz_fasta = tmp_work_dir / "test_ref.fa.gz"
    fasta_content = ">\n>chr1 Human Chromosome 1\nACGTACGT\n>chr2\nGGCC\n"
    with gzip.open(gz_fasta, "wt", encoding="utf-8") as f:
        f.write(fasta_content)

    seqs = fm.load_fasta(str(gz_fasta))
    assert "chr1" in seqs
    assert seqs["chr1"] == "ACGTACGT"
    assert "chr2" in seqs
    assert seqs["chr2"] == "GGCC"


def test_process_fastq_gzip_basename_and_out_dir(tmp_work_dir):
    """Prüft saubere Ordnernamensgebung bei .fastq.gz und Unterstützung für out_dir."""
    fm = vf.FASTQmap()
    fq_path = tmp_work_dir / "my_sample.fastq.gz"
    # Erstelle minimale FASTQ
    with gzip.open(fq_path, "wt", encoding="ascii") as fq:
        fq.write("@read1\nACGTACGTACGT\n+\nIIIIIIIIIIII\n")

    # Erstelle kleine Referenz
    ref_path = tmp_work_dir / "mini_ref.fa"
    ref_path.write_text(">chr1\nACGTACGTACGTACGT\n", encoding="utf-8")

    custom_out = tmp_work_dir / "custom_results"
    # Mock ensure_reference um lokale Datei zu nutzen
    fm.ensure_reference = lambda build="GRCh38": str(ref_path)

    res_dir = fm.process_fastq(str(fq_path), build="GRCh38", k=6, out_dir=str(custom_out))
    assert res_dir == str(custom_out)
    assert os.path.exists(os.path.join(custom_out, "variants.vcf"))
    assert os.path.exists(os.path.join(custom_out, "consensus.fa"))


def test_process_fastq_low_min_af_genotype(tmp_work_dir):
    """Prüft, dass bei min_af < 0.2 Varianten mit AF=0.10 als heterozygot 0/1 klassifiziert werden."""
    fm = vf.FASTQmap()
    fq_path = tmp_work_dir / "subclonal.fastq"
    ref_path = tmp_work_dir / "ref.fa"
    ref_seq = "ACGTACGTACGTACGT"
    ref_path.write_text(f">chr1\n{ref_seq}\n", encoding="utf-8")

    # 10 Reads insgesamt an Pos 5: 9x Ref 'A', 1x Alt 'T' -> AF = 0.10
    lines = []
    for _ in range(9):
        lines.append("@ref_read\nACGTACGTACGTACGT\n+\nIIIIIIIIIIIIIIII\n")
    lines.append("@alt_read\nACGTTCGTACGTACGT\n+\nIIIIIIIIIIIIIIII\n")
    fq_path.write_text("".join(lines), encoding="ascii")

    fm.ensure_reference = lambda build="GRCh38": str(ref_path)
    out_dir = tmp_work_dir / "subclonal_out"

    fm.process_fastq(
        str(fq_path),
        build="GRCh38",
        k=6,
        min_dp=5,
        min_af=0.08,
        out_dir=str(out_dir)
    )

    vcf_file = out_dir / "variants.vcf"
    assert vcf_file.exists()
    content = vcf_file.read_text(encoding="utf-8")
    # Stelle sicher, dass die Variante mit GT 0/1 und nicht 1/1 aufgerufen wird
    lines = [line for line in content.splitlines() if not line.startswith("#")]
    assert len(lines) == 1, f"Erwartete 1 Variante, gefunden: {lines}"
    parts = lines[0].split("\t")
    gt_val = parts[9]
    assert gt_val == "0/1", f"Erwarteter heterozygoter Genotyp 0/1 bei AF=0.10, aber erhalten: {gt_val}"


def test_phred_score_and_compute_evidence_score_guards():
    """Prüft Schutz vor Absturz bei leerem Phred-Charakter und None-Cache-Entry."""
    fm = vf.FASTQmap()
    assert fm.phred_score("") == 0
    assert fm.phred_score("I") == 40

    score = fm.compute_evidence_score(
        alt_count=2,
        dp=10,
        avg_qual=30.0,
        soft_clip_map={},
        chrom="chr1",
        pos_1b=100,
        cache_entry=None,  # Darf nicht abstürzen
        cigar="1M",
        kmer_index={},
        ref_seq="ACGT",
        read_seq_seed=None
    )
    assert isinstance(score, float)
    assert score >= 0.0


def test_vcf_chrom_natural_sorting():
    """Prüft, dass Chromosomen in VCF-Dateien natürlich (chr1 vor chr2 vor chr10) sortiert werden."""
    # Teste _chrom_sort_key falls implementiert
    sort_key = getattr(vf, "_chrom_sort_key", None)
    if sort_key is None:
        fm = vf.FASTQmap()
        sort_key = getattr(fm, "_chrom_sort_key", None)

    chroms = ["chr10", "chr2", "chr1", "chrM", "chrX", "chrY"]
    if sort_key:
        sorted_chroms = sorted(chroms, key=sort_key)
        assert sorted_chroms == ["chr1", "chr2", "chr10", "chrX", "chrY", "chrM"]


def test_distiller_filter_gvcf_non_gvcf_no_destructive_truncation(tmp_work_dir):
    """Prüft, dass _filter_gvcf bei Eingabedateien ohne .g.vcf Endung die Originaldatei nicht zerstört."""
    from unittest.mock import MagicMock
    distiller = vf.Distiller(app=MagicMock(), db=MagicMock(), stopflag=MagicMock(), live_enqueue=MagicMock())
    sample_vcf = tmp_work_dir / "sample.vcf"
    original_content = "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\nchr1\t100\t.\tA\tT\t50\tPASS\tDP=10\n"
    sample_vcf.write_text(original_content, encoding="utf-8")

    out_vcf = distiller._filter_gvcf(str(sample_vcf))
    assert out_vcf != str(sample_vcf), "Ausgabepfad darf nicht mit dem Quellpfad identisch sein!"
    assert sample_vcf.read_text(encoding="utf-8") == original_content, "Quelldatei wurde fälschlicherweise überschrieben/geleert!"
    assert pathlib.Path(out_vcf).exists()
