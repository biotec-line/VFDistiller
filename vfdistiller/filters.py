# -*- coding: utf-8 -*-
"""AF-None-Policies, Fetch-Status, Filter-Gate und Flag-Verwaltung."""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from vfdistiller.db import VariantDB

    GeneAnnotator = Any


class _DefaultFilterConfig:
    STALE_DAYS_AF = 365
    STALE_DAYS_FULL = 30


_FILTER_CONFIG = _DefaultFilterConfig


def configure_filter_environment(config_cls=None) -> None:
    """Bindet eine Laufzeit-Config-Klasse (mit STALE_DAYS_AF / STALE_DAYS_FULL) ein."""
    global _FILTER_CONFIG
    if config_cls is not None:
        _FILTER_CONFIG = config_cls


def _cfg_int(name: str, default: int) -> int:
    return int(getattr(_FILTER_CONFIG, name, default))


class FetchStatusManager:
    """
    Zentrale Verwaltung und Interpretation der Fetch-Statuscodes.
    - Kapselt Update-Logik (inkl. Eskalation)
    - Übersetzt Codes in Klartext
    - Bietet Hilfsfunktionen für Erfolg/Fehlschlag/Deletion
    """
    """
    ✅ DOKUMENTIERT: Status-Code-System für AF & Full-Anno

    ========================================================================
    STATUS-CODE-SYSTEM (3-stellig)
    ========================================================================

    Position:  [1] [2] [3]
               │   │   └─── Bearbeitungsstatus/Retry-Count (0-9)
               │   └─────── Fehlerart/Erfolgsart (0-4+)
               └─────────── Erfolg/Fehler (0=Fehler, 1=Erfolg)

    AKTUELLE CODES:
    ---------------
    "0"/"000" = Generischer Fehler, nie bearbeitet
    "1"/"111" = Erfolg, alle Quellen
    "010"     = Fehler in Queue, noch nicht bearbeitet
    "011"     = Fehler in Queue, 1. Retry fehlgeschlagen
    "012"     = Fehler in Queue, 2. Retry fehlgeschlagen
    "013"     = Fehler in Queue, 3. Retry/Exhausted

    RESERVIERT (zukünftig):
    -----------------------
    "020"-"029" = Quarantäne-System (9 Retries)
    "030"-"039" = Andere Fehlerklasse
    "040"       = Zur Löschung freigegeben

    ========================================================================
    4 AF-NONE-ZUSTÄNDE
    ========================================================================

    1. has_af          → af_filter_mean != NULL
    2. never_fetched   → meanAF_last_fetch = NULL
                          OR is_stale(>30d)
                          OR code="013"
    3. fetch_failed    → code in (0,000,010-012,020,030,040)
                          AND af_filter_mean = NULL
    4. true_none       → code in (1,111)
                          AND af_filter_mean = NULL
                          (validiert selten)

    ========================================================================
    """

    FETCH_STATUS_LABELS = {
        # Klassische Werte
        "0":   "Fehlschlag (generisch, wird erneut probiert)",
        "1":   "Erfolgreich",

        # Neue feinere Codes
        "000": "Fehlschlag (generisch, wird erneut probiert)",
        "010": "Normalisierung angefragt",
        "011": "Re-Normalisierung fehlgeschlagen (1. Versuch)",
        "012": "Re-Normalisierung fehlgeschlagen (2. Versuch)",
        "013": "Re-Normalisierung fehlgeschlagen (3. Versuch, zur Löschung markiert)",

        # Reservierte Codes
        "020": "Reserviert: andere Fehlerklasse (z. B. API-Fehler)",
        "030": "Reserviert: andere Fehlerklasse",
        "040": "Reserviert: andere Fehlerklasse",

        # Erfolgsstatus
        "111": "Erfolgreich"
    }

    @classmethod
    def status_label(cls, code) -> str:
        """Gibt eine menschenlesbare Beschreibung für den Fetch-Status zurück."""
        c = cls.normalize(code)
        return cls.FETCH_STATUS_LABELS.get(c, f"Unbekannter Status {c}")

    @classmethod
    def is_success(cls, code) -> bool:
        """True, wenn Status ein Erfolg ist."""
        c = cls.normalize(code)
        return c in {"1", "111"}

    @classmethod
    def is_failure(cls, code) -> bool:
        """True, wenn Status ein Fehlschlag ist (alle 0er-Codes)."""
        c = cls.normalize(code)
        return c in {"0", "000", "010", "011", "012", "013", "020", "030", "040"}

    @classmethod
    def needs_renormalization(cls, code) -> bool:
        """True, wenn Variante erneut normalisiert werden soll."""
        c = cls.normalize(code)
        return c in {"010", "011", "012"}

    @classmethod
    def is_deletable(cls, code) -> bool:
        """True, wenn Variante endgültig zur Löschung freigegeben ist."""
        c = cls.normalize(code)
        return c == "013"

    @classmethod
    def update_status(cls, current_status, success: bool) -> str:
        """
        Aktualisiert den Status nach Eskalationslogik.
        - success=True  -> "111"
        - success=False -> Eskalation
        """
        current = cls.normalize(current_status)

        if success:
            return "111"

        # Behandle leere Strings wie "0"
        if current in (None, "", "0", "000", "1", "111"):
            return "010"
        elif current == "010":
            return "011"
        elif current == "011":
            return "012"
        elif current == "012":
            return "013"
        elif current in {"020", "030", "040"}:
            return current
        else:
            return "000"

    @staticmethod
    def normalize(code) -> str:
        """Normalisiert Eingaben auf String-Statuscode."""
        if code is None:
            return "0"
        if isinstance(code, int):
            return str(code)
        return str(code).strip()

    @classmethod
    def classify_af_status(
        cls,
        af_value: Optional[float],
        last_fetch: Optional[str],
        fetch_status: Optional[str],
        stale_days: Optional[int] = None
    ) -> str:
        """
        ✅ Klassifiziert AF-Status in 4 Kategorien.

        Args:
            af_value: af_filter_mean Wert (oder None)
            last_fetch: meanAF_last_fetch Timestamp
            fetch_status: meanAF_fetch_success Status-Code
            stale_days: Tage bis Stale (default 30)

        Returns:
            "has_af"         - Hat validen AF-Wert
            "never_fetched"  - Noch nie/lange nicht/exhausted gefetcht
            "fetch_failed"   - Technischer Fehler (unvalidiert)
            "true_none"      - Erfolgreich, aber AF=None (validiert selten)

        =====================================================================
        MAPPING ZU DB-ZUSTÄNDEN:
        =====================================================================

        has_af:
          - af_filter_mean != NULL

        never_fetched:
          - meanAF_last_fetch = NULL
          - OR is_stale(meanAF_last_fetch, 30d)
          - OR meanAF_fetch_success = "013" (exhausted)

        fetch_failed:
          - meanAF_fetch_success NOT IN ("1","111","013",NULL)
          - AND af_filter_mean = NULL
          - Codes: "0","000","010","011","012","020","030","040"

        true_none:
          - meanAF_fetch_success IN ("1","111")
          - AND af_filter_mean = NULL
          - (Erfolgreicher Fetch, aber nicht in DBs → wahrscheinlich selten)

        =====================================================================
        """
        import datetime

        if stale_days is None:
            stale_days = _cfg_int("STALE_DAYS_AF", 365)

        # 1. Hat AF-Wert? → has_af
        if af_value is not None:
            return "has_af"

        # 2. Noch nie gefetcht?
        if not last_fetch or last_fetch == "":
            return "never_fetched"

        # 3. Stale-Check (>30 Tage alt)
        try:
            dt = datetime.datetime.fromisoformat(last_fetch.replace("Z", "+00:00"))
            age_days = (datetime.datetime.now(datetime.timezone.utc) - dt).days
            if age_days > stale_days:
                return "never_fetched"  # Stale = needs refetch
        except Exception:
            return "never_fetched"

        # 4. Status analysieren
        status = cls.normalize(fetch_status)

        # Exhausted? → never_fetched (Background-Only)
        if status == "013":
            return "never_fetched"

        # Erfolg ohne AF? → true_none (validiert selten)
        if cls.is_success(status):  # "1" oder "111"
            return "true_none"

        # Sonst: Fetch fehlgeschlagen
        return "fetch_failed"


