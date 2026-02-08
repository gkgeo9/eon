"""
Main backtester orchestrator.

Coordinates signal extraction, price fetching, return computation,
and metric aggregation to answer: "Do STRONG analysis signals generate true alpha?"
"""

import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

from .data_loader import (
    get_signal_summary,
    get_unique_tickers,
    load_all_multi_analysis_signals,
)
from .metrics import (
    BacktestMetrics,
    TradeResult,
    compute_backtest_metrics,
    compute_trade_returns,
)
from .price_fetcher import PriceFetcher
from .report import (
    export_metrics_to_csv,
    export_trades_to_csv,
    print_backtest_report,
    print_signal_summary,
)
from .signals import (
    CompositeSignal,
    SignalStrength,
    filter_strong_signals,
)

logger = logging.getLogger(__name__)

# Standard holding periods in trading days
DEFAULT_HOLDING_PERIODS = [5, 21, 63, 126, 252]  # 1W, 1M, 3M, 6M, 12M


class Backtester:
    """
    Backtests EON multi-perspective analysis signals against actual stock returns.

    Workflow:
    1. Load analysis results from database
    2. Extract signals and classify by strength
    3. Fetch historical prices for all tickers + SPY benchmark
    4. Compute forward returns at multiple holding periods
    5. Calculate alpha, Sharpe, win rates, and statistical significance
    6. Generate report
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
        alphavantage_key: Optional[str] = None,
        max_fiscal_year: int = 2024,
        holding_periods: Optional[List[int]] = None,
        batch_name: Optional[str] = None,
    ):
        """
        Args:
            db_path: Path to eon.db.
            cache_dir: Directory for price data cache.
            alphavantage_key: AlphaVantage API key (optional).
            max_fiscal_year: Max fiscal year to include (avoids look-ahead bias).
            holding_periods: Holding periods in trading days.
            batch_name: If set, only backtest signals from this batch.
        """
        self.db_path = db_path
        self.max_fiscal_year = max_fiscal_year
        self.holding_periods = holding_periods or DEFAULT_HOLDING_PERIODS
        self.batch_name = batch_name

        self.price_fetcher = PriceFetcher(
            cache_dir=cache_dir,
            alphavantage_key=alphavantage_key,
        )

        # State
        self.signals: List[CompositeSignal] = []
        self.trades: List[TradeResult] = []
        self.metrics_by_group: Dict[str, BacktestMetrics] = {}

    def run(self) -> Dict[str, BacktestMetrics]:
        """
        Execute the full backtest pipeline.

        Returns:
            Dictionary mapping signal group labels to their BacktestMetrics.
        """
        # Step 1: Load signals
        print("Step 1/5: Loading analysis signals from database...")
        self.signals = load_all_multi_analysis_signals(
            db_path=self.db_path,
            max_fiscal_year=self.max_fiscal_year,
            batch_name=self.batch_name,
        )

        if not self.signals:
            print("No signals found. Check database path and fiscal year filter.")
            return {}

        summary = get_signal_summary(self.signals)
        print_signal_summary(len(self.signals), summary)

        # Step 2: Fetch prices
        print("Step 2/5: Fetching historical price data...")
        tickers = get_unique_tickers(self.signals)
        price_data, bench_data = self._fetch_all_prices(tickers)

        if bench_data is None:
            print("ERROR: Could not fetch SPY benchmark data. Aborting.")
            return {}

        print(
            f"  Fetched prices for {len(price_data)}/{len(tickers)} tickers + SPY benchmark"
        )

        # Step 3: Compute trade returns
        print("Step 3/5: Computing forward returns...")
        self.trades = self._compute_all_returns(price_data, bench_data)
        print(f"  Computed returns for {len(self.trades)} trades")

        # Step 4: Aggregate metrics by signal group
        print("Step 4/5: Calculating metrics...")
        self.metrics_by_group = self._compute_grouped_metrics()

        # Step 5: Report
        print("Step 5/5: Generating report...")
        print_backtest_report(self.metrics_by_group, self.holding_periods)

        return self.metrics_by_group

    def export(self, output_dir: Optional[Path] = None) -> None:
        """Export results to CSV files."""
        output_dir = output_dir or Path("data/backtest_results")
        output_dir.mkdir(parents=True, exist_ok=True)

        if self.trades:
            export_trades_to_csv(
                self.trades,
                self.holding_periods,
                output_dir / "trades.csv",
            )

        if self.metrics_by_group:
            export_metrics_to_csv(
                self.metrics_by_group,
                self.holding_periods,
                output_dir / "metrics_summary.csv",
            )

    def _fetch_all_prices(self, tickers: List[str]):
        """Fetch prices for all tickers and the SPY benchmark."""
        # Determine date range needed
        # Earliest signal: fiscal_year+1 April (signal date)
        # Latest: max_fiscal_year+1 April + max holding period
        min_year = min(s.fiscal_year for s in self.signals)
        earliest_start = f"{min_year}-01-01"
        # Need data through max_fiscal_year + 2 to cover 12-month holding
        latest_end = f"{self.max_fiscal_year + 3}-01-01"

        # Fetch all tickers including SPY
        all_symbols = list(set(tickers + ["SPY"]))
        all_prices = self.price_fetcher.get_prices_batch(
            all_symbols, earliest_start, latest_end
        )

        bench = all_prices.pop("SPY", None)
        return all_prices, bench

    def _compute_all_returns(self, price_data, bench_data) -> List[TradeResult]:
        """Compute forward returns for all signals."""
        trades = []

        for signal in self.signals:
            if signal.ticker not in price_data:
                logger.debug(f"No price data for {signal.ticker}, skipping")
                continue

            stock_prices = price_data[signal.ticker]

            trade = TradeResult(
                ticker=signal.ticker,
                fiscal_year=signal.fiscal_year,
                signal_strength=signal.strength.value,
                priority_count=signal.priority_count,
                entry_date=signal.signal_date,
                entry_price=0.0,
                buffett_signal=signal.buffett.action_signal,
                buffett_verdict=signal.buffett.verdict,
                taleb_signal=signal.taleb.action_signal,
                taleb_verdict=signal.taleb.verdict,
                contrarian_signal=signal.contrarian.action_signal,
                contrarian_verdict=signal.contrarian.verdict,
                contrarian_conviction=signal.contrarian.conviction_level or "",
            )

            trade = compute_trade_returns(
                trade=trade,
                stock_prices=stock_prices,
                bench_prices=bench_data,
                holding_periods=self.holding_periods,
            )

            # Only include if we got at least some return data
            if any(v is not None for v in trade.returns.values()):
                trades.append(trade)

        return trades

    def _compute_grouped_metrics(self) -> Dict[str, BacktestMetrics]:
        """Compute metrics for different signal strength groups."""
        groups = {}

        # Group 1: ALL PRIORITY (all 3 perspectives agree)
        all_priority = [
            t for t in self.trades if t.signal_strength == SignalStrength.ALL_PRIORITY.value
        ]
        groups["ALL_PRIORITY (3/3)"] = compute_backtest_metrics(
            all_priority, self.holding_periods, "ALL_PRIORITY (3/3)"
        )

        # Group 2: MAJORITY PRIORITY (2+ perspectives)
        majority = [
            t
            for t in self.trades
            if t.signal_strength
            in (SignalStrength.ALL_PRIORITY.value, SignalStrength.MAJORITY_PRIORITY.value)
        ]
        groups["MAJORITY_PRIORITY (2+/3)"] = compute_backtest_metrics(
            majority, self.holding_periods, "MAJORITY_PRIORITY (2+/3)"
        )

        # Group 3: ANY PRIORITY (at least 1 perspective)
        any_priority = [
            t for t in self.trades if t.signal_strength != SignalStrength.NO_SIGNAL.value
        ]
        groups["ANY_PRIORITY (1+/3)"] = compute_backtest_metrics(
            any_priority, self.holding_periods, "ANY_PRIORITY (1+/3)"
        )

        # Group 4: NO SIGNAL (control group)
        no_signal = [
            t for t in self.trades if t.signal_strength == SignalStrength.NO_SIGNAL.value
        ]
        groups["NO_SIGNAL (control)"] = compute_backtest_metrics(
            no_signal, self.holding_periods, "NO_SIGNAL (control)"
        )

        # Group 5: ALL signals combined (baseline)
        groups["ALL_SIGNALS (baseline)"] = compute_backtest_metrics(
            self.trades, self.holding_periods, "ALL_SIGNALS (baseline)"
        )

        # Perspective-specific groups
        buffett_priority = [t for t in self.trades if t.buffett_signal == "PRIORITY"]
        groups["BUFFETT_PRIORITY"] = compute_backtest_metrics(
            buffett_priority, self.holding_periods, "BUFFETT_PRIORITY"
        )

        taleb_priority = [t for t in self.trades if t.taleb_signal == "PRIORITY"]
        groups["TALEB_PRIORITY"] = compute_backtest_metrics(
            taleb_priority, self.holding_periods, "TALEB_PRIORITY"
        )

        contrarian_priority = [t for t in self.trades if t.contrarian_signal == "PRIORITY"]
        groups["CONTRARIAN_PRIORITY"] = compute_backtest_metrics(
            contrarian_priority, self.holding_periods, "CONTRARIAN_PRIORITY"
        )

        return groups
