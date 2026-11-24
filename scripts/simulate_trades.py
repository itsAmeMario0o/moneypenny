"""Fill the trade journal with SIMULATED trades for demos. None of these trades are real.

What it makes:
  - about 12 months of day trades ending today, in an account called "Simulated account"
  - every entry and exit price sits inside that day's real low-high range (from Yahoo)
  - a profit target for each month that follows the real market: MONTHLY_PROFIT on
    average, more in months when SPY rose, less (or a loss) in months when it fell
  - in the last few sessions the trades are long from the open to the close,
    so their results follow what the market really did on those days

Run it from the Moneypenny folder (it runs inside the api container, which has yfinance):

    docker compose exec -T api python - < scripts/simulate_trades.py

Running it again deletes the old simulated account and makes a new one.
"""
import json
import random
import urllib.request
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import yfinance

JOURNAL_URL = "http://journal:3000/api"
ACCOUNT_NAME = "Simulated account"
STARTING_BALANCE = 100000
MONTHLY_PROFIT = 3500        # the average month
DOLLARS_PER_MARKET_PERCENT = 600   # extra profit for each 1% SPY moved that month
MONTHLY_NOISE = 1500         # random extra, up or down, so months are not too tidy
MONTHS_BACK = 12
MARKET_DAYS = 5              # the last sessions, where trades follow the real market
FEE = 1.0                    # dollars per fill
SYMBOLS = ["SPY", "QQQ", "NVDA", "AAPL", "MSFT", "AMD", "META", "TSLA"]
NEW_YORK = ZoneInfo("America/New_York")


