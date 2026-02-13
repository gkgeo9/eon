#!/usr/bin/env python3
"""
Paper Trading Portfolio Tracker for HIGH CONVICTION Strategy

Tracks the Feb 13, 2026 portfolio based on FY2024 signals.
Run this periodically to monitor performance vs SPY benchmark.

Portfolio:
- 10 LONG positions (~$44K): SFIX, CELH, DOCN, PCOR, ABNB, TSLA, SNOW, NVDA, RUN, EME (doubled)
- 21 SHORT positions (~$44K): TDOC, RDFN, HQY, DASH, TDC, CVNA, NCLH, CCL, DAL, UAL,
                               GTLS, UBER, LYFT, CHWY, RVLV, BROS, NKLA, RIVN, SOFI,
                               UPST, AFRM

Expected outcomes per backtest:
- 3M: +4.6% alpha (p=0.035)
- 6M: +9.4% alpha (p=0.017)
- 1Y: +4.2% alpha (ns)
- 2Y: +25.5% alpha (p=0.004) ← strongest signal
"""

import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import pandas as pd
from pathlib import Path

# Portfolio positions (as executed Feb 13, 2026)
LONG_POSITIONS = {
    "SFIX": {"shares": 26, "entry_price": 173.50},
    "CELH": {"shares": 137, "entry_price": 32.88},
    "DOCN": {"shares": 84, "entry_price": 53.50},
    "PCOR": {"shares": 326, "entry_price": 13.80},
    "ABNB": {"shares": 28, "entry_price": 159.14},
    "TSLA": {"shares": 11, "entry_price": 405.88},
    "SNOW": {"shares": 33, "entry_price": 136.15},
    "NVDA": {"shares": 32, "entry_price": 139.44},
    "RUN": {"shares": 417, "entry_price": 10.76},
    "EME": {"shares": 10, "entry_price": 806.09},  # Doubled position
}

SHORT_POSITIONS = {
    "TDOC": {"shares": 512, "entry_price": 8.77},
    "RDFN": {"shares": 434, "entry_price": 10.35},
    "HQY": {"shares": 235, "entry_price": 19.10},
    "DASH": {"shares": 24, "entry_price": 186.66},
    "TDC": {"shares": 98, "entry_price": 45.83},
    "CVNA": {"shares": 19, "entry_price": 236.20},
    "NCLH": {"shares": 194, "entry_price": 23.14},
    "CCL": {"shares": 177, "entry_price": 25.35},
    "DAL": {"shares": 82, "entry_price": 54.71},
    "UAL": {"shares": 43, "entry_price": 104.37},
    "GTLS": {"shares": 81, "entry_price": 55.39},
    "UBER": {"shares": 66, "entry_price": 67.94},
    "LYFT": {"shares": 324, "entry_price": 13.84},
    "CHWY": {"shares": 155, "entry_price": 28.94},
    "RVLV": {"shares": 138, "entry_price": 32.51},
    "BROS": {"shares": 87, "entry_price": 51.56},
    "NKLA": {"shares": 727, "entry_price": 6.17},
    "RIVN": {"shares": 354, "entry_price": 12.67},
    "SOFI": {"shares": 313, "entry_price": 14.33},
    "UPST": {"shares": 63, "entry_price": 71.24},
    "AFRM": {"shares": 88, "entry_price": 50.98},
}

ENTRY_DATE = "2026-02-13"
BENCHMARK = "SPY"


def get_current_prices(tickers: List[str]) -> Dict[str, float]:
    """Fetch current prices for all tickers."""
    data = yf.download(tickers, period="1d", progress=False)
    if len(tickers) == 1:
        return {tickers[0]: data["Close"].iloc[-1]}
    return {ticker: data["Close"][ticker].iloc[-1] for ticker in tickers}


def calculate_position_pnl(
    positions: Dict[str, dict], current_prices: Dict[str, float], is_short: bool = False
) -> Tuple[float, float, pd.DataFrame]:
    """Calculate P&L for long or short positions."""
    results = []
    total_entry_value = 0.0
    total_current_value = 0.0

    for ticker, pos in positions.items():
        shares = pos["shares"]
        entry_price = pos["entry_price"]
        current_price = current_prices.get(ticker, entry_price)

        entry_value = shares * entry_price
        current_value = shares * current_price

        if is_short:
            # For shorts: profit when price goes down
            pnl = shares * (entry_price - current_price)
            pnl_pct = (entry_price - current_price) / entry_price
        else:
            # For longs: profit when price goes up
            pnl = shares * (current_price - entry_price)
            pnl_pct = (current_price - entry_price) / entry_price

        total_entry_value += entry_value
        total_current_value += current_value

        results.append(
            {
                "Ticker": ticker,
                "Shares": shares,
                "Entry": f"${entry_price:.2f}",
                "Current": f"${current_price:.2f}",
                "P&L": f"${pnl:,.2f}",
                "P&L %": f"{pnl_pct:.1%}",
                "Entry Value": f"${entry_value:,.2f}",
                "Current Value": f"${current_value:,.2f}",
            }
        )

    df = pd.DataFrame(results)
    return total_entry_value, total_current_value, df


