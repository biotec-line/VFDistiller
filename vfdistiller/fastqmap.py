# -*- coding: utf-8 -*-
"""Pure-Python FASTQ-zu-VCF/Consensus-Mapper (FASTQmap) ohne GUI-Abhängigkeit."""
from __future__ import annotations

from collections import Counter, defaultdict
import gzip
import os
import shutil
from typing import Callable, Dict, List, Optional, Set, Tuple, Union

try:
    from Bio.Align import PairwiseAligner
except ImportError:
    PairwiseAligner = None

from vfdistiller.converters import _CONVERTER_ENV, configure_converters_environment, get_robust_session
from vfdistiller.vcf_io import is_gzipped

_FASTQ_ENV = {
    "default_logger": None,
}


def configure_fastqmap_environment(fasta_paths=None, fasta_urls=None, logger=None) -> None:
    """Bindet optionale FASTA-Ressourcen und einen Standard-Logger für FASTQmap ein."""
    configure_converters_environment(fasta_paths=fasta_paths, fasta_urls=fasta_urls)
    if logger is not None:
        _FASTQ_ENV["default_logger"] = logger


class FASTQmap:
    def __init__(self, build: str = "GRCh38", logger=None):
        self.build = build
        self.logger = logger if logger is not None else _FASTQ_ENV["default_logger"]

    @staticmethod
    def _chrom_sort_key(chrom: str) -> Tuple[int, Union[int, str]]:
        c = str(chrom).strip().lower()
        if c.startswith("chr"):
            c = c[3:]
        if c.isdigit():
            return (0, int(c))
        special = {"x": 23, "y": 24, "m": 25, "mt": 25}
        if c in special:
            return (0, special[c])
        return (1, c)

    def convert(self, fastq_path: str, build: Optional[str] = None, out_dir: Optional[str] = None) -> str:
        used_build = build or self.build
        if not os.path.exists(fastq_path):
            raise FileNotFoundError(f"FASTQ-Datei nicht gefunden: {fastq_path}")

        def progress_callback(done: int, total: int):
            percent = (done / total * 100.0) if total else 0.0
            if self.logger:
                self.logger.log(f"[FASTQmap] Fortschritt: {done}/{total} Reads ({percent:.1f}%)")

        if self.logger:
            self.logger.log(f"[FASTQmap] Starte Verarbeitung von {fastq_path} (Build: {used_build})")

        final_out_dir = self.process_fastq(
            fastq_path,
            progress_callback=progress_callback,
            build=used_build,
            out_dir=out_dir
        )

        vcf_path = os.path.join(final_out_dir, "variants.vcf")
        if not os.path.exists(vcf_path):
            if self.logger:
                self.logger.log("[FASTQmap] ❌ Keine VCF erzeugt.")
            raise RuntimeError(f"FASTQmap: keine VCF erzeugt unter {vcf_path}")

        if self.logger:
            self.logger.log(f"[FASTQmap] ✅ Verarbeitung abgeschlossen: {vcf_path}")

        return vcf_path

    # -------------------------
    # small helpers (methods)
    # -------------------------
    def phred_score(self, char: str) -> int:
        if not char:
            return 0
        return max(0, ord(char) - 33)

    def load_fasta(self, fasta_path: str) -> Dict[str, str]:
        if is_gzipped(fasta_path) or str(fasta_path).lower().endswith((".gz", ".bgz")):
            ctx = gzip.open(fasta_path, "rt", encoding="utf-8", errors="ignore")
        else:
            ctx = open(fasta_path, "r", encoding="utf-8")
        seqs: Dict[str, List[str]] = {}
        chrom: Optional[str] = None
        with ctx as f:
            for line in f:
                if line.startswith(">"):
                    parts = line[1:].strip().split()
                    chrom = parts[0] if parts else None
                    if chrom:
                        seqs[chrom] = []
                else:
                    if chrom is not None:
                        seqs[chrom].append(line.strip().upper())
        return {c: "".join(s) for c, s in seqs.items()}

    def build_kmer_index(self, ref_seq: str, k: int = 15) -> Dict[str, List[int]]:
        index: Dict[str, List[int]] = {}
        if len(ref_seq) < k:
            return index
        for i in range(len(ref_seq) - k + 1):
            kmer = ref_seq[i:i+k]
            index.setdefault(kmer, []).append(i)
        return index

    def map_read(self, read_seq: str, ref_seq: str, kmer_index: Dict[str, List[int]], k: int = 15) -> Optional[int]:
        if len(read_seq) < k:
            return None
        candidate_starts = set()
        step = max(1, k // 2)
        for offset in range(0, len(read_seq) - k + 1, step):
            kmer = read_seq[offset:offset+k]
            hits = kmer_index.get(kmer)
            if hits:
                for hit_pos in hits:
                    start = hit_pos - offset
                    if 0 <= start and start + len(read_seq) <= len(ref_seq):
                        candidate_starts.add(start)
                if len(candidate_starts) >= 10:
                    break

        if not candidate_starts:
            return None

        best_pos: Optional[int] = None
        best_mismatches = len(read_seq) + 1
        for start in sorted(candidate_starts):
            segment = ref_seq[start:start+len(read_seq)]
            if len(segment) != len(read_seq):
                continue
            mismatches = sum(1 for a, b in zip(segment, read_seq) if a != b)
            if mismatches < best_mismatches:
                best_mismatches = mismatches
                best_pos = start
        return best_pos

    def ensure_reference(self, build: str = "GRCh38") -> str:
        fasta_path = _CONVERTER_ENV["fasta_paths"][build]
        parent = os.path.dirname(os.path.abspath(fasta_path))
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        if os.path.exists(fasta_path):
            return fasta_path
        url = _CONVERTER_ENV["fasta_urls"][build]
        gz_path = fasta_path + ".gz"
        if self.logger:
            self.logger.log(f"[FASTQmap] Lade Referenz {build} herunter von {url} ...")
        try:
            with get_robust_session() as session:
                with session.get(url, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    r.raw.decode_content = True
                    with open(gz_path, "wb") as f:
                        shutil.copyfileobj(r.raw, f)
            with gzip.open(gz_path, "rb") as f_in, open(fasta_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
            os.remove(gz_path)

        except Exception as e:
            raise RuntimeError(f"Referenz konnte nicht geladen/entpackt werden: {e}")
        return fasta_path

    def count_reads(self, fastq_path: str) -> int:
        opener = gzip.open if fastq_path.lower().endswith((".gz", ".bgz")) else open
        mode = "rt" if opener is gzip.open else "r"
        with opener(fastq_path, mode, encoding="ascii", errors="ignore") as fq:
            lines = sum(1 for _ in fq)
        return lines // 4

    def init_cache_entry(self, ref_base: str) -> Dict:
        clean_ref = (ref_base.strip().upper() if ref_base else "N")
        return {
            "ref": clean_ref,
            "bases": {b: {"count": 0, "qual_sum": 0.0} for b in ["A", "C", "G", "T", "-", "N"]},
            "alt_edge_5p": 0,
            "alt_edge_3p": 0
        }

    def _sanitize_base(self, base: Optional[str]) -> str:
        if base is None:
            return "N"
        b = base.strip().upper()
        return b if b in {"A", "C", "G", "T", "-"} else "N"

    def add_base_to_cache(self, cache: Dict[Tuple[str, int], Dict], chrom: str, pos: int, base: str, qual: int,
                          is_edge_5p: bool = False, is_edge_3p: bool = False) -> None:
        if (chrom, pos) not in cache:
            cache[(chrom, pos)] = self.init_cache_entry("N")
        entry = cache[(chrom, pos)]
        b = self._sanitize_base(base)
        # ensure key exists in bases
        if b not in entry["bases"]:
            entry["bases"][b] = {"count": 0, "qual_sum": 0.0}
        entry["bases"][b]["count"] += 1
        entry["bases"][b]["qual_sum"] += float(max(0, qual))
        if b in {"A", "C", "G", "T"} and b != entry["ref"] and (is_edge_5p or is_edge_3p):
            if is_edge_5p:
                entry["alt_edge_5p"] += 1
            if is_edge_3p:
                entry["alt_edge_3p"] += 1

    def try_insertion(self, read_seq: str, qual_str: str, ref_seq: str, read_i: int, ref_pos: int,
                      max_ins: int = 10, window: int = 6) -> int:
        for k in range(1, max_ins + 1):
            if read_i + k >= len(read_seq):
                break
            rs = read_seq[read_i + k: read_i + k + window]
            rf = ref_seq[ref_pos: ref_pos + window]
            if not rs or not rf or len(rs) != len(rf):
                continue
            mism = sum(1 for a, b in zip(rs, rf) if a != b)
            if mism <= 1:
                return k
        return 0

    def trim_and_map_insertion(self, daughter_seq: str, daughter_qual: str, ref_seq: str,
                               kmer_index: Dict[str, List[int]], k: int, max_trim: int = 12) -> Tuple[int, str, str, str, Optional[int]]:
        for t in range(1, max_trim + 1):
            if len(daughter_seq) <= t:
                break
            ins_seq = daughter_seq[:t]
            new_seq = daughter_seq[t:]
            new_qual = daughter_qual[t:]
            pos = self.map_read(new_seq, ref_seq, kmer_index, k)
            if pos is not None:
                return t, ins_seq, new_seq, new_qual, pos
        return 0, "", daughter_seq, daughter_qual, None

    def left_normalize(self, ref_seq: str, pos_1b: int, ref_event: str, alt_event: str) -> Tuple[int, str, str]:
        if ref_event == alt_event:
            return pos_1b, ref_event, alt_event
        is_insertion = len(alt_event) > len(ref_event)
        is_deletion = len(ref_event) > len(alt_event)
        if not (is_insertion or is_deletion):
            return pos_1b, ref_event, alt_event
        while pos_1b > 1:
            prev_ref_base = ref_seq[pos_1b - 2]
            if not ref_event or not alt_event:
                break
            if is_deletion:
                if ref_event.endswith(prev_ref_base) and alt_event.endswith(prev_ref_base):
                    ref_event = prev_ref_base + ref_event[:-1]
                    alt_event = prev_ref_base + alt_event[:-1]
                    pos_1b -= 1
                else:
                    break
            elif is_insertion:
                if ref_event[-1] == prev_ref_base and alt_event[-1] == prev_ref_base:
                    ref_event = prev_ref_base + ref_event[:-1]
                    alt_event = prev_ref_base + alt_event[:-1]
                    pos_1b -= 1
                else:
                    break
            else:
                break
        return pos_1b, ref_event, alt_event

    def refine_indel_with_sw(self, ref_seq: str, read_seq: str, cut_ref_pos: int, cut_read_pos: int,
                             initial_flank: int = 10, max_iter: int = 3) -> Tuple[int, str, str, float, str]:
        if PairwiseAligner is None:
            corrected_pos = cut_ref_pos + 1
            ref_event = ref_seq[cut_ref_pos] if 0 <= cut_ref_pos < len(ref_seq) else "N"
            alt_event = read_seq[cut_read_pos] if 0 <= cut_read_pos < len(read_seq) else ref_event
            return corrected_pos, ref_event, alt_event, -1.0, "N"

        aligner = PairwiseAligner()
        aligner.mode = "local"
        aligner.match_score = 2
        aligner.mismatch_score = -1
        aligner.open_gap_score = -2
        aligner.extend_gap_score = -0.5

        best_tuple = (cut_ref_pos + 1,
                      ref_seq[cut_ref_pos] if 0 <= cut_ref_pos < len(ref_seq) else "N",
                      read_seq[cut_read_pos] if 0 <= cut_read_pos < len(read_seq) else "N",
                      -1.0, "N")
        prev_score = None
        prev_clip = None

        for it in range(max_iter):
            flank = initial_flank + (5 * it)
            ref_start = max(0, cut_ref_pos - flank)
            ref_end = min(len(ref_seq), cut_ref_pos + flank)
            read_start = max(0, cut_read_pos - flank)
            read_end = min(len(read_seq), cut_read_pos + flank)

            ref_window = ref_seq[ref_start:ref_end]
            read_window = read_seq[read_start:read_end]

            alns = aligner.align(ref_window, read_window)
            if not alns:
                continue

            best = alns[0]
            score = float(best.score)

            try:
                aligned_lines = str(best).splitlines()
                aligned_ref_str = aligned_lines[0].replace(" ", "")
                aligned_read_str = aligned_lines[1].replace(" ", "")
            except Exception:
                aligned_ref_str = ref_window
                aligned_read_str = read_window

            leading_gaps = aligned_ref_str.startswith('-') or aligned_read_str.startswith('-')
            trailing_gaps = aligned_ref_str.endswith('-') or aligned_read_str.endswith('-')
            clip_mode = "N"
            if leading_gaps and not trailing_gaps:
                clip_mode = "L"
            elif trailing_gaps and not leading_gaps:
                clip_mode = "R"

            ref_aln: List[str] = []
            alt_aln: List[str] = []
            for r, q in zip(aligned_ref_str, aligned_read_str):
                r_clean = self._sanitize_base(r)
                q_clean = self._sanitize_base(q)
                if r_clean != "-" and q_clean != "-":
                    ref_aln.append(r_clean)
                    alt_aln.append(q_clean)
                elif r_clean != "-" and q_clean == "-":
                    ref_aln.append(r_clean)
                elif r_clean == "-" and q_clean != "-":
                    alt_aln.append(q_clean)

            ref_seq_event = "".join(ref_aln) if ref_aln else (ref_seq[cut_ref_pos] if 0 <= cut_ref_pos < len(ref_seq) else "N")
            alt_seq_event = "".join(alt_aln) if alt_aln else (read_seq[cut_read_pos] if 0 <= cut_read_pos < len(read_seq) else ref_seq_event)
            corrected_pos = ref_start + 1

            if prev_score is not None and abs(score - prev_score) <= 0.5 and prev_clip == clip_mode:
                return corrected_pos, ref_seq_event, alt_seq_event, score, clip_mode

            best_tuple = (corrected_pos, ref_seq_event, alt_seq_event, score, clip_mode)
            prev_score, prev_clip = score, clip_mode

        return best_tuple

    def record_soft_clip(self, soft_clip_map: Dict[Tuple[str, int], Dict[str, int]],
                         chrom: str, anchor_pos_1b: int, side: str) -> None:
        d = soft_clip_map.setdefault((chrom, anchor_pos_1b), {"L": 0, "R": 0})
        d[side] = d.get(side, 0) + 1

    def cluster_events_by_cigar(self, cigar_counts: Dict[Tuple[str, int], Counter]) -> Dict[Tuple[str, int], str]:
        chosen: Dict[Tuple[str, int], str] = {}
        for key, ctr in cigar_counts.items():
            if ctr:
                cigar, _ = ctr.most_common(1)[0]
                chosen[key] = cigar
        return chosen

    def is_homopolymer(self, ref_seq: str, pos_1b: int, span: int = 8, min_run: int = 4) -> bool:
        start = max(1, pos_1b - span // 2)
        end = min(len(ref_seq), pos_1b + span // 2)
        window = ref_seq[start-1:end]
        if not window:
            return False
        run_char = window[0]
        run_len = 1
        best_run = 1
        for ch in window[1:]:
            if ch == run_char:
                run_len += 1
                best_run = max(best_run, run_len)
            else:
                run_char = ch
                run_len = 1
        return best_run >= min_run

    def seed_coherence_penalty(self, kmer_index: Dict[str, List[int]], kmer: str) -> float:
        cands = kmer_index.get(kmer, [])
        if not cands:
            return 1.0
        n = len(cands)
        if n <= 1:
            return 1.0
        if n <= 3:
            return 0.8
        if n <= 10:
            return 0.6
        return 0.4

    def compute_evidence_score(self, alt_count: int,
                               dp: int,
                               avg_qual: float,
                               soft_clip_map: Dict[Tuple[str, int], Dict[str, int]],
                               chrom: str,
                               pos_1b: int,
                               cache_entry: Dict,
                               cigar: str,
                               kmer_index: Dict[str, List[int]],
                               ref_seq: str,
                               read_seq_seed: Optional[str]) -> float:
        if dp <= 0:
            return 0.0
        af = alt_count / dp
        clip_support = 0
        for delta in (-2, -1, 0, 1, 2):
            d = soft_clip_map.get((chrom, pos_1b + delta), {})
            clip_support += d.get('L', 0) + d.get('R', 0)
        clip_factor = min(1.0, clip_support / max(1, 5))

        L = sum(soft_clip_map.get((chrom, pos_1b + d), {}).get('L', 0) for d in (-2, -1, 0, 1, 2))
        R = sum(soft_clip_map.get((chrom, pos_1b + d), {}).get('R', 0) for d in (-2, -1, 0, 1, 2))
        total_lr = L + R
        if total_lr > 0:
            balance = min(L, R) / total_lr
        else:
            balance = 0.5

        edge_hits = (cache_entry or {}).get("alt_edge_5p", 0) + (cache_entry or {}).get("alt_edge_3p", 0)
        edge_factor = 1.0 - min(0.8, edge_hits / max(1, alt_count)) * 0.5

        seed_penalty = 1.0
        if read_seq_seed and len(read_seq_seed) >= 15:
            seed_penalty = self.seed_coherence_penalty(kmer_index, read_seq_seed[:15])

        homo_penalty = 0.8 if self.is_homopolymer(ref_seq, pos_1b) else 1.0
        qual_factor = min(1.0, avg_qual / 40.0)

        cigar_simple = 1.0 if ("I" in cigar and "D" not in cigar and "X" not in cigar) or \
                             ("D" in cigar and "I" not in cigar and "X" not in cigar) or \
                             ("X" in cigar and "I" not in cigar and "D" not in cigar) else 0.8

        balance_factor = 1.0 if 0.3 <= balance <= 0.7 else 0.8

        score = (af * 0.35 +
                 clip_factor * 0.2 +
                 balance_factor * 0.1 +
                 edge_factor * 0.1 +
                 qual_factor * 0.15 +
                 cigar_simple * 0.05) * seed_penalty * homo_penalty
        return score

    # ------------------------------------------------------------
    # process_read (uses self.* consistently)
    # ------------------------------------------------------------
    def process_read(self, chrom: str, ref_seq: str, start_pos: int, read_seq: str, qual_str: str,
                     cache: Dict,
                     kmer_index: Dict[str, List[int]],
                     k: int = 15,
                     mismatch_cut: int = 2,
                     ins_cache: Optional[Dict[Tuple[str, int], Dict[str, Dict[str, float]]]] = None,
                     soft_clip_map: Optional[Dict[Tuple[str, int], Dict[str, int]]] = None,
                     cigar_counts: Optional[Dict[Tuple[str, int], Counter]] = None) -> None:
        if len(read_seq) != len(qual_str):
            min_len = min(len(read_seq), len(qual_str))
            read_seq = read_seq[:min_len]
            qual_str = qual_str[:min_len]

        i = 0
        while i < len(read_seq):
            ref_pos = start_pos + i
            if ref_pos >= len(ref_seq):
                if soft_clip_map is not None:
                    self.record_soft_clip(soft_clip_map, chrom, (start_pos + i) + 1, 'R')
                break
            ref_base = ref_seq[ref_pos]
            base = read_seq[i]
            qual = self.phred_score(qual_str[i]) if i < len(qual_str) else 0
            is_edge_5p = (i < 5)
            is_edge_3p = (len(read_seq) - i <= 5)

            key = (chrom, ref_pos + 1)
            if key not in cache:
                cache[key] = self.init_cache_entry(ref_base)

            if base != ref_base:
                if ins_cache is not None:
                    ins_k = self.try_insertion(read_seq, qual_str, ref_seq, i, ref_pos)
                    if ins_k > 0:
                        anchor_pos_1b = ref_pos + 1
                        ins_seq = read_seq[i:i + ins_k]
                        ins_qual_vals = [self.phred_score(q) for q in qual_str[i:i + ins_k]]
                        ins_entry = ins_cache.setdefault((chrom, anchor_pos_1b), {}).setdefault(ins_seq, {"count": 0, "qual_sum": 0.0})
                        ins_entry["count"] += 1
                        ins_entry["qual_sum"] += (sum(ins_qual_vals) / max(1, len(ins_qual_vals))) if ins_qual_vals else 0.0
                        if cigar_counts is not None:
                            cigar_counts.setdefault((chrom, anchor_pos_1b), Counter())[f"1M{ins_k}I"] += 1
                        i += ins_k
                        continue

                mismatch_run = 1
                while (i + mismatch_run < len(read_seq) and
                       start_pos + i + mismatch_run < len(ref_seq) and
                       read_seq[i + mismatch_run] != ref_seq[start_pos + i + mismatch_run]):
                    mismatch_run += 1

                if mismatch_run >= mismatch_cut:
                    candidates: List[int] = []
                    anchor_1b = ref_pos + 1
                    if soft_clip_map is not None:
                        for delta in (-2, -1, 0, 1, 2):
                            p = anchor_1b + delta
                            if soft_clip_map.get((chrom, p), {}).get('L', 0) + soft_clip_map.get((chrom, p), {}).get('R', 0) >= 1:
                                candidates.append(p)
                    if not candidates:
                        candidates = [anchor_1b]

                    best_pick = None
                    best_score_val = -1.0

                    for cand_pos_1b in candidates:
                        cut_ref_pos = max(0, cand_pos_1b - 1)
                        corr_pos, ref_event, alt_event, sw_score, clip_mode = self.refine_indel_with_sw(
                            ref_seq, read_seq, cut_ref_pos, i, initial_flank=10, max_iter=3
                        )
                        corr_pos, ref_event, alt_event = self.left_normalize(ref_seq, corr_pos, ref_event, alt_event)

                        cigar = "1M"
                        if len(ref_event) > len(alt_event):
                            cigar = f"1M{len(ref_event) - len(alt_event)}D"
                        elif len(alt_event) > len(ref_event):
                            cigar = f"1M{len(alt_event) - len(ref_event)}I"
                        elif ref_event != alt_event:
                            cigar = "1X"

                        if cigar_counts is not None:
                            cigar_counts.setdefault((chrom, corr_pos), Counter())[cigar] += 1

                        cache_key = (chrom, corr_pos)
                        if cache_key not in cache:
                            ref_b = ref_seq[corr_pos - 1] if 0 < corr_pos <= len(ref_seq) else "N"
                            cache[cache_key] = self.init_cache_entry(ref_b)

                        dp_here = sum(cache[cache_key]["bases"][b]["count"] for b in "ACGT")
                        avgq_here = qual
                        read_seed = read_seq[:k] if len(read_seq) >= k else None
                        score_val = self.compute_evidence_score(
                            alt_count=1, dp=max(1, dp_here), avg_qual=avgq_here,
                            soft_clip_map=soft_clip_map or {}, chrom=chrom, pos_1b=corr_pos,
                            cache_entry=cache[cache_key], cigar=cigar,
                            kmer_index=kmer_index, ref_seq=ref_seq, read_seq_seed=read_seed
                        )
                        score_val += min(1.0, sw_score / 20.0) * 0.2

                        if score_val > best_score_val:
                            best_score_val = score_val
                            best_pick = (corr_pos, ref_event, alt_event, sw_score, clip_mode)

                    if best_pick is not None:
                        corr_pos, ref_event, alt_event, _, _ = best_pick
                        for j, rb in enumerate(ref_event):
                            pos_key = corr_pos + j
                            key2 = (chrom, pos_key)
                            if key2 not in cache:
                                ref_b = ref_seq[pos_key - 1] if 0 < pos_key <= len(ref_seq) else "N"
                                cache[key2] = self.init_cache_entry(ref_b)
                            if j < len(alt_event):
                                self.add_base_to_cache(cache, chrom, pos_key, alt_event[j], qual, is_edge_5p=is_edge_5p, is_edge_3p=is_edge_3p)
                            else:
                                self.add_base_to_cache(cache, chrom, pos_key, "-", 0)

                    daughter_seq = read_seq[i + mismatch_run:]
                    daughter_qual = qual_str[i + mismatch_run:]
                    if len(daughter_seq) != len(daughter_qual):
                        min_len = min(len(daughter_seq), len(daughter_qual))
                        daughter_seq = daughter_seq[:min_len]
                        daughter_qual = daughter_qual[:min_len]

                    if daughter_seq:
                        new_start = self.map_read(daughter_seq, ref_seq, kmer_index, k)
                        if new_start is not None:
                            self.process_read(chrom, ref_seq, new_start, daughter_seq, daughter_qual,
                                              cache, kmer_index, k, mismatch_cut, ins_cache, soft_clip_map, cigar_counts)
                        else:
                            if soft_clip_map is not None:
                                self.record_soft_clip(soft_clip_map, chrom, (ref_pos + mismatch_run) + 1, 'R')
                            tlen, ins_seq, trimmed_seq, trimmed_qual, pos2 = self.trim_and_map_insertion(
                                daughter_seq, daughter_qual, ref_seq, kmer_index, k)
                            if tlen > 0 and pos2 is not None and ins_cache is not None:
                                anchor_pos_1b = (ref_pos + mismatch_run) + 1
                                ins_entry = ins_cache.setdefault((chrom, anchor_pos_1b), {}).setdefault(ins_seq, {"count": 0, "qual_sum": 0.0})
                                ins_entry["count"] += 1
                                ins_entry["qual_sum"] += (sum(self.phred_score(q) for q in daughter_qual[:tlen]) / max(1, tlen))
                                if cigar_counts is not None:
                                    cigar_counts.setdefault((chrom, anchor_pos_1b), Counter())[f"1M{tlen}I"] += 1
                                self.process_read(chrom, ref_seq, pos2, trimmed_seq, trimmed_qual,
                                                 cache, kmer_index, k, mismatch_cut, ins_cache, soft_clip_map, cigar_counts)
                    return
                else:
                    self.add_base_to_cache(cache, chrom, ref_pos + 1, base, qual, is_edge_5p=is_edge_5p, is_edge_3p=is_edge_3p)
            else:
                self.add_base_to_cache(cache, chrom, ref_pos + 1, base, qual, is_edge_5p=is_edge_5p, is_edge_3p=is_edge_3p)
            i += 1

    # ------------------------------------------------------------
    # process_fastq (uses self.* consistently)
    # ------------------------------------------------------------
    def process_fastq(self,
        fastq_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        build: str = "GRCh38",
        k: int = 15,
        qual_threshold: int = 20,
        min_dp: int = 5,
        min_af: float = 0.2,
        out_dir: Optional[str] = None
    ) -> str:
        ref_fasta_path: str = self.ensure_reference(build)
        ref_seqs: Dict[str, str] = self.load_fasta(ref_fasta_path)
        if not ref_seqs:
            raise RuntimeError("Referenz FASTA enthält keine Sequenzen.")

        clean_name = os.path.basename(fastq_path)
        if clean_name.lower().endswith((".gz", ".bgz")):
            clean_name = os.path.splitext(clean_name)[0]
        base_name: str = os.path.splitext(clean_name)[0]

        if out_dir is not None:
            final_out_dir: str = os.path.abspath(out_dir)
        else:
            final_out_dir = os.path.join(os.getcwd(), base_name)
        os.makedirs(final_out_dir, exist_ok=True)
        out_fasta: str = os.path.join(final_out_dir, "consensus.fa")
        out_vcf: str = os.path.join(final_out_dir, "variants.vcf")

        cache: Dict[Tuple[str, int], Dict] = {}
        kmer_indices: Dict[str, Dict[str, List[int]]] = {chrom: self.build_kmer_index(seq, k) for chrom, seq in ref_seqs.items()}
        total_reads: int = self.count_reads(fastq_path)
        processed_reads: int = 0
        ins_cache: Dict[Tuple[str, int], Dict[str, Dict[str, float]]] = defaultdict(dict)
        soft_clip_map: Dict[Tuple[str, int], Dict[str, int]] = defaultdict(lambda: {"L": 0, "R": 0})
        cigar_counts: Dict[Tuple[str, int], Counter] = defaultdict(Counter)

        opener = gzip.open if fastq_path.lower().endswith((".gz", ".bgz")) else open
        mode = "rt" if opener is gzip.open else "r"
        with opener(fastq_path, mode, encoding="ascii", errors="ignore") as fq:
            while True:
                header: str = fq.readline()
                if not header:
                    break
                seq: str = fq.readline().rstrip().upper()
                fq.readline()
                qual_str: str = fq.readline().rstrip()

                if not seq or not qual_str:
                    continue
                if len(seq) != len(qual_str):
                    min_len: int = min(len(seq), len(qual_str))
                    seq, qual_str = seq[:min_len], qual_str[:min_len]

                for chrom, ref_seq in ref_seqs.items():
                    if len(seq) < k:
                        continue
                    pos: Optional[int] = self.map_read(seq, ref_seq, kmer_indices[chrom], k)
                    if pos is not None:
                        self.process_read(
                            chrom, ref_seq, pos, seq, qual_str,
                            cache, kmer_indices[chrom], k,
                            mismatch_cut=2, ins_cache=ins_cache,
                            soft_clip_map=soft_clip_map, cigar_counts=cigar_counts
                        )
                        break

                processed_reads += 1
                if progress_callback and processed_reads % 100 == 0:
                    progress_callback(processed_reads, total_reads)

        consensus_seqs: Dict[str, List[str]] = {chrom: list(seq) for chrom, seq in ref_seqs.items()}

        events: List[Tuple[str, int, str, str, Optional[float], str, str, int, int, str]] = []
        visited_del: Set[Tuple[str, int]] = set()

        for chrom in sorted(ref_seqs.keys(), key=lambda c: self._chrom_sort_key(c)):
            chrom_positions = sorted([p for (c, p) in cache.keys() if c == chrom])
            ref_seq = ref_seqs[chrom]

            idx = 0
            while idx < len(chrom_positions):
                pos = chrom_positions[idx]
                entry = cache.get((chrom, pos), None)
                if not entry:
                    idx += 1
                    continue

                ref_base: str = self._sanitize_base(entry["ref"])
                base_counts = entry["bases"]

                total_cov: int = sum(base_counts.get(b, {"count":0})["count"] for b in "ACGT")

                is_del_here = (base_counts["-"]["count"] >= max(base_counts[b]["count"] for b in "ACGT"))

                if is_del_here and (chrom, pos) not in visited_del:
                    block_len = 1
                    j = 1
                    while (chrom, pos + j) in cache:
                        nxt = cache[(chrom, pos + j)]["bases"]
                        if nxt["-"]["count"] >= max(nxt[b]["count"] for b in "ACGT"):
                            block_len += 1
                            j += 1
                        else:
                            break

                    ref_block = "".join(
                        self._sanitize_base(cache[(chrom, pos + j)]["ref"])
                        for j in range(block_len)
                        if (chrom, pos + j) in cache
                    )
                    if not ref_block:
                        ref_block = ref_seq[pos - 1: pos - 1 + block_len]
                    if not ref_block:
                        idx += block_len
                        continue

                    alt_block = ref_block[0]
                    npos, nref, nalt = self.left_normalize(ref_seq, pos, ref_block, alt_block)

                    dp_block = 0
                    ac_block = 0
                    for j in range(block_len):
                        key_j = (chrom, pos + j)
                        if key_j not in cache:
                            continue
                        counts_j = cache[key_j]["bases"]
                        dp_block += sum(counts_j.get(b, {"count":0})["count"] for b in "ACGT")
                        ac_block += counts_j["-"]["count"]

                    af_block = (ac_block / dp_block) if dp_block else 0.0
                    if dp_block >= min_dp and af_block >= min_af:
                        filt = "PASS"
                        cigar_str = f"1M{len(nref) - len(nalt)}D"
                        gt = "1/1" if af_block >= 0.8 else "0/1"
                        events.append((chrom, npos, nref, nalt, None, filt, cigar_str, dp_block, ac_block, gt))

                    for j in range(block_len):
                        visited_del.add((chrom, pos + j))
                    idx += block_len
                    continue

                for alt_b in ("A", "C", "G", "T"):
                    if alt_b == ref_base:
                        continue
                    alt_count = base_counts[alt_b]["count"]
                    if alt_count == 0:
                        continue
                    af = (alt_count / max(1, total_cov)) if total_cov else 0.0
                    if total_cov >= min_dp and af >= min_af:
                        avg_qual = (base_counts[alt_b]["qual_sum"] / max(1, alt_count)) if alt_count else 0.0
                        local_thr = qual_threshold + 5 if self.is_homopolymer(ref_seq, pos) else qual_threshold
                        filt = "PASS" if avg_qual >= local_thr else "LowQual"
                        cigar_str = "1X"
                        gt = "1/1" if af >= 0.8 else "0/1"
                        events.append((chrom, pos, ref_base, alt_b, avg_qual, filt, cigar_str, total_cov, alt_count, gt))
                        if af >= 0.5 and 0 < pos <= len(consensus_seqs[chrom]):
                            consensus_seqs[chrom][pos - 1] = alt_b

                idx += 1

        for (chrom, pos), seqs in ins_cache.items():
            if not seqs:
                continue
            ins_seq, stats = max(seqs.items(), key=lambda kv: kv[1]["count"])
            if any(ch not in "ACGT" for ch in ins_seq.upper()):
                continue

            if (chrom, pos) not in cache:
                ref_anchor_b = ref_seqs[chrom][pos - 1] if 0 < pos <= len(ref_seqs[chrom]) else "N"
                cache[(chrom, pos)] = self.init_cache_entry(ref_anchor_b)
            dp_here = sum(cache[(chrom, pos)]["bases"].get(b, {"count":0})["count"] for b in "ACGT")
            ac_i = int(stats["count"])
            af_i = (ac_i / dp_here) if dp_here else 0.0
            if dp_here < min_dp or af_i < min_af:
                continue

            avgq_i = stats["qual_sum"] / max(1, ac_i)
            ref_anchor = cache[(chrom, pos)]["ref"]

            npos, nref, nalt = self.left_normalize(ref_seqs[chrom], pos, ref_anchor, ref_anchor + ins_seq)
            local_thr = qual_threshold + 5 if self.is_homopolymer(ref_seqs[chrom], npos) else qual_threshold
            filt_i = "PASS" if avgq_i >= local_thr else "LowQual"
            cigar_i = f"1M{len(nalt) - len(nref)}I"
            gt_i = "1/1" if af_i >= 0.8 else "0/1"

            events.append((chrom, npos, nref, nalt, avgq_i, filt_i, cigar_i, dp_here, ac_i, gt_i))

        top_cigars = self.cluster_events_by_cigar(cigar_counts)
        filtered_events: List[Tuple[str, int, str, str, Optional[float], str, str, int, int, str]] = []
        for ev in events:
            key = (ev[0], ev[1])
            top_cigar = top_cigars.get(key)
            if top_cigar and top_cigar != ev[6]:
                filtered_events.append((ev[0], ev[1], ev[2], ev[3], ev[4], "Secondary", ev[6], ev[7], ev[8], ev[9]))
            else:
                filtered_events.append(ev)

        unique_events: Dict[Tuple[str, int, str, str], Tuple[str, int, str, str, Optional[float], str, str, int, int, str]] = {}
        for ev in filtered_events:
            key = (ev[0], ev[1], ev[2], ev[3])
            if key not in unique_events or (ev[4] or 0.0) > (unique_events[key][4] or 0.0):
                unique_events[key] = ev

        with open(out_vcf, "w", encoding="utf-8") as vcf:
            vcf.write("##fileformat=VCFv4.2\n")
            vcf.write(f"##reference={ref_fasta_path}\n")
            vcf.write("##INFO=<ID=CIGAR,Number=1,Type=String,Description=\"Local CIGAR string for variant\">\n")
            vcf.write("##INFO=<ID=DP,Number=1,Type=Integer,Description=\"Total depth at position\">\n")
            vcf.write("##INFO=<ID=AC,Number=1,Type=Integer,Description=\"Alt allele count\">\n")
            vcf.write("##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">\n")
            vcf.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\n")
            for chrom, pos, ref, alt, qual, filt, cigar, dp, ac, gt in sorted(unique_events.values(), key=lambda e: (self._chrom_sort_key(e[0]), e[1])):
                if not ref or not alt or pos < 1:
                    continue
                info_str = f"CIGAR={cigar};DP={dp};AC={ac}"
                q = 0.0 if qual is None else float(qual)
                vcf.write(f"{chrom}\t{pos}\t.\t{ref}\t{alt}\t{q:.2f}\t{filt}\t{info_str}\tGT\t{gt}\n")

        with open(out_fasta, "w", encoding="utf-8") as fa:
            for chrom, seq_list in consensus_seqs.items():
                fa.write(f">{chrom}_consensus\n")
                for j in range(0, len(seq_list), 60):
                    fa.write("".join(seq_list[j:j+60]) + "\n")

        return final_out_dir
