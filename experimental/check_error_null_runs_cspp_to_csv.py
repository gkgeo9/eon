#!/usr/bin/env python3
"""
Scan a batch for broken runs and export them to a re-queue CSV.

Two categories are captured:
  FAILED          - batch_items.status = 'failed' (download errors, bad tickers, etc.)
  GHOST-COMPLETED - batch_items.status = 'completed' but zero rows in analysis_results
                    (worker crashed mid-analysis and the run was incorrectly closed out)

Output: data/batch_errors_<id8>.csv  with columns: ticker, company_name, note

Just edit BATCH_ID or BATCH_NAME below and run:
    python experimental/check_error_null_runs_cspp_to_csv.py
"""

import csv
import sqlite3
import sys
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────
# Set one of these. BATCH_ID takes priority if both are set.
# Leave BATCH_ID as None to match by name instead.
# Leave both as None to use the most recently started batch.

BATCH_ID   = "7167deb5-a81b-48cd-8f06-7d0d56c3c1b4"
BATCH_NAME = None   # e.g. "russell 1000" — partial match, most recent wins

# ── Paths (no need to change) ──────────────────────────────────────────────────
ROOT       = Path(__file__).resolve().parent.parent
DB_PATH    = ROOT / "data" / "eon.db"
OUTPUT_DIR = ROOT / "data"


# ── DB helpers ─────────────────────────────────────────────────────────────────

def connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        sys.exit(f"[ERROR] Database not found: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def resolve_batch_id(conn: sqlite3.Connection) -> str:
    cur = conn.cursor()

    if BATCH_ID:
        cur.execute("SELECT batch_id FROM batch_jobs WHERE batch_id = ?", (BATCH_ID,))
        row = cur.fetchone()
        if not row:
            sys.exit(f"[ERROR] BATCH_ID not found in DB: {BATCH_ID}")
        return row["batch_id"]

    if BATCH_NAME:
        cur.execute(
            "SELECT batch_id, name FROM batch_jobs WHERE name LIKE ?"
            " ORDER BY COALESCE(started_at, created_at) DESC LIMIT 1",
            (f"%{BATCH_NAME}%",),
        )
        row = cur.fetchone()
        if not row:
            sys.exit(f"[ERROR] No batch found matching BATCH_NAME: '{BATCH_NAME}'")
        print(f"[INFO] Matched batch: {row['batch_id']}  ({row['name']})")
        return row["batch_id"]

    # Fallback: most recently started batch
    cur.execute(
        "SELECT batch_id, name FROM batch_jobs"
        " ORDER BY COALESCE(started_at, created_at) DESC LIMIT 1"
    )
    row = cur.fetchone()
    if not row:
        sys.exit("[ERROR] No batches found in the database.")
    print(f"[INFO] Using most recent batch: {row['batch_id']}  ({row['name']})")
    return row["batch_id"]


# ── Queries ────────────────────────────────────────────────────────────────────

def get_failed(conn: sqlite3.Connection, batch_id: str) -> list[dict]:
    cur = conn.cursor()
    cur.execute("""
        SELECT ticker, company_name, error_message
        FROM batch_items
        WHERE batch_id = ? AND status = 'failed'
        ORDER BY ticker
    """, (batch_id,))
    rows = []
    for r in cur.fetchall():
        err = (r["error_message"] or "unknown error").strip().rstrip(".")
        note = f"FAILED - {err}"
        if "." in r["ticker"]:
            note += " (dot in ticker)"
        rows.append({
            "ticker":       r["ticker"],
            "company_name": r["company_name"] or "",
            "note":         note,
        })
    return rows


def get_ghost_completed(conn: sqlite3.Connection, batch_id: str) -> list[dict]:
    """Completed in batch_items but no rows written to analysis_results."""
    cur = conn.cursor()
    cur.execute("""
        SELECT bi.ticker, bi.company_name, ar.progress_message
        FROM batch_items bi
        LEFT JOIN analysis_runs ar ON bi.run_id = ar.run_id
        WHERE bi.batch_id = ?
          AND bi.status = 'completed'
          AND NOT EXISTS (
              SELECT 1 FROM analysis_results res WHERE res.run_id = bi.run_id
          )
        ORDER BY bi.ticker
    """, (batch_id,))
    rows = []
    for r in cur.fetchall():
        year_hint = ""
        progress = r["progress_message"] or ""
        for part in progress.split():
            if part.isdigit() and len(part) == 4:
                year_hint = f" year {part}"
                break
        note = (
            f"GHOST-COMPLETED - Marked done but no results saved"
            f" (worker crashed mid-analysis{year_hint})"
        )
        rows.append({
            "ticker":       r["ticker"],
            "company_name": r["company_name"] or "",
            "note":         note,
        })
    return rows


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    conn = connect()
    batch_id = resolve_batch_id(conn)

    cur = conn.cursor()
    cur.execute("SELECT * FROM batch_jobs WHERE batch_id = ?", (batch_id,))
    job = cur.fetchone()

    print(f"\nBatch : {job['name']}")
    print(f"ID    : {batch_id}")
    print(
        f"Status: {job['status']}  |  "
        f"{job['completed_tickers']}/{job['total_tickers']} completed, "
        f"{job['failed_tickers']} failed"
    )

    failed = get_failed(conn, batch_id)
    ghosts = get_ghost_completed(conn, batch_id)
    conn.close()

    all_rows = failed + ghosts

    short_id    = batch_id.replace("-", "")[:8]
    output_path = OUTPUT_DIR / f"batch_errors_{short_id}.csv"

    if not all_rows:
        print("\n[OK] No failures or ghost-completed runs found.")
        return

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ticker", "company_name", "note"])
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n{'='*60}")
    print(f"  FAILED (no filing found):           {len(failed)}")
    for r in failed:
        print(f"    [{r['ticker']}] {r['company_name']}")
    print(f"\n  GHOST-COMPLETED (no results saved): {len(ghosts)}")
    for r in ghosts:
        print(f"    [{r['ticker']}] {r['company_name']}")
    print(f"\n  TOTAL: {len(all_rows)}")
    print(f"  Output: {output_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
