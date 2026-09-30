"""Fetch adjusted daily closes for every evaluated ticker, into the whitepaper only.

The project's own data/price_cache is never modified. Output is one wide parquet
file, evaluation/prices/closes.parquet, plus a run.json with its hash and the
fetch date. Needs network access and yfinance (an EON dependency):

  .venv/bin/python docs/whitepaper/refresh_prices.py
  .venv/bin/python docs/whitepaper/refresh_prices.py --origin   # 2025 ledger tickers

With --origin, only tickers from the 2025 origin project that closes.parquet
lacks are fetched, into evaluation/prices/origin-closes.parquet.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import yaml
import yfinance as yf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "evaluation" / "prices"
START = "2019-01-01"
BATCH = 100


def origin_tickers() -> list[str]:
    """Tickers of the 2025 origin readings, from file names only (read-only)."""
    config = yaml.safe_load((HERE / "origin-ledger-config.yaml").read_text())
    root = Path(config["origin_root"])
    names = set()
    for spec in config["scores"].values():
        for path in root.glob(spec["source"]):
            names.add(path.name.split("_")[0])
    have = set(pd.read_parquet(OUT / "closes.parquet").columns)
    return sorted(names - have)


def fetch_origin() -> None:
    tickers = origin_tickers() + ["SPY"]
    frames = []
    for i in range(0, len(tickers), BATCH):
        data = yf.download(tickers[i : i + BATCH], start=START, auto_adjust=True, progress=False)
        frames.append(data["Close"] if isinstance(data.columns, pd.MultiIndex) else data[["Close"]])
    closes = pd.concat(frames, axis=1)
    closes = closes.loc[:, ~closes.columns.duplicated()].dropna(axis=1, how="all")
    closes.columns = [c.replace("-", ".") if c != "SPY" else c for c in closes.columns]
    closes.index = pd.to_datetime(closes.index).tz_localize(None)
    path = OUT / "origin-closes.parquet"
    closes.drop(columns=["SPY"], errors="ignore").sort_index(axis=1).to_parquet(path)
    record = {
        "stage": "whitepaper-origin-price-refresh",
        "timestamp": datetime.now(UTC).isoformat(),
        "requested_tickers": len(tickers) - 1,
        "returned_tickers": int(closes.shape[1]) - 1,
        "last_date": closes.index.max().date().isoformat(),
        "outputs": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()},
    }
    (OUT / "origin-run.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


def main() -> None:
    if "--origin" in sys.argv:
        fetch_origin()
        return
    config = yaml.safe_load((HERE / "evaluation-config.yaml").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    fetched = datetime.now(UTC)
    run = {
        "stage": "whitepaper-price-refresh",
        "timestamp": fetched.isoformat(),
        "source": "Yahoo Finance via yfinance, auto_adjust=True",
        "start": START,
        "versions": {"python": sys.version.split()[0], "yfinance": yf.__version__},
    }
    (OUT / "run.json").write_text(json.dumps(run, indent=2) + "\n")

    con = sqlite3.connect(f"file:{ROOT / config['database']}?mode=ro&immutable=1", uri=True)
    tickers = sorted(
        {t for (t,) in con.execute("SELECT DISTINCT ticker FROM analysis_results")}
        | {config["benchmark"]}
    )
    con.close()
    symbols = {t: t.replace(".", "-") for t in tickers}
    frames = []
    names = list(symbols.values())
    for i in range(0, len(names), BATCH):
        chunk = names[i : i + BATCH]
        data = yf.download(chunk, start=START, auto_adjust=True, progress=False, threads=True)
        closes = data["Close"] if isinstance(data.columns, pd.MultiIndex) else data[["Close"]]
        frames.append(closes)
        print(f"{min(i + BATCH, len(names))}/{len(names)}")
    closes = pd.concat(frames, axis=1)
    closes = closes.loc[:, ~closes.columns.duplicated()].dropna(axis=1, how="all")
    # Bulk downloads are throttled; retry each missing symbol once, slowly.
    retried = []
    for name in sorted(set(names) - set(closes.columns)):
        time.sleep(1.0)
        data = yf.download(name, start=START, auto_adjust=True, progress=False)
        if not data.empty:
            series = data["Close"]
            series = series.iloc[:, 0] if isinstance(series, pd.DataFrame) else series
            closes[name] = series
            retried.append(name)
    print(f"recovered on retry: {len(retried)}")
    closes.columns = [next(t for t, s in symbols.items() if s == c) for c in closes.columns]
    closes.index = pd.to_datetime(closes.index).tz_localize(None)
    path = OUT / "closes.parquet"
    closes.sort_index(axis=1).to_parquet(path)
    run.update(
        {
            "requested_tickers": len(tickers),
            "recovered_on_retry": retried,
            "returned_tickers": int(closes.shape[1]),
            "missing_tickers": sorted(set(tickers) - set(closes.columns)),
            "last_date": closes.index.max().date().isoformat(),
            "benchmark_last_date": closes[config["benchmark"]].dropna().index.max().date().isoformat(),
            "outputs": {"closes.parquet": hashlib.sha256(path.read_bytes()).hexdigest()},
        }
    )
    (OUT / "run.json").write_text(json.dumps(run, indent=2) + "\n")
    print(json.dumps({k: v for k, v in run.items() if k != "missing_tickers"}, indent=2))


if __name__ == "__main__":
    main()
