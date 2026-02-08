"""
Backtesting metrics calculation.

Computes alpha, Sharpe ratio, win rates, and other performance metrics
for signal-based trading strategies.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional

TRADING_DAYS_PER_YEAR = 252


@dataclass
class TradeResult:
    """Result of a single trade triggered by a signal."""

    ticker: str
    fiscal_year: int
    signal_strength: str  # e.g. "all_priority", "majority_priority"
    priority_count: int
    entry_date: str
    entry_price: float

    # Forward returns at various holding periods (trading days)
    returns: Dict[int, Optional[float]] = field(default_factory=dict)
    # Benchmark (SPY) returns for same periods
    bench_returns: Dict[int, Optional[float]] = field(default_factory=dict)
    # Excess returns (stock - benchmark)
    excess_returns: Dict[int, Optional[float]] = field(default_factory=dict)

    # Perspective details
    buffett_signal: str = ""
    buffett_verdict: str = ""
    taleb_signal: str = ""
    taleb_verdict: str = ""
    contrarian_signal: str = ""
    contrarian_verdict: str = ""
    contrarian_conviction: str = ""


@dataclass
class BacktestMetrics:
    """Aggregate performance metrics for a set of trades."""

    label: str  # e.g. "ALL_PRIORITY", "MAJORITY_PRIORITY"
    n_trades: int

    # Per holding period metrics
    period_metrics: Dict[int, "PeriodMetrics"] = field(default_factory=dict)

    # Overall
    avg_priority_count: float = 0.0


@dataclass
class PeriodMetrics:
    """Metrics for a specific holding period."""

    holding_days: int
    n_trades: int  # Trades with data for this period

    # Return stats
    mean_return: float = 0.0
    median_return: float = 0.0
    mean_bench_return: float = 0.0
    mean_excess_return: float = 0.0
    median_excess_return: float = 0.0

    # Hit rates
    win_rate: float = 0.0  # % of trades with positive return
    beat_benchmark_rate: float = 0.0  # % of trades that beat SPY

    # Risk metrics
    return_std: float = 0.0
    excess_return_std: float = 0.0
    max_return: float = 0.0
    min_return: float = 0.0
    max_excess: float = 0.0
    min_excess: float = 0.0

    # Risk-adjusted
    sharpe_ratio: float = 0.0  # Annualized
    information_ratio: float = 0.0

    # Statistical significance
    t_statistic: float = 0.0
    p_value: float = 1.0


def compute_trade_returns(
    trade: TradeResult,
    stock_prices: pd.DataFrame,
    bench_prices: pd.DataFrame,
    holding_periods: List[int],
) -> TradeResult:
    """
    Compute forward returns for a trade at various holding periods.

    Entry is at close on the first trading day on or after signal_date.
    This avoids look-ahead bias - the signal is known, we enter next day.

    Args:
        trade: TradeResult with entry_date set.
        stock_prices: DataFrame with 'Close' column for the stock.
        bench_prices: DataFrame with 'Close' column for SPY.
        holding_periods: List of holding periods in trading days.

    Returns:
        Updated TradeResult with returns filled in.
    """
    entry_date = pd.Timestamp(trade.entry_date)

    stock_close = stock_prices["Close"]
    bench_close = bench_prices["Close"]

    # Find entry index in stock prices
    stock_dates = stock_close.index
    valid_entry = stock_dates[stock_dates >= entry_date]
    if len(valid_entry) == 0:
        return trade

    actual_entry = valid_entry[0]
    entry_price = stock_close.loc[actual_entry]
    trade.entry_price = entry_price
    trade.entry_date = actual_entry.strftime("%Y-%m-%d")

    # Benchmark entry
    bench_dates = bench_close.index
    valid_bench_entry = bench_dates[bench_dates >= entry_date]
    if len(valid_bench_entry) == 0:
        return trade
    bench_entry = valid_bench_entry[0]
    bench_entry_price = bench_close.loc[bench_entry]

    for period in holding_periods:
        # Stock exit
        entry_idx = stock_dates.get_loc(actual_entry)
        exit_idx = entry_idx + period
        if exit_idx >= len(stock_dates):
            trade.returns[period] = None
            trade.bench_returns[period] = None
            trade.excess_returns[period] = None
            continue

        exit_price = stock_close.iloc[exit_idx]
        stock_return = (exit_price / entry_price) - 1.0

        # Benchmark exit
        bench_entry_idx = bench_dates.get_loc(bench_entry)
        bench_exit_idx = bench_entry_idx + period
        if bench_exit_idx >= len(bench_dates):
            trade.returns[period] = stock_return
            trade.bench_returns[period] = None
            trade.excess_returns[period] = None
            continue

        bench_exit_price = bench_close.iloc[bench_exit_idx]
        bench_return = (bench_exit_price / bench_entry_price) - 1.0
        excess = stock_return - bench_return

        trade.returns[period] = stock_return
        trade.bench_returns[period] = bench_return
        trade.excess_returns[period] = excess

    return trade


def compute_backtest_metrics(
    trades: List[TradeResult],
    holding_periods: List[int],
    label: str = "",
    risk_free_rate: float = 0.05,
) -> BacktestMetrics:
    """
    Compute aggregate metrics across all trades.

    Args:
        trades: List of completed TradeResult objects.
        holding_periods: Holding periods to compute metrics for.
        label: Label for this group (e.g. "ALL_PRIORITY").
        risk_free_rate: Annual risk-free rate for Sharpe calculation.

    Returns:
        BacktestMetrics with per-period statistics.
    """
    from scipy import stats as scipy_stats

    metrics = BacktestMetrics(
        label=label,
        n_trades=len(trades),
        avg_priority_count=np.mean([t.priority_count for t in trades]) if trades else 0,
    )

    for period in holding_periods:
        # Collect returns for this period
        stock_rets = []
        bench_rets = []
        excess_rets = []

        for trade in trades:
            sr = trade.returns.get(period)
            br = trade.bench_returns.get(period)
            er = trade.excess_returns.get(period)

            if sr is not None:
                stock_rets.append(sr)
            if br is not None:
                bench_rets.append(br)
            if er is not None:
                excess_rets.append(er)

        n = len(stock_rets)
        if n == 0:
            metrics.period_metrics[period] = PeriodMetrics(
                holding_days=period, n_trades=0
            )
            continue

        stock_arr = np.array(stock_rets)
        excess_arr = np.array(excess_rets) if excess_rets else np.array([0.0])
        bench_arr = np.array(bench_rets) if bench_rets else np.array([0.0])

        # Annualization factor for this holding period
        ann_factor = TRADING_DAYS_PER_YEAR / period

        # Sharpe ratio (annualized)
        period_rf = (1 + risk_free_rate) ** (period / TRADING_DAYS_PER_YEAR) - 1
        excess_of_rf = stock_arr - period_rf
        sharpe = 0.0
        if excess_of_rf.std() > 0:
            sharpe = (excess_of_rf.mean() / excess_of_rf.std()) * np.sqrt(ann_factor)

        # Information ratio
        info_ratio = 0.0
        if len(excess_rets) > 1 and excess_arr.std() > 0:
            info_ratio = (excess_arr.mean() / excess_arr.std()) * np.sqrt(ann_factor)

        # T-test: is mean excess return significantly different from 0?
        t_stat, p_val = 0.0, 1.0
        if len(excess_rets) >= 3:
            t_stat, p_val = scipy_stats.ttest_1samp(excess_arr, 0)

        pm = PeriodMetrics(
            holding_days=period,
            n_trades=n,
            mean_return=float(stock_arr.mean()),
            median_return=float(np.median(stock_arr)),
            mean_bench_return=float(bench_arr.mean()) if bench_rets else 0.0,
            mean_excess_return=float(excess_arr.mean()) if excess_rets else 0.0,
            median_excess_return=float(np.median(excess_arr)) if excess_rets else 0.0,
            win_rate=float((stock_arr > 0).mean()),
            beat_benchmark_rate=float((excess_arr > 0).mean()) if excess_rets else 0.0,
            return_std=float(stock_arr.std()),
            excess_return_std=float(excess_arr.std()) if excess_rets else 0.0,
            max_return=float(stock_arr.max()),
            min_return=float(stock_arr.min()),
            max_excess=float(excess_arr.max()) if excess_rets else 0.0,
            min_excess=float(excess_arr.min()) if excess_rets else 0.0,
            sharpe_ratio=float(sharpe),
            information_ratio=float(info_ratio),
            t_statistic=float(t_stat),
            p_value=float(p_val),
        )

        metrics.period_metrics[period] = pm

    return metrics
