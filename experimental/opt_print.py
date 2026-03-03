import yfinance as yf
import pandas as pd
from datetime import datetime
import math

pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)
pd.set_option("display.float_format", "{:.4f}".format)

STRATEGIES = [
    {"ticker": "BLBD",  "target_expiry": "2027-01-15", "label": "Anchor Upside Play"},
    {"ticker": "LBRDK", "target_expiry": "2026-09-18", "label": "Binary Volatility Straddle"},
    {"ticker": "GEL",   "target_expiry": "2027-01-15", "label": "Offshore Production Ramp"},
    {"ticker": "KALV",  "target_expiry": "2027-01-15", "label": "De-Risked Biotech"},
    {"ticker": "PBT",   "target_expiry": "2026-12-18", "label": "Broken Trust"},
    {"ticker": "BW",    "target_expiry": "2026-12-18", "label": "Going-Concern Lottery"},
]

COLS = ["strike", "lastPrice", "bid", "ask", "volume", "openInterest", "impliedVolatility"]

def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df[COLS].copy()
    df["volume"] = df["volume"].apply(lambda x: int(x) if x and not (isinstance(x, float) and math.isnan(x)) else 0)
    df["openInterest"] = df["openInterest"].apply(lambda x: int(x) if x and not (isinstance(x, float) and math.isnan(x)) else 0)
    df["impliedVolatility"] = df["impliedVolatility"] * 100
    df = df.rename(columns={"impliedVolatility": "IV%", "lastPrice": "last", "openInterest": "OI"})
    return df.reset_index(drop=True)

def find_closest_expiry(available: list[str], target: str) -> str:
    target_dt = datetime.strptime(target, "%Y-%m-%d")
    return min(available, key=lambda d: abs(datetime.strptime(d, "%Y-%m-%d") - target_dt))

sep = "=" * 80

for strat in STRATEGIES:
    ticker = yf.Ticker(strat["ticker"])
    hist = ticker.history(period="1d")
    current_price = hist["Close"].iloc[-1] if not hist.empty else 0.0

    available = ticker.options
    if not available:
        print(f"\n[!] No options available for {strat['ticker']}")
        continue

    chosen = find_closest_expiry(list(available), strat["target_expiry"])
    chain = ticker.option_chain(chosen)

    calls = clean_df(chain.calls)
    puts  = clean_df(chain.puts)

    print(f"\n{sep}")
    print(f"  {strat['ticker']} | {strat['label']}")
    print(f"  Current Price  : ${current_price:.2f}")
    print(f"  Target Expiry  : {strat['target_expiry']}")
    print(f"  Expiry Used    : {chosen}")
    print(f"  Available Dates: {', '.join(available)}")
    print(sep)

    print("\n  --- CALLS ---")
    print(calls.to_string(index=True))

    print("\n  --- PUTS ---")
    print(puts.to_string(index=True))

print(f"\n{sep}")
print("Done.")