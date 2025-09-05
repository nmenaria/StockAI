import os
import json
import yfinance as yf
import pandas as pd
import streamlit as st
from yahooquery import search
from dotenv import load_dotenv
from graph_agent import crew  # Gemini-driven stock analysis agent

# ----------------------------
# Load environment variables
# ----------------------------
load_dotenv()

# ----------------------------
# Persistent Watchlist Storage
# ----------------------------
WATCHLIST_FILE = "watchlist.json"

def load_watchlist() -> list[str]:
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []

def save_watchlist(watchlist: list[str]) -> None:
    try:
        with open(WATCHLIST_FILE, "w") as f:
            json.dump(watchlist, f)
    except Exception as e:
        st.error(f"Failed to save watchlist: {e}")

if "watchlist" not in st.session_state:
    st.session_state.watchlist = load_watchlist()

# ----------------------------
# Symbol Search Helper (Yahooquery)
# ----------------------------
def search_symbol(query: str):
    try:
        results = search(query)
        quotes = results.get("quotes", [])
        matches = []

        for q in quotes:
            symbol = q.get("symbol")
            shortname = q.get("shortname") or q.get("longname")
            exch = q.get("exchange") or q.get("exchangeName")
            if symbol and shortname:
                matches.append({
                    "symbol": symbol,
                    "name": shortname,
                    "exchange": exch
                })
        return matches
    except Exception:
        return []

# ----------------------------
# Fetch Stock Data Row
# ----------------------------
def fetch_stock_row(symbol: str) -> dict:
    row = {
        "Symbol": symbol,
        "Current Price": "N/A",
        "Change": "N/A",
        "% Change": "N/A",
        "P/E Ratio": "N/A",
        "P/B Ratio": "N/A",
    }

    try:
        ticker = yf.Ticker(symbol)

        # --- Price ---
        price = None
        prev_close = None
        try:
            fi = getattr(ticker, "fast_info", None)
            if fi:
                price = fi.get("last_price") or fi.get("last_close")
                prev_close = fi.get("previous_close")
        except Exception:
            pass

        # Fallback to history if fast_info fails
        if price is None or prev_close is None:
            hist = ticker.history(period="5d", interval="1d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
                if len(hist) > 1:
                    prev_close = float(hist["Close"].iloc[-2])

        if price is not None:
            row["Current Price"] = f"{price:.2f}"
        if price is not None and prev_close:
            change = price - prev_close
            pct = (change / prev_close) * 100 if prev_close else 0.0
            row["Change"] = f"{change:+.2f}"
            row["% Change"] = f"{pct:+.2f}%"

        # --- Valuation ---
        try:
            info = ticker.info
            pe = info.get("trailingPE")
            pb = info.get("priceToBook")
            if isinstance(pe, (int, float)):
                row["P/E Ratio"] = f"{pe:.2f}"
            if isinstance(pb, (int, float)):
                row["P/B Ratio"] = f"{pb:.2f}"
        except Exception:
            pass

    except Exception:
        pass

    return row

# ----------------------------
# Streamlit Page Setup
# ----------------------------
st.set_page_config(page_title="📊 Stock AI Agent", layout="wide")
st.title("📈 Stock AI Analysis Agent")

tab1, tab2 = st.tabs(["🔍 Stock Analysis", "📊 Live Watchlist"])

# -------------------------------------------------
# TAB 1: STOCK ANALYSIS
# -------------------------------------------------
with tab1:
    st.subheader("🔍 On-Demand Analysis")
    query = st.text_input("Enter a company name or ticker symbol:", "")

    if st.button("Run Analysis") and query:
        with st.spinner("Analyzing..."):
            state = {"query": query}
            result = crew.invoke(state)

        st.success("✅ Analysis complete!")

        st.markdown("**🔎 Detected Symbol**")
        st.write(result.get("symbol", "N/A"))

        st.markdown("**💵 Latest Price**")
        st.write(result.get("latest_price", "N/A"))

        st.markdown("**💰 Valuation**")
        st.write(result.get("valuation", "N/A"))

        st.markdown("**📊 Analysis**")
        st.write(result.get("analysis", "N/A"))

        chart_path = result.get("chart")
        if chart_path and os.path.exists(chart_path):
            st.subheader("📉 1-Year Price Chart")
            st.image(chart_path, use_container_width=True)
        else:
            st.info("No chart generated.")

# -------------------------------------------------
# TAB 2: LIVE WATCHLIST
# -------------------------------------------------
with tab2:
    st.subheader("📌 Watchlist")

    company_input = st.text_input("Enter company name or ticker symbol:")

    if st.button("➕ Search & Add"):
        if company_input.strip():
            matches = search_symbol(company_input.strip())
            if not matches:
                st.error("❌ No matches found.")
            elif len(matches) == 1:
                sym = matches[0]["symbol"]
                if sym not in st.session_state.watchlist:
                    st.session_state.watchlist.append(sym)
                    save_watchlist(st.session_state.watchlist)
                    st.success(f"Added {sym} ({matches[0]['name']}) to watchlist.")
                    st.rerun()
                else:
                    st.info(f"{sym} is already in your watchlist.")
            else:
                st.session_state["matches"] = matches
        else:
            st.warning("⚠️ Please enter a company name or symbol.")

    # Handle multiple match dropdown
    if "matches" in st.session_state and st.session_state["matches"]:
        selected = st.selectbox(
            "Multiple matches found. Please pick one:",
            [f"{m['symbol']} - {m['name']} ({m['exchange']})" for m in st.session_state["matches"]],
        )
        if st.button("✅ Confirm Add"):
            sym = selected.split(" - ")[0]
            if sym not in st.session_state.watchlist:
                st.session_state.watchlist.append(sym)
                save_watchlist(st.session_state.watchlist)
                st.success(f"Added {sym} to watchlist.")
                st.session_state.pop("matches")
                st.rerun()
            else:
                st.info(f"{sym} is already in your watchlist.")

    if st.button("🗑 Clear All"):
        st.session_state.watchlist = []
        save_watchlist(st.session_state.watchlist)
        st.warning("Watchlist cleared.")
        st.rerun()

    st.markdown("---")

    if st.session_state.watchlist:
        if st.button("🔄 Refresh Prices Now"):
            st.rerun()

        rows = [fetch_stock_row(sym) for sym in st.session_state.watchlist]
        df = pd.DataFrame(rows, columns=["Symbol", "Current Price", "Change", "% Change", "P/E Ratio", "P/B Ratio"])

        def color_change(val: str):
            try:
                if isinstance(val, str) and val not in ("N/A", ""):
                    return "color: green;" if val.strip().startswith("+") else "color: red;"
            except Exception:
                pass
            return ""

        st.dataframe(
            df.style.applymap(color_change, subset=["Change", "% Change"]),
            use_container_width=True,
            height=400,
        )
    else:
        st.info("Your watchlist is empty. Add companies above to get started.")
