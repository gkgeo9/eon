#!/usr/bin/env python3
"""
Spread / Relative backtester.

Tests whether the SPREAD between AI-rated BUY stocks and SELL stocks
generates real, statistically significant alpha.

The key insight from Test #5: the AI can't reliably beat SPY on either
leg individually, but the spread between its best and worst picks IS
significant. This file tests that thesis comprehensively.

Portfolios constructed:
  1. ALL BUY vs ALL SELL                 (broadest)
  2. HIGH CONVICTION BUY vs HIGH CONV SELL
  3. STRONG BUY vs STRONG SELL           (tightest)
  4. BUY+Wide Moat vs SELL+Fragile       (quality-filtered)
  5. BUY+Robust vs SELL+Fragile          (Taleb-filtered)
  6. Quintile spread: top-rated vs bottom-rated by composite score

Each portfolio is tested as:
  - Long/Short return = mean(long stock returns) - mean(short stock returns)
  - Per-trade excess = stock_return - SPY_return, tested separately for
    long and short legs, then combined for significance.

Vintage analysis: results are also broken out by fiscal year to check
whether alpha is regime-dependent.

Usage:
    python -c "
    import sys; sys.argv = ['', '--batch', 'all_comp_08022026']
    from experimental.backtester.run_spread_backtest import main; main()
    "
    # Or without batch filter to run on the whole DB:
    python -c "
    import sys; sys.argv = ['']
    from experimental.backtester.run_spread_backtest import main; main()
    "
"""

import argparse
import csv
import json
import logging
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from .data_loader import DEFAULT_DB_PATH
from .metrics import TRADING_DAYS_PER_YEAR, compute_trade_returns, TradeResult
from .price_fetcher import PriceFetcher
from .report import _period_label

logger = logging.getLogger(__name__)

DEFAULT_HOLDING_PERIODS = [21, 63, 126, 252, 504, 1260]


# ═══════════════════════════════════════════════════════════════════════════════
#  Data Loading & Signal Parsing
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ParsedSignal:
    """All useful fields extracted from a SimplifiedAnalysis result."""

    ticker: str
    fiscal_year: int
    signal_date: str

    # Final verdict
    action: str  # STRONG BUY / BUY / HOLD / SELL / STRONG SELL / UNKNOWN
    conviction: str  # High / Medium / Low / Unknown

    # Perspective action signals
    buffett_action: str = ""
    taleb_action: str = ""
    contrarian_action: str = ""

    # Quality filters
    moat_rating: str = ""  # Wide / Narrow / None
    antifragile_rating: str = ""  # Antifragile / Robust / Fragile

    # Contrarian conviction
    contrarian_conviction: str = ""

    # Composite score (higher = more bullish)
    composite_score: float = 0.0


def _parse_moat(raw: str) -> str:
    """Normalize moat_rating to Wide/Narrow/None."""
    r = raw.strip()
    if r.startswith("Wide"):
        return "Wide"
    if r.startswith("None") or r.startswith("No "):
        return "None"
    if r.startswith("Narrow"):
        return "Narrow"
    return "Narrow"  # default


def _parse_antifragile(raw: str) -> str:
    """Normalize antifragile_rating to Antifragile/Robust/Fragile."""
    m = re.match(r"(Antifragile|Robust|Fragile)", raw)
    return m.group(1) if m else "Robust"


def _compute_composite_score(action: str, conviction: str, moat: str, af: str) -> float:
    """
    Numeric composite score from -10 (worst) to +10 (best).

    Components:
      action:     STRONG BUY=+4, BUY=+2, HOLD=0, SELL=-2, STRONG SELL=-4
      conviction: High=+2, Medium=+1, Low=0, Unknown=+0.5
      moat:       Wide=+2, Narrow=0, None=-1
      antifragile: Antifragile=+2, Robust=+1, Fragile=-1
    """
    action_map = {"STRONG BUY": 4, "BUY": 2, "HOLD": 0, "SELL": -2, "STRONG SELL": -4, "UNKNOWN": 0}
    conv_map = {"High": 2, "Medium": 1, "Low": 0, "Unknown": 0.5}
    moat_map = {"Wide": 2, "Narrow": 0, "None": -1}
    af_map = {"Antifragile": 2, "Robust": 1, "Fragile": -1}

    return (
        action_map.get(action, 0)
        + conv_map.get(conviction, 0.5)
        + moat_map.get(moat, 0)
        + af_map.get(af, 0)
    )


