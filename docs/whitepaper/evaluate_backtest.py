"""Re-evaluate EON's multi-perspective verdicts against forward returns.

Follows evaluation-config.yaml (version 1 was written before the first run; version
2's amendments are listed in it). Reads the analysis database read-only and the
price snapshot made by refresh_prices.py; makes no network or model calls. Writes
only to docs/whitepaper/evaluation/. Run from the eon root:

  python docs/whitepaper/evaluate_backtest.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from scipy import stats

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "evaluation"
CONFIG_PATH = HERE / "evaluation-config.yaml"

# The leading verdict, allowing the label some readings put first:
# "Overall investment recommendation: HOLD (Medium conviction)".
VERDICT = re.compile(
    r"^\W*(?:(?:OVERALL\s+)?(?:INVESTMENT\s+)?(?:FINAL\s+)?(?:RECOMMENDATION|VERDICT)\s*:\s*)?"
    r"\W*(STRONG BUY|STRONG SELL|BUY|SELL|HOLD)\b"
)
# The model writes conviction several ways: "SELL. Conviction: High",
# "HOLD (Medium Conviction)", "Conviction level is Medium". Read the opening only.
CONVICTION = re.compile(
    r"\b(HIGH|MEDIUM|LOW)[\s-]+CONVICTION"
    r"|CONVICTION(?:\s+LEVEL)?(?:\s+IS|\s*[:-])?\s*\W?\s*(HIGH|MEDIUM|LOW)\b"
)


@dataclass
class Reading:
    row_id: int
    ticker: str
    fiscal_year: int
    verdict: str | None
    conviction: str | None
    run_status: str
    model: str
    read_at: str
    filing_date: str | None = None
    industry: str | None = None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_config() -> tuple[dict[str, Any], str]:
    config = yaml.safe_load(CONFIG_PATH.read_text())
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return config, hashlib.sha256(canonical.encode()).hexdigest()


def load_readings(config: dict[str, Any]) -> tuple[list[Reading], dict[str, int]]:
    uri = f"file:{ROOT / config['database']}?mode=ro&immutable=1"
    con = sqlite3.connect(uri, uri=True)
    rows = con.execute(
        """
        SELECT ar.id, ar.ticker, ar.fiscal_year, ar.result_json, COALESCE(r.status, 'unknown'),
               r.config_json, ar.created_at
        FROM analysis_results ar LEFT JOIN analysis_runs r ON r.run_id = ar.run_id
        WHERE ar.result_type = ? ORDER BY ar.id
        """,
        (config["result_type"],),
    ).fetchall()
    filings: dict[tuple[str, int], str] = {}
    for ticker, year, date in con.execute(
        "SELECT ticker, fiscal_year, filing_date FROM file_cache "
        "WHERE filing_type = '10-K' AND filing_date IS NOT NULL"
    ):
        key = (ticker, year)
        filings[key] = min(date, filings.get(key, date))
    con.close()

    counts = {"stored": len(rows)}
    seen: set[tuple[str, int]] = set()
    readings: list[Reading] = []
    for row_id, ticker, year, payload, status, run_config, read_at in rows:
        if (ticker, year) in seen:  # keep_lowest_row_id: rows are ordered by id
            continue
        seen.add((ticker, year))
        model = json.loads(run_config or "{}").get("model", "unknown")
        if model != config["model"]:
            continue
        verdict_text = str(json.loads(payload).get("final_verdict", "")).upper()
        verdict = VERDICT.search(verdict_text)
        conviction = CONVICTION.search(verdict_text[:300])
        readings.append(
            Reading(
                row_id=row_id,
                ticker=ticker,
                fiscal_year=int(year),
                verdict=verdict[1] if verdict else None,
                conviction=(conviction[1] or conviction[2]) if conviction else None,
                run_status=status,
                model=model,
                read_at=read_at,
                filing_date=filings.get((ticker, year)),
            )
        )
    counts["deduped_all_models"] = len(seen)
    counts["excluded_model_mismatch"] = len(seen) - len(readings)
    counts["unique_company_years"] = len(readings)
    counts["from_completed_runs"] = sum(r.run_status == "completed" for r in readings)
    counts["with_parsed_verdict"] = sum(r.verdict is not None for r in readings)
    counts["with_filing_date"] = sum(r.filing_date is not None for r in readings)
    return readings, counts


def anachronism_probe(config: dict[str, Any]) -> dict[str, Any]:
    """Count term mentions, and those in readings of filings that predate the term."""
    uri = f"file:{ROOT / config['database']}?mode=ro&immutable=1"
    con = sqlite3.connect(uri, uri=True)
    filings: dict[tuple[str, int], str] = {}
    for ticker, year, day in con.execute(
        "SELECT ticker, fiscal_year, filing_date FROM file_cache "
        "WHERE filing_type = '10-K' AND filing_date IS NOT NULL"
    ):
        filings[(ticker, year)] = min(day, filings.get((ticker, year), day))
    terms = {t: str(d) for t, d in config["anachronism_terms"].items()}
    found = {t: {"first_public": d, "mentions": 0, "before_term": []} for t, d in terms.items()}
    seen: set[tuple[str, int]] = set()
    scanned = 0
    for ticker, year, payload in con.execute(
        "SELECT ticker, fiscal_year, result_json FROM analysis_results "
        "WHERE result_type = ? ORDER BY id",
        (config["result_type"],),
    ):
        if (ticker, year) in seen or (ticker, year) not in filings:
            continue
        seen.add((ticker, year))
        scanned += 1
        lowered = payload.lower()
        for term, first in terms.items():
            if term.lower() in lowered:
                found[term]["mentions"] += 1
                if filings[(ticker, year)] < first:
                    found[term]["before_term"].append(f"{ticker} FY{year}")
    con.close()
    return {"readings_scanned": scanned, "terms": found}


def load_industries(config: dict[str, Any]) -> dict[str, str]:
    with (ROOT / config["industry_source"]).open(encoding="utf-8", errors="replace") as handle:
        return {
            row["ticker"].strip(): (row.get(config["industry_column"]) or "").strip() or "Unknown"
            for row in csv.DictReader(handle)
        }


class Prices:
    """Adjusted closes from the refreshed wide parquet, truncated at price_end."""

    def __init__(self, source: Path, end: str) -> None:
        closes = pd.read_parquet(source)
        closes.index = pd.to_datetime(closes.index).tz_localize(None)
        self.closes = closes.loc[: pd.Timestamp(end)]
        self.used: set[str] = set()

    def close(self, ticker: str) -> pd.Series | None:
        if ticker not in self.closes:
            return None
        self.used.add(ticker)
        return self.closes[ticker].dropna()


def forward_returns(
    readings: list[Reading], prices: Prices, config: dict[str, Any]
) -> pd.DataFrame:
    spy = prices.close(config["benchmark"])
    assert spy is not None, "benchmark prices are required"
    records = []
    for r in readings:
        if r.filing_date is None or r.verdict is None:
            continue
        series = prices.close(r.ticker)
        if series is None or series.empty:
            continue
        after = series.index > pd.Timestamp(r.filing_date)
        if not after.any():
            continue
        entry = int(np.argmax(after))
        record: dict[str, Any] = {
            "ticker": r.ticker,
            "model": r.model,
            "read_at": r.read_at,
            "fiscal_year": r.fiscal_year,
            "verdict": r.verdict,
            "conviction": r.conviction,
            "industry": r.industry,
            "filing_date": r.filing_date,
            "entry_date": series.index[entry].date().isoformat(),
        }
        for label, days in config["horizons_trading_days"].items():
            exit_ = entry + days
            if exit_ >= len(series):
                continue
            start, stop = series.index[entry], series.index[exit_]
            stock = series.iloc[exit_] / series.iloc[entry] - 1
            bench = spy.asof(stop) / spy.asof(start) - 1
            record[f"excess_{label}"] = float(stock - bench)
            record[f"exit_{label}"] = stop.date().isoformat()
        records.append(record)
    return pd.DataFrame.from_records(records)


def legs(frame: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.Series, pd.Series]:
    return (
        frame["verdict"].isin(config["long_verdicts"]),
        frame["verdict"].isin(config["short_verdicts"]),
    )


def vintage_ranks(data: pd.DataFrame, column: str) -> pd.Series:
    """Percentile rank of excess return among all readings of the same vintage."""
    return data.groupby("fiscal_year")[column].rank(pct=True)


def spread_summary(frame: pd.DataFrame, column: str, config: dict[str, Any]) -> dict[str, Any]:
    data = frame.dropna(subset=[column])
    long_mask, short_mask = legs(data, config)
    long_, short = data.loc[long_mask, column], data.loc[short_mask, column]
    ranks = vintage_ranks(data, column)
    long_r, short_r = ranks[long_mask], ranks[short_mask]
    result: dict[str, Any] = {
        "n_long": int(len(long_)),
        "n_short": int(len(short)),
        "n_all": int(len(data)),
    }
    if len(long_) < 2 or len(short) < 2:
        return result
    welch = stats.ttest_ind(long_, short, equal_var=False)
    by_ticker = data.assign(long=long_mask, short=short_mask)
    long_t = by_ticker[by_ticker["long"]].groupby("ticker")[column].mean()
    short_t = by_ticker[by_ticker["short"]].groupby("ticker")[column].mean()
    clustered = stats.ttest_ind(long_t, short_t, equal_var=False)
    result.update(
        {
            "spread_se": float(np.sqrt(long_.var() / len(long_) + short.var() / len(short))),
            "long_mean_excess": float(long_.mean()),
            "short_mean_excess": float(short.mean()),
            "all_mean_excess": float(data[column].mean()),
            "spread": float(long_.mean() - short.mean()),
            "median_spread": float(long_.median() - short.median()),
            "rank_spread": float(long_r.mean() - short_r.mean()),
            "rank_spread_se": float(
                np.sqrt(long_r.var() / len(long_r) + short_r.var() / len(short_r))
            ),
            "naive_welch_p": float(welch.pvalue),
            "ticker_averaged_naive_p": float(clustered.pvalue),
            "n_long_tickers": int(len(long_t)),
            "n_short_tickers": int(len(short_t)),
        }
    )
    return result


def permutation_test(
    frame: pd.DataFrame,
    column: str,
    blocks: list[str],
    config: dict[str, Any],
    rng: np.random.Generator,
    ranks: bool = False,
) -> dict[str, Any]:
    """Shuffle verdicts within blocks; the null is 'no information beyond the block'.

    With ranks=True the statistic uses within-vintage percentile ranks, so that a
    single extreme return cannot decide it.
    """
    data = frame.dropna(subset=[column]).copy()
    keys = data[blocks].astype(str).agg("|".join, axis=1)
    sizes = keys.map(keys.value_counts())
    data = data[sizes >= config["min_block_size"]]
    keys = keys.loc[data.index]
    block = pd.factorize(keys)[0]
    values = (vintage_ranks(data, column) if ranks else data[column]).to_numpy()
    long_mask, short_mask = (m.to_numpy() for m in legs(data, config))
    labels = np.where(long_mask, 1, np.where(short_mask, -1, 0))

    def statistic(lab: np.ndarray) -> float:
        return float(values[lab == 1].mean() - values[lab == -1].mean())

    observed = statistic(labels)
    base = np.argsort(block, kind="stable")
    null = np.empty(config["permutations"])
    for i in range(len(null)):
        shuffled = np.argsort(block + rng.random(len(block)), kind="stable")
        permuted = np.empty_like(labels)
        permuted[base] = labels[shuffled]
        null[i] = statistic(permuted)
    centre = float(null.mean())
    extreme = int(np.sum(np.abs(null - centre) >= abs(observed - centre)))
    return {
        "blocks": blocks,
        "statistic": "rank" if ranks else "mean",
        "n": int(len(data)),
        "n_long": int(long_mask.sum()),
        "n_short": int(short_mask.sum()),
        "p_method": "two_sided_distance_from_permutation_null_mean",
        "n_blocks": int(block.max() + 1),
        "observed_spread": observed,
        "p_two_sided": (1 + extreme) / (1 + len(null)),
        "null_p2_5": float(np.percentile(null, 2.5)),
        "null_p97_5": float(np.percentile(null, 97.5)),
        "null_mean": float(null.mean()),
        "null_sd": float(null.std()),
        # Approximate spread detectable with 80% power at two-sided alpha 0.05.
        "min_detectable_spread": float(2.8 * null.std()),
    }


def main() -> None:
    config, config_hash = load_config()
    OUT.mkdir(exist_ok=True)
    database = ROOT / config["database"]
    run: dict[str, Any] = {
        "stage": "whitepaper-backtest-evaluation",
        "timestamp": datetime.now(UTC).isoformat(),
        "config_hash": config_hash,
        "config": config,
        "versions": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": __import__("scipy").__version__,
        },
        "inputs": {
            config["database"]: sha256(database),
            config["industry_source"]: sha256(ROOT / config["industry_source"]),
            config["price_source"]: sha256(ROOT / config["price_source"]),
            Path(__file__).name: sha256(Path(__file__)),
        },
    }
    (OUT / "run.json").write_text(json.dumps(run, indent=2) + "\n")

    readings, counts = load_readings(config)
    industries = load_industries(config)
    for reading in readings:
        reading.industry = industries.get(reading.ticker, "Unknown")
    prices = Prices(ROOT / config["price_source"], config["price_end"])
    frame = forward_returns(readings, prices, config)
    counts["with_entry_price"] = int(len(frame))
    counts["tickers_with_entry_price"] = int(frame["ticker"].nunique())

    cutoff = pd.Timestamp(config["knowledge_cutoff"])
    filed = pd.to_datetime(frame["filing_date"])
    frame["post_cutoff_filing"] = filed > cutoff
    rng = np.random.default_rng(config["permutation_seed"])

    results: dict[str, Any] = {"counts": counts, "horizons": {}, "vintages": {}}
    dated = [r for r in readings if r.verdict and r.filing_date]
    results["verdicts_by_vintage"] = {
        str(year): dict(Counter(r.verdict for r in dated if r.fiscal_year == year))
        for year in sorted({r.fiscal_year for r in dated})
    }
    results["filing_months"] = dict(Counter(int(r.filing_date[5:7]) for r in dated))
    results["april_convention_after_filing"] = sum(
        r.filing_date <= f"{r.fiscal_year + 1}-04-01" for r in dated
    )
    results["conviction_counts"] = dict(Counter(f"{r.verdict}|{r.conviction}" for r in dated))

    for label in config["horizons_trading_days"]:
        column, exit_column = f"excess_{label}", f"exit_{label}"
        if column not in frame:
            continue
        pre = frame[pd.to_datetime(frame[exit_column]) < cutoff]
        post = frame[frame["post_cutoff_filing"]]
        high = frame[frame["conviction"] == "HIGH"]
        results["horizons"][label] = {
            "all": spread_summary(frame, column, config),
            "window_before_cutoff": spread_summary(pre, column, config),
            "filed_after_cutoff": spread_summary(post, column, config),
            "high_conviction": spread_summary(high, column, config),
        }
        for year, group in frame.groupby("fiscal_year"):
            summary = spread_summary(group, column, config)
            if summary.get("spread") is not None:
                results["vintages"].setdefault(str(year), {})[label] = summary

    primary = {}
    for spec in config["primary"]:
        label = spec["horizon"]
        column, exit_column = f"excess_{label}", f"exit_{label}"
        if spec["sample"].startswith("outcome window"):
            sample = frame[pd.to_datetime(frame[exit_column]) < cutoff]
        else:
            sample = frame[frame["post_cutoff_filing"]]
        primary[spec["id"]] = {
            "question": spec["question"],
            "horizon": label,
            "summary": spread_summary(sample, column, config),
            "within_vintage": permutation_test(sample, column, ["fiscal_year"], config, rng),
            "within_vintage_industry": permutation_test(
                sample, column, ["fiscal_year", "industry"], config, rng
            ),
            # Secondary, added in v2 after the post-cutoff tails were inspected.
            "rank_within_vintage_industry": permutation_test(
                sample, column, ["fiscal_year", "industry"], config, rng, ranks=True
            ),
        }
    results["primary"] = primary

    # Secondary: the same permutation test at every horizon, whole sample.
    results["secondary_permutation"] = {
        label: permutation_test(
            frame, f"excess_{label}", ["fiscal_year", "industry"], config, rng
        )
        for label in config["horizons_trading_days"]
        if f"excess_{label}" in frame
    }
    results["anachronism_probe"] = anachronism_probe(config)
    results["industry_unknown_share"] = float((frame["industry"] == "Unknown").mean())
    results["price_files_used"] = len(prices.used)

    frame.to_csv(OUT / "trades.csv", index=False)
    (OUT / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    run["outputs"] = {
        name: sha256(OUT / name) for name in ("results.json", "trades.csv")
    }
    (OUT / "run.json").write_text(json.dumps(run, indent=2) + "\n")
    print(json.dumps({"counts": counts, "primary": primary}, indent=2))


if __name__ == "__main__":
    main()
