"""
Shared helpers for EON backtesting experiments.
All experiments import from here to avoid duplication.
"""

import json
import logging
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path("data/eon.db")
DEFAULT_HOLDING_PERIODS = [21, 63, 126, 252, 504]
PERIOD_LABELS = {21: "1M", 63: "3M", 126: "6M", 252: "1Y", 504: "2Y"}
ACTION_RANK = {"STRONG BUY": 2, "BUY": 1, "HOLD": 0, "SELL": -1, "STRONG SELL": -2, "UNKNOWN": 0}


def pl(p: int) -> str:
    return PERIOD_LABELS.get(p, f"{p}d")


# ── Signal dataclass ───────────────────────────────────────────────────────────

@dataclass
class Signal:
    ticker: str
    fiscal_year: int
    action: str
    conviction: str
    buffett_action: str
    taleb_action: str
    contrarian_action: str
    moat: str
    antifragile: str
    # raw text fields for richer analysis
    roic_text: str = ""
    tail_risk_text: str = ""
    consensus_wrong: str = ""
    variant_perception: str = ""
    hidden_strengths: str = ""
    hidden_weaknesses: str = ""
    positioning: str = ""
    synthesis_text: str = ""
    final_verdict_raw: str = ""


# ── Parsing helpers ────────────────────────────────────────────────────────────

def parse_action(fv: str) -> str:
    m = re.match(r"(STRONG BUY|STRONG SELL|BUY|SELL|HOLD)", fv.upper())
    return m.group(1) if m else "UNKNOWN"


def parse_conviction(fv: str) -> str:
    m = re.search(r"Conviction[:\s]*(\w+)", fv, re.IGNORECASE)
    if m:
        c = m.group(1).capitalize()
        if c in ("High", "Medium", "Low"):
            return c
    return "Unknown"


def parse_moat(raw: str) -> str:
    r = raw.strip()
    if r.startswith("Wide"):
        return "Wide"
    if r.startswith("None") or r.startswith("No "):
        return "None"
    return "Narrow"


def parse_af(raw: str) -> str:
    m = re.match(r"(Antifragile|Robust|Fragile)", raw)
    return m.group(1) if m else "Robust"


# ── DB loader ─────────────────────────────────────────────────────────────────

