import json
import os
import pandas as pd
import yfinance as yf

# Expanded list of highly active Nifty F&O Tickers (Yahoo Finance requires '.NS' suffix)
FO_TICKERS = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "BHARTIARTL.NS",
    "ITC.NS",
    "MARUTI.NS",
    "TATASTEEL.NS",
    "AXISBANK.NS",
    "KOTAKBANK.NS",
    "LT.NS",
    "BAJAJFINSV.NS",
    "BAJFINANCE.NS",
    "M&M.NS",
    "SUNPHARMA.NS",
    "TATAMOTORS.NS",
    "HINDALCO.NS",
    "WIPRO.NS",
    "JSWSTEEL.NS",
    "ADANIENT.NS",
    "NTPC.NS",
    "POWERGRID.NS",
]


def calculate_rsi(df, period=14):
    """Calculates smoothed RSI matching standard TradingView/Wilder's logic."""
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # Wilder's smoothing technique using EMA
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def run_scanner():
    crossed_above_60 = []
    crossed_below_40 = []

    print("Starting market scan...")

    for ticker in FO_TICKERS:
        try:
            # Download 5 days of 1-hour interval data
            df = yf.download(ticker, period="5d", interval="1h", progress=False)

            if len(df) < 15:
                print(f"Skipping {ticker}: Not enough hourly candles.")
                continue

            df["RSI"] = calculate_rsi(df)

            # Get the second-to-last (previous complete) and last (current complete) values
            rsi_prev = float(df["RSI"].iloc[-2])
            rsi_curr = float(df["RSI"].iloc[-1])

            clean_ticker = ticker.replace(".NS", "")
            tv_format = f"NSE:{clean_ticker}"

            # --- Crossover Logic ---
            # Bullish: Crossed ABOVE 60
            if rsi_prev <= 60 and rsi_curr > 60:
                crossed_above_60.append(tv_format)

            # Bearish: Crossed BELOW 40
            elif rsi_prev >= 40 and rsi_curr < 40:
                crossed_below_40.append(tv_format)

        except Exception as e:
            print(f"Error processing token {ticker}: {str(e)}")

    # Prepare data payload with India timestamp
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

    print("Scan completed successfully. Results saved to signals.json")


if __name__ == "__main__":
    run_scanner()
