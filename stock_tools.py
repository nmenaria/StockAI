import yfinance as yf

def get_fundamentals(symbol: str) -> dict:
    stock = yf.Ticker(symbol)
    info = stock.info

    return {
        "symbol": symbol,
        "currentPrice": info.get("currentPrice"),
        "marketCap": info.get("marketCap"),
        "peRatio": info.get("trailingPE"),
        "pbRatio": info.get("priceToBook"),
        "roe": info.get("returnOnEquity"),
        "roa": info.get("returnOnAssets"),
    }

def get_technicals(symbol: str) -> dict:
    stock = yf.Ticker(symbol)
    hist = stock.history(period="6mo")
    if hist.empty:
        return {"error": "No data"}

    ma50 = hist["Close"].rolling(50).mean().iloc[-1]
    ma200 = hist["Close"].rolling(200).mean().iloc[-1]

    return {
        "symbol": symbol,
        "lastClose": hist["Close"].iloc[-1],
        "ma50": round(ma50, 2),
        "ma200": round(ma200, 2),
        "trend": "Bullish" if ma50 > ma200 else "Bearish",
    }

def get_valuation(symbol: str) -> dict:
    fundamentals = get_fundamentals(symbol)
    pe = fundamentals.get("peRatio")
    pb = fundamentals.get("pbRatio")

    if not pe or not pb:
        return {"symbol": symbol, "valuation": "Data not available"}

    if pe < 15 and pb < 1.5:
        status = "Undervalued"
    elif pe < 25 and pb < 3:
        status = "Fairly valued"
    else:
        status = "Overvalued"

    return {
        "symbol": symbol,
        "peRatio": pe,
        "pbRatio": pb,
        "valuation": status,
    }