def load_signals(
    db_path: Path,
    batch_name: Optional[str],
    max_fiscal_year: int,
    min_fiscal_year: int,
) -> List[ParsedSignal]:
    """Load all SimplifiedAnalysis results, parse into structured signals."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    if batch_name:
        cur = conn.cursor()
        cur.execute("SELECT batch_id FROM batch_jobs WHERE name = ?", (batch_name,))
        row = cur.fetchone()
        if not row:
            print(f"  Batch '{batch_name}' not found.")
            conn.close()
            return []
        batch_id = row["batch_id"]
        cur.execute(
            """
            SELECT ar.ticker, ar.fiscal_year, ar.result_json
            FROM analysis_results ar
            JOIN batch_items bi ON ar.run_id = bi.run_id
            WHERE bi.batch_id = ?
              AND ar.result_type = 'SimplifiedAnalysis'
              AND ar.fiscal_year <= ? AND ar.fiscal_year >= ?
            ORDER BY ar.ticker, ar.fiscal_year
            """,
            (batch_id, max_fiscal_year, min_fiscal_year),
        )
    else:
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
            (max_fiscal_year, min_fiscal_year),
        )

    # Deduplicate: keep only one entry per (ticker, fiscal_year).
    # If the same stock+year appears multiple times (e.g. from different batches),
    # keep the first (arbitrary — they should be identical analyses).
    seen = set()
    signals = []
    skipped_dupes = 0
    for row in cur.fetchall():
        key = (row["ticker"], row["fiscal_year"])
        if key in seen:
            skipped_dupes += 1
            continue
        seen.add(key)

        try:
            data = json.loads(row["result_json"])
            fv = data.get("final_verdict", "")
            am = re.match(r"(STRONG BUY|STRONG SELL|BUY|SELL|HOLD)", fv.upper())
            action = am.group(1) if am else "UNKNOWN"
            cm = re.search(r"(?:Conviction)[:\s]*(\w+)", fv, re.IGNORECASE)
            conviction = "Unknown"
            if cm:
                c = cm.group(1).capitalize()
                if c in ("High", "Medium", "Low"):
                    conviction = c

            b = data.get("buffett", {})
            t = data.get("taleb", {})
            c_data = data.get("contrarian", {})

            moat = _parse_moat(b.get("moat_rating", ""))
            af = _parse_antifragile(t.get("antifragile_rating", ""))

            score = _compute_composite_score(action, conviction, moat, af)

            signals.append(ParsedSignal(
                ticker=row["ticker"],
                fiscal_year=row["fiscal_year"],
                signal_date=f"{row['fiscal_year'] + 1}-04-01",
                action=action,
                conviction=conviction,
                buffett_action=b.get("action_signal", ""),
                taleb_action=t.get("action_signal", ""),
                contrarian_action=c_data.get("action_signal", ""),
                moat_rating=moat,
                antifragile_rating=af,
                contrarian_conviction=c_data.get("conviction_level", ""),
                composite_score=score,
            ))
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse {row['ticker']} FY{row['fiscal_year']}: {e}")

    conn.close()
    if skipped_dupes:
        print(f"  Deduplicated: skipped {skipped_dupes} duplicate (ticker, fiscal_year) entries")
    return signals


def filter_latest_only(signals: List[ParsedSignal]) -> List[ParsedSignal]:
    """Keep only the most recent fiscal year per ticker (eliminates cross-year correlation)."""
    latest = {}
    for s in signals:
        if s.ticker not in latest or s.fiscal_year > latest[s.ticker].fiscal_year:
            latest[s.ticker] = s
    return list(latest.values())


# ═══════════════════════════════════════════════════════════════════════════════
#  Trade Computation
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class SpreadTrade:
    """A single trade with its returns and metadata."""

    ticker: str
    fiscal_year: int
    side: str  # "long" or "short"
    group: str
    entry_date: str
    entry_price: float
    action: str
    conviction: str
    composite_score: float

    # Returns indexed by holding period (trading days)
    stock_return: Dict[int, Optional[float]] = field(default_factory=dict)
    bench_return: Dict[int, Optional[float]] = field(default_factory=dict)
    excess_return: Dict[int, Optional[float]] = field(default_factory=dict)


def compute_spread_trade(
    signal: ParsedSignal,
    stock_prices: pd.DataFrame,
    bench_prices: pd.DataFrame,
    holding_periods: List[int],
    side: str,
    group: str,
) -> Optional[SpreadTrade]:
    """Compute forward returns for a single trade."""
    entry_ts = pd.Timestamp(signal.signal_date)
    stock_close = stock_prices["Close"]
    bench_close = bench_prices["Close"]

    stock_dates = stock_close.index
    valid = stock_dates[stock_dates >= entry_ts]
    if len(valid) == 0:
        return None
    actual_entry = valid[0]
    entry_price = float(stock_close.loc[actual_entry])

    bench_dates = bench_close.index
    bv = bench_dates[bench_dates >= entry_ts]
    if len(bv) == 0:
        return None
    bench_entry = bv[0]
    bench_entry_price = float(bench_close.loc[bench_entry])

    trade = SpreadTrade(
        ticker=signal.ticker,
        fiscal_year=signal.fiscal_year,
        side=side,
        group=group,
        entry_date=actual_entry.strftime("%Y-%m-%d"),
        entry_price=entry_price,
        action=signal.action,
        conviction=signal.conviction,
        composite_score=signal.composite_score,
    )

    has_data = False
    for period in holding_periods:
        idx = stock_dates.get_loc(actual_entry)
        exit_idx = idx + period
        if exit_idx >= len(stock_dates):
            trade.stock_return[period] = None
            trade.bench_return[period] = None
            trade.excess_return[period] = None
            continue

        stock_ret = (float(stock_close.iloc[exit_idx]) / entry_price) - 1.0

        bidx = bench_dates.get_loc(bench_entry)
        bex = bidx + period
        if bex >= len(bench_dates):
            trade.stock_return[period] = stock_ret
            trade.bench_return[period] = None
            trade.excess_return[period] = None
            has_data = True
            continue

        bench_ret = (float(bench_close.iloc[bex]) / bench_entry_price) - 1.0
        trade.stock_return[period] = stock_ret
        trade.bench_return[period] = bench_ret
        trade.excess_return[period] = stock_ret - bench_ret
        has_data = True

    return trade if has_data else None


# ═══════════════════════════════════════════════════════════════════════════════
#  Spread Portfolio Metrics
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class SpreadPeriodMetrics:
    """Metrics for one holding period of a spread portfolio."""

    period: int
    n_long: int
    n_short: int

    # Long leg
    long_mean_return: float = 0.0
    long_median_return: float = 0.0
    long_mean_excess: float = 0.0
    long_beat_spy: float = 0.0

    # Short leg (these are raw stock returns — negative = short profits)
    short_mean_return: float = 0.0
    short_median_return: float = 0.0
    short_mean_excess: float = 0.0
    short_beat_spy: float = 0.0  # % where stock underperformed SPY

    # Spread
    ls_return: float = 0.0  # long_return - short_return
    spread_alpha: float = 0.0  # long_excess - short_excess (should = ls_return)
    long_alpha: float = 0.0
    short_alpha: float = 0.0  # = -short_excess = bench - stock

    # Significance — on the combined pool of per-trade excess returns
    # Long excess: stock - SPY  (want > 0)
    # Short excess: SPY - stock (want > 0, i.e. stock underperformed)
    combined_t: float = 0.0
    combined_p: float = 1.0

    # Also test long and short legs independently
    long_t: float = 0.0
    long_p: float = 1.0
    short_t: float = 0.0
    short_p: float = 1.0


def _clustered_ttest(values: np.ndarray, clusters: List[str]) -> Tuple[float, float]:
    """
    One-sample t-test with clustered standard errors (by ticker).

    Instead of assuming N independent observations, this computes the mean
    of cluster-level means and uses the between-cluster variance for the
    standard error. This properly accounts for within-ticker correlation.

    Returns (t_stat, p_value).
    """
    if len(values) < 3:
        return 0.0, 1.0

    # Group by cluster
    cluster_sums = defaultdict(list)
    for val, cid in zip(values, clusters):
        cluster_sums[cid].append(val)

    cluster_means = np.array([np.mean(v) for v in cluster_sums.values()])
    n_clusters = len(cluster_means)

    if n_clusters < 3:
        return 0.0, 1.0

    grand_mean = cluster_means.mean()
    se = cluster_means.std(ddof=1) / np.sqrt(n_clusters)

    if se < 1e-12:
        return 0.0, 1.0

    t_stat = grand_mean / se
    p_value = 2 * scipy_stats.t.sf(abs(t_stat), df=n_clusters - 1)
    return float(t_stat), float(p_value)


def compute_spread_metrics(
    long_trades: List[SpreadTrade],
    short_trades: List[SpreadTrade],
    holding_periods: List[int],
    use_clustered_se: bool = False,
) -> Dict[int, SpreadPeriodMetrics]:
    """Compute spread metrics across holding periods.

    Args:
        use_clustered_se: If True, use clustered standard errors by ticker
            for t-tests (robust to within-ticker correlation from repeated
            fiscal years). Default False uses standard i.i.d. t-tests.
    """
    result = {}
    for period in holding_periods:
        # Long leg
        l_rets = [t.stock_return[period] for t in long_trades if t.stock_return.get(period) is not None]
        l_bench = [t.bench_return[period] for t in long_trades if t.bench_return.get(period) is not None]
        l_excess = [t.excess_return[period] for t in long_trades if t.excess_return.get(period) is not None]
        l_tickers = [t.ticker for t in long_trades if t.excess_return.get(period) is not None]

        # Short leg
        s_rets = [t.stock_return[period] for t in short_trades if t.stock_return.get(period) is not None]
        s_bench = [t.bench_return[period] for t in short_trades if t.bench_return.get(period) is not None]
        s_excess = [t.excess_return[period] for t in short_trades if t.excess_return.get(period) is not None]
        s_tickers = [t.ticker for t in short_trades if t.excess_return.get(period) is not None]

        nl, ns = len(l_rets), len(s_rets)
        pm = SpreadPeriodMetrics(period=period, n_long=nl, n_short=ns)

        if nl == 0 or ns == 0:
            result[period] = pm
            continue

        la, sa = np.array(l_rets), np.array(s_rets)
        le, se = np.array(l_excess) if l_excess else np.zeros(1), np.array(s_excess) if s_excess else np.zeros(1)

        pm.long_mean_return = float(la.mean())
        pm.long_median_return = float(np.median(la))
        pm.long_mean_excess = float(le.mean()) if l_excess else 0.0
        pm.long_beat_spy = float((le > 0).mean()) if l_excess else 0.0

        pm.short_mean_return = float(sa.mean())
        pm.short_median_return = float(np.median(sa))
        pm.short_mean_excess = float(se.mean()) if s_excess else 0.0
        pm.short_beat_spy = float((se < 0).mean()) if s_excess else 0.0  # stock < SPY = good for short

        pm.ls_return = pm.long_mean_return - pm.short_mean_return
        pm.long_alpha = pm.long_mean_excess
        pm.short_alpha = -pm.short_mean_excess  # flip: positive = stock fell relative to bench
        pm.spread_alpha = pm.long_alpha + pm.short_alpha

        if use_clustered_se:
            # Clustered standard errors by ticker
            combined_vals = list(le) + list(-se) if l_excess and s_excess else []
            combined_clusters = l_tickers + s_tickers if l_excess and s_excess else []
            if len(combined_vals) >= 3:
                pm.combined_t, pm.combined_p = _clustered_ttest(
                    np.array(combined_vals), combined_clusters
                )
            if len(l_excess) >= 3:
                pm.long_t, pm.long_p = _clustered_ttest(le, l_tickers)
            if len(s_excess) >= 3:
                pm.short_t, pm.short_p = _clustered_ttest(-se, s_tickers)
        else:
            # Standard i.i.d. t-tests
            combined = list(le) + list(-se) if l_excess and s_excess else []
            if len(combined) >= 3:
                pm.combined_t, pm.combined_p = scipy_stats.ttest_1samp(np.array(combined), 0)
            if len(l_excess) >= 3:
                pm.long_t, pm.long_p = scipy_stats.ttest_1samp(le, 0)
            if len(s_excess) >= 3:
                pm.short_t, pm.short_p = scipy_stats.ttest_1samp(-se, 0)

        result[period] = pm

    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  Report Printing
# ═══════════════════════════════════════════════════════════════════════════════


def print_portfolio_report(
    name: str,
    description: str,
    n_long: int,
    n_short: int,
    metrics: Dict[int, SpreadPeriodMetrics],
    holding_periods: List[int],
) -> None:
    """Print a single portfolio's spread report."""
    print(f"\n{'━' * 90}")
    print(f"  {name}")
    print(f"  {description}")
    print(f"  Long: {n_long} trades  |  Short: {n_short} trades")
    print(f"{'━' * 90}")

    periods = [p for p in holding_periods if p in metrics and (metrics[p].n_long > 0 and metrics[p].n_short > 0)]
    if not periods:
        print("  No overlapping data for any period.")
        return

    hdr = f"{'':42s}"
    for p in periods:
        hdr += f" {_period_label(p):>9s}"
    print(hdr)
    print("─" * (42 + 10 * len(periods)))

    def row(label, fn, blank=False):
        if blank:
            print()
            return
        line = f"{label:42s}"
        for p in periods:
            pm = metrics.get(p)
            if pm and pm.n_long > 0 and pm.n_short > 0:
                line += f" {fn(pm):>9s}"
            else:
                line += f" {'N/A':>9s}"
        print(line)

    row("Long trades (n)", lambda pm: f"{pm.n_long:d}")
    row("Short trades (n)", lambda pm: f"{pm.n_short:d}")
    row("", None, blank=True)
    row("LONG: Mean Return", lambda pm: f"{pm.long_mean_return:+.1%}")
    row("LONG: Mean Excess vs SPY", lambda pm: f"{pm.long_mean_excess:+.1%}")
    row("LONG: Beat SPY Rate", lambda pm: f"{pm.long_beat_spy:.0%}")
    row("", None, blank=True)
    row("SHORT: Mean Stock Return", lambda pm: f"{pm.short_mean_return:+.1%}")
    row("SHORT: Mean Excess vs SPY", lambda pm: f"{pm.short_mean_excess:+.1%}")
    row("SHORT: Stock < SPY Rate", lambda pm: f"{pm.short_beat_spy:.0%}")
    row("", None, blank=True)
    row("═══ SPREAD (Long - Short) ═══", lambda pm: f"{pm.ls_return:+.1%}")
    row("    Long Alpha contribution", lambda pm: f"{pm.long_alpha:+.1%}")
    row("    Short Alpha contribution", lambda pm: f"{pm.short_alpha:+.1%}")
    row("    Total Spread Alpha", lambda pm: f"{pm.spread_alpha:+.1%}")
    row("", None, blank=True)
    row("Combined t-stat", lambda pm: f"{pm.combined_t:.2f}")
    row("Combined p-value", lambda pm: f"{pm.combined_p:.4f}")
    row("Significant (p<0.05)", lambda pm: "*** YES" if pm.combined_p < 0.05 else "no")
    row("", None, blank=True)
    row("  Long-only t / p", lambda pm: f"{pm.long_t:.2f}/{pm.long_p:.3f}")
    row("  Short-only t / p", lambda pm: f"{pm.short_t:.2f}/{pm.short_p:.3f}")