class AfNoneTreatmentManager:
    """
    ✅ Policy-Verwaltung für AF-None-Behandlung.

    Verantwortlichkeiten:
    - Verwaltet Preset-basierte Policies
    - Klassifiziert None-Typen (via FetchStatusManager)
    - Tracked Statistiken
    - Beantwortet Policy-Fragen

    WICHTIG: Trifft KEINE Filter-Entscheidungen!
             Wird von _apply_af_filter_final() GENUTZT.

    ========================================================================
    STATUS-CODE-SYSTEM (3-stellig)
    ========================================================================

    Position:  [1] [2] [3]
               │   │   └─── Bearbeitungsstatus/Retry-Count (0-9)
               │   └─────── Fehlerart/Erfolgsart (0-4+)
               └─────────── Erfolg/Fehler (0=Fehler, 1=Erfolg)

    AKTUELLE CODES:
    ---------------
    "0"/"000" = Generischer Fehler, nie bearbeitet
    "1"/"111" = Erfolg, alle Quellen
    "010"     = Fehler in Queue, noch nicht bearbeitet
    "011"     = Fehler in Queue, 1. Retry fehlgeschlagen
    "012"     = Fehler in Queue, 2. Retry fehlgeschlagen
    "013"     = Fehler in Queue, 3. Retry/Exhausted

    RESERVIERT (zukünftig):
    -----------------------
    "020"-"029" = Quarantäne-System (9 Retries)
    "030"-"039" = Andere Fehlerklasse
    "040"       = Zur Löschung freigegeben

    ========================================================================
    4 AF-NONE-ZUSTÄNDE
    ========================================================================

    1. has_af          → af_filter_mean != NULL
    2. never_fetched   → meanAF_last_fetch = NULL
                          OR is_stale(>30d)
                          OR code="013"
    3. fetch_failed    → code in (0,000,010-012,020,030,040)
                          AND af_filter_mean = NULL
    4. true_none       → code in (1,111)
                          AND af_filter_mean = NULL
                          (validiert selten)

    ========================================================================
    VERWENDUNG
    ========================================================================

    # Initialisierung
    >>> manager = AfNoneTreatmentManager(preset="clinical", logger=logger)

    # None-Typ klassifizieren
    >>> none_type = manager.classify_none_type(row)

    # Policy abfragen
    >>> should_include = manager.should_include_type(none_type)

    # Statistik tracken
    >>> manager.record_decision(none_type, included=True)

    ========================================================================
    """

    # Preset-Policies
    PRESETS = {
        "permissive": {
            "description": "Maximale Sensitivität - alle None-Typen inkludieren",
            "never_fetched": True,
            "fetch_failed": True,
            "true_none": True,
        },
        "research": {
            "description": "Standard für Forschung - konservativ bei Fehlern",
            "never_fetched": True,
            "fetch_failed": False,
            "true_none": True,
        },
        "clinical": {
            "description": "Klinische Anwendung - nur validierte",
            "never_fetched": False,
            "fetch_failed": False,
            "true_none": True,
        },
        "strict": {
            "description": "Maximale Spezifität - nur echte AF-Werte",
            "never_fetched": False,
            "fetch_failed": False,
            "true_none": False,
        },
    }

    def __init__(self, preset: str = "clinical", logger=None):
        """
        Initialisiert Manager mit Preset.

        Args:
            preset: Name des Presets
            logger: Optional Logger
        """
        self.logger = logger
        self._lock = threading.RLock()

        self.current_preset = preset
        self.policy = self._load_preset(preset)

        # Statistiken (für Reporting)
        self.stats = {
            "total_checked": 0,
            "has_af_included": 0,
            "has_af_excluded": 0,
            "never_fetched_included": 0,
            "never_fetched_excluded": 0,
            "fetch_failed_included": 0,
            "fetch_failed_excluded": 0,
            "true_none_included": 0,
            "true_none_excluded": 0,
        }

        if self.logger:
            desc = self.policy.get("description", "")
            self.logger.log(
                f"[AfNoneTreatment] Initialisiert mit Preset '{preset}': {desc}"
            )

    def _load_preset(self, preset: str) -> dict:
        """Lädt Preset-Policy."""
        if preset not in self.PRESETS:
            if self.logger:
                self.logger.log(
                    f"[AfNoneTreatment] ⚠️ Unknown preset '{preset}', using 'clinical'"
                )
            preset = "clinical"

        return dict(self.PRESETS[preset])

    def set_preset(self, preset: str):
        """Setzt neues Preset."""
        with self._lock:
            self.policy = self._load_preset(preset)
            self.current_preset = preset

            if self.logger:
                desc = self.policy.get("description", "")
                self.logger.log(f"[AfNoneTreatment] Preset: '{preset}' - {desc}")

    def set_custom_policy(
        self,
        never_fetched: bool,
        fetch_failed: bool,
        true_none: bool
    ):
        """Setzt Custom-Policy."""
        with self._lock:
            self.policy = {
                "description": "Custom Policy",
                "never_fetched": never_fetched,
                "fetch_failed": fetch_failed,
                "true_none": true_none,
            }
            self.current_preset = "custom"

            if self.logger:
                self.logger.log(
                    f"[AfNoneTreatment] Custom Policy: "
                    f"never={never_fetched}, failed={fetch_failed}, true={true_none}"
                )

    def set_legacy_include_none(self, include_none: bool):
        """
        ✅ RÜCKWÄRTSKOMPATIBILITÄT: Legacy include_none → Policy.

        DEPRECATED: Nutze stattdessen set_custom_policy()
        """
        with self._lock:
            if include_none:
                self.set_custom_policy(
                    never_fetched=True,
                    fetch_failed=True,
                    true_none=True
                )
            else:
                self.set_custom_policy(
                    never_fetched=False,
                    fetch_failed=False,
                    true_none=True
                )

            if self.logger:
                self.logger.log(
                    f"[AfNoneTreatment] Legacy include_none={include_none} "
                    f"→ Konvertiert zu Custom Policy"
                )


    """
    ✅ ÖFFENTLICHE API (vom BackgroundMaintainer zu nutzen):
    """
    def classify_none_type(self, row: dict, stale_days: Optional[int] = None) -> str:
        """
        ✅ Klassifiziert AF-None-Typ.

        Args:
            row: DB-Row mit af_filter_mean, meanAF_last_fetch, meanAF_fetch_success
            stale_days: Tage bis Daten stale sind

        Returns:
            "has_af"        - AF-Wert vorhanden
            "never_fetched" - Noch nie geprüft oder stale
            "fetch_failed"  - Fetch-Fehler
            "true_none"     - Validiert ultra-rare
        """
        if stale_days is None:
            stale_days = _cfg_int("STALE_DAYS_AF", 365)
        return FetchStatusManager.classify_af_status(
            af_value=row.get("af_filter_mean"),
            last_fetch=row.get("meanAF_last_fetch"),
            fetch_status=row.get("meanAF_fetch_success"),
            stale_days=stale_days
        )

    def should_include_type(self, none_type: str) -> bool:
        """
        ✅ Fragt Policy für None-Typ ab.

        Args:
            none_type: "never_fetched" | "fetch_failed" | "true_none" | "has_af"

        Returns:
            True wenn inkludieren, False wenn excludieren
        """
        with self._lock:
            if none_type == "never_fetched":
                return self.policy.get("never_fetched", False)
            elif none_type == "fetch_failed":
                return self.policy.get("fetch_failed", False)
            elif none_type == "true_none":
                return self.policy.get("true_none", True)
            else:
                # "has_af" oder unknown
                return False

    def record_decision(
        self,
        none_type: str,
        included: bool
    ):
        """
        ✅ Tracked Statistik (von _apply_af_filter_final() aufgerufen).

        Args:
            none_type: Klassifizierter None-Typ
            included: Wurde inkludiert?
        """
        with self._lock:
            self.stats["total_checked"] += 1

            if none_type == "has_af":
                if included:
                    self.stats["has_af_included"] += 1
                else:
                    self.stats["has_af_excluded"] += 1
            elif none_type == "never_fetched":
                if included:
                    self.stats["never_fetched_included"] += 1
                else:
                    self.stats["never_fetched_excluded"] += 1
            elif none_type == "fetch_failed":
                if included:
                    self.stats["fetch_failed_included"] += 1
                else:
                    self.stats["fetch_failed_excluded"] += 1
            elif none_type == "true_none":
                if included:
                    self.stats["true_none_included"] += 1
                else:
                    self.stats["true_none_excluded"] += 1

    def get_policy(self) -> dict:
        """Gibt aktuelle Policy zurück."""
        with self._lock:
            return {
                "preset": self.current_preset,
                "never_fetched": self.policy.get("never_fetched"),
                "fetch_failed": self.policy.get("fetch_failed"),
                "true_none": self.policy.get("true_none"),
                "description": self.policy.get("description", "")
            }

    def get_stats(self) -> dict:
        """Gibt Statistiken zurück."""
        with self._lock:
            total = self.stats["total_checked"]
            if total == 0:
                return dict(self.stats)

            stats_with_pct = dict(self.stats)
            stats_with_pct["has_af_included_pct"] = (
                100.0 * self.stats["has_af_included"] / total
            )
            stats_with_pct["never_fetched_excluded_pct"] = (
                100.0 * self.stats["never_fetched_excluded"] / total
            )
            stats_with_pct["fetch_failed_excluded_pct"] = (
                100.0 * self.stats["fetch_failed_excluded"] / total
            )
            stats_with_pct["true_none_included_pct"] = (
                100.0 * self.stats["true_none_included"] / total
            )

            return stats_with_pct

    def print_stats(self):
        """Gibt formatierte Statistiken aus."""
        with self._lock:
            stats = self.get_stats()
            total = stats["total_checked"]

            if total == 0:
                if self.logger:
                    self.logger.log("[AfNoneTreatment] Keine Varianten geprüft")
                return

            policy = self.get_policy()

            msg = (
                f"[AfNoneTreatment] Statistik ({policy['preset']}):\n"
                f"  Total: {total:,} Varianten\n"
                f"\n"
                f"  ✅ AF vorhanden:\n"
                f"    Inkludiert: {stats['has_af_included']:,} "
                f"({stats.get('has_af_included_pct', 0):.1f}%)\n"
                f"    Exkludiert: {stats['has_af_excluded']:,} (AF > Threshold)\n"
                f"\n"
                f"  🔵 Nie geprüft: {policy['never_fetched'] and '✓' or '✗'}\n"
                f"    Inkludiert: {stats['never_fetched_included']:,}\n"
                f"    Exkludiert: {stats['never_fetched_excluded']:,} "
                f"({stats.get('never_fetched_excluded_pct', 0):.1f}%)\n"
                f"\n"
                f"  🟠 Fehlerhafte Abrufe: {policy['fetch_failed'] and '✓' or '✗'}\n"
                f"    Inkludiert: {stats['fetch_failed_included']:,}\n"
                f"    Exkludiert: {stats['fetch_failed_excluded']:,} "
                f"({stats.get('fetch_failed_excluded_pct', 0):.1f}%)\n"
                f"\n"
                f"  🟢 Validiert selten: {policy['true_none'] and '✓' or '✗'}\n"
                f"    Inkludiert: {stats['true_none_included']:,} "
                f"({stats.get('true_none_included_pct', 0):.1f}%)\n"
                f"    Exkludiert: {stats['true_none_excluded']:,}\n"
            )

            if self.logger:
                self.logger.log(msg)
            else:
                print(msg)

    def reset_stats(self):
        """Reset Statistiken."""
        with self._lock:
            self.stats = {k: 0 for k in self.stats.keys()}

    def get_preset_names(self) -> list:
        """Gibt Liste aller Preset-Namen zurück."""
        return list(self.PRESETS.keys())

    def get_preset_description(self, preset: str) -> str:
        """Gibt Beschreibung eines Presets zurück."""
        return self.PRESETS.get(preset, {}).get("description", "Unknown")