def load_signals(
    db_path: Path = DEFAULT_DB_PATH,
    max_fy: int = 2024,
    min_fy: int = 2020,
) -> List[Signal]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ar.ticker, ar.fiscal_year, ar.result_json
        FROM analysis_results ar
        JOIN analysis_runs runs ON ar.run_id = runs.run_id
        WHERE ar.result_type = 'SimplifiedAnalysis'
          AND ar.fiscal_year <= ? AND ar.fiscal_year >= ?
          AND runs.status = 'completed'
        ORDER BY ar.ticker, ar.fiscal_year
        """,
        (max_fy, min_fy),
    )
    seen = set()
    signals: List[Signal] = []
    for row in cur.fetchall():
        key = (row["ticker"], row["fiscal_year"])
        if key in seen:
            continue
        seen.add(key)
        try:
            d = json.loads(row["result_json"])
            fv = d.get("final_verdict", "")
            b = d.get("buffett", {})
            t = d.get("taleb", {})
            c = d.get("contrarian", {})
            tail = t.get("tail_risk_exposure", "")
            if isinstance(tail, list):
                tail = " ".join(tail)
            signals.append(Signal(
                ticker=row["ticker"],
                fiscal_year=row["fiscal_year"],
                action=parse_action(fv),
                conviction=parse_conviction(fv),
                buffett_action=b.get("action_signal", ""),
                taleb_action=t.get("action_signal", ""),
                contrarian_action=c.get("action_signal", ""),
                moat=parse_moat(b.get("moat_rating", "")),
                antifragile=parse_af(t.get("antifragile_rating", "")),
                roic_text=b.get("return_on_invested_capital", ""),
                tail_risk_text=tail,
                consensus_wrong=c.get("consensus_wrong_because", ""),
                variant_perception=c.get("variant_perception", ""),
                hidden_strengths=c.get("hidden_strengths", ""),
                hidden_weaknesses=c.get("hidden_weaknesses", ""),
                positioning=c.get("positioning", ""),
                synthesis_text=str(d.get("synthesis", "")),
                final_verdict_raw=fv,
            ))
        except Exception:
            pass
    conn.close()
    logger.info(f"Loaded {len(signals)} signals (FY{min_fy}–{max_fy})")
    return signals


# ── Price fetching ─────────────────────────────────────────────────────────────

def fetch_prices(
    tickers: List[str],
    min_fy: int,
    max_fy: int,
) -> Tuple[Dict[str, pd.DataFrame], Optional[pd.DataFrame]]:
    from experimental.backtester.price_fetcher import PriceFetcher
    pf = PriceFetcher()
    all_tickers = list(set(tickers + ["SPY"]))
    prices = pf.get_prices_batch(all_tickers, f"{min_fy}-01-01", f"{max_fy + 7}-01-01")
    bench = prices.pop("SPY", None)
    return prices, bench


# ── Forward return computation ─────────────────────────────────────────────────

def forward_returns(
    sig: Signal,
    stock_prices: pd.DataFrame,
    bench_prices: pd.DataFrame,
    holding_periods: List[int],
) -> Dict[int, Tuple[float, Optional[float], Optional[float]]]:
    """Returns {period: (stock_ret, bench_ret, excess_ret)}. Missing periods omitted."""
    entry_ts = pd.Timestamp(f"{sig.fiscal_year + 1}-04-01")
    sc = stock_prices["Close"]
    bc = bench_prices["Close"]

    valid = sc.index[sc.index >= entry_ts]
    if len(valid) == 0:
        return {}
    actual = valid[0]
    entry_p = float(sc.loc[actual])

    bv = bc.index[bc.index >= entry_ts]
    if len(bv) == 0:
        return {}
    b_actual = bv[0]
    b_entry_p = float(bc.loc[b_actual])

    result = {}
    for period in holding_periods:
        idx = sc.index.get_loc(actual)
        exit_idx = idx + period
        if exit_idx >= len(sc):
            continue
        stock_ret = float(sc.iloc[exit_idx]) / entry_p - 1.0
        bidx = bc.index.get_loc(b_actual)
        bex = bidx + period
        if bex >= len(bc):
            result[period] = (stock_ret, None, None)
            continue
        bench_ret = float(bc.iloc[bex]) / b_entry_p - 1.0
        result[period] = (stock_ret, bench_ret, stock_ret - bench_ret)
    return result


# ── Stats helpers ──────────────────────────────────────────────────────────────

def ttest(values: List[float]) -> Tuple[float, float]:
    """One-sample t-test vs 0. Returns (t, p)."""
    if len(values) < 3:
        return 0.0, 1.0
    arr = np.array(values)
    t, p = scipy_stats.ttest_1samp(arr, 0)
    return float(t), float(p)


def welch(a: List[float], b: List[float]) -> Tuple[float, float]:
    """Welch two-sample t-test. Returns (t, p)."""
    if len(a) < 3 or len(b) < 3:
        return 0.0, 1.0
    t, p = scipy_stats.ttest_ind(np.array(a), np.array(b), equal_var=False)
    return float(t), float(p)


def sig_stars(p: float) -> str:
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "** "
    if p < 0.10:
        return "*  "
    return "   "


def describe(values: List[float]) -> str:
    if len(values) < 3:
        return f"n={len(values):3d}  N/A"
    arr = np.array(values)
    t, p = ttest(values)
    return (
        f"n={len(arr):4d}  mean={arr.mean():+.1%}  "
        f"med={np.median(arr):+.1%}  "
        f"beat={float((arr > 0).mean()):.0%}  "
        f"t={t:.2f}  p={p:.3f}{sig_stars(p)}"
    )


# ── Table printer ──────────────────────────────────────────────────────────────

def print_table(
    title: str,
    groups: List[str],
    data: Dict[str, Dict[int, List[float]]],
    holding_periods: List[int] = DEFAULT_HOLDING_PERIODS,
    metric: str = "excess",  # "excess" or "raw"
):
    """Print a clean aligned comparison table."""
    print(f"\n{'═' * 120}")
    print(f"  {title}")
    print(f"{'═' * 120}")
    hdr = f"  {'Group':44s}  {'n':>5s}"
    for p in holding_periods:
        hdr += f"  {pl(p):>16s}"
    print(hdr)
    print("─" * 120)
    for g in groups:
        d = data.get(g, {})
        n = max((len(v) for v in d.values()), default=0)
        line = f"  {g:44s}  {n:>5d}"
        for p in holding_periods:
            vals = d.get(p, [])
            if len(vals) < 3:
                line += f"  {'N/A':>16s}"
            else:
                arr = np.array(vals)
                _, pv = ttest(vals)
                s = sig_stars(pv).strip()
                cell = f"{arr.mean():+.1%}{(''+s) if s else ''} ({len(vals)})"
                line += f"  {cell:>16s}"
        print(line)
    print(f"\n  {'*p<.10  **p<.05  ***p<.01  |  values = mean excess return vs SPY'}")


def section(label: str):
    print(f"\n{'█' * 120}")
    print(f"  {label}")
    print(f"{'█' * 120}")