def print_verdict_line(pm: SpreadPeriodMetrics, period: int) -> str:
    """One-line verdict for a period."""
    pl = _period_label(period)
    if pm.n_long < 3 or pm.n_short < 3:
        return f"    {pl}: Insufficient data (long={pm.n_long}, short={pm.n_short})"
    alpha = pm.spread_alpha
    ls = pm.ls_return
    p = pm.combined_p
    if p < 0.01 and alpha > 0:
        tag = "STRONG ALPHA"
    elif p < 0.05 and alpha > 0:
        tag = "ALPHA"
    elif alpha > 0 and p < 0.10:
        tag = "Suggestive"
    elif alpha > 0:
        tag = "Positive (not sig.)"
    else:
        tag = "No alpha"
    return f"    {pl}: {tag:22s} spread={ls:+.1%}  alpha={alpha:+.1%}  p={p:.4f}  (L={pm.n_long}, S={pm.n_short})"


def print_vintage_report(
    name: str,
    vintage_metrics: Dict[int, Dict[int, SpreadPeriodMetrics]],
    holding_periods: List[int],
) -> None:
    """Print spread results broken out by fiscal year vintage."""
    print(f"\n{'─' * 90}")
    print(f"  VINTAGE BREAKDOWN: {name}")
    print(f"{'─' * 90}")

    for fy in sorted(vintage_metrics.keys()):
        mets = vintage_metrics[fy]
        any_data = any(
            mets.get(p) and mets[p].n_long > 0 and mets[p].n_short > 0
            for p in holding_periods
        )
        if not any_data:
            continue
        # Find n for first available period
        sample_p = next((p for p in holding_periods if mets.get(p) and mets[p].n_long > 0), None)
        if not sample_p:
            continue
        n_l = mets[sample_p].n_long
        n_s = mets[sample_p].n_short
        print(f"\n  FY{fy} (entered ~Apr {fy+1})  long={n_l}  short={n_s}")
        for period in holding_periods:
            pm = mets.get(period)
            if pm and pm.n_long > 0 and pm.n_short > 0:
                print(print_verdict_line(pm, period))


