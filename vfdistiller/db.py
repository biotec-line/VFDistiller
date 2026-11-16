# -*- coding: utf-8 -*-
"""SQLite-Datenbanklayer (VariantDB) ohne GUI-Abhängigkeit."""
from __future__ import annotations

from contextlib import contextmanager
import datetime
import json
import os
import sqlite3
import sys
import threading
import time
from typing import Dict, List, Optional, Tuple


class _DefaultDBConfig:
    DB_TIMEOUT_SEC = 30
    DB_WAL_MODE = True
    LOCAL_DB_DIR = ""


_DB_ENV = {
    "config_cls": _DefaultDBConfig,
    "base_dir_getter": os.getcwd,
    "resource_manager_getter": None,
}


def configure_db_environment(
    config_cls=None,
    base_dir_getter=None,
    resource_manager_getter=None,
) -> None:
    """Bindet Laufzeit-Config, BASE_DIR und ResourceManager in den DB-Layer ein."""
    if config_cls is not None:
        _DB_ENV["config_cls"] = config_cls
    if base_dir_getter is not None:
        _DB_ENV["base_dir_getter"] = base_dir_getter
    if resource_manager_getter is not None:
        _DB_ENV["resource_manager_getter"] = resource_manager_getter


class VariantDB:
    # Spaltenkonstanten (unverändert)
    KEY_COLS = ("chr", "pos", "ref", "alt", "build")
    DATA_COLS = (
        "rsid",
        "af_filter_mean", "af_exac", "af_gnomad_exomes", "af_gnomad_genomes", "af_1kg",
        "cadd_phred", "gene_symbol", "impact", "consequence",
        "clinical_significance", "phenotypes",
        "protein_coding", "is_coding", "conservation", "ag_score",
        "extra_json",
        "meanAF_last_fetch", "meanAF_fetch_success",
        "full_last_fetch", "full_fetch_success"
    )
    ALL_COLS = KEY_COLS + DATA_COLS

    # AKTUALISIERTE MAPPING-TABELLE (Single Source of Truth)
    UI_TO_DB = {
        # GUI Spaltenname : DB Spaltenname
        "chr": "chr",
        "pos": "pos",
        "ref": "ref",
        "alt": "alt",
        "build": "build",
        "rsid": "rsid",

        # Annotationen
        "af": "af_filter_mean",
        "cadd": "cadd_phred",
        "gene": "gene_symbol",
        "Gene": "gene_symbol",      # Alias
        "impact": "impact",
        "consequence": "consequence",
        "clin_sig": "clinical_significance",
        "phenotypes": "phenotypes",
        "coding": "is_coding",
        "ag": "ag_score",
        "cons": "conservation",

        # Status-Felder (für interne Zwecke)
        "meanAF_status": "meanAF_fetch_success",
        "full_status": "full_fetch_success"
    }
    DB_TO_UI = {v: k for k, v in UI_TO_DB.items()}

    # Status-Sets (unverändert)
    SUCCESS_CODES = {"1", "111"}
    GENERIC_FAIL_CODES = {"0", "000"}
    RENORM_CODES = {"010", "011", "012"}
    OTHER_FAIL_CODES = {"020", "030", "040"}
    DELETABLE_CODES = {"013"}

    @staticmethod
    def _get_writable_db_dir() -> str:
        """
        V17.3 MSIX FIX: Ermittelt einen beschreibbaren Ordner für die DB.

        Im MSIX/Store-Container ist das Installationsverzeichnis read-only.
        In diesem Fall wird %LOCALAPPDATA%/VariantFusion verwendet, das auch
        im MSIX-Container immer beschreibbar ist.
        """
        if getattr(sys, 'frozen', False):
            install_dir = os.path.dirname(sys.executable)
            test_path = os.path.join(install_dir, ".vf_write_test")
            try:
                with open(test_path, 'w') as f:
                    f.write("ok")
                os.remove(test_path)
            except (OSError, PermissionError):
                # Read-only → MSIX-Container
                appdata = os.path.join(
                    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                    "VariantFusion"
                )
                os.makedirs(appdata, exist_ok=True)
                print(f"[DB] MSIX-Modus erkannt, nutze AppData: {appdata}")
                return appdata
        return None

    def __init__(self, db_path: str = None):
        """
        Einfache Initialisierung ohne Connection Pool.

        V16: Wenn db_path=None, wird ResourceManager für variant_db genutzt.
        V17.2 FIX: Fallback nutzt BASE_DIR statt CWD (verhindert "unable to open
        database file" wenn CWD ein Systemordner ist, z.B. bei EXE-Start via Shortcut).
        V17.3 FIX: MSIX/Store-Kompatibilität – bei read-only Installationsverzeichnis
        wird %LOCALAPPDATA%/VariantFusion als DB-Speicherort verwendet.
        """
        # V17.3: MSIX/Store – prüfe ob Installationsverzeichnis beschreibbar ist
        msix_dir = self._get_writable_db_dir()

        cfg = _DB_ENV["config_cls"]
        base_dir = _DB_ENV["base_dir_getter"]()
        rm_getter = _DB_ENV["resource_manager_getter"]
        # V16: ResourceManager für DB-Pfad nutzen
        if db_path is None:
            try:
                rm = rm_getter() if rm_getter is not None else None
                rm_path = rm.get("variant_db") if rm is not None else None
                if rm_path and os.path.exists(rm_path):
                    db_path = rm_path
                    print(f"[DB] ✅ Via ResourceManager: {db_path}")
                else:
                    # Fallback: Check getattr(cfg, "LOCAL_DB_DIR", "")
                    if bool(getattr(cfg, "LOCAL_DB_DIR", "")) and os.path.exists(getattr(cfg, "LOCAL_DB_DIR", "")):
                        db_path = os.path.join(getattr(cfg, "LOCAL_DB_DIR", ""), "variant_fusion.sqlite")
                        print(f"[DB] Nutze lokalen Storage: {db_path}")
                    elif msix_dir:
                        # V17.3: MSIX-Fallback vor BASE_DIR
                        db_path = os.path.join(msix_dir, "variant_fusion.sqlite")
                        print(f"[DB] MSIX-Store: {db_path}")
                    else:
                        db_path = os.path.join(base_dir, "variant_fusion.sqlite")
                        print(f"[DB] ResourceManager: variant_db nicht gefunden, nutze Default: {db_path}")
            except Exception:
                db_path = os.path.join(msix_dir or base_dir, "variant_fusion.sqlite")

        # Sicherstellen dass der Zielordner existiert
        db_dir = os.path.dirname(os.path.abspath(db_path))
        os.makedirs(db_dir, exist_ok=True)

        self.db_path = db_path
        self.lock = threading.RLock()  # RLock für nested calls

        if not os.path.exists(self.db_path):
            print(f"[DB] {self.db_path} nicht gefunden – wird neu erstellt.")

        self._init_db()
        self._ensure_annotation_cache()

    @contextmanager
    def _conn(self):
        """
        Context manager für DB-Verbindungen.
        Jeder Thread bekommt bei Bedarf eine neue Connection.

        V12 FIX: Proper transaction management with DEFERRED isolation level.
        Automatic commit on success, rollback on error.
        """
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=getattr(_DB_ENV["config_cls"], "DB_TIMEOUT_SEC", 30),
                isolation_level=None,  # ✅ V12.1 REVERT: Autocommit (wie V11) - DEFERRED war zu langsam!
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row

            # Pragmas für Performance
            try:
                if getattr(_DB_ENV["config_cls"], "DB_WAL_MODE", True):
                    conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
                conn.execute("PRAGMA temp_store=MEMORY;")
                conn.execute("PRAGMA foreign_keys=ON;")
                conn.execute("PRAGMA busy_timeout=30000;")  # ✅ V12 FIX: Add busy timeout
            except Exception as e:
                print(f"[DB] Warning: PRAGMA config failed: {e}")

            yield conn

            # ✅ V12.1: Kein manuelles Commit bei Autocommit-Modus (isolation_level=None)
            # conn.commit()

        except Exception as e:
            # ✅ V12.1: Kein Rollback bei Autocommit-Modus
            # if conn:
            #     try:
            #         conn.rollback()
            #     except Exception as rb_err:
            #         print(f"[DB] Rollback error: {rb_err}")
            print(f"[DB] Connection error: {e}")
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def _init_db(self):
        """Initialisiert Schema."""
        with self.lock, self._conn() as con:
            cur = con.cursor()
            cur.execute("""
            CREATE TABLE IF NOT EXISTS variants (
                chr   TEXT    NOT NULL,
                pos   INTEGER NOT NULL,
                ref   TEXT    NOT NULL,
                alt   TEXT    NOT NULL,
                build TEXT    NOT NULL,

                rsid TEXT,

                af_filter_mean     REAL,
                af_exac            REAL,
                af_gnomad_exomes   REAL,
                af_gnomad_genomes  REAL,
                af_1kg             REAL,

                cadd_phred REAL,
                gene_symbol TEXT,
                impact TEXT,
                consequence TEXT,
                clinical_significance TEXT,
                phenotypes TEXT,
                protein_coding INTEGER,
                is_coding INTEGER,
                conservation TEXT,
                ag_score REAL,

                extra_json TEXT,

                meanAF_last_fetch   TEXT,
                meanAF_fetch_success TEXT,
                full_last_fetch     TEXT,
                full_fetch_success  TEXT,

                PRIMARY KEY (chr, pos, ref, alt, build)
            )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_rsid ON variants (rsid)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_full_status ON variants (full_fetch_success)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_meanAF_status ON variants (meanAF_fetch_success)")
            # ✅ V12 FIX: No manual commit - context manager handles it

    def _ensure_annotation_cache(self):
        """Cache-Tabelle für Gene-Annotationen."""
        with self.lock, self._conn() as con:
            cur = con.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS annotation_cache (
                    chr TEXT,
                    pos INTEGER,
                    ref TEXT,
                    alt TEXT,
                    build TEXT,
                    gene_symbol TEXT,
                    is_coding INTEGER,
                    PRIMARY KEY (chr, pos, ref, alt, build)
                )
            """)
            # ✅ V12 FIX: No manual commit - context manager handles it

    # -----------------------
    # Hilfsfunktion für Mapping
    # -----------------------
    def resolve_column(self, field: str) -> str:
        """Mappt UI- oder Alias-Namen auf den echten DB-Spaltennamen."""
        return self.UI_TO_DB.get(field, field)

    def upsert_variant(self, key, fields):
        """Fügt ein Variant-Row ein oder aktualisiert es (COALESCE verhindert Überschreiben mit NULL)."""
        with self.lock, self._conn() as con:
            self._upsert_variant_conn(con, key, fields)

    #CACHE für parallel zum Distiller laufenden GEN-Symbol-Annotation.
    def cache_annotations(self, updates):
        """
        Legt Annotationen in einer Cache-Tabelle ab.
        updates = [(key, {"gene_symbol": "BRCA1", "is_coding": True}), ...]
        """
        if not updates:
            return
        with self.lock, self._conn() as con:
            cur = con.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS annotation_cache (
                    chr TEXT,
                    pos INTEGER,
                    ref TEXT,
                    alt TEXT,
                    build TEXT,
                    gene_symbol TEXT,
                    is_coding INTEGER,
                    PRIMARY KEY (chr, pos, ref, alt, build)
                )
            """)
            for key, data in updates:
                cur.execute("""
                    INSERT OR REPLACE INTO annotation_cache
                    (chr, pos, ref, alt, build, gene_symbol, is_coding)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    key[0], key[1], key[2], key[3], key[4],
                    data["gene_symbol"], int(data["is_coding"])
                ))
            # ✅ V12 FIX: No manual commit - context manager handles it

    def flush_annotation_cache(self):
        rows_to_flush = []

        # ✅ Lese Cache außerhalb des DB-Locks
        try:
            with self.lock, self._conn() as con:
                cur = con.cursor()
                cur.execute("SELECT chr, pos, ref, alt, build, gene_symbol, is_coding FROM annotation_cache")
                rows_to_flush = cur.fetchall()

                if not rows_to_flush:
                    return 0

                cur.execute("DELETE FROM annotation_cache")
                # ✅ V12 FIX: No manual commit - context manager handles it
        except Exception as e:
            print(f"[DB] Cache-Flush-Fehler: {e}")
            return 0

        # ✅ Update außerhalb des Locks (parallel möglich)
        update_count = 0
        batch = []
        BATCH_SIZE = 1000

        for row in rows_to_flush:
            try:
                key = (row[0], row[1], row[2], row[3], row[4])
                batch.append((key, {
                    "gene_symbol": row[5],
                    "is_coding": bool(row[6])
                }))

                if len(batch) >= BATCH_SIZE:
                    self.update_variant_fields_bulk(batch)
                    update_count += len(batch)
                    batch.clear()

            except Exception as e:
                print(f"[DB] Fehler bei Cache-Flush für {key}: {e}")

        if batch:
            self.update_variant_fields_bulk(batch)
            update_count += len(batch)

        return update_count

    def _upsert_variant_conn(self, con, key, fields):
        fields = self._normalize_for_db(fields or {})
        cols = list(self.ALL_COLS)
        # Default-Daten: None, dann mit fields überschreiben
        data = {c: None for c in cols}
        data.update(fields)
        # Key setzen (überschreibt ggf. in fields gesetzte key-Werte konsistent)
        data["chr"], data["pos"], data["ref"], data["alt"], data["build"] = key

        placeholders = ",".join(["?"] * len(cols))
        updates = ",".join([
            f"{c}=COALESCE(excluded.{c}, {c})"
            for c in cols if c not in self.KEY_COLS
        ])
        vals = [data[c] for c in cols]

        con.execute(f"""
            INSERT INTO variants ({",".join(cols)})
            VALUES ({placeholders})
            ON CONFLICT(chr,pos,ref,alt,build) DO UPDATE SET {updates}
        """, vals)
    # Einfügen nach Zeile 7646 in der VariantDB Klasse
    def upsert_many(self, items, batch_commit=1000):
        """
        V12 FIX: Removed manual transaction management.
        Context manager now handles BEGIN/COMMIT/ROLLBACK automatically.
        Intermediate commits are handled by closing and reopening the connection.
        """
        if not items:
            return
        cols = list(self.ALL_COLS)
        placeholders = ",".join(["?"] * len(cols))
        updates = ",".join([f"{c}=COALESCE(excluded.{c}, {c})" for c in cols if c not in self.KEY_COLS])
        sql = f"INSERT INTO variants ({','.join(cols)}) VALUES ({placeholders}) ON CONFLICT(chr,pos,ref,alt,build) DO UPDATE SET {updates}"

        # ✅ V12 FIX: Process in batches with separate transactions
        for batch_start in range(0, len(items), batch_commit):
            batch_end = min(batch_start + batch_commit, len(items))
            batch_items = items[batch_start:batch_end]

            with self.lock, self._conn() as con:
                cur = con.cursor()
                for key, fields in batch_items:
                    fields = self._normalize_for_db(fields or {})
                    data = {c: None for c in cols}
                    data.update(fields)
                    data["chr"], data["pos"], data["ref"], data["alt"], data["build"] = key
                    vals = [data[c] for c in cols]
                    cur.execute(sql, vals)
                # Context manager commits automatically at end of batch


    # -----------------------
    # Select/Get-Operationen
    # -----------------------
    def get_positions(self, keys):
        """
        Liefert ein Mapping key -> (chrom, pos).
        Erwartet keys als (chr, pos, ref, alt, build).
        """
        return {key: (key[0], key[1]) for key in keys}

    def _normalize_for_db(self, record: dict) -> dict:
        """Sorgt dafür, dass JSON-Felder korrekt serialisiert werden."""
        rec = dict(record)
        if "conservation" in rec and isinstance(rec["conservation"], dict):
            rec["conservation"] = json.dumps(rec["conservation"])
        return rec

    def _parse_from_db(self, row: dict) -> dict:
        """Sorgt dafür, dass JSON-Felder beim Lesen automatisch geparst werden."""
        rec = dict(row)
        if "conservation" in rec and isinstance(rec["conservation"], str):
            try:
                rec["conservation"] = json.loads(rec["conservation"])
            except Exception:
                # Falls kein valides JSON, String unverändert lassen
                pass
        return rec

    def get_variant(self, key):
        with self.lock, self._conn() as con:
            cur = con.cursor()
            chr_, pos, ref, alt, build = key
            cur.execute(
                "SELECT * FROM variants WHERE chr=? AND pos=? AND ref=? AND alt=? AND build=?",
                (chr_, pos, ref, alt, build)
            )
            row = cur.fetchone()
            return self._parse_from_db(dict(row)) if row else None


    def get_variant_field(self, key, field):
        """Gibt einzelnes Feld zurück oder None, wenn Row/Feld fehlt."""
        if field not in self.ALL_COLS:
            return None
        with self.lock, self._conn() as con:
            cur = con.cursor()
            cur.execute(f"""
                SELECT {field} FROM variants
                WHERE chr=? AND pos=? AND ref=? AND alt=? AND build=?
            """, key)
            row = cur.fetchone()
            if not row:
                return None
            val = row[0]
            # Falls conservation-Feld: JSON parsen
            if field == "conservation" and isinstance(val, str):
                try:
                    import json
                    return json.loads(val)
                except Exception:
                    return val
            return val


    def get_variants_bulk(self, keys: List[Tuple]) -> Dict[Tuple, Optional[Dict]]:
        if not keys:
            return {}

        keys_clean = [tuple(k) for k in keys]
        results = {k: None for k in keys_clean}

        CHUNK_SIZE = 900
        CHUNK_TIMEOUT = 5.0  # ✅ Max 5 Sekunden pro Chunk
        MAX_TOTAL_TIME = 30.0  # ✅ Max 30s für gesamten Bulk-Lookup

        total_start = time.time()

        for i in range(0, len(keys_clean), CHUNK_SIZE):
            # ✅ Global Timeout Check
            if time.time() - total_start > MAX_TOTAL_TIME:
                if hasattr(self, 'logger') and self.logger:
                    self.logger.log(
                        f"[DB] ⚠️ Bulk-Fetch timeout after {MAX_TOTAL_TIME}s "
                        f"({i}/{len(keys_clean)} processed)"
                    )
                break

            chunk = keys_clean[i:i+CHUNK_SIZE]
            chunk_start = time.time()

            try:
                with self.lock, self._conn() as con:
                    # ✅ SQLite Lock-Timeout setzen
                    con.execute("PRAGMA busy_timeout = 3000")
                    cur = con.cursor()

                    # ✅ Timeout-Check vor Temp-Table
                    if time.time() - chunk_start > CHUNK_TIMEOUT:
                        continue

                    # ✅ V12 FIX: No manual BEGIN - context manager handles it

                    # Temp-Table erstellen
                    cur.execute("""
                        CREATE TEMP TABLE IF NOT EXISTS tmp_fetch_keys(
                            chr TEXT, pos INTEGER, ref TEXT, alt TEXT, build TEXT
                        )
                    """)
                    cur.execute("DELETE FROM tmp_fetch_keys")

                    # Chunk-Insert mit Timeout-Check
                    insert_sql = "INSERT INTO tmp_fetch_keys VALUES (?, ?, ?, ?, ?)"
                    timeout_occurred = False
                    for j in range(0, len(chunk), 100):
                        if time.time() - chunk_start > CHUNK_TIMEOUT:
                            timeout_occurred = True
                            break
                        mini_chunk = chunk[j:j+100]
                        cur.executemany(insert_sql, mini_chunk)

                    # ✅ V12.1: Skip on timeout (Autocommit - keine Rollback-Logik nötig)
                    if timeout_occurred:
                        continue  # Skip diesen Chunk, weiter mit nächstem

                    # JOIN mit Timeout-Check
                    if time.time() - chunk_start > CHUNK_TIMEOUT:
                        continue  # Skip diesen Chunk

                    cur.execute("""
                        SELECT v.*
                        FROM variants v
                        JOIN tmp_fetch_keys t
                          ON v.chr = t.chr
                         AND v.pos = t.pos
                         AND v.ref = t.ref
                         AND v.alt = t.alt
                         AND v.build = t.build
                    """)

                    rows = cur.fetchall()
                    colnames = [d[0] for d in cur.description]

                    for row in rows:
                        rowd = dict(zip(colnames, row))
                        rowd = self._parse_from_db(rowd)
                        key = (rowd["chr"], rowd["pos"], rowd["ref"], rowd["alt"], rowd["build"])
                        results[key] = rowd

                    cur.execute("DELETE FROM tmp_fetch_keys")
                    # ✅ V12 FIX: No manual COMMIT - context manager handles it

            except TimeoutError:
                # ✅ V12 FIX: Timeout exceptions are handled gracefully
                continue
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower():
                    continue
                raise
            except Exception as e:
                if hasattr(self, 'logger') and self.logger:
                    self.logger.log(f"[DB] ⚠️ Chunk {i//CHUNK_SIZE} failed: {e}")
                continue

        return results

    def get_all_variant_keys(self, build=None):
        with self.lock, self._conn() as con:
            cur = con.cursor()
            if build:
                cur.execute("""
                    SELECT chr,pos,ref,alt,build
                    FROM variants
                    WHERE build=?
                """, (build,))
            else:
                cur.execute("""
                    SELECT chr,pos,ref,alt,build
                    FROM variants
                """)
            return list(cur.fetchall())

    # -----------------------
    # Schlüssel-Migration
    # -----------------------

    def update_variant_key(self, old_key, new_key):
        """
        Migriert einen Datensatz atomar auf neuen zusammengesetzten Primärschlüssel.
        - Kopiert alle Nicht-Schlüssel-Felder.
        - Vermeidet Datenverlust bei Fehlern via Transaktion.

        V12 FIX: Removed manual transaction management.
        """
        with self.lock, self._conn() as con:
            cur = con.cursor()
            # ✅ V12 FIX: No manual BEGIN - context manager handles it

            cur.execute("""
                SELECT * FROM variants
                WHERE chr=? AND pos=? AND ref=? AND alt=? AND build=?""", old_key)
            row = cur.fetchone()
            if not row:
                return  # ✅ V12 FIX: Just return, context manager commits

            colnames = [d[0] for d in cur.description]
            data = dict(zip(colnames, row))

            # Neue Schlüsselwerte setzen
            data["chr"], data["pos"], data["ref"], data["alt"], data["build"] = new_key

            cols = colnames
            placeholders = ",".join(["?"] * len(cols))
            values = [data[c] for c in cols]

            merge_updates = ",".join([
                f"{c}=COALESCE(excluded.{c}, {c})"
                for c in cols if c not in self.KEY_COLS
            ])
            cur.execute(f"""
                INSERT INTO variants ({','.join(cols)}) VALUES ({placeholders})
                ON CONFLICT(chr,pos,ref,alt,build) DO UPDATE SET {merge_updates}
            """, values)

            cur.execute("""
                DELETE FROM variants
                WHERE chr=? AND pos=? AND ref=? AND alt=? AND build=?""", old_key)

            # ✅ V12 FIX: No manual COMMIT - context manager handles it
            # Exception will trigger automatic ROLLBACK

    def update_variant_fields(self, key, updates: dict):
        """
        Aktualisiert mehrere Felder für eine Variante.
        updates = {"gene_symbol": "BRCA1", "is_coding": True}
        """
        updates = self._normalize_for_db(updates or {})
        with self.lock, self._conn() as con:
            cur = con.cursor()
            sets = ", ".join([f"{field}=?" for field in updates.keys()])
            values = list(updates.values()) + list(key)
            cur.execute(f"""
                UPDATE variants
                SET {sets}
                WHERE chr=? AND pos=? AND ref=? AND alt=? AND build=?
            """, values)
            # ✅ V12 FIX: No manual commit - context manager handles it


    def update_variant_field(self, key, field, value):
        """
        Aktualisiert ein einzelnes Feld für eine Variante.
        key = (chr, pos, ref, alt, build)
        """
        updates = self._normalize_for_db({field: value})
        norm_value = updates[field]
        with self.lock, self._conn() as con:
            cur = con.cursor()
            cur.execute(f"""
                UPDATE variants
                SET {field} = ?
                WHERE chr=? AND pos=? AND ref=? AND alt=? AND build=?
            """, (norm_value, key[0], key[1], key[2], key[3], key[4]))
            con.commit()


    def update_variant_fields_bulk(self, updates):
        """
        updates = [(key, {"gene_symbol": "BRCA1", "is_coding": True}), ...]
        """
        if not updates:
            return
        with self.lock, self._conn() as con:
            cur = con.cursor()
            for key, data in updates:
                data = self._normalize_for_db(data or {})
                if not data:
                    continue
                # Nur tatsächlich übergebene Felder setzen (wie update_variant_fields).
                # Vorher hardcoded SET ...conservation=? -> der Live-Aufrufer
                # flush_annotation_cache (nur gene_symbol/is_coding) überschrieb
                # conservation bei JEDEM Flush mit NULL (Datenverlust).
                sets = ", ".join([f"{field}=?" for field in data.keys()])
                values = list(data.values()) + list(key)
                cur.execute(f"""
                    UPDATE variants
                    SET {sets}
                    WHERE chr=? AND pos=? AND ref=? AND alt=? AND build=?
                """, values)
            con.commit()

    def upsert_variants_bulk(self, records: dict):
        """
        records: {key: {"field1": val1, "field2": val2, ...}, ...}
        key = (chr, pos, ref, alt, build)

        Schreibt nur AF-Spalten und Success-/Timestamp-Felder.
        """
        if not records:
            return

        # Alle bekannten Spalten der Tabelle
        all_columns = [
            "chr", "pos", "ref", "alt", "build",
            "rsid",
            "af_filter_mean", "af_exac", "af_gnomad_exomes", "af_gnomad_genomes", "af_1kg",
            "cadd_phred", "gene_symbol", "impact", "consequence",
            "clinical_significance", "phenotypes",
            "protein_coding", "is_coding", "conservation",
            "ag_score", "extra_json",
            "meanAF_last_fetch", "meanAF_fetch_success",
            "full_last_fetch", "full_fetch_success"
        ]

        # Whitelist: nur diese Spalten dürfen überschrieben werden
        AF_COLUMNS = {
            "af_filter_mean", "af_exac", "af_gnomad_exomes", "af_gnomad_genomes", "af_1kg",
            "meanAF_last_fetch", "meanAF_fetch_success",
            "full_last_fetch", "full_fetch_success"
        }

        with self.lock, self._conn() as con:
            cur = con.cursor()
            for key, fields in records.items():
                chr_, pos, ref, alt, build = key

                # Default-Record mit None für alle Spalten
                record = {col: None for col in all_columns if col not in ("chr", "pos", "ref", "alt", "build")}
                # Eingehende Felder normalisieren und überschreiben
                record.update(self._normalize_for_db(fields or {}))

                cols = ["chr", "pos", "ref", "alt", "build"] + list(record.keys())
                placeholders = ",".join(["?"] * len(cols))
                values = [chr_, pos, ref, alt, build] + list(record.values())

                # Nur AF- und Success-Felder überschreiben
                merge_updates = ",".join([
                    f"{c}=excluded.{c}" for c in record.keys() if c in AF_COLUMNS
                ])

                sql = f"""
                    INSERT INTO variants ({','.join(cols)})
                    VALUES ({placeholders})
                    ON CONFLICT(chr,pos,ref,alt,build)
                    DO UPDATE SET {merge_updates}
                """
                cur.execute(sql, values)
            con.commit()

    def update_variant_rsids_bulk(self, updates):
        """
        updates = [(key, {"rsid": "rs123"}), ...]
        """
        if not updates:
            return
        with self.lock, self._conn() as con:
            cur = con.cursor()
            for key, data in updates:
                cur.execute("""
                    UPDATE variants
                    SET rsid=?
                    WHERE chr=? AND pos=? AND ref=? AND alt=? AND build=?
                """, (
                    data.get("rsid"),
                    key[0], key[1], key[2], key[3], key[4]
                ))
            # ✅ V12 FIX: No manual commit - context manager handles it

    # -----------------------
    # Shutdown / Cleanup
    # -----------------------

    def close(self):
        """
        V12 FIX: Proper database shutdown with WAL checkpoint.
        Call this before application exit to ensure data integrity.
        """
        try:
            with self._conn() as con:
                # ✅ Force WAL checkpoint before closing
                con.execute("PRAGMA wal_checkpoint(FULL);")
                print("[DB] WAL checkpoint completed successfully")
        except Exception as e:
            print(f"[DB] Warning: WAL checkpoint failed during shutdown: {e}")

    # -----------------------
    # Export/Reporting
    # -----------------------

    def select_for_export(self, build=None, af_threshold=None, include_none=False):
        """
        Gibt Tuples im UI-Format zurück. genotype und pubmed sind UI-only -> NULL/leer.
        Wendet AF-Threshold konsistent an (<= Schwelle; optional NULL zulassen).
        """
        # Dynamisch SELECT-Liste aus UI_COLUMNS erzeugen
        select_parts = []
        for col in self.UI_COLUMNS:
            if col == "genotype":
                select_parts.append("NULL AS genotype")
            elif col == "pubmed":
                select_parts.append("'' AS pubmed")
            else:
                db_field = self.resolve_column(col)
                if db_field != col:
                    select_parts.append(f"{db_field} AS {col}")
                else:
                    select_parts.append(col)

        base_select = "SELECT " + ", ".join(select_parts) + " FROM variants"

        params, conds = [], []
        if build:
            conds.append("build=?")
            params.append(build)
        if af_threshold is not None:
            if include_none:
                conds.append("(af_filter_mean <= ? OR af_filter_mean IS NULL)")
            else:
                conds.append("af_filter_mean <= ?")
            params.append(float(af_threshold))

        query = base_select
        if conds:
            query += " WHERE " + " AND ".join(conds)

        with self.lock, self._conn() as con:
            cur = con.execute(query, params)
            return cur.fetchall()

    # -----------------------
    # Feldprüfung
    # -----------------------

    def find_keys_without_field(self, field: str, limit: int = 100, only_filtered: bool = False):
        """
        Liefert Keys zurück, bei denen das angegebene Feld fehlt oder nur einen Platzhalter enthält.
        Nutzt resolve_column(), um UI- oder Alias-Namen auf DB-Feldnamen zu mappen.
        """
        db_field = self.resolve_column(field)
        with self.lock, self._conn() as con:
            cur = con.cursor()
            cur.execute(f"""
                SELECT chr, pos, ref, alt, build
                FROM variants
                WHERE {db_field} IS NULL
                   OR {db_field} = ''
                   OR {db_field} = '.'
                LIMIT ?
            """, (limit,))
            rows = cur.fetchall()

        keys = [(r[0], r[1], r[2], r[3], r[4]) for r in rows]

        if only_filtered:
            visible = getattr(self.distiller, "display_keys", set())
            keys = [k for k in keys if k in visible]

        return keys
    # -----------------------
    # Löschen
    # -----------------------

    def delete_variant(self, key):
        """Löscht eine Variante per zusammengesetztem Primärschlüssel."""
        with self.lock, self._conn() as con:
            con.execute("""
                DELETE FROM variants
                WHERE chr=? AND pos=? AND ref=? AND alt=? AND build=?
            """, key)

    def for_background_priorities(
        self,
        stale_days: int,
        p1_cooldown_hours: int,
        mode: str = "full",
        af_none_policy: str = "clinical",
        limit: int = 1000
    ):
        """
        ✅ GEFIXT: SQL-Syntax-Fehler in P3-Query behoben.
        ✅ V12.1: `limit` Parameter für GUI-Responsiveness beim Start.

        Liefert vier Listen (P0–P3) mit Kandidaten.

        Zeilenform: (chr, pos, ref, alt, build, fetch_success, last_fetch)

        Args:
            stale_days: Tage bis Daten als veraltet gelten
            p1_cooldown_hours: Cooldown für generische Fehler
            mode: "full" für Full-Annotation, "af" für AF-Only
            af_none_policy: "clinical", "research", "permissive", "strict"
            limit: Max. Anzahl Kandidaten pro Priority (Default 1000, beim Start 50)

        Returns:
            Tuple (P0, P1, P2, P3) - Listen von Kandidaten

        BUG-FIX:
        - ORDER BY muss NACH UNION kommen, nicht innerhalb
        - Separate Queries für P3 statt UNION mit ORDER BY
        - V12.1: Kleineres LIMIT beim ersten Call verhindert GUI-Freeze
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        stale_cutoff = now - datetime.timedelta(days=stale_days)
        p1_cutoff = now - datetime.timedelta(hours=p1_cooldown_hours)

        # Dynamisches Status-Feld basierend auf Mode
        status_field = "full_fetch_success" if mode == "full" else "meanAF_fetch_success"
        last_fetch_field = "full_last_fetch" if mode == "full" else "meanAF_last_fetch"

        def in_clause(vals):
            """Werte als Strings in SQL-Literal-Form"""
            return ",".join(f"'{str(v)}'" for v in vals)

        not_success = f"{status_field} NOT IN ({in_clause(self.SUCCESS_CODES)})"
        not_deletable = f"{status_field} NOT IN ({in_clause(self.DELETABLE_CODES)})"

        # AF-None-Awareness für AF-Mode
        af_none_clause = ""
        if mode == "af" and af_none_policy == "clinical":
            # Clinical: Priorisiere Varianten MIT AF-Daten
            af_none_clause = "AND af_filter_mean IS NOT NULL"

        with self.lock, self._conn() as con:
            cur = con.cursor()

            # ============================================================
            # P0: Stale Candidates
            # ============================================================
            cur.execute(f"""
                SELECT chr, pos, ref, alt, build, {status_field}, {last_fetch_field}
                FROM variants
                WHERE {not_success} AND {not_deletable}
                  AND ({last_fetch_field} IS NULL OR {last_fetch_field} < ?)
                  {af_none_clause}
                ORDER BY COALESCE({last_fetch_field}, '1970-01-01T00:00:00Z') ASC
                LIMIT ?
            """, (stale_cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"), limit))
            P0 = cur.fetchall()

            # ============================================================
            # P1: Generic Failures
            # ============================================================
            cur.execute(f"""
                SELECT chr, pos, ref, alt, build, {status_field}, {last_fetch_field}
                FROM variants
                WHERE {status_field} IN ({in_clause(self.GENERIC_FAIL_CODES)})
                  AND ({last_fetch_field} IS NULL OR {last_fetch_field} < ?)
                  {af_none_clause}
                ORDER BY COALESCE({last_fetch_field}, '1970-01-01T00:00:00Z') ASC
                LIMIT ?
            """, (p1_cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"), limit))
            P1 = cur.fetchall()

            # ============================================================
            # P2: Re-Normalization Cases
            # ============================================================
            cur.execute(f"""
                SELECT chr, pos, ref, alt, build, {status_field}, {last_fetch_field}
                FROM variants
                WHERE {status_field} IN ({in_clause(self.RENORM_CODES)})
                  {af_none_clause}
                ORDER BY COALESCE({last_fetch_field}, '1970-01-01T00:00:00Z') ASC
                LIMIT ?
            """, (limit,))
            P2 = cur.fetchall()

            # ============================================================
            # P3: Other Failures + AF=None (Clinical)
            # ✅ GEFIXT: Separate Queries statt UNION mit ORDER BY
            # ============================================================
            if mode == "af" and af_none_policy == "clinical":
                # Clinical-Mode: Erst OTHER_FAIL_CODES, dann AF=None

                # Teil 1: Other Failure Codes (ohne AF=None)
                p3_limit_half = max(1, limit // 2)
                cur.execute(f"""
                    SELECT chr, pos, ref, alt, build, {status_field}, {last_fetch_field}
                    FROM variants
                    WHERE {status_field} IN ({in_clause(self.OTHER_FAIL_CODES)})
                      AND af_filter_mean IS NOT NULL
                    ORDER BY COALESCE({last_fetch_field}, '1970-01-01T00:00:00Z') ASC
                    LIMIT ?
                """, (p3_limit_half,))
                p3_failures = cur.fetchall()

                # Teil 2: AF=None Varianten (niedrigere Priorität)
                cur.execute(f"""
                    SELECT chr, pos, ref, alt, build, {status_field}, {last_fetch_field}
                    FROM variants
                    WHERE {not_success} AND {not_deletable}
                      AND af_filter_mean IS NULL
                      AND ({last_fetch_field} IS NULL OR {last_fetch_field} < ?)
                    ORDER BY COALESCE({last_fetch_field}, '1970-01-01T00:00:00Z') ASC
                    LIMIT ?
                """, (stale_cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"), p3_limit_half))
                p3_af_none = cur.fetchall()

                # Kombiniere: Failures zuerst, dann AF=None
                P3 = p3_failures + p3_af_none
            else:
                # Standard: Nur OTHER_FAIL_CODES
                cur.execute(f"""
                    SELECT chr, pos, ref, alt, build, {status_field}, {last_fetch_field}
                    FROM variants
                    WHERE {status_field} IN ({in_clause(self.OTHER_FAIL_CODES)})
                      {af_none_clause}
                    ORDER BY COALESCE({last_fetch_field}, '1970-01-01T00:00:00Z') ASC
                    LIMIT ?
                """, (limit,))
                P3 = cur.fetchall()

        return P0, P1, P2, P3

    def find_cross_build_candidates(self, limit=100):
        """
        Findet Varianten-Paare (Build 37 <-> 38) mit gleicher rsID,
        bei denen Annotationen übertragen werden können.

        Strategie:
        Suche Target (T) ohne Gene/CADD/ClinVar, das einen Source (S)
        mit gleicher rsID aber anderem Build UND vorhandenen Daten hat.
        """
        # Felder, die wir übertragen wollen


        # Dynamische WHERE-Klausel: Target muss leer sein, Source muss voll sein
        # Wir prüfen exemplarisch auf 'gene_symbol', um Kandidaten zu finden

        query = """
            SELECT
                t.chr, t.pos, t.ref, t.alt, t.build,  -- Target Key
                s.gene_symbol, s.cadd_phred, s.clinical_significance,
                s.phenotypes, s.impact, s.consequence,
                s.build AS source_build
            FROM variants t
            JOIN variants s ON t.rsid = s.rsid
            WHERE
                t.rsid IS NOT NULL AND t.rsid != '.' AND t.rsid != ''
                AND t.build != s.build
                AND (t.gene_symbol IS NULL OR t.gene_symbol = '') -- Target fehlt Info
                AND (s.gene_symbol IS NOT NULL AND s.gene_symbol != '') -- Source hat Info
            LIMIT ?
        """

        with self.lock, self._conn() as con:
            cur = con.cursor()
            cur.execute(query, (limit,))
            return cur.fetchall()
