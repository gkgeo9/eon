"""
Monthly Seasonality Detector & Backtest

For every stock in the price cache (2020-2024):
  1. Compute monthly returns for each January, February, ... December
  2. Detect "seasonal tendencies" - months that are consistently +/- across years
  3. Build a simple trading algo: go long on historically positive months, short on negative
  4. Backtest on 2025 and measure accuracy

Usage:
    python -m experimental.backtester.monthly_seasonality
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from rich.console import Console
from rich.table import Table

console = Console()

CACHE_DIR = Path("data/price_cache")
TRAIN_START = "2020-01-01"
TRAIN_END = "2024-12-31"
TEST_START = "2025-01-01"
TEST_END = "2025-12-31"

# Minimum years a month must show the same sign to count as a "pattern"
MIN_CONSISTENT_YEARS = 4  # out of 5 (2020-2024)


def load_all_prices() -> dict[str, pd.DataFrame]:
    """Load all cached parquet price data."""
    prices = {}
    parquet_files = sorted(CACHE_DIR.glob("*_daily.parquet"))
    console.print(f"[cyan]Found {len(parquet_files)} cached price files[/cyan]")

    for path in parquet_files:
        ticker = path.stem.replace("_daily", "")
        if ticker == "SPY":
            continue  # skip benchmark
        try:
            df = pd.read_parquet(path)
            df.index = pd.to_datetime(df.index).tz_localize(None)
            if len(df) > 100:  # need enough data
                prices[ticker] = df
        except Exception:
            pass

    console.print(f"[green]Loaded {len(prices)} tickers with sufficient data[/green]")
    return prices


def compute_monthly_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Compute monthly returns from daily close prices.

    Returns DataFrame with columns [year, month, monthly_return].
    """
    monthly = df["Close"].resample("ME").last()
    rets = monthly.pct_change().dropna()
    result = pd.DataFrame(
        {
            "year": rets.index.year,
            "month": rets.index.month,
            "monthly_return": rets.values,
        }
    )
    return result


def detect_seasonal_patterns(
    monthly_rets: pd.DataFrame,
) -> dict[int, dict]:
    """Find months with consistent directional bias across training years.

    Returns dict: month -> {direction: +1/-1, years_positive, years_negative,
                            avg_return, consistency}
    """
    train = monthly_rets[
        (monthly_rets["year"] >= 2020) & (monthly_rets["year"] <= 2024)
    ]

    patterns = {}
    for month in range(1, 13):
        month_data = train[train["month"] == month]
        if len(month_data) < 3:
            continue

        pos_count = (month_data["monthly_return"] > 0).sum()
        neg_count = (month_data["monthly_return"] <= 0).sum()
        total = len(month_data)
        avg_ret = month_data["monthly_return"].mean()

        if pos_count >= MIN_CONSISTENT_YEARS:
            patterns[month] = {
                "direction": 1,
                "years_positive": int(pos_count),
                "years_negative": int(neg_count),
                "total_years": total,
                "avg_return": avg_ret,
                "consistency": pos_count / total,
            }
        elif neg_count >= MIN_CONSISTENT_YEARS:
            patterns[month] = {
                "direction": -1,
                "years_positive": int(pos_count),
                "years_negative": int(neg_count),
                "total_years": total,
                "avg_return": avg_ret,
                "consistency": neg_count / total,
            }

    return patterns


def backtest_2025(
    ticker: str,
    df: pd.DataFrame,
    patterns: dict[int, dict],
) -> list[dict]:
    """Backtest seasonal patterns on 2025 data.

    For each month with a pattern, check if 2025 followed the prediction.
    """
    monthly = df["Close"].resample("ME").last()
    rets = monthly.pct_change().dropna()
    test = rets[(rets.index.year == 2025)]

    trades = []
    for idx, ret in test.items():
        month = idx.month
        if month not in patterns:
            continue

        pat = patterns[month]
        predicted_dir = pat["direction"]
        actual_dir = 1 if ret > 0 else -1
        correct = predicted_dir == actual_dir

        # P&L: if we go long on predicted +, short on predicted -, our return is:
        pnl = predicted_dir * ret

        trades.append(
            {
                "ticker": ticker,
                "month": month,
                "month_name": pd.Timestamp(2025, month, 1).strftime("%b"),
                "predicted": "LONG" if predicted_dir == 1 else "SHORT",
                "actual_return": ret,
                "correct": correct,
                "pnl": pnl,
                "consistency": pat["consistency"],
                "train_avg": pat["avg_return"],
            }
        )

    return trades


