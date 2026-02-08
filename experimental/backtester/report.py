"""
Report generation for backtesting results.

Outputs results as formatted console tables and CSV exports.
"""

import csv
import logging
from pathlib import Path
from typing import Dict, List, Optional

from .metrics import BacktestMetrics, PeriodMetrics, TradeResult

logger = logging.getLogger(__name__)


def _period_label(days: int) -> str:
    """Human-readable label for a holding period in trading days."""
    mapping = {5: "1W", 21: "1M", 63: "3M", 126: "6M", 252: "12M"}
    return mapping.get(days, f"{days}d")


def print_signal_summary(
    total_signals: int,
    strength_counts: Dict[str, int],
) -> None:
    """Print summary of extracted signals."""
    print("\n" + "=" * 70)
    print("SIGNAL EXTRACTION SUMMARY")
    print("=" * 70)
    print(f"Total analysis results loaded: {total_signals}")
    print()
    for strength, count in sorted(strength_counts.items(), key=lambda x: -x[1]):
        pct = (count / total_signals * 100) if total_signals > 0 else 0
        print(f"  {strength:25s}  {count:5d}  ({pct:5.1f}%)")
    print()


def print_backtest_report(
    metrics_by_group: Dict[str, BacktestMetrics],
    holding_periods: List[int],
) -> None:
    """
    Print a formatted backtest report to console.

    Shows performance metrics for each signal strength group
    across all holding periods.
    """
    print("\n" + "=" * 70)
    print("BACKTESTING RESULTS")
    print("=" * 70)

    for group_label, metrics in metrics_by_group.items():
        print(f"\n{'─' * 70}")
        print(f"Signal Group: {group_label}")
        print(f"Total Trades: {metrics.n_trades}")
        print(f"Avg Priority Count: {metrics.avg_priority_count:.1f}")
        print(f"{'─' * 70}")

        if metrics.n_trades == 0:
            print("  No trades in this group.\n")
            continue

        # Header
        periods = [p for p in holding_periods if p in metrics.period_metrics]
        header = f"{'Metric':30s}"
        for p in periods:
            header += f"  {_period_label(p):>8s}"
        print(header)
        print("-" * (30 + 10 * len(periods)))

        # Rows
        rows = [
            ("Trades with Data", lambda pm: f"{pm.n_trades:>8d}"),
            ("Mean Return", lambda pm: f"{pm.mean_return:>7.1%}"),
            ("Median Return", lambda pm: f"{pm.median_return:>7.1%}"),
            ("Mean Benchmark Return", lambda pm: f"{pm.mean_bench_return:>7.1%}"),
            ("Mean Excess Return", lambda pm: f"{pm.mean_excess_return:>7.1%}"),
            ("Median Excess Return", lambda pm: f"{pm.median_excess_return:>7.1%}"),
            ("", None),  # separator
            ("Win Rate (>0%)", lambda pm: f"{pm.win_rate:>7.1%}"),
            ("Beat SPY Rate", lambda pm: f"{pm.beat_benchmark_rate:>7.1%}"),
            ("", None),
            ("Return Std Dev", lambda pm: f"{pm.return_std:>7.1%}"),
            ("Max Return", lambda pm: f"{pm.max_return:>7.1%}"),
            ("Min Return", lambda pm: f"{pm.min_return:>7.1%}"),
            ("Max Excess", lambda pm: f"{pm.max_excess:>7.1%}"),
            ("Min Excess", lambda pm: f"{pm.min_excess:>7.1%}"),
            ("", None),
            ("Sharpe Ratio (ann.)", lambda pm: f"{pm.sharpe_ratio:>8.2f}"),
            ("Information Ratio", lambda pm: f"{pm.information_ratio:>8.2f}"),
            ("", None),
            ("t-statistic", lambda pm: f"{pm.t_statistic:>8.2f}"),
            ("p-value", lambda pm: f"{pm.p_value:>8.4f}"),
            (
                "Significant (p<0.05)",
                lambda pm: f"{'YES':>8s}" if pm.p_value < 0.05 else f"{'no':>8s}",
            ),
        ]

        for label, fmt_fn in rows:
            if fmt_fn is None:
                print()
                continue
            line = f"{label:30s}"
            for p in periods:
                pm = metrics.period_metrics.get(p)
                if pm and pm.n_trades > 0:
                    line += f"  {fmt_fn(pm)}"
                else:
                    line += f"  {'N/A':>8s}"
            print(line)

    # Alpha verdict
    print("\n" + "=" * 70)
    print("ALPHA VERDICT")
    print("=" * 70)
    _print_alpha_verdict(metrics_by_group, holding_periods)


