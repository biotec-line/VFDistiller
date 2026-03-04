#!/usr/bin/env python3
import sqlite3, sys, json, time, os, traceback

def ensure_index_worker(db_path: str, progress_file: str):
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # Prüfen, ob Index existiert
        cur.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND name='idx_variants_light_lookup';
        """)
        if cur.fetchone():
            print("[LightDB] Index bereits vorhanden.")
            conn.close()
            return

        # Anzahl Zeilen bestimmen
        cur.execute("SELECT COUNT(*) FROM variants_light;")
        total_rows = cur.fetchone()[0]
        print(f"[LightDB] Erstelle Index über {total_rows:,} Zeilen...")

        start_time = time.time()
        last_log = 0  # Zeitstempel für Logging
        steps = {"count": 0}

        def write_progress(done, total, pct):
            """Atomar Fortschritt schreiben."""
            tmp_file = progress_file + ".tmp"
            with open(tmp_file, "w") as f:
                json.dump({"done": done, "total": total, "pct": pct}, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_file, progress_file)

        def progress_handler():
            nonlocal last_log
            steps["count"] += 1

            # Nur alle 60s loggen oder am Ende
            now = time.time()
            if now - last_log >= 60 or steps["count"] >= total_rows:
                elapsed = now - start_time
                done = steps["count"]
                pct = 100.0 * done / max(1, total_rows)
                rate = done / elapsed if elapsed > 0 else 0
                eta = (total_rows - done) / rate if rate > 0 else None
                eta_str = "--:--"
                if eta:
                    m, s = divmod(int(eta), 60)
                    h, m = divmod(m, 60)
                    eta_str = f"{h:02d}:{m:02d}:{s:02d}"

                write_progress(done, total_rows, pct)
                print(f"[LightDB] Fortschritt: {pct:.1f}% (ETA {eta_str})")
                last_log = now

            return 0

        # Progress-Handler seltener triggern (Performance)
        conn.set_progress_handler(progress_handler, 50000)

        # Index erstellen
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_variants_light_lookup
            ON variants_light (chrom,pos,ref,alt,build);
        """)
        conn.commit()
        conn.close()
        print("[LightDB] Index erfolgreich erstellt.")

        # Finalen Fortschritt schreiben
        write_progress(total_rows, total_rows, 100.0)
        print("[LightDB] Fortschritt: 100% (fertig)")

        # PID-Datei löschen, wenn vorhanden
        pid_file = os.path.join(os.path.dirname(progress_file), "lightdb_index.pid")
        try:
            if os.path.exists(pid_file):
                os.remove(pid_file)
        except Exception:
            pass

    except Exception as e:
        print(f"[LightDB] Fehler im Index-Worker: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: lightdb_index_worker.py <db_path> <progress_file>")
        sys.exit(1)
    db_path, progress_file = sys.argv[1], sys.argv[2]
    ensure_index_worker(db_path, progress_file)