# ═══════════════════════════════════════════════════════════════════════════════
#  CSV Export
# ═══════════════════════════════════════════════════════════════════════════════


def export_spread_trades(
    all_trades: List[SpreadTrade],
    holding_periods: List[int],
    path: Path,
) -> None:
    """Export all spread trades to CSV."""
    fields = [
        "ticker", "fiscal_year", "side", "group", "action", "conviction",
        "composite_score", "entry_date", "entry_price",
    ]
    for p in holding_periods:
        pl = _period_label(p)
        fields.extend([f"return_{pl}", f"bench_{pl}", f"excess_{pl}"])

    rows = []
    for t in all_trades:
        r = {
            "ticker": t.ticker, "fiscal_year": t.fiscal_year,
            "side": t.side, "group": t.group,
            "action": t.action, "conviction": t.conviction,
            "composite_score": f"{t.composite_score:.1f}",
            "entry_date": t.entry_date,
            "entry_price": f"{t.entry_price:.2f}",
        }
        for p in holding_periods:
            pl = _period_label(p)
            sr = t.stock_return.get(p)
            br = t.bench_return.get(p)
            er = t.excess_return.get(p)
            r[f"return_{pl}"] = f"{sr:.4f}" if sr is not None else ""
            r[f"bench_{pl}"] = f"{br:.4f}" if br is not None else ""
            r[f"excess_{pl}"] = f"{er:.4f}" if er is not None else ""
        rows.append(r)

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"  Trades: {path}")


