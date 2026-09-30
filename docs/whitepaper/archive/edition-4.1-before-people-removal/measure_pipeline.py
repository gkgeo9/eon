"""Measure what one filing costs on its way through EON, for Part I of the paper.

Reads cached PDFs and raw EDGAR HTML from data/ (read-only), a seeded sample of
each. Writes evaluation/pipeline-measurements.json. Needs PyPDF2, an EON
dependency, so run with EON's environment from the eon root:

  .venv/bin/python docs/whitepaper/measure_pipeline.py
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import random
import re
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from PyPDF2 import PdfReader

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "evaluation" / "pipeline-measurements.json"
SEED = 20260930
SAMPLE = 40


def pct(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(q * len(ordered)))]


def main() -> None:
    pdfs = sorted(glob.glob(str(ROOT / "data/pdfs/*/*10-K*.pdf")))
    sizes = [os.path.getsize(p) for p in pdfs]
    rng = random.Random(SEED)
    sample = rng.sample(pdfs, SAMPLE)
    pages, chars, seconds = [], [], []
    for path in sample:
        start = time.time()
        reader = PdfReader(path)
        text = "".join((page.extract_text() or "") for page in reader.pages)
        seconds.append(time.time() - start)
        pages.append(len(reader.pages))
        chars.append(len(text))

    html = [p for p in glob.glob(str(ROOT / "data/raw/**/primary-document.html"), recursive=True) if "/10-K/" in p]
    html_rows = []
    for path in sorted(html):
        raw = Path(path).read_text(encoding="utf-8", errors="ignore")
        hidden = sum(len(m) for m in re.findall(r"<ix:header>.*?</ix:header>", raw, flags=re.S | re.I))
        visible = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
        visible = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", visible))
        html_rows.append(
            {
                "file": str(Path(path).relative_to(ROOT)),
                "html_chars": len(raw),
                "visible_chars": len(visible),
                "markup_ratio": round(len(raw) / max(1, len(visible)), 2),
                "inline_xbrl_tags": len(re.findall(r"<ix:[a-z]+", raw, flags=re.I)),
                "hidden_xbrl_header_chars": hidden,
            }
        )
    result = {
        "stage": "whitepaper-pipeline-measurements",
        "timestamp": datetime.now(UTC).isoformat(),
        "python": sys.version.split()[0],
        "seed": SEED,
        "pdf_10k_files": len(pdfs),
        "pdf_total_gb": round(sum(sizes) / 1e9, 1),
        "pdf_mb_median": round(statistics.median(sizes) / 1e6, 2),
        "pdf_mb_p90": round(pct(sizes, 0.9) / 1e6, 2),
        "sample": SAMPLE,
        "pages_median": statistics.median(pages),
        "pages_max": max(pages),
        "chars_median": int(statistics.median(chars)),
        "chars_p90": int(pct(chars, 0.9)),
        "chars_max": max(chars),
        "tokens_median_est": int(statistics.median(chars) / 4),
        "tokens_p90_est": int(pct(chars, 0.9) / 4),
        "tokens_max_est": int(max(chars) / 4),
        "extract_seconds_median": round(statistics.median(seconds), 2),
        "html_10k_samples": html_rows,
        "sample_files_sha256": hashlib.sha256("\n".join(sample).encode()).hexdigest(),
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "html_10k_samples"}, indent=1))
    for row in html_rows:
        print(row)


if __name__ == "__main__":
    main()
