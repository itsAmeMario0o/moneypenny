"""Tool: latest headlines for a ticker."""
import market_data

TITLE = "Headlines"
DESCRIPTION = "The latest news headlines for the ticker from Yahoo Finance. No AI involved, no token cost."


def run(ticker):
    rows = []
    for item in market_data.fetch_news(ticker):
        rows.append({
            "published": (item["published"] or "")[:16].replace("T", " "),
            "publisher": item["publisher"],
            "title": item["title"],
        })
    return rows