class Flag_and_Options_Manager:
    """
    V10: Zentrale Verwaltung ALLER Flags und Optionen.

    Kategorien:
    - Pipeline-Steuerung (af_threshold, include_none, etc.)
    - Filter-Flags (only_protein_coding, filter_pass_only)
    - Stale-Days (für Cache-Invalidierung)
    - API-Keys (AlphaGenome)
    - Post-Filter (CADD, ClinVar, Impact)
    - Debug-Optionen

    Thread-safe durch RLock.
    """

    def __init__(self, logger=None):
        self.logger = logger
        self._lock = threading.RLock()

        # ═══════════════════════════════════════════════════════════════════
        # PIPELINE HAUPTFILTER
        # ═══════════════════════════════════════════════════════════════════
        self.af_threshold: float = 0.01  # Max AF (1%)
        self.include_none: bool = True   # AF=None einschließen
        self.filter_pass_only: bool = False  # Nur PASS-Varianten
        self.qual_threshold: float = 30.0  # Min QUAL Score

        # ═══════════════════════════════════════════════════════════════════
        # PRÄ-FILTER (vor Pipeline)
        # ═══════════════════════════════════════════════════════════════════
        self.only_protein_coding: bool = False  # Nur protein-codierende Gene

        # ═══════════════════════════════════════════════════════════════════
        # CACHE STALE DAYS
        # ═══════════════════════════════════════════════════════════════════
        self.stale_days: int = _cfg_int("STALE_DAYS_AF", 365)        # AF-Daten Staleness
        self.stale_days_full: int = _cfg_int("STALE_DAYS_FULL", 30)  # Vollannotation Staleness

        # ═══════════════════════════════════════════════════════════════════
        # API KEYS
        # ═══════════════════════════════════════════════════════════════════
        self.alphagenome_key: Optional[str] = None

        # ═══════════════════════════════════════════════════════════════════
        # AF-NONE POLICY
        # ═══════════════════════════════════════════════════════════════════
        self.af_none_policy: str = "clinical"  # clinical, research, permissive, strict

        # ═══════════════════════════════════════════════════════════════════
        # POST-FILTER (GUI-Tabelle)
        # ═══════════════════════════════════════════════════════════════════
        self.postfilter_protein_coding: bool = False
        self.postfilter_cadd_min: Optional[float] = None

        # ClinVar Filter
        self.postfilter_benign: bool = True
        self.postfilter_likely_benign: bool = True
        self.postfilter_vus: bool = True
        self.postfilter_likely_path: bool = True
        self.postfilter_path: bool = True

        # Impact Filter
        self.postfilter_impact_high: bool = True
        self.postfilter_impact_moderate: bool = True
        self.postfilter_impact_low: bool = True

        # ═══════════════════════════════════════════════════════════════════
        # GEN-LISTEN
        # ═══════════════════════════════════════════════════════════════════
        self.gen_whitelist: str = ""
        self.gen_blacklist: str = ""

        # ═══════════════════════════════════════════════════════════════════
        # DEBUG / ENTWICKLUNG
        # ═══════════════════════════════════════════════════════════════════
        self.debug_show_db: bool = False
        self.skip_info_recycling: bool = False
        self.vcf_export_mode: str = "complete"  # complete, filtered
        self.cadd_highlight_threshold: float = 20.0

        # ═══════════════════════════════════════════════════════════════════
        # EXTERNE TOOLS
        # ═══════════════════════════════════════════════════════════════════
        self.external_db_viewer: str = ""

        if self.logger:
            self.logger.log("[FlagManager] V10 Initialisiert mit Defaults")

    # ───────────────────────────────────────────────────────────────────────
    # SYNC MIT GUI (tk.Var → Flag_Manager)
    # ───────────────────────────────────────────────────────────────────────

    def sync_from_gui(self, app):
        """
        Synchronisiert alle Werte von GUI tk-Variablen.
        Sollte vor Pipeline-Start aufgerufen werden.
        """
        with self._lock:
            try:
                # Pipeline
                self.af_threshold = float(app.af_threshold.get())
                self.include_none = bool(app.include_none.get())
                self.filter_pass_only = bool(app.filter_pass_only.get())
                self.qual_threshold = float(app.qual_threshold.get())

                # Prä-Filter
                self.only_protein_coding = bool(app.prefilter_protein_coding.get())

                # Stale Days
                self.stale_days = int(app.stale_days.get())
                self.stale_days_full = int(app.stale_days_full.get())

                # API Keys
                key = app.alphagenome_key.get().strip() if hasattr(app, 'alphagenome_key') else ""
                self.alphagenome_key = key if key else None

                # Post-Filter
                self.postfilter_protein_coding = bool(app.postfilter_protein_coding.get())
                cadd_str = app.postfilter_cadd_min.get().strip()
                self.postfilter_cadd_min = float(cadd_str) if cadd_str else None

                self.postfilter_benign = bool(app.postfilter_benign.get())
                self.postfilter_likely_benign = bool(app.postfilter_likely_benign.get())
                self.postfilter_vus = bool(app.postfilter_vus.get())
                self.postfilter_likely_path = bool(app.postfilter_likely_path.get())
                self.postfilter_path = bool(app.postfilter_path.get())

                self.postfilter_impact_high = bool(app.postfilter_impact_high.get())
                self.postfilter_impact_moderate = bool(app.postfilter_impact_moderate.get())
                self.postfilter_impact_low = bool(app.postfilter_impact_low.get())

                # Gen-Listen
                self.gen_whitelist = app.gen_whitelist.get().strip()
                self.gen_blacklist = app.gen_blacklist.get().strip()

                # Debug
                self.debug_show_db = bool(app.debug_show_db.get())
                self.skip_info_recycling = bool(app.skip_info_recycling.get())
                self.vcf_export_mode = app.vcf_export_mode.get()
                self.cadd_highlight_threshold = float(app.cadd_highlight_threshold.get())

                # Externe Tools
                self.external_db_viewer = app.external_db_viewer.get()

                if self.logger:
                    self.logger.log(f"[FlagManager] Sync von GUI: AF<={self.af_threshold}, Coding={self.only_protein_coding}")

            except Exception as e:
                if self.logger:
                    self.logger.log(f"[FlagManager] Sync-Fehler: {e}")

    # ───────────────────────────────────────────────────────────────────────
    # GETTER (Thread-Safe)
    # ───────────────────────────────────────────────────────────────────────

    def get_af_threshold(self) -> float:
        with self._lock:
            return self.af_threshold

    def get_include_none(self) -> bool:
        with self._lock:
            return self.include_none

    def get_filter_pass_only(self) -> bool:
        with self._lock:
            return self.filter_pass_only

    def get_qual_threshold(self) -> float:
        with self._lock:
            return self.qual_threshold

    def get_only_protein_coding(self) -> bool:
        with self._lock:
            return self.only_protein_coding

    def get_stale_days(self) -> int:
        with self._lock:
            return self.stale_days

    def get_stale_days_full(self) -> int:
        with self._lock:
            return self.stale_days_full

    def get_alphagenome_key(self) -> Optional[str]:
        with self._lock:
            return self.alphagenome_key

    def get_af_none_policy(self) -> str:
        with self._lock:
            return self.af_none_policy

    def get_cadd_highlight_threshold(self) -> float:
        with self._lock:
            return self.cadd_highlight_threshold

    # ───────────────────────────────────────────────────────────────────────
    # SETTER (Thread-Safe, mit Logging)
    # ───────────────────────────────────────────────────────────────────────

    def set_af_threshold(self, value: float):
        with self._lock:
            self.af_threshold = float(value)
            if self.logger:
                self.logger.log(f"[FlagManager] AF-Threshold -> {value}")

    def set_include_none(self, value: bool):
        with self._lock:
            self.include_none = bool(value)

    def set_only_protein_coding(self, value: bool):
        with self._lock:
            self.only_protein_coding = bool(value)
            if self.logger:
                self.logger.log(f"[FlagManager] Protein-Coding -> {value}")

    def set_af_none_policy(self, policy: str):
        valid = ["clinical", "research", "permissive", "strict"]
        with self._lock:
            if policy in valid:
                self.af_none_policy = policy
                if self.logger:
                    self.logger.log(f"[FlagManager] AF-None-Policy -> {policy}")
            else:
                if self.logger:
                    self.logger.log(f"[FlagManager] Ungueltige Policy: {policy}")

    def set_stale_days(self, days: int):
        with self._lock:
            self.stale_days = int(days)

    def set_stale_days_full(self, days: int):
        with self._lock:
            self.stale_days_full = int(days)

    def set_alphagenome_key(self, key: Optional[str]):
        with self._lock:
            self.alphagenome_key = key.strip() if key else None

    # ───────────────────────────────────────────────────────────────────────
    # EXPORT / IMPORT
    # ───────────────────────────────────────────────────────────────────────

    def get_all_flags(self) -> dict:
        """Exportiert alle Flags als Dict."""
        with self._lock:
            return {
                "af_threshold": self.af_threshold,
                "include_none": self.include_none,
                "filter_pass_only": self.filter_pass_only,
                "qual_threshold": self.qual_threshold,
                "only_protein_coding": self.only_protein_coding,
                "stale_days": self.stale_days,
                "stale_days_full": self.stale_days_full,
                "af_none_policy": self.af_none_policy,
                "cadd_highlight_threshold": self.cadd_highlight_threshold,
            }

    def set_from_dict(self, flags: dict):
        """Importiert Flags aus Dict."""
        with self._lock:
            for key, value in flags.items():
                if hasattr(self, key):
                    setattr(self, key, value)


