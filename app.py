import json
import os
import streamlit as st

# Configure mobile viewport optimization
st.set_page_config(
    page_title="RSI Pulse Scanner", page_icon="🏹", layout="centered"
)

st.title("🏹 Nifty F&O RSI Pulse")
st.markdown("---")

if os.path.exists("signals.json"):
    with open("signals.json", "r") as f:
        data = json.load(f)

    st.caption(f"⏱️ **Last Scanner Update (IST):** {data['last_updated']}")

    # --- BULLISH MOMENTUM SECTION ---
    st.success("### 📈 Bullish Momentum (Crossed Above 60)")
    bullish_list = data.get("bullish_signals", [])

    if bullish_list:
        # Display as readable blocks
        st.write(", ".join([stock.replace("NSE:", "") for stock in bullish_list]))

        # Format string for easy copying to TradingView
        bullish_string = ",".join(bullish_list)
        st.text_input(
            "📋 Copy & Paste into TradingView Watchlist:",
            value=bullish_string,
            key="bull_tv",
        )
    else:
        st.info("No F&O stocks crossed above RSI 60 this hour.")

    st.markdown("---")

    # --- BEARISH MOMENTUM SECTION ---
    st.error("### 📉 Bearish Momentum (Crossed Below 40)")
    bearish_list = data.get("bearish_signals", [])

    if bearish_list:
        # Display as readable blocks
        st.write(", ".join([stock.replace("NSE:", "") for stock in bearish_list]))

        # Format string for easy copying to TradingView
        bearish_string = ",".join(bearish_list)
        st.text_input(
            "📋 Copy & Paste into TradingView Watchlist:",
            value=bearish_string,
            key="bear_tv",
        )
    else:
        st.info("No F&O stocks crossed below RSI 40 this hour.")

else:
    st.warning(
        "⏳ Waiting for data... Trigger a manual scan in GitHub Actions to generate your first list!"
    )
