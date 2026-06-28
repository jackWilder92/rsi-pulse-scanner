import json
import os
import pandas as pd
import yfinance as yf


def get_live_fo_tickers():
    """Fetches the live up-to-date F&O stock list directly from Nifty Indices."""
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

    # Get the up-to-date ~180+ F&O tickers from NSE
    fo_tickers = get_live_fo_tickers()

    # Bulk download 1 month of hourly data to ensure data speed and perfect RSI convergence
    print("Downloading all market data in bulk from Yahoo Finance...")
    try:
        market_data = yf.download(
            fo_tickers,
            period="1mo",
            interval="1h",
            progress=False,
            threads=False,  # Prevents CPU hanging on GitHub runners
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
            # Drop any missing rows to get a clean historical timeline
            series = close_df[ticker].dropna()

            # Ensure we have enough candles to build a stabilized RSI
            if len(series) < 30:
                continue

            # Calculate Wilder's Smoothed RSI
            delta = series.diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)

            # Standard 14-period exponential smoothing matching TradingView & Chartink
            avg_gain = gain.ewm(com=13, adjust=False).mean()
            avg_loss = loss.ewm(com=13, adjust=False).mean()

            rs = avg_gain / avg_loss
            rsi_series = 100 - (100 / (1 + rs))

            # Grab the last three complete hourly records to capture closing anomalies
            rsi_latest = float(rsi_series.iloc[-1])  # Final 15-minute closing window (3:15-3:30 PM)
            rsi_prev1 = float(rsi_series.iloc[-2])  # Main closing trading hour (2:15-3:15 PM)
            rsi_prev2 = float(rsi_series.iloc[-3])  # Afternoon trading hour (1:15-2:15 PM)

            clean_ticker = ticker.replace(".NS", "")
            tv_format = f"NSE:{clean_ticker}"

            # --- Smart Crossover Logic ---
            # Bullish Check: Crossed above 60 in either of the last two candle windows
            crossed_above = (rsi_prev1 <= 60 and rsi_latest > 60) or (
                rsi_prev2 <= 60 and rsi_prev1 > 60
            )

            # Bearish Check: Crossed below 40 in either of the last two candle windows
            crossed_below = (rsi_prev1 >= 40 and rsi_latest < 40) or (
                rsi_prev2 >= 40 and rsi_prev1 < 40
            )

            if crossed_above:
                crossed_above_60.append(tv_format)
            elif crossed_below:
                crossed_below_40.append(tv_format)

        except Exception as ticker_error:
            # Skip any corrupt stock data without stopping the whole scan
            continue

    # Create timestamp formatted explicitly for India Time
    india_time = pd.Timestamp.now(tz="Asia/Kolkata").strftime(
        "%Y-%m-%d %I:%M %p"
    )

    output_data = {
        "last_updated": india_time,
        "bullish_signals": crossed_above_60,
        "bearish_signals": crossed_below_40,
    }

    # Save output data to JSON file
    with open("signals.json", "w") as f:
        json.dump(output_data, f, indent=4)

    print(
        f"Scan complete! Bullish: {len(crossed_above_60)} | Bearish: {len(crossed_below_40)}"
    )


if __name__ == "__main__":
    run_scanner()