class MainFilterGate:
    """
    V10: Zentrales Filter-Gate für alle Varianten-Filter.

    SubGates:
    - CodingFilter (Protein-Coding Check)
    - AfNoneTreatmentManager (AF=None Policy)

    Der Distiller fragt NUR dieses Gate, nicht die SubGates direkt.
    Alle Filter-Einstellungen werden vom Flag_and_Options_Manager geholt.

    Usage:
        gate = MainFilterGate(flag_manager, db, gene_annotator, logger)

        # Einzelne Variante:
        passed, reason, data = gate.check_variant(key, af_value=0.005)

        # Batch:
        results = gate.check_batch(variants)  # [(key, af, status), ...]
    """

    def __init__(
        self,
        flag_manager: 'Flag_and_Options_Manager',
        db: 'VariantDB',
        gene_annotator: Optional['GeneAnnotator'],
        logger
    ):
        self.flag_manager = flag_manager
        self.db = db
        self.logger = logger
        self._lock = threading.RLock()

        self._log("=" * 60)
        self._log("[MainFilterGate] V10 INITIALISIERUNG")
        self._log("=" * 60)

        # ═══════════════════════════════════════════════════════════════════
        # SUBGATE: CodingFilter
        # ═══════════════════════════════════════════════════════════════════
        self._coding_filter: Optional[CodingFilter] = None
        self._gene_annotator = gene_annotator

        if gene_annotator and getattr(gene_annotator, 'available', False):
            self._coding_filter = CodingFilter(db, gene_annotator, logger)
            self._log("[MainFilterGate] SubGate CodingFilter AKTIV")
        else:
            self._log("[MainFilterGate] SubGate CodingFilter INAKTIV (kein GeneAnnotator)")

        # ═══════════════════════════════════════════════════════════════════
        # SUBGATE: AfNoneTreatmentManager
        # ═══════════════════════════════════════════════════════════════════
        self._af_none_manager = AfNoneTreatmentManager(
            preset=flag_manager.get_af_none_policy(),
            logger=logger
        )
        self._log(f"[MainFilterGate] SubGate AfNoneTreatment (Policy: {flag_manager.get_af_none_policy()})")

        # ═══════════════════════════════════════════════════════════════════
        # BATCH BUFFER für Coding-Checks
        # ═══════════════════════════════════════════════════════════════════
        self._coding_batch_buffer: List[Tuple] = []
        self._coding_batch_results: Dict = {}
        self.CODING_BATCH_SIZE = 500

        # ═══════════════════════════════════════════════════════════════════
        # STATISTIKEN
        # ═══════════════════════════════════════════════════════════════════
        self.stats = {
            "total_checked": 0,
            "passed": 0,
            "failed_af": 0,
            "failed_coding": 0,
            "failed_none_policy": 0,
            "af_none_included": 0,
        }

        self._log("[MainFilterGate] Initialisierung abgeschlossen")
        self._log("=" * 60)

    def _log(self, msg: str):
        if self.logger:
            self.logger.log(msg)

    # ───────────────────────────────────────────────────────────────────────
    # SUBGATE ACCESSORS
    # ───────────────────────────────────────────────────────────────────────

    def get_coding_filter(self) -> Optional['CodingFilter']:
        """Gibt CodingFilter SubGate zurück (oder None)."""
        return self._coding_filter

    def get_af_none_manager(self) -> 'AfNoneTreatmentManager':
        """Gibt AfNoneTreatmentManager SubGate zurück."""
        return self._af_none_manager

    def is_coding_available(self) -> bool:
        """Prüft ob CodingFilter verfügbar ist."""
        return self._coding_filter is not None

    def set_gene_annotator(self, gene_annotator: 'GeneAnnotator'):
        """Setzt GeneAnnotator nachträglich (für Lazy Loading)."""
        self._gene_annotator = gene_annotator
        if gene_annotator and getattr(gene_annotator, 'available', False):
            self._coding_filter = CodingFilter(self.db, gene_annotator, self.logger)
            self._log("[MainFilterGate] CodingFilter nachträglich aktiviert")

    # ───────────────────────────────────────────────────────────────────────
    # HAUPTMETHODE: check_variant
    # ───────────────────────────────────────────────────────────────────────

    def check_variant(
        self,
        key: Tuple,
        af_value: Optional[float] = None,
        fetch_status: Optional[str] = None,
        last_fetch: Optional[str] = None
    ) -> Tuple[bool, str, dict]:
        """
        HAUPTMETHODE: Prüft ob Variante alle Filter besteht.

        Filter-Reihenfolge:
        1. AF-Filter (schnell)
        2. AF-None Policy (wenn AF=None)
        3. Protein-Coding Filter (wenn aktiviert)

        Args:
            key: Varianten-Key (chr, pos, ref, alt, build)
            af_value: Populations-AF (kann None sein)
            fetch_status: Status des AF-Fetches

        Returns:
            (passed, reason, data)
            - passed: True wenn alle Filter bestanden
            - reason: Grund für Ablehnung (oder "passed")
            - data: Zusätzliche Daten (gene_symbol, is_coding, etc.)
        """
        with self._lock:
            self.stats["total_checked"] += 1

        result_data = {"gene_symbol": None, "is_coding": None}

        # Hole aktuelle Einstellungen vom FlagManager
        af_threshold = self.flag_manager.get_af_threshold()
        include_none = self.flag_manager.get_include_none()
        only_coding = self.flag_manager.get_only_protein_coding()

        # ─────────────────────────────────────────────────────────────────
        # FILTER 1: AF-Threshold
        # ─────────────────────────────────────────────────────────────────
        if af_value is not None:
            if af_value > af_threshold:
                with self._lock:
                    self.stats["failed_af"] += 1
                return False, f"af>{af_threshold}", result_data

        # ─────────────────────────────────────────────────────────────────
        # FILTER 2: AF-None Policy (SubGate)
        # ─────────────────────────────────────────────────────────────────
        if af_value is None:
            # V10 FIX: classify_none_type erwartet row-Dict, nicht einzelne Parameter
            temp_row = {
                "af_filter_mean": af_value,
                "meanAF_fetch_success": fetch_status,
                "meanAF_last_fetch": last_fetch
            }
            none_type = self._af_none_manager.classify_none_type(temp_row)

            should_include = self._af_none_manager.should_include_type(none_type)

            if not should_include and not include_none:
                with self._lock:
                    self.stats["failed_none_policy"] += 1
                return False, f"af_none:{none_type}", result_data

            with self._lock:
                self.stats["af_none_included"] += 1

        # ─────────────────────────────────────────────────────────────────
        # FILTER 3: Protein-Coding (SubGate)
        # ─────────────────────────────────────────────────────────────────
        if only_coding:
            if not self._coding_filter:
                # Kein CodingFilter -> durchlassen
                pass
            else:
                # Einzelabfrage
                chrom, pos = key[0], key[1]
                coding_result = self._coding_filter.process_batch([(key, chrom, pos)])

                if key in coding_result:
                    data = coding_result[key]
                    result_data["gene_symbol"] = data.get("gene_symbol")
                    result_data["is_coding"] = data.get("is_coding")

                    if data.get("is_coding") in (False, 0):
                        with self._lock:
                            self.stats["failed_coding"] += 1
                        return False, "not_coding", result_data

        # ─────────────────────────────────────────────────────────────────
        # ALLE FILTER BESTANDEN
        # ─────────────────────────────────────────────────────────────────
        with self._lock:
            self.stats["passed"] += 1

        return True, "passed", result_data

    # ───────────────────────────────────────────────────────────────────────
    # BATCH-METHODE: check_batch
    # ───────────────────────────────────────────────────────────────────────

    def check_batch(
        self,
        variants: List[Tuple[Tuple, Optional[float], Optional[str]]]
    ) -> Dict[Tuple, Tuple[bool, str, dict]]:
        """
        Batch-Prüfung für mehrere Varianten.

        Args:
            variants: Liste von (key, af_value, fetch_status) Tupeln

        Returns:
            Dict[key -> (passed, reason, data)]
        """
        results = {}

        # Hole Einstellungen einmal
        af_threshold = self.flag_manager.get_af_threshold()
        include_none = self.flag_manager.get_include_none()
        only_coding = self.flag_manager.get_only_protein_coding()

        # Sammle Varianten für Coding-Batch
        coding_candidates = []

        for key, af_value, fetch_status in variants:
            with self._lock:
                self.stats["total_checked"] += 1

            result_data = {"gene_symbol": None, "is_coding": None}

            # AF-Filter
            if af_value is not None and af_value > af_threshold:
                with self._lock:
                    self.stats["failed_af"] += 1
                results[key] = (False, f"af>{af_threshold}", result_data)
                continue

            # AF-None Policy
            if af_value is None:
                # V10 FIX: classify_none_type erwartet row-Dict
                temp_row = {
                    "af_filter_mean": af_value,
                    "meanAF_fetch_success": fetch_status,
                    "meanAF_last_fetch": None
                }
                none_type = self._af_none_manager.classify_none_type(temp_row)
                should_include = self._af_none_manager.should_include_type(none_type)

                if not should_include and not include_none:
                    with self._lock:
                        self.stats["failed_none_policy"] += 1
                    results[key] = (False, f"af_none:{none_type}", result_data)
                    continue

                with self._lock:
                    self.stats["af_none_included"] += 1

            # Für Coding-Filter sammeln
            if only_coding and self._coding_filter:
                coding_candidates.append((key, key[0], key[1], af_value, fetch_status))
            else:
                with self._lock:
                    self.stats["passed"] += 1
                results[key] = (True, "passed", result_data)

        # Coding-Batch verarbeiten
        if coding_candidates and self._coding_filter:
            batch_input = [(k, c, p) for k, c, p, _, _ in coding_candidates]
            coding_results = self._coding_filter.process_batch(batch_input)

            for key, chrom, pos, af_value, fetch_status in coding_candidates:
                result_data = {"gene_symbol": None, "is_coding": None}

                if key in coding_results:
                    data = coding_results[key]
                    result_data["gene_symbol"] = data.get("gene_symbol")
                    result_data["is_coding"] = data.get("is_coding")

                    if data.get("is_coding") in (False, 0):
                        with self._lock:
                            self.stats["failed_coding"] += 1
                        results[key] = (False, "not_coding", result_data)
                        continue

                with self._lock:
                    self.stats["passed"] += 1
                results[key] = (True, "passed", result_data)

        return results

    # ───────────────────────────────────────────────────────────────────────
    # LEGACY COMPATIBILITY: passes()
    # ───────────────────────────────────────────────────────────────────────

    def passes(self, key: Tuple, af_value: Optional[float] = None) -> Tuple[bool, str]:
        """Legacy-Methode für Kompatibilität."""
        passed, reason, _ = self.check_variant(key, af_value)
        return passed, reason

    # ───────────────────────────────────────────────────────────────────────
    # STATISTIKEN
    # ───────────────────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        with self._lock:
            stats = self.stats.copy()

        # SubGate Stats hinzufügen
        if self._coding_filter:
            stats["coding_filter"] = self._coding_filter.get_stats()
        stats["af_none_policy"] = self._af_none_manager.current_preset

        return stats

    def reset_stats(self):
        with self._lock:
            self.stats = {k: 0 for k in self.stats}
        if self._coding_filter:
            self._coding_filter.reset_stats()

    def print_stats(self):
        stats = self.get_stats()
        total = stats.get("total_checked", 0)

        if total == 0:
            self._log("[MainFilterGate] Keine Varianten geprueft")
            return

        msg = (
            f"[MainFilterGate] Statistik:\n"
            f"  Geprueft: {total:,}\n"
            f"  Bestanden: {stats['passed']:,} ({100*stats['passed']/total:.1f}%)\n"
            f"  AF-Filter: {stats['failed_af']:,} abgelehnt\n"
            f"  None-Policy: {stats['failed_none_policy']:,} abgelehnt, {stats['af_none_included']:,} eingeschlossen\n"
            f"  Coding-Filter: {stats['failed_coding']:,} abgelehnt\n"
            f"  Policy: {stats['af_none_policy']}"
        )
        self._log(msg)


