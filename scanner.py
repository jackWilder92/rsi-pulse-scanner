import json
import os
import pandas as pd
import yfinance as yf


def get_live_fo_tickers():
    """Fetches the live up-to-date F&O stock list from Nifty Indices."""
    print("Fetching live F&O stock list...")
    try:
        url = "https://niftyindices.com/Securities_in_FnO.csv"
        df = pd.read_csv(url)
        raw_tickers = df["Symbol"].dropna().tolist()
        return [f"{ticker.strip()}.NS" for ticker in raw_tickers]
    except Exception as e:
        print(f"⚠️ Error fetching live list: {e}. Using emergency backup.")
        return [
            "RELIANCE.NS",
            "TCS.NS",
            "INFY.NS",
            "HDFCBANK.NS",
            "ICICIBANK.NS",
            "KOTAKBANK.NS",
            "TATAELXSI.NS",
            "ADANIPORTS.NS",
            "GLENMARK.NS",
        ]


def run_scanner():
    crossed_above_60 = []
    crossed_below_40 = []

    # Get the ~180+ tickers
    fo_tickers = get_live_fo_tickers()

    # 1. BULK DOWNLOAD: 1 request instead of 180 loops.
    # 2. INCREASED LOOKBACK: '2mo' provides ~300 hourly candles for perfect RSI convergence.
    print("Downloading all market data in bulk from Yahoo Finance...")
    try:
       # Changed period from '2mo' to '1mo' to speed up the network request
        market_data = yf.download(
            fo_tickers, period="1mo", interval="1h", progress=False
        )
    except Exception as e:
        print(f"Critical error downloading data block: {e}")
        return

    # Extract the Closing prices matrix
    close_df = market_data["Close"]

    print("Processing mathematical indicators...")
    for ticker in fo_tickers:
        if ticker not in close_df.columns:
            continue

        try:
            # Drop any missing rows to get a clean chronological hourly line
            series = close_df[ticker].dropna()

            # Ensure we have enough deep historical data to calculate true RSI
            if len(series) < 50:
                continue

            # Calculate Wilder's Smoothed RSI
            delta = series.diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)

            # Using standard 14 period exponential smoothing
            avg_gain = gain.ewm(com=13, adjust=False).mean()
            avg_loss = loss.ewm(com=13, adjust=False).mean()

            rs = avg_gain / avg_loss
            rsi_series = 100 - (100 / (1 + rs))

            # Grab the last two complete hourly elements
            rsi_prev = float(rsi_series.iloc[-2])
            rsi_curr = float(rsi_series.iloc[-1])

            clean_ticker = ticker.replace(".NS", "")
            tv_format = f"NSE:{clean_ticker}"

            # Strategy Crossover Validations
            if rsi_prev <= 60 and rsi_curr > 60:
                crossed_above_60.append(tv_format)
            elif rsi_prev >= 40 and rsi_curr < 40:
                crossed_below_40.append(tv_format)

        except Exception as ticker_error:
            # Prevents a single stock data error from breaking the whole run
            continue

    # Create timestamp formatted for India
    india_time = pd.Timestamp.now(tz="Asia/Kolkata").strftime(
        "%Y-%m-%d %I:%M %p"
    )

    output_data = {
        "last_updated": india_time,
        "bullish_signals": crossed_above_60,
        "bearish_signals": crossed_below_40,
    }

    # Save to your structured repository file
    with open("signals.json", "w") as f:
        json.dump(output_data, f, indent=4)

    print(
        f"Scan complete! Bullish: {len(crossed_above_60)} | Bearish: {len(crossed_below_40)}"
    )


if __name__ == "__main__":
    run_scanner()
