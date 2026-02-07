import pandas as pd

# Load your CSV
df = pd.read_csv("/Users/gkg/PycharmProjects/Fintel/data/multi_analysis_export.csv")

# Replace 'ticker' with the actual column name if different
ticker_counts = df["ticker"].value_counts()

# Print results
print(ticker_counts)

# Optional: save to a new CSV
ticker_counts.to_csv("ticker_counts.csv", header=["count"])