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

    fo_tickers = get_live_fo_tickers()

    # UPGRADE 1: Increased to '3mo' for 100% stable RSI convergence matching Chartink
    print("Downloading 3 months of market data in bulk...")
    try:
        market_data = yf.download(
            fo_tickers,
            period="3mo",
            interval="1h",
            progress=False,
            threads=True,  # Keeps speed lightning fast
        )
    except Exception as e:
        print(f"Critical error downloading data block: {e}")
        return

    close_df = market_data["Close"]

    print("Filtering market anomalies and processing RSI...")
    for ticker in fo_tickers:
        if ticker not in close_df.columns:
            continue

        try:
            # Drop empty rows
            series = close_df[ticker].dropna()

            # UPGRADE 2: Filter out weekend/off-market data anomalies
            # We filter the index to only include hours between 09:00 and 16:00
            series = series[
                (series.index.hour >= 9) & (series.index.hour <= 15)
            ]

            if len(series) < 50:
                continue

            # Calculate Wilder's Smoothed RSI
            delta = series.diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)

            avg_gain = gain.ewm(com=13, adjust=False).mean()
            avg_loss = loss.ewm(com=13, adjust=False).mean()

            rs = avg_gain / avg_loss
            rsi_series = 100 - (100 / (1 + rs))

            # UPGRADE 3: Grab the final true trading session candles
            rsi_latest = float(rsi_series.iloc[-1])  # 3:15 - 3:30 PM candle
            rsi_prev1 = float(rsi_series.iloc[-2])  # 2:15 - 3:15 PM candle
            rsi_prev2 = float(rsi_series.iloc[-3])  # 1:15 - 2:15 PM candle

            clean_ticker = ticker.replace(".NS", "")
            tv_format = f"NSE:{clean_ticker}"

            # Smart Crossover verification
            crossed_above = (rsi_prev1 <= 60 and rsi_latest > 60) or (
                rsi_prev2 <= 60 and rsi_prev1 > 60
            )
            crossed_below = (rsi_prev1 >= 40 and rsi_latest < 40) or (
                rsi_prev2 >= 40 and rsi_prev1 < 40
            )

            if crossed_above:
                crossed_above_60.append(tv_format)
            elif crossed_below:
                crossed_below_40.append(tv_format)

        except Exception as e:
            continue

    # Generate explicit India Time stamp
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

    print(
        f"Scan complete! Bullish: {len(crossed_above_60)} | Bearish: {len(crossed_below_40)}"
    )


if __name__ == "__main__":
    run_scanner()

