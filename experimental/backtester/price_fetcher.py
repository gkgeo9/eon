"""
Historical price data fetcher with yfinance primary and AlphaVantage fallback.

Includes local file-based caching to avoid redundant API calls.
"""

import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Default cache directory
DEFAULT_CACHE_DIR = Path("data/price_cache")

# AlphaVantage rate limit: 75 requests/min for premium
AV_MIN_INTERVAL = 60.0 / 75.0  # ~0.8 seconds between calls


class PriceFetcher:
    """
    Fetches historical OHLCV price data with caching.

    Primary source: yfinance (free, no rate limit)
    Fallback source: AlphaVantage (requires API key, 75 req/min)
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        alphavantage_key: Optional[str] = None,
    ):
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.av_key = alphavantage_key or os.environ.get("ALPHAVANTAGE_API_KEY")
        self._av_last_call = 0.0

    def get_prices(
        self,
        symbol: str,
        start: str,
        end: str,
        use_cache: bool = True,
    ) -> Optional[pd.DataFrame]:
        """
        Fetch adjusted daily OHLCV data for a symbol.

        Args:
            symbol: Ticker symbol (e.g., 'AAPL').
            start: Start date 'YYYY-MM-DD'.
            end: End date 'YYYY-MM-DD'.
            use_cache: Whether to use/store cached data.

        Returns:
            DataFrame with columns [Open, High, Low, Close, Volume] indexed by date,
            or None if data unavailable.
        """
        # Check cache first
        if use_cache:
            cached = self._load_cache(symbol)
            if cached is not None:
                subset = cached.loc[start:end]
                if not subset.empty:
                    return subset

        # Try yfinance first
        df = self._fetch_yfinance(symbol, start, end)

        # Fallback to AlphaVantage
        if df is None and self.av_key:
            df = self._fetch_alphavantage(symbol, start, end)

        if df is not None and use_cache:
            self._save_cache(symbol, df)

        return df

    def get_benchmark(self, start: str, end: str) -> Optional[pd.DataFrame]:
        """Fetch S&P 500 (SPY) benchmark data."""
        return self.get_prices("SPY", start, end)

    def get_prices_batch(
        self,
        symbols: List[str],
        start: str,
        end: str,
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch prices for multiple symbols. Uses yfinance bulk download
        for efficiency, then fills gaps from cache/AlphaVantage.
        """
        results = {}

        # Check cache first for all symbols
        uncached = []
        for symbol in symbols:
            cached = self._load_cache(symbol)
            if cached is not None:
                subset = cached.loc[start:end]
                if not subset.empty:
                    results[symbol] = subset
                    continue
            uncached.append(symbol)

        # Bulk download uncached via yfinance
        if uncached:
            try:
                import yfinance as yf

                logger.info(f"Bulk downloading {len(uncached)} symbols via yfinance")
                data = yf.download(
                    tickers=uncached,
                    start=start,
                    end=end,
                    auto_adjust=True,
                    progress=False,
                    threads=True,
                )

                if len(uncached) == 1:
                    # Single ticker: yfinance returns flat DataFrame
                    symbol = uncached[0]
                    if not data.empty:
                        df = data[["Open", "High", "Low", "Close", "Volume"]].copy()
                        df.dropna(inplace=True)
                        if not df.empty:
                            results[symbol] = df
                            self._save_cache(symbol, df)
                else:
                    # Multiple tickers: multi-level columns
                    for symbol in uncached:
                        try:
                            df = data.xs(symbol, level="Ticker", axis=1)
                            df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
                            df.dropna(inplace=True)
                            if not df.empty:
                                results[symbol] = df
                                self._save_cache(symbol, df)
                        except (KeyError, ValueError):
                            logger.warning(f"No data returned for {symbol}")
            except Exception as e:
                logger.warning(f"Bulk yfinance download failed: {e}")
                # Fall back to individual fetches
                for symbol in uncached:
                    df = self.get_prices(symbol, start, end)
                    if df is not None:
                        results[symbol] = df

        return results

    def _fetch_yfinance(
        self, symbol: str, start: str, end: str
    ) -> Optional[pd.DataFrame]:
        """Fetch from yfinance with auto_adjust=True for split/dividend adjustment."""
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start, end=end, auto_adjust=True)

            if df.empty:
                logger.warning(f"yfinance returned no data for {symbol}")
                return None

            # Standardize columns
            df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
            df.dropna(inplace=True)
            df.index = pd.to_datetime(df.index).tz_localize(None)
            return df

        except Exception as e:
            logger.warning(f"yfinance failed for {symbol}: {e}")
            return None

    def _fetch_alphavantage(
        self, symbol: str, start: str, end: str
    ) -> Optional[pd.DataFrame]:
        """Fetch from AlphaVantage API with rate limiting."""
        try:
            import requests

            # Rate limit
            elapsed = time.time() - self._av_last_call
            if elapsed < AV_MIN_INTERVAL:
                time.sleep(AV_MIN_INTERVAL - elapsed)
            self._av_last_call = time.time()

            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": "full",
                "apikey": self.av_key,
                "datatype": "json",
            }

            response = requests.get(
                "https://www.alphavantage.co/query", params=params, timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if "Error Message" in data:
                logger.warning(f"AlphaVantage error for {symbol}: {data['Error Message']}")
                return None
            if "Note" in data:
                logger.warning(f"AlphaVantage rate limit for {symbol}: {data['Note']}")
                return None

            ts_key = "Time Series (Daily)"
            if ts_key not in data:
                logger.warning(f"AlphaVantage: no time series data for {symbol}")
                return None

            df = pd.DataFrame.from_dict(data[ts_key], orient="index")
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            df.columns = [col.split(". ", 1)[1].title() for col in df.columns]
            df = df.astype(float)

            # Rename to standard columns
            col_map = {
                "Open": "Open",
                "High": "High",
                "Low": "Low",
                "Close": "Close",
                "Volume": "Volume",
            }
            df = df.rename(columns=col_map)
            df = df[["Open", "High", "Low", "Close", "Volume"]]
            df = df.loc[start:end]

            if df.empty:
                return None

            return df

        except Exception as e:
            logger.warning(f"AlphaVantage failed for {symbol}: {e}")
            return None

    def _cache_path(self, symbol: str) -> Path:
        """Get cache file path for a symbol."""
        return self.cache_dir / f"{symbol.upper()}_daily.parquet"

    def _load_cache(self, symbol: str) -> Optional[pd.DataFrame]:
        """Load cached price data if available."""
        path = self._cache_path(symbol)
        if path.exists():
            try:
                df = pd.read_parquet(path)
                df.index = pd.to_datetime(df.index).tz_localize(None)
                return df
            except Exception as e:
                logger.warning(f"Failed to load cache for {symbol}: {e}")
        return None

    def _save_cache(self, symbol: str, df: pd.DataFrame) -> None:
        """Save price data to cache, merging with existing data."""
        path = self._cache_path(symbol)
        try:
            existing = self._load_cache(symbol)
            if existing is not None:
                # Merge: keep new data where overlap, extend with existing
                combined = pd.concat([existing, df])
                combined = combined[~combined.index.duplicated(keep="last")]
                combined = combined.sort_index()
                combined.to_parquet(path)
            else:
                df.to_parquet(path)
        except Exception as e:
            logger.warning(f"Failed to save cache for {symbol}: {e}")
