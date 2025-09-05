import os
import time
import yfinance as yf
import streamlit as st
from graph_agent import crew
from dotenv import load_dotenv
import pandas as pd

# --------------------------------------------------------
# Load environment variables
# --------------------------------------------------------
load_dotenv()

st.set_page_config(page_title="📊 Stock AI Agent", layout="wide")
st.title("📈 Stock AI Analysis & Live Watchlist")

# ========================================================
# SECTION 1: STOCK ANALYSIS (On-demand)
# ========================================================
st.header("🔍 On-Demand Stock Analysis")

query = st.text_input("Enter a company name or ticker symbol for analysis:", "")

if st.button("Run Analysis") and query:
    with st.spinner("Analyzing..."):
        state = {"query": query}
        result = crew.invoke(state)

    st.success("✅ Analysis complete!")

    st.subheader("🔎 Detected Symbol")
    st.write(result.get("symbol", "N/A"))

    st.subheader("💵 Latest Price")
    st.write(result.get("latest_price", "N/A"))

    st.subheader("💰 Valuation")
    st.write(result.get("valuation", "N/A"))

    st.subheader("📊 Analysis")
    st.write(result.get("analysis", "N/A"))

    # Show chart if available
    chart_path = result.get("chart")
    if chart_path and os.path.exists(chart_path):
        st.subheader("📉 1-Year Price Chart")
        st.image(chart_path, use_container_width=True)
    else:
        st.warning("No chart generated.")


st.markdown("---")

# ========================================================
# SECTION 2: LIVE STOCK WATCHLIST DASHBOARD
# ========================================================
st.header("📡 Live Stock Watchlist")

# Initialize watchlist in session state
if "watchlist" not in st.session_state:
    st.session_state.watchlist = []

# Input to add a new stock
new_stock = st.text_input("➕ Add a stock symbol to watchlist:", "")

if st.button("Add Stock"):
    symbol = new_stock.upper().strip()
    if symbol and symbol not in st.session_state.watchlist:
        st.session_state.watchlist.append(symbol)
        st.success(f"✅ {symbol} added to watchlist!")
    elif symbol in st.session_state.watchlist:
        st.warning(f"⚠️ {symbol} is already in the watchlist.")
    else:
        st.error("❌ Please enter a valid stock symbol.")

# Remove stock option
if st.session_state.watchlist:
    remove_stock = st.selectbox("🗑️ Remove stock from watchlist:", [""] + st.session_state.watchlist)
    if remove_stock and st.button("Remove Selected Stock"):
        st.session_state.watchlist.remove(remove_stock)
        st.success(f"🗑️ {remove_stock} removed from watchlist.")

# Function to fetch live stock data
def fetch_stock_details(symbol):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")
        info = ticker.info

        latest_price = round(hist["Close"].iloc[-1], 2) if not hist.empty else None
        pe = info.get("trailingPE", None)
        pb = info.get("priceToBook", None)

        return {
            "Symbol": symbol,
            "Current Price": latest_price if latest_price is not None else "N/A",
            "P/E Ratio": round(pe, 2) if pe else "N/A",
            "P/B Ratio": round(pb, 2) if pb else "N/A",
        }
    except Exception:
        return {
            "Symbol": symbol,
            "Current Price": "N/A",
            "P/E Ratio": "N/A",
            "P/B Ratio": "N/A",
        }

# Display watchlist table if there are stocks
if st.session_state.watchlist:
    st.subheader("📊 Live Prices")
    with st.spinner("Fetching live prices..."):
        data = [fetch_stock_details(sym) for sym in st.session_state.watchlist]
        df = pd.DataFrame(data)

        st.dataframe(df, use_container_width=True)

    # Auto-refresh every 30 seconds
    #st.caption("⏳ Auto-refreshing every 30 seconds...")
    #st.experimental_rerun()
    from streamlit_autorefresh import st_autorefresh

    # Auto-refresh every 30 seconds
    st.caption("⏳ Auto-refreshing every 30 seconds...")
    st_autorefresh(interval=30 * 1000, key="datarefresh")
else:
    st.info("⚠️ No stocks in your watchlist yet. Add one above to get started!")
