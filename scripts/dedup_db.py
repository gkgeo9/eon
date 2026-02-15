#!/usr/bin/env python3
"""
Remove duplicate rows from the EON database.

Targets tables that can accumulate duplicate entries from batch processing
or resume runs. For each table, duplicates are identified by their logical
key columns (ignoring auto-increment id and timestamp differences).
The earliest row (lowest id) is kept.

Usage:
    python scripts/dedup_db.py                  # dry-run (default)
    python scripts/dedup_db.py --apply          # actually delete duplicates
    python scripts/dedup_db.py --db data/other.db --apply
"""

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_DB = "data/eon.db"

# Define the logical key columns that identify a unique row per table.
# Rows matching on these columns are considered duplicates — we keep the one
# with the lowest primary key (earliest inserted).
TABLE_DEDUP_KEYS = {
    "analysis_results": {
        "pk": "id",
        "key_cols": ["run_id", "ticker", "fiscal_year", "filing_type", "result_type"],
    },
    "file_cache": {
        "pk": "id",
        "key_cols": ["ticker", "fiscal_year", "filing_type"],
    },
    "batch_items": {
        "pk": "id",
        "key_cols": ["batch_id", "ticker"],
    },
    "workflow_step_outputs": {
        "pk": "id",
        "key_cols": ["workflow_run_id", "step_id"],
    },
    "api_usage": {
        "pk": "id",
        "key_cols": ["api_key_suffix", "usage_date"],
    },
}


def scan_table(conn: sqlite3.Connection, table: str, pk: str, key_cols: list[str]) -> dict:
    """Count total rows and duplicates for a table based on its logical key."""
    cur = conn.cursor()
    cur.row_factory = sqlite3.Row

    cur.execute(f"SELECT COUNT(*) as cnt FROM {table}")
    total = cur.fetchone()["cnt"]

    col_list = ", ".join(key_cols)
    cur.execute(f"SELECT COUNT(*) as cnt FROM (SELECT DISTINCT {col_list} FROM {table})")
    unique = cur.fetchone()["cnt"]

    return {"total": total, "unique": unique, "duplicates": total - unique}


def show_sample_duplicates(conn: sqlite3.Connection, table: str, pk: str, key_cols: list[str], limit: int = 5):
    """Print sample duplicate groups for review."""
    cur = conn.cursor()
    cur.row_factory = sqlite3.Row

    col_list = ", ".join(key_cols)
    cur.execute(f"""
        SELECT {col_list}, COUNT(*) as cnt
        FROM {table}
        GROUP BY {col_list}
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
        LIMIT {limit}
    """)
    rows = cur.fetchall()
    if rows:
        print(f"    Sample duplicates (top {limit}):")
        for row in rows:
            parts = [f"{k}={row[k]}" for k in key_cols]
            print(f"      {', '.join(parts)}  (x{row['cnt']})")


def remove_duplicates(conn: sqlite3.Connection, table: str, pk: str, key_cols: list[str]) -> int:
    """
    Remove duplicate rows, keeping the one with the lowest primary key.
    Returns the number of rows deleted.
    """
    col_list = ", ".join(key_cols)

    query = f"""
        DELETE FROM {table}
        WHERE {pk} NOT IN (
            SELECT MIN({pk})
            FROM {table}
            GROUP BY {col_list}
        )
    """
    cur = conn.cursor()
    cur.execute(query)
    return cur.rowcount


def main():
    parser = argparse.ArgumentParser(description="Remove duplicate rows from EON database")
    parser.add_argument("--db", default=DEFAULT_DB, help=f"Path to database (default: {DEFAULT_DB})")
    parser.add_argument("--apply", action="store_true", help="Actually delete duplicates (default is dry-run)")
    parser.add_argument("--no-backup", action="store_true", help="Skip creating a backup before changes")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    print(f"Database: {db_path} ({db_path.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"Mode: {'APPLY (will modify database)' if args.apply else 'DRY-RUN (no changes)'}")
    print()

    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")

    # Check which configured tables actually exist
    conn.row_factory = sqlite3.Row
    existing_tables = {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }

    # Scan for duplicates
    tables_with_dupes = {}
    print("Scanning tables...")
    for table, config in TABLE_DEDUP_KEYS.items():
        if table not in existing_tables:
            continue

        stats = scan_table(conn, table, config["pk"], config["key_cols"])
        key_desc = ", ".join(config["key_cols"])

        if stats["duplicates"] > 0:
            tables_with_dupes[table] = {**config, **stats}
            print(f"  {table}: {stats['duplicates']} duplicates / {stats['total']} total  (key: {key_desc})")
            show_sample_duplicates(conn, table, config["pk"], config["key_cols"])
        else:
            print(f"  {table}: clean ({stats['total']} rows)")

    print()

    if not tables_with_dupes:
        print("No duplicates found.")
        conn.close()
        return

    total_dupes = sum(v["duplicates"] for v in tables_with_dupes.values())
    print(f"Total duplicates to remove: {total_dupes}")
    print()

    if not args.apply:
        print("Run with --apply to remove duplicates.")
        conn.close()
        return

    # Backup
    if not args.no_backup:
        backup_dir = db_path.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"{db_path.stem}_pre_dedup_{timestamp}.db"
        print(f"Creating backup: {backup_path}")
        shutil.copy2(str(db_path), str(backup_path))
        print("Backup created.")
        print()

    # Remove duplicates
    print("Removing duplicates...")
    for table, info in sorted(tables_with_dupes.items()):
        deleted = remove_duplicates(conn, table, info["pk"], info["key_cols"])
        print(f"  {table}: deleted {deleted} rows ({info['total']} -> {info['total'] - deleted})")

    conn.commit()
    print()

    # VACUUM to reclaim space
    print("Running VACUUM to reclaim space...")
    conn.execute("VACUUM")

    new_size = db_path.stat().st_size / 1024 / 1024
    print(f"Done. Database size: {new_size:.1f} MB")

    conn.close()
    print()
    print("Deduplication complete.")


if __name__ == "__main__":
    main()
