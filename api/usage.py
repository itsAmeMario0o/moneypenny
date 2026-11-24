"""Token meter: add up the token_usage table and estimate what it cost.

Run `python usage.py` to check the arithmetic.
"""
import os

import database

DAILY_TOKEN_BUDGET = int(os.environ.get("DAILY_TOKEN_BUDGET", "1000000"))

# US dollars per million tokens: (input, output). Standard API prices; ignores
# prompt-cache discounts, so the estimate can run slightly high.
PRICES = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}


def cost_of(model, input_tokens, output_tokens):
    """Estimated dollars for one usage row. Unknown models count as $0."""
    if model not in PRICES:
        return 0.0
    input_price, output_price = PRICES[model]
    return (input_tokens * input_price + output_tokens * output_price) / 1_000_000


def empty_total():
    return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost": 0.0, "calls": 0}


def add_row(total, row):
    total["input_tokens"] += row["input_tokens"]
    total["output_tokens"] += row["output_tokens"]
    total["total_tokens"] += row["input_tokens"] + row["output_tokens"]
    total["cost"] += cost_of(row["model"], row["input_tokens"], row["output_tokens"])
    total["calls"] += 1


def summarize(rows, today):
    """Group usage rows. `today` is a date string like 2026-11-19 (UTC)."""
    summary = {
        "budget": DAILY_TOKEN_BUDGET,
        "today": empty_total(),
        "all_time": empty_total(),
        "by_step": {},
        "by_model": {},
        "by_thesis": {},
        "by_run": {},
    }
    for row in rows:
        add_row(summary["all_time"], row)
        if row["created"].startswith(today):
            add_row(summary["today"], row)

        groupings = [("by_step", row["step"]), ("by_model", row["model"]),
                     ("by_thesis", row["thesis_id"]), ("by_run", row["run_id"])]
        for group_name, key in groupings:
            if key is None:
                continue  # e.g. a Claude call that belongs to no run
            group = summary[group_name]
            if key not in group:
                group[key] = empty_total()
            add_row(group[key], row)

    summary["percent_of_budget"] = round(100 * summary["today"]["total_tokens"] / DAILY_TOKEN_BUDGET, 1)
    return summary


def current_summary():
    today = database.now_text()[:10]
    return summarize(database.list_usage(), today)


def self_check():
    rows = [
        {"created": "2026-11-19T10:00:00+00:00", "thesis_id": 1, "run_id": None, "step": "thesis",
         "model": "claude-opus-5-5", "input_tokens": 1_000_000, "output_tokens": 100_000},
        {"created": "2026-11-18T10:00:00+00:00", "thesis_id": 1, "run_id": 7, "step": "research",
         "model": "claude-sonnet-5-5", "input_tokens": 500_000, "output_tokens": 0},
    ]
    summary = summarize(rows, "2026-11-19")
    assert summary["today"]["total_tokens"] == 1_100_000, summary["today"]
    assert summary["today"]["cost"] == 4.00 + 2.00, summary["today"]       # 1M in @ $4 + 0.1M out @ $20
    assert summary["all_time"]["cost"] == 6.00 + 1.00, summary["all_time"]  # plus 0.5M in @ $2
    assert summary["by_thesis"][1]["calls"] == 2
    assert summary["by_step"]["research"]["input_tokens"] == 500_000
    assert list(summary["by_run"].keys()) == [7]  # the call with no run is left out
    print("usage ok")


if __name__ == "__main__":
    self_check()
