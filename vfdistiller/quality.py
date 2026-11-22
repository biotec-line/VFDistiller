# -*- coding: utf-8 -*-
"""Qualitätsfilter-Verwaltung (QualityManager) für VCF-Records."""
from __future__ import annotations

import re
import threading
from typing import Optional

from vfdistiller.vcf_io import open_text_maybe_gzip


class QualityManager:
    """
    Zentrale Verwaltung aller Quality-Filter für VCF-Varianten.

    Funktionen:
    - Vordefinierte Presets (research, clinical, strict, permissive, rma_sensitive)
    - Custom Settings
    - Einheitliche Quality-Gates für FILTER, QUAL, DP, GENOTYPE
    - Thread-safe für GUI-Updates

    Usage:
        qm = QualityManager(preset="clinical")
        if qm.passes(record):
            # Variante akzeptiert
    """

    # Vordefinierte Profile
    # HINWEIS zu filter_homref:
    #   True  = 0/0 (homozygote Referenz) wird ausgefiltert (Standard)
    #   False = 0/0 wird behalten (wichtig für Reference Minor Allele Analyse)
    #
    #   ACHTUNG: Das Referenzgenom kann pathogene Allele enthalten!
    #   Bei Verdacht auf Reference Minor Alleles (RMAs) filter_homref=False setzen.
    PRESETS = {
        "permissive": {
            "description": "Permissive - Maximale Sensitivität für Forschung",
            "filter_pass_only": False,
            "qual_threshold": 10.0,
            "use_dp_filter": True,
            "min_dp": 5,
            "max_dp": None,
            "filter_homref": True,  # 0/0 ausfiltern
        },
        "research": {
            "description": "Research - Standard für Forschungsprojekte",
            "filter_pass_only": True,
            "qual_threshold": 20.0,
            "use_dp_filter": True,
            "min_dp": 8,
            "max_dp": None,
            "filter_homref": True,  # 0/0 ausfiltern
        },
        "clinical": {
            "description": "Clinical - Empfohlen für klinische Anwendungen",
            "filter_pass_only": True,
            "qual_threshold": 30.0,
            "use_dp_filter": True,
            "min_dp": 20,
            "max_dp": None,
            "filter_homref": True,  # 0/0 ausfiltern
        },
        "strict": {
            "description": "Strict - Maximale Spezifität",
            "filter_pass_only": True,
            "qual_threshold": 50.0,
            "use_dp_filter": True,
            "min_dp": 30,
            "max_dp": None,
            "filter_homref": True,  # 0/0 ausfiltern
        },
        "rma_sensitive": {
            "description": "RMA-Sensitive - Behält 0/0 für Reference Minor Allele Analyse",
            "filter_pass_only": True,
            "qual_threshold": 20.0,
            "use_dp_filter": True,
            "min_dp": 10,
            "max_dp": None,
            "filter_homref": False,  # 0/0 BEHALTEN für RMA-Suche
        },
        "custom": {
            "description": "Custom - Benutzerdefinierte Einstellungen",
            "filter_pass_only": True,
            "qual_threshold": 30.0,
            "use_dp_filter": True,
            "min_dp": 10,
            "max_dp": None,
            "filter_homref": True,  # 0/0 ausfiltern (änderbar)
        },
    }

    def __init__(self, preset="clinical", logger=None):
        """
        Initialisiert QualityManager.

        Args:
            preset: Preset-Name ("research", "clinical", "strict", "permissive", "rma_sensitive", "custom")
            logger: Optional Logger-Instanz
        """
        self.logger = logger
        self.current_preset = preset
        self._lock = threading.Lock()

        # Lade Preset
        if preset not in self.PRESETS:
            if self.logger:
                self.logger.log(f"[QualityManager] ⚠️ Unbekanntes Preset '{preset}', nutze 'clinical'")
            preset = "clinical"
            self.current_preset = preset

        self.settings = self.PRESETS[preset].copy()

        # Statistiken
        self.stats = {
            "total_checked": 0,
            "passed": 0,
            "failed_filter": 0,
            "failed_qual": 0,
            "failed_dp_min": 0,
            "failed_dp_max": 0,
            "failed_homref": 0,  # NEU: Counter für 0/0 Genotypen
            "no_dp": 0,
        }

        # V10 FIX: Auto-Detection für fehlende DP-Werte
        self._dp_samples_checked = 0
        self._dp_samples_found = 0
        self._dp_auto_disabled = False
        self._dp_auto_disable_threshold = 1000  # Nach 1000 Varianten ohne DP -> Warnung

        if self.logger:
            homref_status = "ausfiltern" if self.settings.get('filter_homref', True) else "BEHALTEN (RMA-Modus)"
            self.logger.log(
                f"[QualityManager] ✅ Initialisiert mit Preset '{preset}':\n"
                f"  FILTER: {'PASS only' if self.settings['filter_pass_only'] else 'Alle'}\n"
                f"  QUAL: ≥{self.settings['qual_threshold']}\n"
                f"  DP: {self.settings['min_dp']}-{self.settings['max_dp'] or '∞'} "
                f"({'aktiv' if self.settings['use_dp_filter'] else 'deaktiviert'})\n"
                f"  0/0 (hom-ref): {homref_status}"
            )

    def set_preset(self, preset: str):
        """
        Wechselt zu vordefiniertem Preset.

        Args:
            preset: Preset-Name
        """
        with self._lock:
            if preset not in self.PRESETS:
                raise ValueError(f"Unbekanntes Preset: {preset}. Verfügbar: {list(self.PRESETS.keys())}")

            self.current_preset = preset
            self.settings = self.PRESETS[preset].copy()

            if self.logger:
                self.logger.log(f"[QualityManager] ✅ Preset gewechselt zu '{preset}'")

    def get_preset_names(self) -> list:
        """Gibt Liste aller verfügbaren Preset-Namen zurück."""
        return list(self.PRESETS.keys())

    def get_preset_description(self, preset: str) -> str:
        """Gibt Beschreibung eines Presets zurück."""
        return self.PRESETS.get(preset, {}).get("description", "")

    def set_custom_settings(self,
                           filter_pass_only=None,
                           qual_threshold=None,
                           use_dp_filter=None,
                           min_dp=None,
                           max_dp=None,
                           filter_homref=None):
        """
        Setzt benutzerdefinierte Settings (Custom-Modus).

        Args:
            filter_pass_only: Nur PASS-Varianten akzeptieren
            qual_threshold: Minimum QUAL score
            use_dp_filter: DP-Filter aktivieren
            min_dp: Minimum read depth
            max_dp: Maximum read depth (None = unbegrenzt)
            filter_homref: 0/0 Genotypen ausfiltern (False für RMA-Analyse)
        """
        with self._lock:
            self.current_preset = "custom"

            if filter_pass_only is not None:
                self.settings["filter_pass_only"] = filter_pass_only
            if qual_threshold is not None:
                self.settings["qual_threshold"] = float(qual_threshold)
            if use_dp_filter is not None:
                self.settings["use_dp_filter"] = use_dp_filter
            if min_dp is not None:
                self.settings["min_dp"] = int(min_dp)
            if max_dp is not None:
                self.settings["max_dp"] = int(max_dp) if max_dp else None
            if filter_homref is not None:
                self.settings["filter_homref"] = filter_homref

            if self.logger:
                homref_status = "ausfiltern" if self.settings.get('filter_homref', True) else "BEHALTEN (RMA-Modus)"
                self.logger.log(
                    f"[QualityManager] ✅ Custom Settings aktiviert:\n"
                    f"  FILTER: {'PASS only' if self.settings['filter_pass_only'] else 'Alle'}\n"
                    f"  QUAL: ≥{self.settings['qual_threshold']}\n"
                    f"  DP: {self.settings['min_dp']}-{self.settings['max_dp'] or '∞'} "
                    f"({'aktiv' if self.settings['use_dp_filter'] else 'deaktiviert'})\n"
                    f"  0/0 (hom-ref): {homref_status}"
                )

    def get_settings(self) -> dict:
        """
        Gibt aktuelle Settings zurück.

        Returns:
            Dict mit allen aktuellen Einstellungen
        """
        with self._lock:
            return {
                "preset": self.current_preset,
                "filter_pass_only": self.settings["filter_pass_only"],
                "qual_threshold": self.settings["qual_threshold"],
                "use_dp_filter": self.settings["use_dp_filter"],
                "min_dp": self.settings["min_dp"],
                "max_dp": self.settings["max_dp"],
                "filter_homref": self.settings.get("filter_homref", True),
            }

    def passes(self, record: dict) -> bool:
        """
        ✅ HAUPTMETHODE: Prüft ob Variante Quality-Gates besteht.

        Args:
            record: VCF-Record dict mit Keys: filter, qual, info, fmt, samples

        Returns:
            bool: True wenn akzeptiert, False wenn gefiltert
        """
        with self._lock:
            self.stats["total_checked"] += 1

            # 1. FILTER-Check
            if self.settings["filter_pass_only"]:
                f = (record.get("filter") or ".")
                has_pass = f in ("PASS", ".")

                if not has_pass:
                    self.stats["failed_filter"] += 1
                    return False
            else:
                has_pass = True  # Filter ignorieren

            # 2. QUAL-Check
            try:
                qv = float(record.get("qual") or 0)
                has_qual = qv >= self.settings["qual_threshold"]
            except (ValueError, TypeError):
                has_qual = False

            # ── REVIEW-NOTIZ (Bugsweep 2026-06-22, BEWUSST NICHT geändert) ──────────────
            # Beobachtung: An dieser Stelle ist `has_pass` durch den Kontrollfluss oben
            # IMMER True (filter_pass_only=True → non-PASS wurde in der FILTER-Stufe bereits
            # mit `return False` verworfen; filter_pass_only=False → has_pass=True gesetzt).
            # Folge: `not has_pass and not has_qual` kann nie True werden — qual_threshold
            # (Presets 20/30/50) wirkt damit als KOMBINIERTES "PASS ODER QUAL"-Gate, NICHT
            # als eigenständiges QUAL-Mindest-Gate (QUAL allein verwirft keine Variante).
            # Das ist möglicherweise BEABSICHTIGT (FILTER=PASS impliziert ausreichende
            # Qualität). NICHT durch den automatischen Bugsweep geändert, weil:
            #   (a) jede Änderung das KLINISCHE Filterverhalten verschiebt, und
            #   (b) diese Logik in früheren Reviews mehrfach als "falsch" markiert wurde
            #       und sich dann als korrekt/beabsichtigt herausstellte.
            # Falls QUAL ein eigenständiges Gate sein SOLL: `if not has_qual: return False`.
            # → Fachliche Entscheidung des Maintainers (Lukas), bewusst offen gelassen.
            # ───────────────────────────────────────────────────────────────────────────
            if not has_pass and not has_qual:
                # Weder PASS noch ausreichendes QUAL
                self.stats["failed_qual"] += 1
                return False

            # 3. DP-Check (falls aktiviert UND nicht auto-deaktiviert)
            if self.settings["use_dp_filter"] and not self._dp_auto_disabled:
                dp = self._extract_dp(record)

                # V10 FIX: Tracke DP-Verfügbarkeit
                self._dp_samples_checked += 1

                if dp is not None:
                    self._dp_samples_found += 1

                    # Minimum DP
                    if dp < self.settings["min_dp"]:
                        self.stats["failed_dp_min"] += 1
                        return False

                    # Maximum DP (falls gesetzt)
                    max_dp = self.settings["max_dp"]
                    if max_dp is not None and dp > max_dp:
                        self.stats["failed_dp_max"] += 1
                        return False
                else:
                    # Kein DP vorhanden
                    self.stats["no_dp"] += 1

                    # V10 FIX: Auto-Disable Warnung wenn VCF keine DPs hat
                    if (self._dp_samples_checked >= self._dp_auto_disable_threshold and
                        self._dp_samples_found == 0 and not self._dp_auto_disabled):
                        self._dp_auto_disabled = True
                        if self.logger:
                            self.logger.log("─" * 60)
                            self.logger.log("[QualityManager] ⚠️ VCF enthält KEINE DP-Werte!")
                            self.logger.log("[QualityManager] ℹ️ DP-Filter wird ignoriert (PASS/QUAL bleibt aktiv)")
                            self.logger.log("─" * 60)
                    # Akzeptiere wenn PASS oder QUAL ok

            # 4. GENOTYPE-Check: 0/0 (hom-ref) ausfiltern (falls aktiviert)
            # HINWEIS: Kann deaktiviert werden für Reference Minor Allele (RMA) Analyse
            if self.settings.get("filter_homref", True):
                gt = self._extract_genotype(record)
                if gt == "ref":  # 0/0 = homozygote Referenz
                    self.stats["failed_homref"] += 1
                    return False

            # ✅ Alle Checks bestanden
            self.stats["passed"] += 1
            return True

    def _extract_dp(self, record: dict) -> Optional[int]:
        """
        Extrahiert DP aus FORMAT (bevorzugt - sample-spezifisch) oder INFO (Fallback).

        Args:
            record: VCF-Record dict

        Returns:
            int oder None

        V17 FIX: FORMAT-spezifisches DP vor INFO-DP priorisiert (Analog zu _get_dp_value).
                 Unterstützt sowohl 'sample' als auch 'samples' und bereinigt Tab-Reste.
        """
        # 1. FORMAT-Feld: GT:DP -> 0/1:45 (sample-spezifisch bevorzugt)
        fmt = record.get("fmt")
        if fmt and isinstance(fmt, str):
            try:
                fmt_fields = fmt.split(":")
                if "DP" in fmt_fields:
                    dp_idx = fmt_fields.index("DP")
                    sample_raw = record.get("sample")
                    if not sample_raw:
                        samples = record.get("samples")
                        if samples and isinstance(samples, (list, tuple)) and len(samples) > 0:
                            sample_raw = samples[0]
                    if sample_raw and isinstance(sample_raw, str):
                        if "\t" in sample_raw:
                            sample_raw = sample_raw.split("\t")[0]
                        sample_fields = sample_raw.split(":")
                        if dp_idx < len(sample_fields):
                            val = sample_fields[dp_idx].strip()
                            if val and val != ".":
                                return int(val)
            except (ValueError, IndexError, TypeError, AttributeError):
                pass

        # 2. INFO-Feld: DP=123 (fallback - multi-sample gesamt)
        info = record.get("info")
        if info:
            if isinstance(info, dict):
                dp_val = info.get("DP")
                if dp_val is not None:
                    try:
                        return int(dp_val)
                    except (ValueError, TypeError):
                        pass
            elif isinstance(info, str) and "DP=" in info:
                match = re.search(r'DP=(\d+)', info)
                if match:
                    try:
                        return int(match.group(1))
                    except ValueError:
                        pass

        return None

    def _extract_genotype(self, record: dict) -> str:
        """
        ✅ AKTUALISIERT: Extrahiert normalisierten Genotyp mit Hemizygous-Support.

        VCF-Standard:
        - Autosomen: 0/0, 0/1, 1/1 (diploid)
        - chrX non-PAR (männlich): 0, 1 (hemizygous)
        - chrY (männlich): 0, 1 (hemizygous)
        - chrM/MT: 0, 1 (haploid)

        HINWEIS zu Reference Minor Alleles (RMAs):
        Ein 0/0 Genotyp bedeutet NICHT automatisch "gesund".
        Das Referenzgenom kann pathogene Allele enthalten!

        Args:
            record: VCF-Record dict mit fmt und samples

        Returns:
            "het" | "hom" | "ref" | "hemi" | "." (normalisiert)
        """
        fmt = record.get("fmt")
        samples = record.get("samples", [])

        if not fmt or not samples:
            return "."

        # GT-Index finden
        fmt_keys = fmt.split(":")
        try:
            gt_idx = fmt_keys.index("GT")
        except ValueError:
            return "."

        # Sample-Werte extrahieren
        if not samples:
            return "."

        sample_vals = samples[0].split(":")
        if gt_idx >= len(sample_vals):
            return "."

        gt = sample_vals[gt_idx].strip()

        # Normalisiere (Phasing ignorieren: | -> /)
        gt = gt.replace("|", "/")

        # ═════════════════════════════════════════════════════════════════
        # ✅ KRITISCH: Hemizygous Check ZUERST (vor Diploid)
        # ═════════════════════════════════════════════════════════════════
        if "/" not in gt:
            # Hemizygous/Haploid: chrX non-PAR, chrY, MT
            if gt == ".":
                return "."
            try:
                allele = int(gt)
                if allele == 0:
                    return "ref"  # 0 = Referenz (hemizygous)
                else:
                    return "hemi"  # 1, 2, etc. = hemizygous alternativ
            except (ValueError, TypeError):
                return "."

        # ═════════════════════════════════════════════════════════════════
        # Diploid Mapping (Autosomen, chrX PAR)
        # ═════════════════════════════════════════════════════════════════
        GENOTYPE_MAP = {
            # Heterozygot
            "0/1": "het", "1/0": "het",
            "0/2": "het", "2/0": "het",
            "1/2": "het", "2/1": "het",
            # Homozygot alternativ
            "1/1": "hom", "2/2": "hom", "3/3": "hom",
            # Homozygot Referenz
            "0/0": "ref",
            # Missing
            "./.": ".", "./0": ".", "0/.": ".",
        }

        normalized = GENOTYPE_MAP.get(gt)
        if normalized:
            return normalized

        # ═════════════════════════════════════════════════════════════════
        # Fallback: Analysiere Allele manuell
        # ═════════════════════════════════════════════════════════════════
        alleles = gt.split("/")
        if len(alleles) != 2:
            return "."  # Ungültiges Format

        try:
            if "." in alleles:
                return "."
            a1, a2 = int(alleles[0]), int(alleles[1])

            if a1 == 0 and a2 == 0:
                return "ref"
            elif a1 == a2:
                return "hom"
            else:
                return "het"
        except (ValueError, TypeError):
            return "."

    def get_stats(self) -> dict:
        """
        Gibt Statistiken zurück.

        Returns:
            Dict mit Zählern
        """
        with self._lock:
            return self.stats.copy()

    def reset_stats(self):
        """Setzt Statistiken zurück."""
        with self._lock:
            self.stats = {
                "total_checked": 0,
                "passed": 0,
                "failed_filter": 0,
                "failed_qual": 0,
                "failed_dp_min": 0,
                "failed_dp_max": 0,
                "failed_homref": 0,  # NEU: Counter für 0/0 Genotypen
                "no_dp": 0,
            }

    def print_stats(self):
        """Gibt Statistiken aus."""
        with self._lock:
            total = self.stats["total_checked"]
            if total == 0:
                if self.logger:
                    self.logger.log("[QualityManager] Keine Varianten geprüft")
                return

            passed = self.stats["passed"]
            failed_total = total - passed

            msg = (
                f"[QualityManager] Statistik ({self.current_preset}):\n"
                f"  Total geprüft: {total:,}\n"
                f"  ✅ Bestanden: {passed:,} ({100*passed/total:.1f}%)\n"
                f"  ❌ Gefiltert: {failed_total:,} ({100*failed_total/total:.1f}%)\n"
            )

            if failed_total > 0:
                msg += "  Gründe:\n"
                if self.stats["failed_filter"] > 0:
                    msg += f"    - FILTER: {self.stats['failed_filter']:,}\n"
                if self.stats["failed_qual"] > 0:
                    msg += f"    - QUAL: {self.stats['failed_qual']:,}\n"
                if self.stats["failed_dp_min"] > 0:
                    msg += f"    - DP < {self.settings['min_dp']}: {self.stats['failed_dp_min']:,}\n"
                if self.stats["failed_dp_max"] > 0:
                    msg += f"    - DP > {self.settings['max_dp']}: {self.stats['failed_dp_max']:,}\n"
                if self.stats.get("failed_homref", 0) > 0:
                    msg += f"    - 0/0 (hom-ref): {self.stats['failed_homref']:,}\n"

            if self.stats["no_dp"] > 0:
                msg += f"  ℹ️ Ohne DP: {self.stats['no_dp']:,}\n"

            if self.logger:
                self.logger.log(msg)

    def get_vcf_sample_names(self, path: str) -> list:
        """Extrahiert Sample-Namen aus dem VCF-Header (#CHROM-Zeile, Spalten ab Index 9)."""
        try:
            with open_text_maybe_gzip(path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#CHROM"):
                        cols = line.split("\t")
                        if len(cols) > 9:
                            return cols[9:]
                        return []
                    if not line.startswith("#"):
                        break
        except Exception:
            pass
        return []
