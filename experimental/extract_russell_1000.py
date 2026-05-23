"""
Extract Russell 1000 ticker symbols and company names from Wikipedia.

Wikipedia blocks automated fetches, so the easiest approach is:
  1. Open the page in your browser:
     https://en.wikipedia.org/wiki/Russell_1000_Index
  2. Save it: File > Save Page As > "Webpage, HTML Only" -> e.g. page.html
  3. Run this script pointing at that file:
       python extract_russell1000.py --file page.html
       python extract_russell1000.py --file page.html -o russell1000.csv

Alternatively, try the live fetch (may be blocked by Wikipedia):
       python extract_russell1000.py
       python extract_russell1000.py -o russell1000.csv
"""

import argparse
import csv
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://en.wikipedia.org/wiki/Russell_1000_Index"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def get_html(local_file: str | None) -> str:
    if local_file:
        return Path(local_file).read_text(encoding="utf-8")
    print("Fetching from Wikipedia...", file=sys.stderr)
    r = requests.get(URL, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.text


def parse_components(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    # The Components table has id="constituents" on Wikipedia
    table = soup.find("table", {"id": "constituents"})

    if table is None:
        # Fallback: find the Components heading, walk to the next table
        anchor = soup.find(id="Components")
        if anchor is None:
            for tag in soup.find_all(["h2", "h3"]):
                if "Components" in tag.get_text():
                    anchor = tag
                    break
        if anchor is None:
            raise RuntimeError("Could not locate the Components section.")
        for sib in anchor.parent.find_next_siblings():
            table = sib.find("table")
            if table:
                break

    if table is None:
        raise RuntimeError("Could not find the components table.")

    rows = table.find_all("tr")
    if not rows:
        raise RuntimeError("Components table is empty.")

    # Detect columns from header row
    header_cells = [c.get_text(strip=True).lower() for c in rows[0].find_all(["th", "td"])]
    ticker_col = next(
        (i for i, h in enumerate(header_cells) if "symbol" in h or "ticker" in h), 1
    )
    name_col = next(
        (i for i, h in enumerate(header_cells) if "company" in h or "name" in h), 0
    )

    results = []
    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) <= max(ticker_col, name_col):
            continue
        ticker  = cells[ticker_col].get_text(strip=True)
        company = cells[name_col].get_text(strip=True)
        if ticker and company:
            results.append({"ticker": ticker, "company": company})

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Extract Russell 1000 tickers and company names from Wikipedia.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("-o", "--output", metavar="FILE", help="Save results to a CSV file")
    parser.add_argument(
        "--file", metavar="HTML_FILE",
        help="Use a locally saved copy of the Wikipedia page (recommended)"
    )
    args = parser.parse_args()

    if args.file:
        print(f"Reading local file: {args.file}", file=sys.stderr)
    
    try:
        html = get_html(args.file)
    except Exception as e:
        print(f"\nERROR fetching page: {e}", file=sys.stderr)
        print(
            "\nWikipedia is blocking automated requests.\n"
            "Save the page manually and re-run with --file:\n"
            "  1. Open https://en.wikipedia.org/wiki/Russell_1000_Index\n"
            "  2. File > Save Page As > 'Webpage, HTML Only' -> page.html\n"
            "  3. python extract_russell1000.py --file page.html -o russell1000.csv",
            file=sys.stderr,
        )
        sys.exit(1)

    components = parse_components(html)
    print(f"Found {len(components)} components.\n", file=sys.stderr)

    # Print table to stdout
    print(f"{'Ticker':<12} Company")
    print("-" * 65)
    for item in components:
        print(f"{item['ticker']:<12} {item['company']}")

    # Optionally save to CSV
    if args.output:
        with open(args.output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["ticker", "company"])
            writer.writeheader()
            writer.writerows(components)
        print(f"\nSaved {len(components)} rows to '{args.output}'", file=sys.stderr)


if __name__ == "__main__":
    main()