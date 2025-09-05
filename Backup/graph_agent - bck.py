import os
from dotenv import load_dotenv
import yfinance as yf
from typing import TypedDict, List

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END

# =============================
# Load environment variables
# =============================
load_dotenv()

# Setup Gemini (Google Generative AI)
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    raise ValueError("⚠️ GOOGLE_API_KEY not found in environment. Please set it in your .env file")

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=google_api_key,
    temperature=0
)

# =============================
# Define state structure
# =============================
class AgentState(TypedDict):
    query: str
    symbols: List[str]
    data: dict
    valuation: str
    answer: str

# =============================
# Planner Node
# =============================
def planner_node(state: AgentState) -> AgentState:
    print(f"[Planner] Got query: {state['query']}, symbols: {state['symbols']}")
    return state

# =============================
# Fetcher Node
# =============================
def fetcher_node(state: AgentState) -> AgentState:
    data = {}
    for symbol in state["symbols"]:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d")

        # last price
        last_price = None
        if not hist.empty:
            last_price = hist["Close"].iloc[-1]

        # fundamentals
        info = ticker.info
        fundamentals = {
            "last_price": float(last_price) if last_price else None,
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "pb_ratio": info.get("priceToBook"),
            "debt_to_equity": info.get("debtToEquity"),
            "roe": info.get("returnOnEquity"),
            "revenue_growth": info.get("revenueGrowth"),
        }

        data[symbol] = fundamentals

    state["data"] = data
    print(f"[Fetcher] Data fetched for {list(data.keys())}")
    return state

# =============================
# Valuation Node
# =============================
def valuation_node(state: AgentState) -> AgentState:
    lines = []
    for symbol, d in state["data"].items():
        lines.append(f"""
{symbol} Fundamentals:
- Last Price: {d['last_price']}
- Market Cap: {d['market_cap']}
- P/E Ratio: {d['pe_ratio']}
- P/B Ratio: {d['pb_ratio']}
- Debt/Equity: {d['debt_to_equity']}
- ROE: {d['roe']}
- Revenue Growth: {d['revenue_growth']}
""")
    state["valuation"] = "\n".join(lines)
    print("[Valuation] Done")
    return state

# =============================
# Answer Node (Gemini LLM)
# =============================
def answer_node(state: AgentState) -> AgentState:
    prompt = f"""
You are a financial assistant.
User asked: {state['query']}
Stock data:
{state['valuation']}
Give a simple clear answer.
"""
    response = llm.invoke(prompt)
    state["answer"] = response.content
    print("[Answer] Done")
    return state

# =============================
# Build Graph
# =============================
workflow = StateGraph(AgentState)

workflow.add_node("planner", planner_node)
workflow.add_node("fetcher", fetcher_node)
workflow.add_node("valuation", valuation_node)
workflow.add_node("answer", answer_node)

workflow.set_entry_point("planner")
workflow.add_edge("planner", "fetcher")
workflow.add_edge("fetcher", "valuation")
workflow.add_edge("valuation", "answer")
workflow.add_edge("answer", END)

crew = workflow.compile()

# =============================
# Run App
# =============================
if __name__ == "__main__":
    query = input("Enter your stock query: ")
    symbols = input("Enter stock symbols (comma separated, e.g. INFY.NS,TCS.NS): ").split(",")
    symbols = [s.strip() for s in symbols if s.strip()]

    state = {
        "query": query,
        "symbols": symbols,
        "data": {},
        "valuation": "",
        "answer": ""
    }

    result = crew.invoke(state)
    print("\n=== Final Answer ===")
    print(result["answer"])