def _print_alpha_verdict(
    metrics_by_group: Dict[str, BacktestMetrics],
    holding_periods: List[int],
) -> None:
    """Print a plain-language summary of whether signals generate alpha."""
    for group_label, metrics in metrics_by_group.items():
        if metrics.n_trades == 0:
            continue

        print(f"\n{group_label}:")

        for period in holding_periods:
            pm = metrics.period_metrics.get(period)
            if not pm or pm.n_trades < 3:
                continue

            plabel = _period_label(period)
            excess = pm.mean_excess_return
            sig = "SIGNIFICANT" if pm.p_value < 0.05 else "not significant"
            beat = pm.beat_benchmark_rate

            if pm.p_value < 0.05 and excess > 0:
                verdict = f"TRUE ALPHA ({excess:+.1%} excess, p={pm.p_value:.3f})"
            elif excess > 0 and beat > 0.5:
                verdict = f"Positive but {sig} ({excess:+.1%} excess, p={pm.p_value:.3f})"
            elif excess > 0:
                verdict = f"Weak positive ({excess:+.1%} excess, beat rate {beat:.0%})"
            else:
                verdict = f"NO ALPHA ({excess:+.1%} excess, beat rate {beat:.0%})"

            print(f"  {plabel:>4s}: {verdict}")


def export_trades_to_csv(
    trades: List[TradeResult],
    holding_periods: List[int],
    output_path: Path,
) -> None:
    """Export individual trade results to CSV."""
    fieldnames = [
        "ticker",
        "fiscal_year",
        "signal_strength",
        "priority_count",
        "entry_date",
        "entry_price",
        "buffett_signal",
        "buffett_verdict",
        "taleb_signal",
        "taleb_verdict",
        "contrarian_signal",
        "contrarian_verdict",
        "contrarian_conviction",
    ]

    # Add columns for each holding period
    for p in holding_periods:
        pl = _period_label(p)
        fieldnames.extend([
            f"return_{pl}",
            f"bench_return_{pl}",
            f"excess_return_{pl}",
        ])

    rows = []
    for trade in trades:
        row = {
            "ticker": trade.ticker,
            "fiscal_year": trade.fiscal_year,
            "signal_strength": trade.signal_strength,
            "priority_count": trade.priority_count,
            "entry_date": trade.entry_date,
            "entry_price": f"{trade.entry_price:.2f}" if trade.entry_price else "",
            "buffett_signal": trade.buffett_signal,
            "buffett_verdict": trade.buffett_verdict,
            "taleb_signal": trade.taleb_signal,
            "taleb_verdict": trade.taleb_verdict,
            "contrarian_signal": trade.contrarian_signal,
            "contrarian_verdict": trade.contrarian_verdict,
            "contrarian_conviction": trade.contrarian_conviction,
        }

        for p in holding_periods:
            pl = _period_label(p)
            ret = trade.returns.get(p)
            bench = trade.bench_returns.get(p)
            excess = trade.excess_returns.get(p)
            row[f"return_{pl}"] = f"{ret:.4f}" if ret is not None else ""
            row[f"bench_return_{pl}"] = f"{bench:.4f}" if bench is not None else ""
            row[f"excess_return_{pl}"] = f"{excess:.4f}" if excess is not None else ""

        rows.append(row)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"Exported {len(rows)} trades to {output_path}")
    print(f"\nTrade details exported to: {output_path}")


def export_metrics_to_csv(
    metrics_by_group: Dict[str, BacktestMetrics],
    holding_periods: List[int],
    output_path: Path,
) -> None:
    """Export aggregate metrics to CSV."""
    fieldnames = [
        "group",
        "n_trades",
        "avg_priority_count",
        "holding_period",
        "n_trades_with_data",
        "mean_return",
        "median_return",
        "mean_bench_return",
        "mean_excess_return",
        "median_excess_return",
        "win_rate",
        "beat_benchmark_rate",
        "return_std",
        "sharpe_ratio",
        "information_ratio",
        "t_statistic",
        "p_value",
        "significant",
    ]

    rows = []
    for group_label, metrics in metrics_by_group.items():
        for period in holding_periods:
            pm = metrics.period_metrics.get(period)
            if not pm:
                continue

            rows.append({
                "group": group_label,
                "n_trades": metrics.n_trades,
                "avg_priority_count": f"{metrics.avg_priority_count:.1f}",
                "holding_period": _period_label(period),
                "n_trades_with_data": pm.n_trades,
                "mean_return": f"{pm.mean_return:.4f}",
                "median_return": f"{pm.median_return:.4f}",
                "mean_bench_return": f"{pm.mean_bench_return:.4f}",
                "mean_excess_return": f"{pm.mean_excess_return:.4f}",
                "median_excess_return": f"{pm.median_excess_return:.4f}",
                "win_rate": f"{pm.win_rate:.4f}",
                "beat_benchmark_rate": f"{pm.beat_benchmark_rate:.4f}",
                "return_std": f"{pm.return_std:.4f}",
                "sharpe_ratio": f"{pm.sharpe_ratio:.4f}",
                "information_ratio": f"{pm.information_ratio:.4f}",
                "t_statistic": f"{pm.t_statistic:.4f}",
                "p_value": f"{pm.p_value:.4f}",
                "significant": "YES" if pm.p_value < 0.05 else "no",
            })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"Exported metrics to {output_path}")
    print(f"Metrics summary exported to: {output_path}")
