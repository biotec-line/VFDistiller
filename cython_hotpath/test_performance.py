#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cython Hot-Path Performance Test

Verwendung:
    python cython_hotpath/test_performance.py
"""

import time
import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from cython_hotpath import CythonAccelerator
except ImportError:
    print("❌ FEHLER: cython_hotpath nicht gefunden!")
    print("\nBitte zuerst compilieren:")
    print("  cd cython_hotpath")
    print("  python setup.py build_ext --inplace")
    sys.exit(1)

# ============================================================================
# TEST-DATEN
# ============================================================================

VCF_LINES = [
    "chr1\t12345\trs123\tA\tT\t30.5\tPASS\tDP=100;AF=0.05",
    "chr2\t67890\t.\tGG\tG\t.\tLowQual\tDP=50",
    "chrX\t11111\trs456\tC\tG\t99.9\tPASS\tDP=200;AF=0.95",
    "chr10\t22222\t.\tATG\tA\t45.0\tPASS\tDP=150",
] * 1000  # 4000 Zeilen

AF_VALUES = [0.01, 0.05, 0.1, 0.5, 0.95, None, 1.5, -0.1, "invalid"] * 1000  # 9000 Werte

KEYS = [
    ("chr1", 12345, "A", "T", "hg38"),
    ("2", 67890, "gg", "g", "HG19"),
    ("chrX", 11111, "c", "g", "hg38"),
    ("10", 22222, "atg", "a", "hg19"),
] * 1000  # 4000 Keys


# ============================================================================
# BENCHMARK FUNCTIONS
# ============================================================================

def benchmark_vcf_parsing(acc: CythonAccelerator, iterations: int = 1):
    """Benchmark VCF-Parsing"""
    print("\n" + "="*70)
    print("VCF PARSING BENCHMARK")
    print("="*70)
    
    results = []
    
    # -------------------------------------------------------------------------
    # CYTHON
    # -------------------------------------------------------------------------
    if acc.available:
        start = time.time()
        for _ in range(iterations):
            for line in VCF_LINES:
                try:
                    record = acc.parse_vcf_line(line)
                except:
                    pass
        cython_time = time.time() - start
        results.append(("Cython", cython_time))
        print(f"Cython:  {cython_time:.3f}s  ({len(VCF_LINES)*iterations:,} lines)")
    
    # -------------------------------------------------------------------------
    # PYTHON
    # -------------------------------------------------------------------------
    start = time.time()
    for _ in range(iterations):
        for line in VCF_LINES:
            try:
                parts = line.split('\t')
                record = {
                    'chrom': parts[0],
                    'pos': int(parts[1]),
                    'id': parts[2],
                    'ref': parts[3],
                    'alt': parts[4],
                    'qual': float(parts[5]) if parts[5] != '.' else 0.0,
                    'filter': parts[6],
                    'info': parts[7]
                }
            except:
                pass
    python_time = time.time() - start
    results.append(("Python", python_time))
    print(f"Python:  {python_time:.3f}s  ({len(VCF_LINES)*iterations:,} lines)")
    
    # -------------------------------------------------------------------------
    # SPEEDUP
    # -------------------------------------------------------------------------
    if acc.available and cython_time > 0:
        speedup = python_time / cython_time
        print(f"\n⚡ Speedup: {speedup:.1f}x faster")
    
    return results


def benchmark_af_validation(acc: CythonAccelerator, iterations: int = 1):
    """Benchmark AF-Validierung"""
    print("\n" + "="*70)
    print("AF VALIDATION BENCHMARK")
    print("="*70)
    
    results = []
    
    # -------------------------------------------------------------------------
    # CYTHON
    # -------------------------------------------------------------------------
    if acc.available:
        start = time.time()
        for _ in range(iterations):
            for val in AF_VALUES:
                try:
                    is_valid = acc.validate_af(val)
                except:
                    pass
        cython_time = time.time() - start
        results.append(("Cython", cython_time))
        print(f"Cython:  {cython_time:.3f}s  ({len(AF_VALUES)*iterations:,} validations)")
    
    # -------------------------------------------------------------------------
    # PYTHON
    # -------------------------------------------------------------------------
    start = time.time()
    for _ in range(iterations):
        for val in AF_VALUES:
            try:
                is_valid = (
                    val is not None 
                    and isinstance(val, (int, float)) 
                    and 0.0 <= val <= 1.0
                )
            except:
                pass
    python_time = time.time() - start
    results.append(("Python", python_time))
    print(f"Python:  {python_time:.3f}s  ({len(AF_VALUES)*iterations:,} validations)")
    
    # -------------------------------------------------------------------------
    # SPEEDUP
    # -------------------------------------------------------------------------
    if acc.available and cython_time > 0:
        speedup = python_time / cython_time
        print(f"\n⚡ Speedup: {speedup:.1f}x faster")
    
    return results


def benchmark_key_normalization(acc: CythonAccelerator, iterations: int = 1):
    """Benchmark Key-Normalisierung"""
    print("\n" + "="*70)
    print("KEY NORMALIZATION BENCHMARK")
    print("="*70)
    
    results = []
    
    # -------------------------------------------------------------------------
    # CYTHON
    # -------------------------------------------------------------------------
    if acc.available:
        start = time.time()
        for _ in range(iterations):
            for chrom, pos, ref, alt, build in KEYS:
                try:
                    key = acc.normalize_key(chrom, pos, ref, alt, build)
                except:
                    pass
        cython_time = time.time() - start
        results.append(("Cython", cython_time))
        print(f"Cython:  {cython_time:.3f}s  ({len(KEYS)*iterations:,} normalizations)")
    
    # -------------------------------------------------------------------------
    # PYTHON
    # -------------------------------------------------------------------------
    start = time.time()
    for _ in range(iterations):
        for chrom, pos, ref, alt, build in KEYS:
            try:
                if chrom.startswith('chr'):
                    chrom = chrom[3:]
                ref = ref.upper()
                alt = alt.upper()
                build = build.lower()
                key = (chrom, pos, ref, alt, build)
            except:
                pass
    python_time = time.time() - start
    results.append(("Python", python_time))
    print(f"Python:  {python_time:.3f}s  ({len(KEYS)*iterations:,} normalizations)")
    
    # -------------------------------------------------------------------------
    # SPEEDUP
    # -------------------------------------------------------------------------
    if acc.available and cython_time > 0:
        speedup = python_time / cython_time
        print(f"\n⚡ Speedup: {speedup:.1f}x faster")
    
    return results


def test_correctness(acc: CythonAccelerator):
    """Teste Korrektheit der Cython-Implementierungen"""
    print("\n" + "="*70)
    print("CORRECTNESS TESTS")
    print("="*70)
    
    passed = 0
    failed = 0
    
    # -------------------------------------------------------------------------
    # VCF-PARSING
    # -------------------------------------------------------------------------
    print("\n1. VCF Parsing...")
    line = "chr1\t12345\trs123\tA\tT\t30.5\tPASS\tDP=100"
    
    if acc.available:
        cython_result = acc.parse_vcf_line(line)
    python_result = acc._parse_vcf_line_python(line)
    
    if acc.available:
        if cython_result == python_result:
            print("   ✅ PASS: Cython == Python")
            passed += 1
        else:
            print("   ❌ FAIL: Results differ!")
            print(f"      Cython: {cython_result}")
            print(f"      Python: {python_result}")
            failed += 1
    else:
        print("   ⚠️  SKIP: Cython not available")
    
    # -------------------------------------------------------------------------
    # AF-VALIDIERUNG
    # -------------------------------------------------------------------------
    print("\n2. AF Validation...")
    test_vals = [0.05, 1.5, -0.1, None, "invalid"]
    
    if acc.available:
        for val in test_vals:
            cython_result = acc.validate_af(val)
            python_result = acc._validate_af_python(val)
            
            if cython_result == python_result:
                print(f"   ✅ PASS: {val} -> {cython_result}")
                passed += 1
            else:
                print(f"   ❌ FAIL: {val}")
                print(f"      Cython: {cython_result}")
                print(f"      Python: {python_result}")
                failed += 1
    else:
        print("   ⚠️  SKIP: Cython not available")
    
    # -------------------------------------------------------------------------
    # KEY-NORMALISIERUNG
    # -------------------------------------------------------------------------
    print("\n3. Key Normalization...")
    test_keys = [
        ("chr1", 123, "A", "t", "HG38"),
        ("2", 456, "gg", "G", "hg19"),
    ]
    
    if acc.available:
        for chrom, pos, ref, alt, build in test_keys:
            cython_result = acc.normalize_key(chrom, pos, ref, alt, build)
            python_result = acc._normalize_key_python(chrom, pos, ref, alt, build)
            
            if cython_result == python_result:
                print(f"   ✅ PASS: {chrom}:{pos} -> {cython_result}")
                passed += 1
            else:
                print(f"   ❌ FAIL: {chrom}:{pos}")
                print(f"      Cython: {cython_result}")
                print(f"      Python: {python_result}")
                failed += 1
    else:
        print("   ⚠️  SKIP: Cython not available")
    
    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------
    print("\n" + "-"*70)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*70)
    
    return failed == 0


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("\n" + "="*70)
    print("CYTHON HOT-PATH PERFORMANCE TEST")
    print("="*70)
    
    # Initialize
    acc = CythonAccelerator(enable_stats=True)
    
    print(f"\nCython available: {acc.available}")
    if not acc.available:
        print("\n⚠️  WARNING: Cython not available, running Python-only benchmarks")
        print("\nTo compile Cython modules:")
        print("  cd cython_hotpath")
        print("  python setup.py build_ext --inplace")
    
    # Correctness tests
    if not test_correctness(acc):
        print("\n❌ CORRECTNESS TESTS FAILED!")
        return 1
    
    # Performance benchmarks
    print("\n" + "="*70)
    print("PERFORMANCE BENCHMARKS")
    print("="*70)
    
    iterations = 5
    print(f"\nRunning {iterations} iterations per benchmark...\n")
    
    benchmark_vcf_parsing(acc, iterations=iterations)
    benchmark_af_validation(acc, iterations=iterations)
    benchmark_key_normalization(acc, iterations=iterations)
    
    # Stats
    if acc.enable_stats and acc.available:
        print("\n" + "="*70)
        acc.print_stats()
    
    print("\n✅ ALL TESTS COMPLETE\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())