def main():
    console.print("\n[bold magenta]═══ Monthly Seasonality Detector & Backtest ═══[/bold magenta]\n")
    console.print(f"Training period: {TRAIN_START} → {TRAIN_END}")
    console.print(f"Test period:     {TEST_START} → {TEST_END}")
    console.print(f"Min consistency: {MIN_CONSISTENT_YEARS}/5 years same direction\n")

    # 1. Load all prices
    prices = load_all_prices()

    # 2. Detect patterns for each ticker
    all_patterns = {}  # ticker -> {month -> pattern}
    pattern_counts = {m: {"long": 0, "short": 0} for m in range(1, 13)}

    for ticker, df in prices.items():
        monthly_rets = compute_monthly_returns(df)
        patterns = detect_seasonal_patterns(monthly_rets)
        if patterns:
            all_patterns[ticker] = patterns
            for month, pat in patterns.items():
                if pat["direction"] == 1:
                    pattern_counts[month]["long"] += 1
                else:
                    pattern_counts[month]["short"] += 1

    console.print(f"\n[green]Tickers with at least 1 seasonal pattern: "
                  f"{len(all_patterns)}/{len(prices)}[/green]\n")

    # Show pattern distribution by month
    table = Table(title="Seasonal Pattern Distribution (2020-2024 Training)")
    table.add_column("Month", style="cyan")
    table.add_column("# Bullish", justify="right", style="green")
    table.add_column("# Bearish", justify="right", style="red")
    table.add_column("Total", justify="right", style="yellow")

    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    for m in range(1, 13):
        bull = pattern_counts[m]["long"]
        bear = pattern_counts[m]["short"]
        table.add_row(month_names[m - 1], str(bull), str(bear), str(bull + bear))
    console.print(table)

    # 3. Backtest on 2025
    console.print("\n[bold cyan]═══ Backtesting on 2025 ═══[/bold cyan]\n")

    all_trades = []
    for ticker, patterns in all_patterns.items():
        df = prices[ticker]
        trades = backtest_2025(ticker, df, patterns)
        all_trades.extend(trades)

    if not all_trades:
        console.print("[red]No trades generated for 2025![/red]")
        return

    trades_df = pd.DataFrame(all_trades)

    # Overall accuracy
    total = len(trades_df)
    correct = trades_df["correct"].sum()
    accuracy = correct / total * 100

    console.print(f"Total trades: [bold]{total}[/bold]")
    console.print(f"Correct predictions: [bold green]{correct}[/bold green]")
    console.print(f"Overall accuracy: [bold yellow]{accuracy:.1f}%[/bold yellow]")
    console.print(f"Average P&L per trade: [bold]{trades_df['pnl'].mean() * 100:.2f}%[/bold]")
    console.print(f"Total cumulative P&L: [bold]{trades_df['pnl'].sum() * 100:.1f}%[/bold]\n")

    # Accuracy by month
    table2 = Table(title="2025 Backtest Results by Month")
    table2.add_column("Month", style="cyan")
    table2.add_column("# Trades", justify="right")
    table2.add_column("# Correct", justify="right", style="green")
    table2.add_column("Accuracy", justify="right", style="yellow")
    table2.add_column("Avg P&L", justify="right")
    table2.add_column("Avg |Return|", justify="right")

    for m in range(1, 13):
        month_trades = trades_df[trades_df["month"] == m]
        if month_trades.empty:
            continue
        n = len(month_trades)
        c = month_trades["correct"].sum()
        acc = c / n * 100
        avg_pnl = month_trades["pnl"].mean() * 100
        avg_abs = month_trades["actual_return"].abs().mean() * 100

        pnl_style = "green" if avg_pnl > 0 else "red"
        table2.add_row(
            month_names[m - 1],
            str(n),
            str(int(c)),
            f"{acc:.1f}%",
            f"[{pnl_style}]{avg_pnl:+.2f}%[/{pnl_style}]",
            f"{avg_abs:.2f}%",
        )

    console.print(table2)

    # Accuracy by consistency level
    console.print()
    table3 = Table(title="Accuracy by Pattern Strength")
    table3.add_column("Consistency", style="cyan")
    table3.add_column("# Trades", justify="right")
    table3.add_column("Accuracy", justify="right", style="yellow")
    table3.add_column("Avg P&L", justify="right")

    for label, lo, hi in [
        ("Perfect (5/5)", 0.99, 1.01),
        ("Strong (4/5)", 0.79, 0.81),
    ]:
        subset = trades_df[
            (trades_df["consistency"] >= lo) & (trades_df["consistency"] <= hi)
        ]
        if subset.empty:
            continue
        n = len(subset)
        acc = subset["correct"].mean() * 100
        avg_pnl = subset["pnl"].mean() * 100
        pnl_style = "green" if avg_pnl > 0 else "red"
        table3.add_row(
            label,
            str(n),
            f"{acc:.1f}%",
            f"[{pnl_style}]{avg_pnl:+.2f}%[/{pnl_style}]",
        )

    console.print(table3)

    # Top 20 most profitable seasonal trades
    console.print()
    top_trades = trades_df.nlargest(20, "pnl")
    table4 = Table(title="Top 20 Most Profitable Seasonal Trades (2025)")
    table4.add_column("Ticker", style="cyan")
    table4.add_column("Month", style="white")
    table4.add_column("Signal", style="yellow")
    table4.add_column("Consistency", justify="right")
    table4.add_column("Actual Return", justify="right")
    table4.add_column("P&L", justify="right", style="green")

    for _, row in top_trades.iterrows():
        table4.add_row(
            row["ticker"],
            row["month_name"],
            row["predicted"],
            f"{row['consistency']:.0%}",
            f"{row['actual_return'] * 100:+.1f}%",
            f"{row['pnl'] * 100:+.1f}%",
        )
    console.print(table4)

    # Worst 20
    console.print()
    worst_trades = trades_df.nsmallest(20, "pnl")
    table5 = Table(title="Top 20 Worst Seasonal Trades (2025)")
    table5.add_column("Ticker", style="cyan")
    table5.add_column("Month", style="white")
    table5.add_column("Signal", style="yellow")
    table5.add_column("Consistency", justify="right")
    table5.add_column("Actual Return", justify="right")
    table5.add_column("P&L", justify="right", style="red")

    for _, row in worst_trades.iterrows():
        pnl_pct = row["pnl"] * 100
        table5.add_row(
            row["ticker"],
            row["month_name"],
            row["predicted"],
            f"{row['consistency']:.0%}",
            f"{row['actual_return'] * 100:+.1f}%",
            f"{pnl_pct:+.1f}%",
        )
    console.print(table5)

    # Long vs Short breakdown
    console.print()
    for side in ["LONG", "SHORT"]:
        subset = trades_df[trades_df["predicted"] == side]
        if subset.empty:
            continue
        acc = subset["correct"].mean() * 100
        avg_pnl = subset["pnl"].mean() * 100
        pnl_style = "green" if avg_pnl > 0 else "red"
        console.print(
            f"  {side:5s} trades: {len(subset):>5} | "
            f"Accuracy: {acc:.1f}% | "
            f"Avg P&L: [{pnl_style}]{avg_pnl:+.2f}%[/{pnl_style}]"
        )

    # Quick equity curve: cumulative P&L month by month
    console.print("\n[bold]Cumulative P&L by month (equal-weight all trades):[/bold]")
    cum = 0.0
    for m in range(1, 13):
        month_trades = trades_df[trades_df["month"] == m]
        if month_trades.empty:
            continue
        month_pnl = month_trades["pnl"].mean() * 100
        cum += month_pnl
        bar = "█" * max(1, int(abs(cum) / 0.5))
        color = "green" if cum >= 0 else "red"
        console.print(f"  {month_names[m-1]:>3}: [{color}]{cum:+.2f}% {bar}[/{color}]")

    # Export
    out_path = Path("experimental/backtester/seasonality_trades_2025.csv")
    trades_df.to_csv(out_path, index=False)
    console.print(f"\n[dim]Trades exported to {out_path}[/dim]")

    console.print("\n[bold magenta]═══ Done ═══[/bold magenta]\n")


if __name__ == "__main__":
    main()
