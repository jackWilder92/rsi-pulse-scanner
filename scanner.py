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
        print(f"⚠️ Error fetching live list: {e}. Using backup.")
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


def calculate_rsi(series, period=14):
    """Calculates Wilder's Smoothed RSI matching standard chart setups."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def run_scanner():
    crossed_above_60 = []
    crossed_below_40 = []

    fo_tickers = get_live_fo_tickers()

    # CHUNKING ENGINE: Divide 180+ stocks into micro-batches of 30 to prevent network choking
    chunk_size = 30
    ticker_chunks = [
        fo_tickers[i : i + chunk_size]
        for i in range(0, len(fo_tickers), chunk_size)
    ]

    print(
        f"Separated markets into {len(ticker_chunks)} secure verification streams..."
    )

    for idx, chunk in enumerate(ticker_chunks):
        print(f"Processing batch {idx+1}/{len(ticker_chunks)}...")
        try:
            # Enforce a strict 15-second timeout limit per batch
            data = yf.download(
                tickers=chunk,
                period="3mo",
                interval="1h",
                group_by="ticker",  # Groups data by Ticker first for stable processing
                progress=False,
                threads=True,
                timeout=15,  # ◄── Kills the block if Yahoo stalls
            )

            for ticker in chunk:
                try:
                    # Safe check if the ticker structure successfully downloaded
                    if ticker not in data.columns.levels[0]:
                        continue

                    df_ticker = data[ticker].dropna()

                    # Restrict data to regular NSE market session hours
                    df_ticker = df_ticker[
                        (df_ticker.index.hour >= 9) & (df_ticker.index.hour <= 15)
                    ]

                    if len(df_ticker) < 30:
                        continue

                    # Process indicators
                    rsi_series = calculate_rsi(df_ticker["Close"])

                    rsi_latest = float(rsi_series.iloc[-1])
                    rsi_prev1 = float(rsi_series.iloc[-2])
                    rsi_prev2 = float(rsi_series.iloc[-3])

                    clean_ticker = ticker.replace(".NS", "")
                    tv_format = f"NSE:{clean_ticker}"

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

                except Exception:
                    continue  # Skip any corrupt single rows safely

        except Exception as batch_error:
            print(f"⚠️ Batch {idx+1} timed out or failed. Skipping to next chunk.")
            continue

    # Format the updated execution timestamp
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
        f"Scan successful! Bullish: {len(crossed_above_60)} | Bearish: {len(crossed_below_40)}"
    )


if __name__ == "__main__":
    run_scanner()


