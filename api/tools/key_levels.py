"""Tool: measured price levels for a ticker."""
import market_data
from levels import key_levels

TITLE = "Key levels"
DESCRIPTION = "Prior-day high/low/close, 20-day range, ATR and today's opening range, measured from price bars."


def run(ticker):
    daily = market_data.fetch_bars(ticker, "1d")
    if len(daily) < 21:
        return {"error": "Not enough price history for " + ticker}
    return key_levels(daily, market_data.fetch_bars(ticker, "5m"))
