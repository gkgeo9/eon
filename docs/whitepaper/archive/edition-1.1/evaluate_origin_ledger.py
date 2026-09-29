"""Test the 2025 origin readings against what happened next.

Follows origin-ledger-config.yaml, written before this test was run. Reads the
origin project read-only and the local price snapshots; no network or model
calls. Writes only to docs/whitepaper/evaluation/origin-ledger/. From eon root:

  python docs/whitepaper/evaluate_origin_ledger.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "evaluation" / "origin-ledger"
CONFIG_PATH = HERE / "origin-ledger-config.yaml"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dig(data: dict[str, Any], dotted: str) -> Any:
    for key in dotted.split("."):
        data = data.get(key, {}) if isinstance(data, dict) else {}
    return data


def reading_date(path: Path, name: str) -> date:
    """Alpha and direction files carry a timestamp; compounder files use mtime."""
    if name == "compounder":
        return datetime.fromtimestamp(path.stat().st_mtime).date()
    stamp = path.stem.split("_")[-2]
    return datetime.strptime(stamp, "%Y%m%d").date()


def load_scores(config: dict[str, Any]) -> pd.DataFrame:
    root = Path(config["origin_root"])
    rows = []
    for name, spec in config["scores"].items():
        for path in sorted(root.glob(spec["source"])):
            try:
                data = json.loads(path.read_text())
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            value = dig(data, spec["field"])
            if name == "direction":
                value = {"BUY_CALLS": 1, "BUY_PUTS": -1}.get(str(value))
            if not isinstance(value, int | float) or isinstance(value, bool):
                continue
            rows.append(
                {
                    "score": name,
                    "ticker": path.name.split("_")[0],
                    "value": float(value),
                    "read_on": reading_date(path, name).isoformat(),
                    "horizon": spec.get("horizon_trading_days", config["horizon_trading_days"]),
                }
            )
    frame = pd.DataFrame(rows)
    return frame.drop_duplicates(["score", "ticker"], keep="first")


def load_prices(config: dict[str, Any]) -> pd.DataFrame:
    frames = [pd.read_parquet(ROOT / config[k]) for k in ("price_source", "extra_price_source")]
    closes = pd.concat(frames, axis=1)
    closes = closes.loc[:, ~closes.columns.duplicated()]
    closes.index = pd.to_datetime(closes.index).tz_localize(None)
    return closes.loc[: pd.Timestamp(config["price_end"])]


def excess_returns(scores: pd.DataFrame, closes: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    spy = closes[config["benchmark"]].dropna()
    out = []
    for row in scores.itertuples():
        if row.ticker not in closes:
            continue
        series = closes[row.ticker].dropna()
        after = series.index > pd.Timestamp(row.read_on)
        if not after.any():
            continue
        entry = int(np.argmax(after))
        exit_ = entry + row.horizon
        if exit_ >= len(series):
            continue
        start, stop = series.index[entry], series.index[exit_]
        stock = series.iloc[exit_] / series.iloc[entry] - 1
        bench = spy.asof(stop) / spy.asof(start) - 1
        out.append({**row._asdict(), "entry": start.date().isoformat(), "exit": stop.date().isoformat(), "excess": float(stock - bench)})
    return pd.DataFrame(out).drop(columns=["Index"])


def statistics(values: np.ndarray, excess_ranks: np.ndarray, kind: str) -> dict[str, float]:
    if kind == "direction":
        return {"spread": float(excess_ranks[values > 0].mean() - excess_ranks[values < 0].mean())}
    score_ranks = pd.Series(values).rank().to_numpy()
    rho = float(np.corrcoef(score_ranks, excess_ranks)[0, 1])
    top, bottom = values >= np.quantile(values, 0.8), values <= np.quantile(values, 0.2)
    return {"spearman": rho, "quintile_rank_spread": float(excess_ranks[top].mean() - excess_ranks[bottom].mean())}


def evaluate(frame: pd.DataFrame, kind: str, config: dict[str, Any], rng: np.random.Generator) -> dict[str, Any]:
    sizes = frame["industry"].map(frame["industry"].value_counts())
    frame = frame[sizes >= config["min_block_size"]].reset_index(drop=True)
    values = frame["value"].to_numpy()
    ranks = frame["excess"].rank(pct=True).to_numpy()
    observed = statistics(values, ranks, kind)
    block = pd.factorize(frame["industry"])[0]
    base = np.argsort(block, kind="stable")
    null: dict[str, list[float]] = {k: [] for k in observed}
    for _ in range(config["permutations"]):
        shuffled = np.argsort(block + rng.random(len(block)), kind="stable")
        permuted = np.empty_like(values)
        permuted[base] = values[shuffled]
        for k, v in statistics(permuted, ranks, kind).items():
            null[k].append(v)
    result: dict[str, Any] = {"n": int(len(frame)), "n_blocks": int(block.max() + 1)}
    for k, v in observed.items():
        arr = np.array(null[k])
        result[k] = {
            "observed": v,
            "null_mean": float(arr.mean()),
            "null_sd": float(arr.std()),
            "p_two_sided": (1 + int(np.sum(np.abs(arr - arr.mean()) >= abs(v - arr.mean())))) / (1 + len(arr)),
        }
    if kind == "direction":
        calls, puts = frame[frame["value"] > 0]["excess"], frame[frame["value"] < 0]["excess"]
        result.update(
            n_calls=int(len(calls)), n_puts=int(len(puts)),
            calls_mean=float(calls.mean()), puts_mean=float(puts.mean()),
            calls_median=float(calls.median()), puts_median=float(puts.median()),
            share_calls_beat_spy=float((calls > 0).mean()), share_puts_lag_spy=float((puts < 0).mean()),
        )
    else:
        q = pd.qcut(frame["value"].rank(method="first"), 5, labels=[f"Q{i}" for i in range(1, 6)])
        result["quintiles"] = {
            str(k): {"n": int(len(g)), "mean_excess": float(g["excess"].mean()), "median_excess": float(g["excess"].median()), "score_range": [float(g["value"].min()), float(g["value"].max())]}
            for k, g in frame.groupby(q, observed=True)
        }
    return result


def main() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    run: dict[str, Any] = {
        "stage": "whitepaper-origin-ledger",
        "timestamp": datetime.now(UTC).isoformat(),
        "config": config,
        "config_sha256": sha256(CONFIG_PATH),
        "versions": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__},
        "inputs": {k: sha256(ROOT / config[k]) for k in ("price_source", "extra_price_source", "industry_source")},
    }
    (OUT / "run.json").write_text(json.dumps(run, indent=2) + "\n")
    scores = load_scores(config)
    closes = load_prices(config)
    trades = excess_returns(scores, closes, config)
    with (ROOT / config["industry_source"]).open(encoding="utf-8", errors="replace") as handle:
        industries = {r["ticker"].strip(): (r.get(config["industry_column"]) or "").strip() or "Unknown" for r in csv.DictReader(handle)}
    trades["industry"] = trades["ticker"].map(industries).fillna("Unknown")
    rng = np.random.default_rng(config["permutation_seed"])
    results: dict[str, Any] = {"counts": {}, "scores": {}}
    for kind, group in trades.groupby("score"):
        results["counts"][kind] = {
            "readings": int((scores["score"] == kind).sum()),
            "with_outcome": int(len(group)),
            "read_on": sorted(group["read_on"].unique().tolist()),
            "entry_range": [group["entry"].min(), group["entry"].max()],
            "exit_range": [group["exit"].min(), group["exit"].max()],
            "industry_unknown_share": float((group["industry"] == "Unknown").mean()),
        }
        results["scores"][kind] = evaluate(group.copy(), kind, config, rng)
    trades.to_csv(OUT / "trades.csv", index=False)
    (OUT / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    run["outputs"] = {n: sha256(OUT / n) for n in ("results.json", "trades.csv")}
    (OUT / "run.json").write_text(json.dumps(run, indent=2) + "\n")
    print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
