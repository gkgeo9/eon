import pandas as pd
import yfinance as yf
import time

INPUT_CSV = "C:\\Users\\vdocv\\PycharmProjects\\eon\\russell1000.csv"
OUTPUT_CSV = "russell_1000_market_caps.csv"

def clean_ticker(ticker):
    """
    Converts tickers into Yahoo Finance format.
    Example: BRK.B becomes BRK-B
    """
    if pd.isna(ticker):
        return None
    ticker = str(ticker).strip().upper()
    ticker = ticker.replace(".", "-")
    return ticker

def get_market_cap(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info

        market_cap = info.get("market_cap", None)

        if market_cap is None:
            full_info = stock.info
            market_cap = full_info.get("marketCap", None)

        return market_cap

    except Exception as e:
        print(f"Error for {ticker}: {e}")
        return None

def main():
    df = pd.read_csv(INPUT_CSV)

    print("Columns found:")
    print(df.columns.tolist())

    ticker_col = "ticker"

    if ticker_col not in df.columns:
        raise ValueError(
            f"Could not find column named {ticker_col}. "
            "Change ticker_col to match your CSV column name."
        )

    df["Yahoo_Ticker"] = df[ticker_col].apply(clean_ticker)

    market_caps = []

    for i, ticker in enumerate(df["Yahoo_Ticker"], start=1):
        print(f"{i}/{len(df)} Checking {ticker}")
        market_cap = get_market_cap(ticker)
        market_caps.append(market_cap)
        time.sleep(0.25)

    df["Market_Cap"] = market_caps
    df["Market_Cap_Billions"] = df["Market_Cap"] / 1_000_000_000

    valid = df.dropna(subset=["Market_Cap"])

    min_row = valid.loc[valid["Market_Cap"].idxmin()]
    max_row = valid.loc[valid["Market_Cap"].idxmax()]

    print("\nMIN MARKET CAP")
    print(min_row[[ticker_col, "Yahoo_Ticker", "Market_Cap", "Market_Cap_Billions"]])

    print("\nMAX MARKET CAP")
    print(max_row[[ticker_col, "Yahoo_Ticker", "Market_Cap", "Market_Cap_Billions"]])

    print("\nSUMMARY")
    print(f"Companies checked: {len(df)}")
    print(f"Successful market caps: {len(valid)}")
    print(f"Missing market caps: {len(df) - len(valid)}")
    print(f"Minimum market cap: ${min_row['Market_Cap_Billions']:.2f}B")
    print(f"Maximum market cap: ${max_row['Market_Cap_Billions']:.2f}B")

    df = df.sort_values("Market_Cap", ascending=True)
    df.to_csv(OUTPUT_CSV, index=False)

    print(f"\nSaved output to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()