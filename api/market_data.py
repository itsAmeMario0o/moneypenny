"""News and price bars from Yahoo Finance (free, delayed)."""
import yfinance

# How much history to request for each bar size.
PERIOD_FOR_INTERVAL = {"1d": "6mo", "60m": "1mo", "15m": "5d", "5m": "5d"}


def fetch_news(ticker):
    """Return recent headlines as a list of dictionaries."""
    raw_items = yfinance.Ticker(ticker).news or []
    headlines = []
    for item in raw_items:
        content = item.get("content", item)  # newer yfinance nests the fields under "content"
        title = content.get("title")
        if not title:
            continue
        provider = content.get("provider") or {}
        link = content.get("canonicalUrl") or {}
        headlines.append({
            "title": title,
            "summary": content.get("summary") or "",
            "publisher": provider.get("displayName") or content.get("publisher"),
            "published": content.get("pubDate"),
            "url": link.get("url") or content.get("link"),
        })
    return headlines


def fetch_bars(ticker, interval):
    """Return a pandas DataFrame of OHLC bars, oldest first. Empty if the ticker is unknown."""
    period = PERIOD_FOR_INTERVAL[interval]
    return yfinance.Ticker(ticker).history(period=period, interval=interval)


def bars_for_chart(ticker, interval):
    """Bars in the format the web chart expects."""
    frame = fetch_bars(ticker, interval)
    bars = []
    for timestamp, row in frame.iterrows():
        bars.append({
            "time": int(timestamp.timestamp()),
            "open": row["Open"],
            "high": row["High"],
            "low": row["Low"],
            "close": row["Close"],
        })
    return bars
