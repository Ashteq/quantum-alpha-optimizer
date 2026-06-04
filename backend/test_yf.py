import yfinance as yf

print("Testing yfinance download...")
try:
    # Try to download 5 days of data for AAPL and MSFT
    data = yf.download(["AAPL", "MSFT"], period="5d")
    print("\n--- DOWNLOAD SUCCESS ---")
    print(data.head())
except Exception as e:
    print("\n--- DOWNLOAD FAILED ---")
    print(f"Error: {e}")