def call_journal(method, path, body=None):
    data = None
    if body is not None:
        data = json.dumps(body).encode()
    request = urllib.request.Request(JOURNAL_URL + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as reply:
        return json.loads(reply.read())


def load_daily_bars(start_day):
    """Returns {symbol: {date: (open, high, low, close)}} from Yahoo."""
    bars = {}
    for symbol in SYMBOLS:
        frame = yfinance.Ticker(symbol).history(start=start_day.isoformat(), interval="1d", auto_adjust=False)
        days = {}
        for timestamp, row in frame.iterrows():
            days[timestamp.date()] = (row["Open"], row["High"], row["Low"], row["Close"])
        bars[symbol] = days
    return bars


def month_of(day):
    return day.strftime("%Y-%m")


def time_text(day, minutes_after_open):
    """A UTC timestamp for `day`, some minutes after the 9:30 New York open."""
    local = datetime(day.year, day.month, day.day, 9, 30, tzinfo=NEW_YORK)
    local = local + timedelta(minutes=minutes_after_open, seconds=random.randint(0, 59))
    return local.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def make_random_trade(day, symbol, bar):
    """One day trade somewhere inside the day's range."""
    day_open, high, low, close = bar
    day_range = high - low
    is_long = random.random() < 0.70
    # Trading with the day's real direction wins more often than trading against it.
    stock_rose = close > day_open
    if is_long == stock_rose:
        is_win = random.random() < 0.66
    else:
        is_win = random.random() < 0.40
    if is_win:
        move = day_range * random.uniform(0.25, 0.60)
    else:
        move = day_range * random.uniform(0.15, 0.35)
    lower_price = low + random.random() * (day_range - move)
    upper_price = lower_price + move

    # A long wins when it buys low and sells high; a short wins the other way round.
    if is_long == is_win:
        buy_price, sell_price = lower_price, upper_price
    else:
        buy_price, sell_price = upper_price, lower_price

    entry_minute = random.randint(5, 300)
    return {
        "day": day, "symbol": symbol, "is_long": is_long,
        "buy_price": round(buy_price, 2), "sell_price": round(sell_price, 2),
        "quantity": max(1, round(random.uniform(30000, 60000) / day_open)),
        "entry_minute": entry_minute, "exit_minute": entry_minute + random.randint(5, 85),
        "follows_market": False,
    }


def make_market_trade(day, symbol, bar):
    """A long trade from just after the open to just before the close: the real day's move."""
    day_open, high, low, close = bar
    return {
        "day": day, "symbol": symbol, "is_long": True,
        "buy_price": round(day_open, 2), "sell_price": round(close, 2),
        "quantity": max(1, round(20000 / day_open)),
        "entry_minute": random.randint(2, 20), "exit_minute": random.randint(360, 388),
        "follows_market": True,
    }


def profit_before_fees(trade):
    return trade["quantity"] * (trade["sell_price"] - trade["buy_price"])


def total_profit(trades):
    total = 0.0
    for trade in trades:
        total = total + profit_before_fees(trade) - 2 * FEE
    return total


def make_all_trades(bars):
    trading_days = sorted(bars["SPY"].keys())
    market_days = trading_days[-MARKET_DAYS:]
    trades = []
    for day in trading_days:
        if day in market_days:
            for symbol in random.sample(SYMBOLS, 2):
                if day in bars[symbol]:
                    trades.append(make_market_trade(day, symbol, bars[symbol][day]))
            continue
        if random.random() < 0.25:
            continue  # a day off
        for symbol in random.sample(SYMBOLS, random.randint(1, 3)):
            if day in bars[symbol]:
                trades.append(make_random_trade(day, symbol, bars[symbol][day]))
    return trades


def market_percent_by_month(spy_bars):
    """How far SPY moved in each month of the period, in percent: {"2026-04": 9.9, ...}."""
    first_open = {}
    last_close = {}
    for day in sorted(spy_bars.keys()):
        day_open, high, low, close = spy_bars[day]
        month = month_of(day)
        if month not in first_open:
            first_open[month] = day_open
        last_close[month] = close
    percents = {}
    for month in first_open:
        percents[month] = (last_close[month] / first_open[month] - 1) * 100
    return percents


def monthly_targets(market_percents):
    """Profit to aim for in each month. The average of all months is MONTHLY_PROFIT."""
    raw = {}
    for month in market_percents:
        raw[month] = DOLLARS_PER_MARKET_PERCENT * market_percents[month] + random.uniform(-MONTHLY_NOISE, MONTHLY_NOISE)
    average = sum(raw.values()) / len(raw)
    targets = {}
    for month in raw:
        targets[month] = MONTHLY_PROFIT + raw[month] - average
    return targets


def scale_month(trades, target):
    """Makes one month's trades add up to `target` by resizing only the winning trades."""
    winners = []
    wins = 0.0
    everything_else = 0.0   # losing trades, market-following trades and fees
    for trade in trades:
        profit = profit_before_fees(trade)
        if profit > 0 and not trade["follows_market"]:
            winners.append(trade)
            wins = wins + profit
        else:
            everything_else = everything_else + profit
        everything_else = everything_else - 2 * FEE
    factor = (target - everything_else) / wins
    factor = max(factor, 0.2)   # never shrink winners to almost nothing
    for trade in winners:
        trade["quantity"] = max(1, round(trade["quantity"] * factor))


def to_executions(trades):
    """The journal wants raw fills: one entry fill and one exit fill per trade."""
    fills = []
    for trade in trades:
        buy = {"symbol": trade["symbol"], "side": "buy", "quantity": trade["quantity"],
               "price": trade["buy_price"], "fee": FEE}
        sell = {"symbol": trade["symbol"], "side": "sell", "quantity": trade["quantity"],
                "price": trade["sell_price"], "fee": FEE}
        if trade["is_long"]:
            buy["executedAt"] = time_text(trade["day"], trade["entry_minute"])
            sell["executedAt"] = time_text(trade["day"], trade["exit_minute"])
        else:
            sell["executedAt"] = time_text(trade["day"], trade["entry_minute"])
            buy["executedAt"] = time_text(trade["day"], trade["exit_minute"])
        fills.append(buy)
        fills.append(sell)
    return fills


def replace_account(fills):
    for account in call_journal("GET", "/accounts")["accounts"]:
        if account["name"] == ACCOUNT_NAME:
            call_journal("DELETE", "/accounts/" + account["id"])
    account_id = call_journal("POST", "/accounts", {
        "name": ACCOUNT_NAME, "kind": "import", "broker": "simulated", "initialBalance": STARTING_BALANCE,
    })["id"]
    # send 200 fills at a time
    for start in range(0, len(fills), 200):
        call_journal("POST", "/executions", {"accountId": account_id, "executions": fills[start:start + 200]})
    return account_id


def main():
    random.seed(7)  # the same seed gives the same trades each run
    start_day = date.today() - timedelta(days=MONTHS_BACK * 30.5)
    bars = load_daily_bars(start_day)
    trades = make_all_trades(bars)

    market_percents = market_percent_by_month(bars["SPY"])
    targets = monthly_targets(market_percents)
    print("month     SPY move   target   simulated profit")
    for month in sorted(targets):
        month_trades = []
        for trade in trades:
            if month_of(trade["day"]) == month:
                month_trades.append(trade)
        scale_month(month_trades, targets[month])
        print("%s   %+5.1f%%   $%6.0f   $%6.0f" % (month, market_percents[month], targets[month], total_profit(month_trades)))

    profit = total_profit(trades)
    average = profit / len(targets)
    # self-check: the average month is close to what was asked for
    assert abs(average - MONTHLY_PROFIT) < 300, average

    replace_account(to_executions(trades))
    print("trades:", len(trades), "from", trades[0]["day"], "to", trades[-1]["day"])
    print("total profit: $%.0f over %d calendar months, average $%.0f a month" % (profit, len(targets), average))


main()
