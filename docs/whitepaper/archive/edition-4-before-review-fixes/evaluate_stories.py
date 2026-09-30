"""Descriptive views behind Edition 3's narrative figures.

Follows stories-config.yaml. Reads only Edition 2's evaluation outputs; no
database, network or model access. Writes evaluation/stories.json. Run from
the eon root:

  python docs/whitepaper/evaluate_stories.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONFIG_PATH = HERE / "stories-config.yaml"
OUT = HERE / "evaluation" / "stories.json"
LONG, SHORT = {"BUY", "STRONG BUY"}, {"SELL", "STRONG SELL"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def samples(trades: pd.DataFrame, config: dict[str, Any]) -> dict[str, pd.DataFrame]:
    column, exit_ = f"excess_{config['horizon']}", f"exit_{config['horizon']}"
    cutoff = pd.Timestamp(config["knowledge_cutoff"])
    data = trades.dropna(subset=[column])
    return {
        "historical": data[pd.to_datetime(data[exit_]) < cutoff].copy(),
        "post_cutoff": data[pd.to_datetime(data["filing_date"]) > cutoff].copy(),
    }


def ladder(sample: pd.DataFrame, config: dict[str, Any], rng: np.random.Generator) -> dict[str, Any]:
    column = f"excess_{config['horizon']}"
    sample["rank"] = sample.groupby("fiscal_year")[column].rank(pct=True)
    levels = config["verdict_levels"]
    rows = {}
    for verdict in levels:
        group = sample[sample["verdict"] == verdict]
        rows[verdict] = {
            "n": int(len(group)),
            "mean_rank": float(group["rank"].mean()),
            "rank_se": float(group["rank"].std(ddof=1) / np.sqrt(len(group))) if len(group) > 1 else None,
            "median_excess": float(group[column].median()),
        }
    level = sample["verdict"].map(levels).to_numpy(dtype=float)
    ranks = sample["rank"].to_numpy()

    def rho(x: np.ndarray) -> float:
        return float(np.corrcoef(pd.Series(x).rank().to_numpy(), ranks)[0, 1])

    observed = rho(level)
    block = pd.factorize(sample["fiscal_year"])[0]
    base = np.argsort(block, kind="stable")
    null = np.empty(config["permutations"])
    for i in range(len(null)):
        shuffled = np.argsort(block + rng.random(len(block)), kind="stable")
        permuted = np.empty_like(level)
        permuted[base] = level[shuffled]
        null[i] = rho(permuted)
    extreme = int(np.sum(np.abs(null - null.mean()) >= abs(observed - null.mean())))
    return {
        "verdicts": rows,
        "spearman_level_vs_rank": observed,
        "null_mean": float(null.mean()),
        "p_two_sided": (1 + extreme) / (1 + len(null)),
        "n": int(len(sample)),
    }


def grid(trades: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    spec, column = config["grid"], f"excess_{config['horizon']}"
    years = spec["fiscal_years"]
    data = trades[trades["fiscal_year"].isin(years)].dropna(subset=[column])
    eligible = []
    for ticker, group in data.groupby("ticker"):
        if group["fiscal_year"].nunique() == len(years) and group["verdict"].isin(LONG).any() and group["verdict"].isin(SHORT).any():
            eligible.append(ticker)
    eligible.sort()
    rng = np.random.default_rng(spec["seed"])
    drawn = sorted(rng.choice(eligible, size=spec["draw"], replace=False).tolist())
    with (ROOT / spec["names_source"]).open(encoding="utf-8", errors="replace") as handle:
        names = {r["ticker"].strip(): (r.get("company_name") or "").strip() for r in csv.DictReader(handle)}
    rows = []
    for ticker in drawn:
        group = data[data["ticker"] == ticker].set_index("fiscal_year")
        rows.append(
            {
                "ticker": ticker,
                "name": names.get(ticker, ""),
                "cells": {
                    str(year): {
                        "verdict": group.loc[year, "verdict"],
                        "excess": float(group.loc[year, column]),
                        "filed": group.loc[year, "filing_date"],
                    }
                    for year in years
                },
            }
        )
    cells = [c for r in rows for c in r["cells"].values()]
    agree = [
        (c["verdict"] in LONG and c["excess"] > 0) or (c["verdict"] in SHORT and c["excess"] < 0)
        for c in cells
        if c["verdict"] in LONG | SHORT
    ]
    return {
        "eligible": len(eligible),
        "drawn": rows,
        "directional_cells": len(agree),
        "directional_agree": int(sum(agree)),
    }


def named(trades: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    keep = ["fiscal_year", "verdict", "conviction", "filing_date", "read_at", "entry_date", "excess_6M", "excess_1Y"]
    return {
        t: trades[trades["ticker"] == t][keep].sort_values("fiscal_year").to_dict("records")
        for t in config["named_cases"]
    }


def options_ledger(config: dict[str, Any]) -> dict[str, Any]:
    """EON's February 2026 options scan, graded on outcomes that followed it."""
    import sqlite3

    spec = config["options_ledger"]
    con = sqlite3.connect(f"file:{ROOT / 'data/eon.db'}?mode=ro&immutable=1", uri=True)
    rows = con.execute(
        "SELECT ticker, created_at, result_json FROM analysis_results WHERE result_type = ? ORDER BY id",
        (spec["result_type"],),
    ).fetchall()
    con.close()
    closes = pd.read_parquet(HERE / "evaluation/prices/closes.parquet")
    closes.index = pd.to_datetime(closes.index)
    closes = closes.loc[:"2026-09-28"]
    spy = closes["SPY"].dropna()
    records, seen = [], set()
    for ticker, created, payload in rows:
        if ticker in seen or ticker not in closes:
            continue
        seen.add(ticker)
        data = json.loads(payload)
        series = closes[ticker].dropna()
        after = series.index > pd.Timestamp(created)
        if not after.any():
            continue
        entry = int(np.argmax(after))
        exit_ = entry + spec["horizon_trading_days"]
        if exit_ >= len(series):
            continue
        start, stop = series.index[entry], series.index[exit_]
        excess = float(series.iloc[exit_] / series.iloc[entry] - spy.asof(stop) / spy.asof(start))
        try:
            score = float(data.get("composite_asymmetry_score"))
        except (TypeError, ValueError):
            score = np.nan
        records.append({"ticker": ticker, "bias": str(data.get("directional_bias")), "score": score, "excess": excess})
    frame = pd.DataFrame(records)
    frame["rank"] = frame["excess"].rank(pct=True)
    frame["abs_rank"] = frame["excess"].abs().rank(pct=True)
    rng = np.random.default_rng(spec["seed"])

    def perm(values: np.ndarray, labels: np.ndarray, a: str, b: str) -> dict[str, float]:
        obs = values[labels == a].mean() - values[labels == b].mean()
        null = np.array([
            (lambda lab: values[lab == a].mean() - values[lab == b].mean())(rng.permutation(labels))
            for _ in range(spec["permutations"])
        ])
        extreme = int(np.sum(np.abs(null - null.mean()) >= abs(obs - null.mean())))
        return {"observed": float(obs), "p_two_sided": (1 + extreme) / (1 + len(null))}

    labels = frame["bias"].to_numpy()
    direction = perm(frame["rank"].to_numpy(), labels, "Call Bias (Upside Tail)", "Put Bias (Downside Tail)")
    magnitude = perm(frame["abs_rank"].to_numpy(), labels, "Straddle Bias (Binary)", "No Edge (Skip)")
    scored = frame.dropna(subset=["score"])
    rho = float(np.corrcoef(scored["score"].rank(), scored["abs_rank"])[0, 1])
    null_rho = np.array([float(np.corrcoef(rng.permutation(scored["score"].rank().to_numpy()), scored["abs_rank"])[0, 1]) for _ in range(spec["permutations"])])
    by_bias = {
        b: {
            "n": int(len(g)), "mean_rank": float(g["rank"].mean()), "mean_abs_rank": float(g["abs_rank"].mean()),
            "median_excess": float(g["excess"].median()), "share_beat_spy": float((g["excess"] > 0).mean()),
        }
        for b, g in frame.groupby("bias")
    }
    return {
        "n": int(len(frame)),
        "by_bias": by_bias,
        "call_minus_put_rank": direction,
        "straddle_minus_no_edge_abs_rank": magnitude,
        "score_vs_abs_move_spearman": {"observed": rho, "p_two_sided": (1 + int(np.sum(np.abs(null_rho) >= abs(rho)))) / (1 + len(null_rho))},
        "share_all_beat_spy": float((frame["excess"] > 0).mean()),
    }


def main() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text())
    trades_path = HERE / config["trades"]
    trades = pd.read_csv(trades_path)
    rng = np.random.default_rng(config["permutation_seed"])
    result: dict[str, Any] = {
        "stage": "whitepaper-stories",
        "timestamp": datetime.now(UTC).isoformat(),
        "config": config,
        "inputs": {config["trades"]: sha256(trades_path), CONFIG_PATH.name: sha256(CONFIG_PATH)},
        "versions": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__},
        "ladder": {k: ladder(v, config, rng) for k, v in samples(trades, config).items()},
        "grid": grid(trades, config),
        "named": named(trades, config),
        "options_ledger": options_ledger(config),
    }
    OUT.write_text(json.dumps(result, indent=2, default=str) + "\n")
    for k, v in result["ladder"].items():
        print(k, "rho", round(v["spearman_level_vs_rank"], 3), "p", v["p_two_sided"], {x: round(y["mean_rank"], 3) for x, y in v["verdicts"].items()})
    g = result["grid"]
    print("grid eligible", g["eligible"], "directional", g["directional_agree"], "/", g["directional_cells"])
    print([r["ticker"] for r in g["drawn"]])
    print(json.dumps(result["options_ledger"], indent=1))


if __name__ == "__main__":
    main()