def export_spread_metrics(
    portfolios: List[Tuple[str, Dict[int, SpreadPeriodMetrics]]],
    holding_periods: List[int],
    path: Path,
) -> None:
    """Export spread metrics summary to CSV."""
    fields = [
        "portfolio", "period", "n_long", "n_short",
        "long_mean_return", "long_mean_excess", "long_beat_spy",
        "short_mean_return", "short_mean_excess", "short_underperform_spy",
        "ls_return", "spread_alpha", "long_alpha", "short_alpha",
        "combined_t", "combined_p", "significant",
        "long_t", "long_p", "short_t", "short_p",
    ]
    rows = []
    for name, mets in portfolios:
        for p in holding_periods:
            pm = mets.get(p)
            if not pm or (pm.n_long == 0 and pm.n_short == 0):
                continue
            rows.append({
                "portfolio": name,
                "period": _period_label(p),
                "n_long": pm.n_long,
                "n_short": pm.n_short,
                "long_mean_return": f"{pm.long_mean_return:.4f}",
                "long_mean_excess": f"{pm.long_mean_excess:.4f}",
                "long_beat_spy": f"{pm.long_beat_spy:.4f}",
                "short_mean_return": f"{pm.short_mean_return:.4f}",
                "short_mean_excess": f"{pm.short_mean_excess:.4f}",
                "short_underperform_spy": f"{pm.short_beat_spy:.4f}",
                "ls_return": f"{pm.ls_return:.4f}",
                "spread_alpha": f"{pm.spread_alpha:.4f}",
                "long_alpha": f"{pm.long_alpha:.4f}",
                "short_alpha": f"{pm.short_alpha:.4f}",
                "combined_t": f"{pm.combined_t:.4f}",
                "combined_p": f"{pm.combined_p:.4f}",
                "significant": "YES" if pm.combined_p < 0.05 else "no",
                "long_t": f"{pm.long_t:.4f}",
                "long_p": f"{pm.long_p:.4f}",
                "short_t": f"{pm.short_t:.4f}",
                "short_p": f"{pm.short_p:.4f}",
            })

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"  Metrics: {path}")


