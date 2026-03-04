import os
import sqlite3
import requests
import gzip
import shutil

# Zenodo-Links für die WGS-Datenbanken
URLS = {
    "GRCh37": "https://zenodo.org/record/5770384/files/gnomad_db_v2.1.1.sqlite3.gz?download=1",
    "GRCh38": "https://zenodo.org/record/6818606/files/gnomad_db_v3.1.2.sqlite3.gz?download=1"
}

OUT_DB = "gnomad_light.db"

def download_file(url, out_path):
    """Download file with streaming to avoid memory blowup."""
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

def gunzip_file(gz_path, out_path):
    """Extract .gz file to plain sqlite3 db."""
    with gzip.open(gz_path, "rb") as f_in, open(out_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)

def migrate_build(src_db, build, dest_db):
    """Copy only chrom,pos,ref,alt,rsid,af into a new light DB with build tag."""
    src = sqlite3.connect(src_db)
    dst = sqlite3.connect(dest_db)

    # Ziel-Tabelle anlegen (falls nicht existiert)
    dst.execute("""
        CREATE TABLE IF NOT EXISTS variants_light (
            chrom TEXT,
            pos INTEGER,
            ref TEXT,
            alt TEXT,
            build TEXT,
            rsid TEXT,
            af REAL
        )
    """)
    dst.execute("CREATE INDEX IF NOT EXISTS idx_variants_light ON variants_light(chrom,pos,ref,alt,build)")

    cur = src.cursor()
    # Achtung: Tabellennamen in den Zenodo-DBs ist "variants"
    cur.execute("SELECT chrom, pos, ref, alt, rsid, af FROM variants")

    rows = cur.fetchmany(100000)
    while rows:
        dst.executemany(
            "INSERT INTO variants_light (chrom,pos,ref,alt,build,rsid,af) VALUES (?,?,?,?,?,?,?)",
            [(c, p, r, a, build, rs, af) for (c, p, r, a, rs, af) in rows]
        )
        dst.commit()
        rows = cur.fetchmany(100000)

    src.close()
    dst.close()

def main():
    for build, url in URLS.items():
        gz_path = f"{build}.sqlite3.gz"
        db_path = f"{build}.sqlite3"

        print(f"Downloading {build} from {url} ...")
        download_file(url, gz_path)

        print(f"Extracting {gz_path} ...")
        gunzip_file(gz_path, db_path)
        os.remove(gz_path)

        print(f"Migrating {build} into {OUT_DB} ...")
        migrate_build(db_path, build, OUT_DB)

        print(f"Cleaning up {db_path} ...")
        os.remove(db_path)

    print(f"✅ Light-DB fertig: {OUT_DB}")

if __name__ == "__main__":
    main()