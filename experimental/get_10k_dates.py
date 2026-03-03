#!/usr/bin/env python3
"""
Get the most recent 10-K filing date for every ticker in a CSV.

Usage:
    python experimental/get_10k_dates.py
    python experimental/get_10k_dates.py --input all_companies_08022026.csv --output data/10k_dates.csv
"""

import time
import argparse
import requests
import pandas as pd
from pathlib import Path

# SEC compliance headers (required by SEC EDGAR)
HEADERS = {
    "User-Agent": "Research Thing jamievurnilla@gmail.com",
    "Accept-Encoding": "gzip, deflate",
}

# Polite rate limit: SEC asks for max 10 req/sec, we do ~5/sec to be safe
REQUEST_DELAY = 0.2


def fetch_cik_map() -> dict[str, str]:
    """Download full ticker→CIK mapping from SEC (one request for all tickers)."""
    print("Fetching ticker→CIK map from SEC...")
    resp = requests.get(
        "https://www.sec.gov/files/company_tickers.json",
        headers=HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    # Map: ticker.upper() -> zero-padded CIK string
    return {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in data.values()}


def get_latest_10k_date(cik: str, session: requests.Session) -> str | None:
    """
    Query SEC submissions endpoint for a CIK and return the most recent 10-K filing date.
    Returns date string 'YYYY-MM-DD' or None if not found.
    """
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    try:
        resp = session.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"    HTTP error for CIK {cik}: {e}")
        return None

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    filing_dates = recent.get("filingDate", [])

    # Walk from most-recent → oldest (SEC returns newest first)
    for i, form in enumerate(forms):
        if form.upper() in ("10-K", "10-K/A"):
            return filing_dates[i] if i < len(filing_dates) else None

    # If not in recent filings, check older filing pages
    files = data.get("filings", {}).get("files", [])
    for file_meta in files:
        file_name = file_meta.get("name", "")
        if not file_name:
            continue
        try:
            time.sleep(REQUEST_DELAY)
            page_url = f"https://data.sec.gov/submissions/{file_name}"
            page_resp = session.get(page_url, headers=HEADERS, timeout=10)
            page_resp.raise_for_status()
            page_data = page_resp.json()
            p_forms = page_data.get("form", [])
            p_dates = page_data.get("filingDate", [])
            for j, f in enumerate(p_forms):
                if f.upper() in ("10-K", "10-K/A"):
                    return p_dates[j] if j < len(p_dates) else None
        except Exception as e:
            print(f"    Error fetching older filings page {file_name}: {e}")
            continue

    return None


def main():
    parser = argparse.ArgumentParser(description="Fetch latest 10-K filing date for each ticker")
    parser.add_argument(
        "--input",
        default="all_companies_08022026.csv",
        help="Input CSV file with a 'ticker' column",
    )
    parser.add_argument(
        "--output",
        default="data/10k_dates.csv",
        help="Output CSV file path",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip tickers already in output file (resume interrupted run)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    # Load tickers
    df = pd.read_csv(input_path)
    tickers = df["ticker"].dropna().str.upper().str.strip().unique().tolist()
    print(f"Loaded {len(tickers)} tickers from {input_path}")

    # Resume support: skip already-done tickers
    done: dict[str, str] = {}
    if args.resume and output_path.exists():
        existing = pd.read_csv(output_path)
        done = dict(zip(existing["ticker"], existing["latest_10k_date"]))
        print(f"Resuming: {len(done)} tickers already processed")

    # Fetch CIK map once
    cik_map = fetch_cik_map()
    print(f"CIK map loaded: {len(cik_map)} entries")

    results: list[dict] = [{"ticker": t, "latest_10k_date": d} for t, d in done.items()]
    errors: list[str] = []

    session = requests.Session()
    remaining = [t for t in tickers if t not in done]
    total = len(remaining)

    print(f"\nFetching 10-K dates for {total} tickers...\n")

    for idx, ticker in enumerate(remaining, 1):
        cik = cik_map.get(ticker)
        if not cik:
            print(f"[{idx:4d}/{total}] {ticker:8s}  -> NOT FOUND in SEC CIK map")
            results.append({"ticker": ticker, "latest_10k_date": None, "note": "CIK not found"})
            errors.append(ticker)
            time.sleep(REQUEST_DELAY)
            continue

        filing_date = get_latest_10k_date(cik, session)
        status = filing_date if filing_date else "NO 10-K FOUND"
        print(f"[{idx:4d}/{total}] {ticker:8s}  -> {status}")

        results.append({
            "ticker": ticker,
            "latest_10k_date": filing_date,
            "cik": cik,
            "note": "" if filing_date else "no 10-K found",
        })

        if filing_date is None:
            errors.append(ticker)

        time.sleep(REQUEST_DELAY)

        # Save checkpoint every 50 tickers
        if idx % 50 == 0:
            pd.DataFrame(results).to_csv(output_path, index=False)
            print(f"  [checkpoint saved -> {output_path}]")

    # Final save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out_df = pd.DataFrame(results)
    out_df.to_csv(output_path, index=False)

    found = out_df["latest_10k_date"].notna().sum()
    print(f"\nDone. {found}/{len(results)} tickers have a 10-K date.")
    print(f"Results saved to: {output_path}")

    if errors:
        print(f"\nFailed/missing ({len(errors)}): {', '.join(errors[:30])}")
        if len(errors) > 30:
            print(f"  ... and {len(errors) - 30} more")


if __name__ == "__main__":
    main()
