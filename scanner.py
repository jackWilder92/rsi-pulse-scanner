import json
import os
import pandas as pd
import yfinance as yf


def get_live_fo_tickers():
    """Fetches the live, up-to-date F&O stock list directly from Nifty Indices / NSE."""
    print("Fetching live F&O stock list from NSE source...")
    try:
        # Official Nifty Indices CSV URL for all F&O securities
        url = "https://niftyindices.com/Securities_in_FnO.csv"

        # Read the online CSV file directly into pandas
        df = pd.read_csv(url)

        # The column containing the tickers is named 'Symbol'
        raw_tickers = df["Symbol"].dropna().tolist()

        # Format tickers for Yahoo Finance by appending '.NS'
        yf_tickers = [f"{ticker.strip()}.NS" for ticker in raw_tickers]

        print(f"Successfully loaded {len(yf_tickers)} live F&O stocks.")
        return yf_tickers

    except Exception as e:
        # Fallback list just in case the external website goes down or blocks the request
        print(f"⚠️ Error fetching live list: {e}. Using emergency backup list.")
        return [
            "RELIANCE.NS",
            "TCS.NS",
            "INFY.NS",
            "HDFCBANK.NS",
            "ICICIBANK.NS",
            "SBIN.NS",
        ]


def calculate_rsi(df, period=14):
    """Calculates smoothed RSI matching standard TradingView/Wilder's logic."""
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def run_scanner():
    crossed_above_60 = []
    crossed_below_40 = []

    # DYNAMIC FETCH: Pulls all ~180+ stocks automatically
    fo_tickers = get_live_fo_tickers()

    for ticker in fo_tickers:
        try:
            df = yf.download(ticker, period="5d", interval="1h", progress=False)

            if len(df) < 15:
                continue

            df["RSI"] = calculate_rsi(df)

            rsi_prev = float(df["RSI"].iloc[-2])
            rsi_curr = float(df["RSI"].iloc[-1])

            clean_ticker = ticker.replace(".NS", "")
            tv_format = f"NSE:{clean_ticker}"

            if rsi_prev <= 60 and rsi_curr > 60:
                crossed_above_60.append(tv_format)
            elif rsi_prev >= 40 and rsi_curr < 40:
                crossed_below_40.append(tv_format)

        except Exception as e:
            print(f"Skipping {ticker} due to error: {str(e)}")

    india_time = pd.Timestamp.now(tz="Asia/Kolkata").strftime(
        "%Y-%m-%d %I:%M %p"
    )

    output_data = {
        "last_updated": india_time,
        "bullish_signals": crossed_above_60,
        "bearish_signals": crossed_below_40,
    }

    with open("signals.json", "w") as f:
        json.dump(output_data, f, indent=4)

    print("Scan completed successfully.")


if __name__ == "__main__":
    run_scanner()
