"""Price levels measured from real bars.

Claude chooses which levels matter for a strategy, but it never invents the
numbers. They all come from this file.

Run `python levels.py` to check the math against a small made-up data set.
"""
import pandas


def average_true_range(daily, days=14):
    """Average daily range over the last `days` completed sessions.

    "True range" is the day's high minus low, widened to include any gap from
    the previous close.
    """
    previous_close = daily["Close"].shift(1)
    high_minus_low = daily["High"] - daily["Low"]
    gap_up = (daily["High"] - previous_close).abs()
    gap_down = (daily["Low"] - previous_close).abs()
    true_range = pandas.concat([high_minus_low, gap_up, gap_down], axis=1).max(axis=1)

    completed_days = true_range.iloc[:-1]  # the last bar may be today, still trading
    return completed_days.tail(days).mean()


def key_levels(daily, intraday=None, opening_range_minutes=15):
    """Return a dictionary of levels.

    daily:    daily OHLC bars, oldest first, at least 21 rows
    intraday: optional 5-minute bars; adds the opening range of the latest session
    """
    previous_day = daily.iloc[-2]      # last completed session
    last_20_days = daily.iloc[-21:-1]  # the 20 sessions before the newest bar

    levels = {
        "last": daily["Close"].iloc[-1],
        "prev_high": previous_day["High"],
        "prev_low": previous_day["Low"],
        "prev_close": previous_day["Close"],
        "high_20d": last_20_days["High"].max(),
        "low_20d": last_20_days["Low"].min(),
        "atr14": average_true_range(daily),
    }

    if intraday is not None and len(intraday) > 0:
        latest_date = intraday.index[-1].date()
        todays_bars = intraday[intraday.index.date == latest_date]
        session_open = todays_bars.index[0]
        range_end = session_open + pandas.Timedelta(minutes=opening_range_minutes)
        opening_bars = todays_bars[todays_bars.index < range_end]
        levels["orb_high"] = opening_bars["High"].max()
        levels["orb_low"] = opening_bars["Low"].min()

    rounded = {}
    for name, value in levels.items():
        rounded[name] = round(float(value), 2)
    return rounded


def self_check():
    """25 days where the high rises by 1 each day, so every answer is easy to work out by hand."""
    days = pandas.date_range("2026-01-01", periods=25, freq="D")
    daily = pandas.DataFrame(
        {"High": range(11, 36), "Low": range(9, 34), "Close": range(10, 35)},
        index=days, dtype=float,
    )
    minutes = pandas.date_range("2026-01-25 09:30", periods=12, freq="5min")
    intraday = pandas.DataFrame(
        {"High": [40, 41, 42] + [50] * 9, "Low": [38, 37, 39] + [30] * 9, "Close": 40.0},
        index=minutes,
    )

    levels = key_levels(daily, intraday)
    assert levels["prev_high"] == 34 and levels["prev_low"] == 32 and levels["prev_close"] == 33, levels
    assert levels["high_20d"] == 34 and levels["low_20d"] == 13, levels
    assert levels["atr14"] == 2.0, levels  # no gaps, so true range = high - low = 2
    assert levels["orb_high"] == 42 and levels["orb_low"] == 37, levels  # first 15 minutes = 3 bars
    print("levels ok", levels)


if __name__ == "__main__":
    self_check()
