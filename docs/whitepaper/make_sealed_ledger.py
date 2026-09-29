"""Freeze EON's current verdicts into the paper's own forecast.

Follows sealed-ledger-config.yaml. Reads Edition 2's per-reading records and the
frozen price snapshot; no network or model calls. Writes
evaluation/sealed-ledger/ledger.csv and ledger.json, whose SHA-256 the paper
prints so that the ledger cannot be changed unnoticed. Run once, from the eon root:

  python docs/whitepaper/make_sealed_ledger.py
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import yaml

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "sealed-ledger-config.yaml"
OUT = HERE / "evaluation" / "sealed-ledger"


def main() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "ledger.csv").exists():
        raise SystemExit("The ledger is already frozen. It must not be regenerated.")
    trades = pd.read_csv(HERE / config["trades"])
    closes = pd.read_parquet(HERE / config["prices"])
    closes.index = pd.to_datetime(closes.index)
    lo, hi = config["live_price_window"]
    window = closes.loc[lo:hi]
    live = {c for c in window.columns if window[c].notna().any()}

    post = trades[pd.to_datetime(trades["filing_date"]) > config["knowledge_cutoff"]].copy()
    if config["exclude_read_before_filed"]:
        post = post[pd.to_datetime(post["read_at"]) >= pd.to_datetime(post["filing_date"])]
    post = post.sort_values(["filing_date", "read_at"]).groupby("ticker").tail(1)
    post = post[post["ticker"].isin(live)]

    freeze = pd.Timestamp(config["freeze_date"])
    at_freeze = closes.loc[:freeze].ffill().iloc[-1]
    ledger = post[["ticker", "verdict", "conviction", "fiscal_year", "filing_date", "read_at"]].copy()
    ledger["close_at_freeze"] = ledger["ticker"].map(at_freeze).round(4)
    ledger = ledger.sort_values(["verdict", "ticker"]).reset_index(drop=True)
    ledger.to_csv(OUT / "ledger.csv", index=False)
    digest = hashlib.sha256((OUT / "ledger.csv").read_bytes()).hexdigest()

    strong = ledger[ledger["verdict"].isin(config["publish_in_paper"])]
    record = {
        "stage": "whitepaper-sealed-ledger",
        "frozen_at": datetime.now(UTC).isoformat(),
        "config": config,
        "config_sha256": hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest(),
        "inputs": {
            config["trades"]: hashlib.sha256((HERE / config["trades"]).read_bytes()).hexdigest(),
            config["prices"]: hashlib.sha256((HERE / config["prices"]).read_bytes()).hexdigest(),
        },
        "ledger_sha256": digest,
        "companies": int(len(ledger)),
        "verdicts": ledger["verdict"].value_counts().to_dict(),
        "spy_close_at_freeze": round(float(at_freeze["SPY"]), 4),
        "filing_quarters": ledger["filing_date"].str[:7].value_counts().sort_index().to_dict(),
        "published_calls": strong[["ticker", "verdict", "filing_date"]].to_dict("records"),
    }
    (OUT / "ledger.json").write_text(json.dumps(record, indent=2, default=str) + "\n")
    print(json.dumps({k: record[k] for k in ("companies", "verdicts", "ledger_sha256")}, indent=2))
    print(len(record["published_calls"]), "published calls")


if __name__ == "__main__":
    main()