def get_spy_return(start_date: str) -> float:
    """Get SPY return since entry date."""
    spy_data = yf.download(BENCHMARK, start=start_date, progress=False)
    if len(spy_data) < 2:
        return 0.0
    entry_price = spy_data["Close"].iloc[0]
    current_price = spy_data["Close"].iloc[-1]
    return (current_price - entry_price) / entry_price


def generate_report():
    """Generate portfolio performance report."""
    print("=" * 80)
    print("HIGH CONVICTION LONG/SHORT PORTFOLIO TRACKER")
    print(f"Entry Date: {ENTRY_DATE}")
    print(f"Report Date: {datetime.now().strftime('%Y-%m-%d')}")
    print("=" * 80)

    # Fetch current prices
    all_tickers = list(LONG_POSITIONS.keys()) + list(SHORT_POSITIONS.keys()) + [BENCHMARK]
    print("\nFetching current prices...")
    current_prices = get_current_prices(all_tickers)

    # Calculate long side
    long_entry, long_current, long_df = calculate_position_pnl(
        LONG_POSITIONS, current_prices, is_short=False
    )
    long_pnl = long_current - long_entry
    long_return = long_pnl / long_entry

    # Calculate short side
    short_entry, short_current, short_df = calculate_position_pnl(
        SHORT_POSITIONS, current_prices, is_short=True
    )
    short_pnl = short_entry - short_current  # Profit = entry value - current value
    short_return = short_pnl / short_entry

    # Portfolio total
    total_entry = long_entry + short_entry
    total_pnl = long_pnl + short_pnl
    total_return = total_pnl / total_entry

    # Benchmark
    spy_return = get_spy_return(ENTRY_DATE)
    alpha = total_return - spy_return

    # Days since entry
    entry_dt = datetime.strptime(ENTRY_DATE, "%Y-%m-%d")
    days_elapsed = (datetime.now() - entry_dt).days

    # Print summary
    print("\n" + "=" * 80)
    print("PORTFOLIO SUMMARY")
    print("=" * 80)
    print(f"\nDays Elapsed: {days_elapsed} ({days_elapsed / 30:.1f} months)")
    print(f"\nLONG SIDE ({len(LONG_POSITIONS)} positions):")
    print(f"  Entry Value:   ${long_entry:,.2f}")
    print(f"  Current Value: ${long_current:,.2f}")
    print(f"  P&L:           ${long_pnl:+,.2f}")
    print(f"  Return:        {long_return:+.2%}")

    print(f"\nSHORT SIDE ({len(SHORT_POSITIONS)} positions):")
    print(f"  Entry Value:   ${short_entry:,.2f}")
    print(f"  Current Value: ${short_current:,.2f}")
    print(f"  P&L:           ${short_pnl:+,.2f}")
    print(f"  Return:        {short_return:+.2%}")

    print(f"\nTOTAL PORTFOLIO:")
    print(f"  Entry Value:   ${total_entry:,.2f}")
    print(f"  P&L:           ${total_pnl:+,.2f}")
    print(f"  Return:        {total_return:+.2%}")

    print(f"\nBENCHMARK (SPY):")
    print(f"  Return:        {spy_return:+.2%}")

    print(f"\nALPHA (Portfolio - SPY):")
    print(f"  {alpha:+.2%}")

    # Expected alpha from backtest
    print("\n" + "=" * 80)
    print("EXPECTED ALPHA (from backtest)")
    print("=" * 80)
    if days_elapsed >= 730:
        print(f"2Y: +25.5% (p=0.004) ← TARGET HORIZON")
    elif days_elapsed >= 365:
        print(f"1Y: +4.2% (not significant)")
    elif days_elapsed >= 180:
        print(f"6M: +9.4% (p=0.017)")
    elif days_elapsed >= 90:
        print(f"3M: +4.6% (p=0.035)")
    else:
        print(f"1M: -0.3% (not significant)")
    print("\nNote: Strongest signal is at 2-year horizon (+25.5% alpha, p=0.004)")

    # Detailed position tables
    print("\n" + "=" * 80)
    print("LONG POSITIONS")
    print("=" * 80)
    print(long_df.to_string(index=False))

    print("\n" + "=" * 80)
    print("SHORT POSITIONS")
    print("=" * 80)
    print(short_df.to_string(index=False))

    # Save to CSV
    output_dir = Path("data/paper_trading")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d")
    long_df.to_csv(output_dir / f"long_positions_{timestamp}.csv", index=False)
    short_df.to_csv(output_dir / f"short_positions_{timestamp}.csv", index=False)

    # Save summary
    summary = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "days_elapsed": days_elapsed,
        "long_return": long_return,
        "short_return": short_return,
        "portfolio_return": total_return,
        "spy_return": spy_return,
        "alpha": alpha,
        "long_pnl": long_pnl,
        "short_pnl": short_pnl,
        "total_pnl": total_pnl,
    }

    summary_df = pd.DataFrame([summary])
    summary_file = output_dir / "performance_history.csv"

    if summary_file.exists():
        # Append to existing
        history = pd.read_csv(summary_file)
        summary_df = pd.concat([history, summary_df], ignore_index=True)

    summary_df.to_csv(summary_file, index=False)

    print(f"\n✓ Saved to {output_dir}/")
    print(f"  - long_positions_{timestamp}.csv")
    print(f"  - short_positions_{timestamp}.csv")
    print(f"  - performance_history.csv (updated)")


if __name__ == "__main__":
    generate_report()