class CodingFilter:
    """
    Filtert Varianten basierend auf protein-kodierend Status.

    ✅ BATCH-FIRST Design für Performance.
    ✅ Wird von MainFilterGate aufgerufen.
    """

    def __init__(self, db: 'VariantDB', gene_annotator: Optional['GeneAnnotator'], logger):
        self.db = db
        self.gene_annotator = gene_annotator
        self.logger = logger

        self.stats = {
            "db_hits": 0,
            "annotator_calls": 0,
            "unknown": 0,
            "batches_processed": 0
        }

        # ✅ V9: Status-Logging bei Initialisierung
        if logger:
            logger.log("[CodingFilter] ✅ Initialisiert")
            if gene_annotator:
                logger.log(f"[CodingFilter] GeneAnnotator verfügbar: {gene_annotator.available}")
            else:
                logger.log("[CodingFilter] ⚠️ KEIN GeneAnnotator übergeben!")

    # In CodingFilter Klasse:

    def process_batch(self, variants: list) -> dict:
        """
        ✅ HAUPT-METHODE: Verarbeitet Batch von Varianten.

        Args:
            variants: Liste von (key, chrom, pos) Tupeln

        Returns:
            Dict[key -> {'is_coding': bool, 'gene_symbol': str}]
            Gibt jetzt das volle Datenobjekt zurück, nicht nur den Boolean.
        """
        if not variants:
            return {}

        results = {}
        self.stats["batches_processed"] += 1

        # ✅ V9: Periodisches Logging
        if self.stats["batches_processed"] == 1 or self.stats["batches_processed"] % 10 == 0:
            if self.logger:
                self.logger.log(f"[CodingFilter] Batch #{self.stats['batches_processed']}: {len(variants)} Varianten")
                self.logger.log(f"[CodingFilter] GeneAnnotator vorhanden: {self.gene_annotator is not None}")
                if self.gene_annotator:
                    self.logger.log(f"[CodingFilter] GeneAnnotator.available: {self.gene_annotator.available}")

        # STEP 1: Bulk-Check in VariantDB
        keys = [v[0] for v in variants]
        to_annotate = []

        # Hole existierende Daten
        db_results = self.db.get_variants_bulk(keys)

        for key, chrom, pos in variants:
            row = db_results.get(key)
            # Wir nehmen den Wert aus der DB nur, wenn is_coding gesetzt ist
            if row and row.get("is_coding") is not None:
                results[key] = {
                    "is_coding": bool(row["is_coding"]),
                    "gene_symbol": row.get("gene_symbol")
                }
                self.stats["db_hits"] += 1
            else:
                to_annotate.append((key, chrom, pos))

        # STEP 2: GeneAnnotator-Batch für fehlende
        if to_annotate and self.gene_annotator and self.gene_annotator.available:
            try:
                annotations = self.gene_annotator.annotate_batch(to_annotate)
                bulk_updates = []

                for key, chrom, pos in to_annotate:
                    if key in annotations:
                        data = annotations[key]
                        is_coding = data.get("is_coding")
                        gene_symbol = data.get("gene_symbol")

                        if is_coding is not None:
                            # Ergebnis zusammenbauen
                            result_entry = {
                                "is_coding": bool(is_coding),
                                "gene_symbol": gene_symbol
                            }
                            results[key] = result_entry

                            # DB Update vorbereiten
                            update_fields = {"is_coding": is_coding}
                            if gene_symbol:
                                update_fields["gene_symbol"] = gene_symbol

                            bulk_updates.append((key, update_fields))
                            self.stats["annotator_calls"] += 1
                        else:
                            # Nicht gefunden -> Treat as FALSE (not coding)
                            results[key] = {"is_coding": False, "gene_symbol": None}
                            self.stats["unknown"] += 1
                    else:
                        # Nicht in Annotations gefunden -> Treat as FALSE
                        results[key] = {"is_coding": False, "gene_symbol": None}
                        self.stats["unknown"] += 1

                # STEP 3: Bulk-Update in DB (Cache)
                if bulk_updates:
                    self.db.cache_annotations(bulk_updates)

            except Exception as e:
                self.logger.log(f"[CodingFilter] ⚠️ Batch annotation error: {e}")
                for key, _, _ in to_annotate:
                    if key not in results:
                        results[key] = {"is_coding": None, "gene_symbol": None}
                        self.stats["unknown"] += 1

        elif to_annotate:
            # Fallback wenn kein Annotator da ist
            # ✅ V9: Warnung nur beim ersten Mal
            if self.stats["batches_processed"] == 1:
                if self.logger:
                    self.logger.log(f"[CodingFilter] ⚠️ {len(to_annotate)} Varianten ohne Annotation!")
                    self.logger.log(f"[CodingFilter] ⚠️ GeneAnnotator: {self.gene_annotator}")
                    if self.gene_annotator:
                        self.logger.log(f"[CodingFilter] ⚠️ GeneAnnotator.available: {self.gene_annotator.available}")
                    self.logger.log("[CodingFilter] ⚠️ Gene-Symbole werden NICHT annotiert!")

            for key, _, _ in to_annotate:
                results[key] = {"is_coding": None, "gene_symbol": None}
                self.stats["unknown"] += 1

        return results

    def is_protein_coding(self, key: tuple, chrom: str, pos: int) -> Optional[bool]:
        """Einzelabfrage (Wrapper)."""
        res_dict = self.process_batch([(key, chrom, pos)])
        data = res_dict.get(key)
        return data.get("is_coding") if data else None

    def get_stats(self) -> dict:
        return self.stats.copy()

    def reset_stats(self):
        self.stats = {
            "db_hits": 0,
            "annotator_calls": 0,
            "unknown": 0,
            "batches_processed": 0
        }
