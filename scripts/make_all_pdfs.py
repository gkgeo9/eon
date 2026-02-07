#!/usr/bin/env python3
"""
Export Multi-Perspective Analyses from database to individual PDF reports per company.

Usage:
    python scripts/export_analyses_to_pdf.py

Output:
    Individual PDFs in data/reports/ directory, one per ticker
"""

import json
import sqlite3
import csv
from pathlib import Path
from collections import defaultdict

# Import the PDF generator (assumes it's in same directory or scripts/)
try:
    from convert_to_pdf import json_to_pdf
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from convert_to_pdf import json_to_pdf

# Batch to export
BATCH_NAME = "high_put_call_ratio"

# CSV file with company names
CSV_PATH = "./opt_sort_pc_ratio.csv"

# Paths for branding assets (adjust as needed)
LOGO_PATH = "./logo.png"
WATERMARK_PATH = "./watermark.png"


def load_company_names(csv_path):
    """Load ticker to company_name mapping from CSV."""
    ticker_to_name = {}
    
    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"Warning: CSV file not found at {csv_path}")
        return ticker_to_name
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row.get('ticker', '').strip()
                company_name = row.get('company_name', '').strip()
                if ticker and company_name:
                    ticker_to_name[ticker] = company_name
        
        print(f"Loaded {len(ticker_to_name)} company names from CSV\n")
    except Exception as e:
        print(f"Warning: Could not read CSV file: {e}\n")
    
    return ticker_to_name


def export_analyses_to_pdfs():
    """Extract all multi-perspective analyses from a batch and generate PDFs."""
    # Paths
    project_root = Path(__file__).parent.parent
    db_path = project_root / "data" / "eon.db"
    output_dir = project_root / "data" / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load company names from CSV
    ticker_to_company = load_company_names(CSV_PATH)

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Find the batch
    cursor.execute(
        "SELECT batch_id, name, total_tickers, completed_tickers, status FROM batch_jobs WHERE name = ?",
        (BATCH_NAME,)
    )
    batch_row = cursor.fetchone()

    if not batch_row:
        print(f"Batch '{BATCH_NAME}' not found in database.")
        conn.close()
        return

    batch_id, name, total, completed, status = batch_row
    print(f"Found batch: {name}")
    print(f"  Status: {status}")
    print(f"  Progress: {completed}/{total} tickers completed\n")

    # Query all SimplifiedAnalysis results for this batch
    cursor.execute("""
        SELECT ar.ticker, ar.fiscal_year, ar.filing_type, ar.result_json, ar.created_at
        FROM analysis_results ar
        JOIN batch_items bi ON ar.run_id = bi.run_id
        WHERE bi.batch_id = ?
          AND ar.result_type = 'SimplifiedAnalysis'
        ORDER BY ar.ticker, ar.fiscal_year DESC
    """, (batch_id,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No completed analyses found in this batch yet.")
        return

    # Group analyses by ticker
    ticker_data = defaultdict(dict)
    
    for ticker, fiscal_year, filing_type, result_json, created_at in rows:
        try:
            data = json.loads(result_json)
            ticker_data[ticker][str(fiscal_year)] = data
        except json.JSONDecodeError:
            print(f"  Warning: Could not parse JSON for {ticker} {fiscal_year}")
            continue

    # Generate PDF for each ticker
    print(f"Generating PDFs for {len(ticker_data)} companies...\n")
    
    for ticker, years_data in ticker_data.items():
        pdf_filename = output_dir / f"{ticker}_analysis.pdf"
        
        try:
            # Company name is the ticker (or you could look it up from another source)
            company_name = "Erebus Observatory Network"
            stock_name = f"{ticker_to_company[ticker]} - {ticker}"
            
            # Generate PDF
            json_to_pdf(
                json_input=years_data,
                pdf_filename=str(pdf_filename),
                company_name=company_name,
                stock_name=stock_name,
                logo_path=LOGO_PATH if Path(LOGO_PATH).exists() else None,
                watermark_path=WATERMARK_PATH if Path(WATERMARK_PATH).exists() else None,
            )
            
            year_count = len(years_data)
            print(f"✓ Generated PDF for {ticker} ({year_count} year{'s' if year_count > 1 else ''})")
            
        except Exception as e:
            print(f"✗ Failed to generate PDF for {ticker}: {e}")

    print(f"\nPDFs saved to: {output_dir}")


if __name__ == "__main__":
    export_analyses_to_pdfs()