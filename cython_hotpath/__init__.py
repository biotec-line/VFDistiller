# Datei: cython_hotpath/__init__.py

import sys
import platform
import os

# Globale Variablen für Status und Fehlermeldung
CYTHON_IMPORT_ERROR = None

try:
    # Versuch, die kompilierten Module zu laden
    from . import vcf_parser
    from . import af_validator
    from . import key_normalizer
    from . import fasta_lookup
    CYTHON_AVAILABLE = True

except ImportError as e:
    CYTHON_AVAILABLE = False
    
    # -----------------------------------------------------------
    # FEHLER-ANALYSE: Warum hat es nicht geklappt?
    # -----------------------------------------------------------
    reasons = []
    
    # 1. Das eigentliche Fehler-Event
    reasons.append(str(e))
    
    # 2. Check: Python Version (Deine Dateien sind für 3.12 kompiliert -> cp312)
    current_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    if current_ver != "3.12":
        reasons.append(f"❌ VERSION MISMATCH: You are running Python {current_ver}, but modules likely require Python 3.12 (cp312)")
    
    # 3. Check: Architektur (Deine Dateien sind win_amd64 -> 64 Bit)
    is_64bits = sys.maxsize > 2**32
    if not is_64bits:
        reasons.append(f"❌ ARCH MISMATCH: You are running 32-bit Python, but modules are 64-bit")

    # 4. Check: Sind die Dateien überhaupt da?
    package_dir = os.path.dirname(os.path.abspath(__file__))
    expected_files = ["vcf_parser", "af_validator", "key_normalizer", "fasta_lookup"]
    missing_files = []
    for f in expected_files:
        # Suche nach irgendeiner .pyd oder .so Datei, die so beginnt
        found = any(fn.startswith(f) and (fn.endswith('.pyd') or fn.endswith('.so')) 
                    for fn in os.listdir(package_dir))
        if not found:
            missing_files.append(f)
    
    if missing_files:
        reasons.append(f"❌ MISSING FILES: Could not find compiled modules for: {', '.join(missing_files)}")

    # Fehler zusammenbauen
    CYTHON_IMPORT_ERROR = " | ".join(reasons)

    # Dummy-Zuweisung, damit Importe nicht crashen
    vcf_parser = None
    af_validator = None
    key_normalizer = None
    fasta_lookup = None


class CythonAccelerator:
    def __init__(self, logger=None, enable_stats=True):
        self.logger = logger
        self.enable_stats = enable_stats
        self.available = CYTHON_AVAILABLE
        
        # Stats Counter
        self._call_counts = {
            'parse_vcf_line': 0, 
            'validate_af': 0, 
            'normalize_key': 0, 
            'lookup_fasta': 0
        }
        
        # LOGGING MIT URSACHE
        if self.available:
            self._log("[CythonAccelerator] ✅ Cython modules loaded - FAST MODE")
        else:
            # Hier geben wir den genauen Grund aus!
            msg = f"[CythonAccelerator] ⚠️ Cython not available - using Python fallback."
            if CYTHON_IMPORT_ERROR:
                msg += f"\n    [CAUSE]: {CYTHON_IMPORT_ERROR}"
            self._log(msg)

    def _log(self, msg: str):
        if self.logger:
            self.logger.log(msg)
        else:
            print(msg)

    # --- WRAPPER METHODEN ---

    def normalize_key(self, chrom, pos, ref, alt, build):
        if self.enable_stats: self._call_counts['normalize_key'] += 1
        
        if not self.available:
            # Fallback Python Logik
            chrom = str(chrom).replace("chr", "").replace("CHR", "").upper()
            return (chrom, int(pos), str(ref).upper(), str(alt).upper(), str(build).lower())
        return key_normalizer.normalize_key_fast(chrom, pos, ref, alt, build)

    def validate_af(self, af_value):
        if self.enable_stats: self._call_counts['validate_af'] += 1

        if not self.available:
            # Fallback Python Logik
            if af_value is None: return False
            if not isinstance(af_value, (int, float)): return False
            return 0.0 <= af_value <= 1.0
        return af_validator.validate_af_fast(af_value)

    def parse_vcf_line(self, line):
        if self.enable_stats: self._call_counts['parse_vcf_line'] += 1

        if not self.available:
            # Fallback (sehr vereinfacht, nur für Notfälle)
            parts = line.split('\t')
            if len(parts) < 8: raise ValueError("Invalid VCF line")
            return {
                'chrom': parts[0], 'pos': int(parts[1]), 'id': parts[2],
                'ref': parts[3], 'alt': parts[4], 'qual': parts[5],
                'filter': parts[6], 'info': parts[7]
            }
        return vcf_parser.parse_vcf_line_fast(line)
        
    def lookup_fasta(self, fasta_path, chrom, pos, length=1):
        if self.enable_stats: self._call_counts['lookup_fasta'] += 1

        if self.available:
            try:
                return fasta_lookup.lookup_fasta_fast(fasta_path, chrom, pos, length)
            except Exception as e:
                # Fallback bei spezifischem C-Fehler
                pass
        
        # Python Fallback (ineffizient, liest Datei jedes Mal)
        try:
            chrom = chrom.replace('chr', '')
            with open(fasta_path, 'r') as f:
                current_chrom = None
                seq_parts = []
                for line in f:
                    line = line.strip()
                    if line.startswith('>'):
                        if current_chrom == chrom: break # Stop reading if we passed our chrom
                        current_chrom = line[1:].split()[0].replace('chr', '')
                        seq_parts = []
                    elif current_chrom == chrom:
                        seq_parts.append(line)
                
                if seq_parts:
                    full_seq = "".join(seq_parts)
                    idx = pos - 1
                    if idx + length <= len(full_seq):
                        return full_seq[idx:idx+length].upper()
        except:
            pass
        return None

    def print_stats(self):
        if not self.enable_stats: return
        self._log("\n" + "="*50)
        self._log("Cython Accelerator Stats")
        self._log("="*50)
        for k, v in self._call_counts.items():
            self._log(f"  {k:<20}: {v:,}")
        self._log("="*50 + "\n")