# ═══════════════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(description="Spread/Relative backtester.")
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument("--batch", type=str, default=None)
    parser.add_argument("--min-year", type=int, default=0)
    parser.add_argument("--max-year", type=int, default=2024)
    parser.add_argument("--output", type=Path, default=Path("data/backtest_results/spread"))
    parser.add_argument("--cache-dir", type=Path, default=None)
    parser.add_argument("--periods", type=str, default="21,63,126,252,504,1260")
    parser.add_argument("--no-export", action="store_true")
    parser.add_argument("--latest-only", action="store_true",
                        help="Keep only the most recent fiscal year per ticker (robustness check)")
    parser.add_argument("--clustered", action="store_true",
                        help="Use clustered standard errors by ticker (robust to cross-year correlation)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")

    db_path = args.db or DEFAULT_DB_PATH
    holding_periods = [int(p.strip()) for p in args.periods.split(",")]

    print("=" * 90)
    print("EON SPREAD BACKTESTER — Relative / Long-Short Alpha Analysis")
    print("=" * 90)
    print(f"  Database:     {db_path}")
    print(f"  Batch:        {args.batch or 'ALL (whole database)'}")
    min_yr = str(args.min_year) if args.min_year else "earliest"
    print(f"  Fiscal years: {min_yr} – {args.max_year}")
    print(f"  Periods:      {', '.join(str(p) + 'd' for p in holding_periods)}")
    print(f"  Output:       {args.output}")
    if args.latest_only:
        print(f"  Mode:         LATEST-ONLY (one entry per ticker, most recent FY)")
    if args.clustered:
        print(f"  Std errors:   CLUSTERED by ticker (robust to cross-year correlation)")

    # ── Step 1: Load ──────────────────────────────────────────────────────────
    print("\nStep 1/4: Loading signals...")
    signals = load_signals(db_path, args.batch, args.max_year, args.min_year)
    if not signals:
        print("No signals found.")
        sys.exit(1)

    n_tickers = len(set(s.ticker for s in signals))
    print(f"  Loaded {len(signals)} signals ({n_tickers} unique tickers)")

    if args.latest_only:
        signals = filter_latest_only(signals)
        print(f"  After latest-only filter: {len(signals)} signals ({len(set(s.ticker for s in signals))} tickers)")

    # Distribution summary
    ac = Counter(s.action for s in signals)
    cc = Counter(s.conviction for s in signals)
    mc = Counter(s.moat_rating for s in signals)
    afc = Counter(s.antifragile_rating for s in signals)

    print(f"\n  Actions:     {dict(ac.most_common())}")
    print(f"  Convictions: {dict(cc.most_common())}")
    print(f"  Moats:       {dict(mc.most_common())}")
    print(f"  Antifragile: {dict(afc.most_common())}")

    scores = [s.composite_score for s in signals]
    print(f"  Composite score range: [{min(scores):.1f}, {max(scores):.1f}]  "
          f"mean={np.mean(scores):.1f}  median={np.median(scores):.1f}")

    # ── Step 2: Fetch prices ──────────────────────────────────────────────────
    print("\nStep 2/4: Fetching prices...")
    tickers = sorted(set(s.ticker for s in signals))
    min_year = min(s.fiscal_year for s in signals)
    pf = PriceFetcher(cache_dir=args.cache_dir)
    all_prices = pf.get_prices_batch(
        list(set(tickers + ["SPY"])),
        f"{min_year}-01-01",
        f"{args.max_year + 7}-01-01",
    )
    bench = all_prices.pop("SPY", None)
    if bench is None:
        print("ERROR: No SPY data.")
        sys.exit(1)
    print(f"  Prices for {len(all_prices)}/{len(tickers)} tickers + SPY")

    # ── Step 3: Build portfolios and compute trades ───────────────────────────
    print("\nStep 3/4: Computing spread trades...")

    # Define portfolio groupings
    # Each entry: (name, description, long_filter_fn, short_filter_fn)
    portfolios_def = [
        (
            "1. ALL BUY vs ALL SELL",
            "Broadest: every BUY/STRONG BUY long, every SELL/STRONG SELL short",
            lambda s: s.action in ("BUY", "STRONG BUY"),
            lambda s: s.action in ("SELL", "STRONG SELL"),
        ),
        (
            "2. HIGH CONVICTION BUY vs HIGH CONVICTION SELL",
            "Only signals where final verdict conviction = High",
            lambda s: s.action in ("BUY", "STRONG BUY") and s.conviction == "High",
            lambda s: s.action in ("SELL", "STRONG SELL") and s.conviction == "High",
        ),
        (
            "3. STRONG BUY vs STRONG SELL",
            "Tightest: only the AI's most extreme calls",
            lambda s: s.action == "STRONG BUY",
            lambda s: s.action == "STRONG SELL",
        ),
        (
            "4. BUY + Wide Moat vs SELL + Fragile",
            "Quality filter: long quality BUYs, short fragile SELLs",
            lambda s: s.action in ("BUY", "STRONG BUY") and s.moat_rating == "Wide",
            lambda s: s.action in ("SELL", "STRONG SELL") and s.antifragile_rating == "Fragile",
        ),
        (
            "5. BUY + Robust/Antifragile vs SELL + Fragile",
            "Taleb filter: long resilient BUYs, short fragile SELLs",
            lambda s: s.action in ("BUY", "STRONG BUY") and s.antifragile_rating in ("Robust", "Antifragile"),
            lambda s: s.action in ("SELL", "STRONG SELL") and s.antifragile_rating == "Fragile",
        ),
        (
            "6. Top Quintile vs Bottom Quintile (composite score)",
            "Quintile spread: top 20% by composite score vs bottom 20%",
            None,  # filled dynamically below
            None,
        ),
    ]

    # Compute quintile thresholds for portfolio 6
    sorted_scores = sorted(scores)
    q20 = sorted_scores[int(len(sorted_scores) * 0.20)]
    q80 = sorted_scores[int(len(sorted_scores) * 0.80)]
    portfolios_def[5] = (
        f"6. Top Quintile (score>={q80:.1f}) vs Bottom Quintile (score<={q20:.1f})",
        f"Composite score quintiles: top 20% (>={q80:.1f}) vs bottom 20% (<={q20:.1f})",
        lambda s, t=q80: s.composite_score >= t,
        lambda s, t=q20: s.composite_score <= t,
    )

    all_trades: List[SpreadTrade] = []
    portfolio_results: List[Tuple[str, str, int, int, Dict[int, SpreadPeriodMetrics]]] = []
    portfolio_metrics_for_export: List[Tuple[str, Dict[int, SpreadPeriodMetrics]]] = []

    # Also track by vintage for the first two portfolios
    vintage_portfolios = {}

    for pname, pdesc, long_fn, short_fn in portfolios_def:
        long_sigs = [s for s in signals if long_fn(s)]
        short_sigs = [s for s in signals if short_fn(s)]

        long_trades = []
        for sig in long_sigs:
            if sig.ticker not in all_prices:
                continue
            t = compute_spread_trade(sig, all_prices[sig.ticker], bench, holding_periods, "long", pname)
            if t:
                long_trades.append(t)
                all_trades.append(t)

        short_trades = []
        for sig in short_sigs:
            if sig.ticker not in all_prices:
                continue
            t = compute_spread_trade(sig, all_prices[sig.ticker], bench, holding_periods, "short", pname)
            if t:
                short_trades.append(t)
                all_trades.append(t)

        mets = compute_spread_metrics(long_trades, short_trades, holding_periods, use_clustered_se=args.clustered)
        portfolio_results.append((pname, pdesc, len(long_trades), len(short_trades), mets))
        portfolio_metrics_for_export.append((pname, mets))

        n_long_tickers = len(set(t.ticker for t in long_trades))
        n_short_tickers = len(set(t.ticker for t in short_trades))
        print(f"  {pname}: long={len(long_trades)} ({n_long_tickers} tickers), short={len(short_trades)} ({n_short_tickers} tickers)")

        # Vintage breakdown for first 3 portfolios
        if pname.startswith(("1.", "2.", "3.")):
            fy_long = defaultdict(list)
            for t in long_trades:
                fy_long[t.fiscal_year].append(t)
            fy_short = defaultdict(list)
            for t in short_trades:
                fy_short[t.fiscal_year].append(t)
            all_fys = sorted(set(list(fy_long.keys()) + list(fy_short.keys())))
            vintage_mets = {}
            for fy in all_fys:
                vintage_mets[fy] = compute_spread_metrics(
                    fy_long.get(fy, []), fy_short.get(fy, []), holding_periods,
                    use_clustered_se=args.clustered,
                )
            vintage_portfolios[pname] = vintage_mets

    # ── Step 4: Reports ───────────────────────────────────────────────────────
    print("\nStep 4/4: Generating reports...\n")

    print("=" * 90)
    print("  SPREAD BACKTEST RESULTS")
    print("=" * 90)

    for pname, pdesc, nl, ns, mets in portfolio_results:
        print_portfolio_report(pname, pdesc, nl, ns, mets, holding_periods)

    # Summary verdict
    print("\n" + "=" * 90)
    print("  SPREAD ALPHA SUMMARY")
    print("=" * 90)

    for pname, pdesc, nl, ns, mets in portfolio_results:
        print(f"\n  {pname}")
        for period in holding_periods:
            pm = mets.get(period)
            if pm:
                print(print_verdict_line(pm, period))

    # Vintage breakdowns
    for pname, vmets in vintage_portfolios.items():
        print_vintage_report(pname, vmets, holding_periods)

    # Export
    if not args.no_export:
        print(f"\nExporting to {args.output}/")
        export_spread_trades(all_trades, holding_periods, args.output / "spread_trades.csv")
        export_spread_metrics(portfolio_metrics_for_export, holding_periods, args.output / "spread_metrics.csv")

    print("\nSpread backtest complete.")


if __name__ == "__main__":
    main()
