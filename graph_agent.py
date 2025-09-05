import os
import yfinance as yf
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from typing import TypedDict, Optional, Any

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI

# --------------------------------------------------------
# Load environment variables
# --------------------------------------------------------
load_dotenv()

# Get Gemini API key
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("❌ GOOGLE_API_KEY not found in .env file!")

# Initialize Gemini LLM
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GEMINI_API_KEY)

# --------------------------------------------------------
# Define State schema
# --------------------------------------------------------
class StockState(TypedDict, total=False):
    query: str
    symbol: str
    data: Any
    latest_price: Optional[float]
    valuation: str
    analysis: str
    chart: Optional[str]

# --------------------------------------------------------
# Nodes
# --------------------------------------------------------

def auto_symbol_node(state: StockState):
    """Detect stock symbol from query using Gemini"""
    query = state.get("query", "")
    if not query:
        return {"symbol": ""}

    prompt = f"Extract the stock ticker symbol (Yahoo Finance format) for this query: '{query}'. Reply only with the ticker symbol."
    response = llm.invoke(prompt)
    symbol = response.content.strip().upper()
    return {"symbol": symbol}


def fetcher_node(state: StockState):
    """Fetch stock data, latest price, and generate 1Y chart"""
    symbol = state.get("symbol", "")
    if not symbol:
        return {"data": None, "latest_price": None, "chart": None}

    chart_path = None
    latest_price = None
    hist = None

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1y")

        if not hist.empty:
            # Latest price = last Close
            latest_price = round(hist["Close"].iloc[-1], 2)

            # Generate chart
            chart_path = f"{symbol}_chart.png"
            plt.figure(figsize=(10, 5))
            plt.plot(hist.index, hist["Close"], label=f"{symbol} Close Price")
            plt.title(f"{symbol} - 1 Year Price Chart")
            plt.xlabel("Date")
            plt.ylabel("Price")
            plt.legend()
            plt.grid(True)
            plt.savefig(chart_path)
            plt.close()
    except Exception as e:
        return {"data": None, "latest_price": None, "chart": None, "analysis": f"Error fetching data: {e}"}

    return {
        "data": hist if hist is not None else None,
        "latest_price": latest_price,
        "chart": chart_path
    }


def valuation_node(state: StockState):
    """Get valuation commentary using Gemini"""
    symbol = state.get("symbol", "")
    if not symbol:
        return {"valuation": "No symbol available for valuation."}

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        pe = info.get("trailingPE")
        pb = info.get("priceToBook")
        roe = info.get("returnOnEquity")

        fundamentals = f"P/E: {pe}, P/B: {pb}, ROE: {roe}"
        prompt = f"Stock {symbol} fundamentals: {fundamentals}. Provide a short valuation commentary."
        response = llm.invoke(prompt)
        return {"valuation": response.content}
    except Exception:
        return {"valuation": "Valuation data unavailable."}


def analysis_node(state: StockState):
    """Get broader analysis using Gemini"""
    symbol = state.get("symbol", "")
    data = state.get("data", None)

    if not symbol or data is None:
        return {"analysis": "No data available for analysis."}

    latest_price = state.get("latest_price", "N/A")
    prompt = f"""
    Analyze the stock {symbol} based on its last 1 year price trend and fundamentals.
    The current stock price is {latest_price}.
    Give a concise technical + fundamental outlook in 4-5 lines.
    """
    response = llm.invoke(prompt)

    return {"analysis": response.content}

# --------------------------------------------------------
# Build Graph
# --------------------------------------------------------
workflow = StateGraph(StockState)

workflow.add_node("AutoSymbol", auto_symbol_node)
workflow.add_node("Fetcher", fetcher_node)
workflow.add_node("Valuation", valuation_node)
workflow.add_node("Analysis", analysis_node)

workflow.set_entry_point("AutoSymbol")
workflow.add_edge("AutoSymbol", "Fetcher")
workflow.add_edge("Fetcher", "Valuation")
workflow.add_edge("Valuation", "Analysis")
workflow.add_edge("Analysis", END)

crew = workflow.compile()

# --------------------------------------------------------
# Run standalone
# --------------------------------------------------------
if __name__ == "__main__":
    query = input("Enter stock/company name: ")
    state = {"query": query}
    result = crew.invoke(state)

    print("\n--- RESULT ---")
    print("Symbol:", result.get("symbol"))
    print("Latest Price:", result.get("latest_price"))
    print("Valuation:", result.get("valuation"))
    print("Analysis:", result.get("analysis"))
    print("Chart saved at:", result.get("chart"))
