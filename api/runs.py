"""TradingAgents runs: start one, watch it step by step, save what each agent says.

A run takes several minutes, so it works in a background thread. While it
works we save an "event" each time an agent produces something. The dashboard
reads those events to show the team live.

Run `python runs.py` to check the event-detection logic with a fake run.
"""
import os
import threading
from datetime import date

import database
import telegram

# The team, in the order they work. `stage` groups them into columns on the dashboard.
AGENTS = [
    {"key": "market", "name": "Market analyst", "stage": "Analysts"},
    {"key": "social", "name": "Sentiment analyst", "stage": "Analysts"},
    {"key": "news", "name": "News analyst", "stage": "Analysts"},
    {"key": "fundamentals", "name": "Fundamentals analyst", "stage": "Analysts"},
    {"key": "bull", "name": "Bull researcher", "stage": "Research debate"},
    {"key": "bear", "name": "Bear researcher", "stage": "Research debate"},
    {"key": "research_manager", "name": "Research manager", "stage": "Research debate"},
    {"key": "trader", "name": "Trader", "stage": "Trader"},
    {"key": "risk_aggressive", "name": "Aggressive risk", "stage": "Risk debate"},
    {"key": "risk_conservative", "name": "Conservative risk", "stage": "Risk debate"},
    {"key": "risk_neutral", "name": "Neutral risk", "stage": "Risk debate"},
    {"key": "portfolio_manager", "name": "Portfolio manager", "stage": "Decision"},
]

ANALYST_KEYS = ["market", "social", "news", "fundamentals"]
REPORT_NAMES = ["market_report", "sentiment_report", "news_report", "fundamentals_report",
                "investment_plan", "trader_investment_plan", "final_trade_decision"]


class RunError(Exception):
    """A problem with the request that we can explain to the user."""


def default_settings():
    return {
        "analysts": list(ANALYST_KEYS),
        "depth": 1,
        "deep_model": os.environ.get("TA_DEEP_MODEL", "claude-opus-5-5"),
        "quick_model": os.environ.get("TA_QUICK_MODEL", "claude-sonnet-5-5"),
    }


def check_settings(settings):
    """Fill in defaults and reject values that make no sense. Returns clean settings."""
    clean = default_settings()

    if settings.get("analysts"):
        for analyst in settings["analysts"]:
            if analyst not in ANALYST_KEYS:
                raise RunError("Unknown analyst: " + str(analyst))
        clean["analysts"] = settings["analysts"]

    if settings.get("depth"):
        if settings["depth"] not in [1, 2, 3]:
            raise RunError("Depth must be 1, 2 or 3.")
        clean["depth"] = settings["depth"]

    for name in ["deep_model", "quick_model"]:
        if settings.get(name):
            clean[name] = settings[name].strip()
    return clean


def check_trade_date(text):
    """Return a valid YYYY-MM-DD date, defaulting to today."""
    if not text:
        return date.today().isoformat()
    try:
        chosen = date.fromisoformat(text)
    except ValueError:
        raise RunError("Date must look like 2026-11-19.")
    if chosen > date.today():
        raise RunError("Date cannot be in the future.")
    return chosen.isoformat()


# ---------- turning the run's state into events ----------

def read_agent_texts(state):
    """Pull out what each agent has written so far from a TradingAgents state dictionary."""
    debate = state.get("investment_debate_state") or {}
    risk = state.get("risk_debate_state") or {}
    return {
        "market": state.get("market_report") or "",
        "social": state.get("sentiment_report") or "",
        "news": state.get("news_report") or "",
        "fundamentals": state.get("fundamentals_report") or "",
        "bull": debate.get("bull_history") or "",
        "bear": debate.get("bear_history") or "",
        "research_manager": state.get("investment_plan") or "",
        "trader": state.get("trader_investment_plan") or "",
        "risk_aggressive": risk.get("aggressive_history") or "",
        "risk_conservative": risk.get("conservative_history") or "",
        "risk_neutral": risk.get("neutral_history") or "",
        "portfolio_manager": state.get("final_trade_decision") or "",
    }


def find_new_events(seen_texts, state):
    """Compare the state with what we've already seen. Return a list of (agent, new text).

    seen_texts is a dictionary we update, so each piece of text is reported once.
    Debate histories grow over time; for those we report only the added part.
    """
    events = []
    for agent, text in read_agent_texts(state).items():
        text = str(text)
        already_seen = seen_texts.get(agent, "")
        if text == "" or text == already_seen:
            continue
        if text.startswith(already_seen):
            new_part = text[len(already_seen):].strip()
        else:
            new_part = text
        seen_texts[agent] = text
        events.append((agent, new_part))
    return events


# ---------- running ----------

def do_run(run_id, ticker, trade_date, settings, thesis_id):
    """The background job. Streams the run and saves events, then the final result."""
    from langchain_core.callbacks import UsageMetadataCallbackHandler
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.graph.trading_graph import TradingAgentsGraph, run_rating

    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = "anthropic"
    config["deep_think_llm"] = settings["deep_model"]
    config["quick_think_llm"] = settings["quick_model"]
    config["max_debate_rounds"] = settings["depth"]
    config["max_risk_discuss_rounds"] = settings["depth"]

    token_counter = UsageMetadataCallbackHandler()  # adds up tokens across every agent's calls
    try:
        graph = TradingAgentsGraph(selected_analysts=settings["analysts"], config=config, callbacks=[token_counter])
        start_state = graph.create_run_state(ticker, trade_date)
        graph_arguments = graph.propagator.get_graph_args()

        final_state = {}
        seen_texts = {}
        for messages, state in graph.stream_run(start_state, **graph_arguments):
            if state is None:
                continue
            final_state.update(state)
            for agent, text in find_new_events(seen_texts, state):
                database.insert_run_event(run_id, agent, text)

        signal = run_rating(final_state)
        reports = {}
        for name in REPORT_NAMES:
            reports[name] = final_state.get(name)
        database.update_run(run_id, status="done", signal=signal, reports=reports, finished=database.now_text())
        if thesis_id is not None:
            research = dict(reports)
            research["signal"] = signal
            database.update_thesis(thesis_id, research=research, status="researched")
        telegram.send_message(finished_message(run_id, ticker, signal, reports))
    except Exception as error:
        message = "Run failed: " + str(error)
        database.update_run(run_id, status="error", error=message, finished=database.now_text())
        if thesis_id is not None:
            database.update_thesis(thesis_id, status="error", error=message)
        telegram.send_message("Run #" + str(run_id) + " " + ticker + " FAILED\n" + str(error)[:300])

    # Record tokens even if the run failed part-way; they were still spent.
    for model, counts in token_counter.usage_metadata.items():
        database.record_usage(thesis_id, "research", model, counts["input_tokens"], counts["output_tokens"], run_id)


def finished_message(run_id, ticker, signal, reports):
    """The Telegram text for a finished run: the rating and the start of the final decision."""
    text = "Run #" + str(run_id) + " " + ticker + " finished: " + str(signal)
    decision = reports.get("final_trade_decision") or ""
    if decision != "":
        text = text + "\n\n" + decision[:700]
        if len(decision) > 700:
            text = text + "..."
    return text + "\n\nFull reports: http://localhost:5173 (Agent runs)"


def start_run(ticker, trade_date=None, settings=None, thesis_id=None):
    """Validate the request, save a new run row, and start the background job. Returns the run id."""
    ticker = ticker.strip().upper()
    if ticker == "":
        raise RunError("Enter a ticker.")
    trade_date = check_trade_date(trade_date)
    settings = check_settings(settings or {})

    run_id = database.insert_run(ticker, trade_date, settings, thesis_id)
    thread = threading.Thread(target=do_run, args=(run_id, ticker, trade_date, settings, thesis_id), daemon=True)
    thread.start()
    return run_id


def self_check():
    seen = {}
    # 1. an analyst files a report
    events = find_new_events(seen, {"market_report": "Trend is down."})
    assert events == [("market", "Trend is down.")], events
    # 2. same state again: nothing new
    assert find_new_events(seen, {"market_report": "Trend is down."}) == []
    # 3. the debate starts; only the bull has spoken
    state = {"market_report": "Trend is down.", "investment_debate_state": {"bull_history": "Bull: buy.", "bear_history": ""}}
    assert find_new_events(seen, state) == [("bull", "Bull: buy.")]
    # 4. the bull speaks again: we report only the added part
    state["investment_debate_state"]["bull_history"] = "Bull: buy.\nBull: still buy."
    assert find_new_events(seen, state) == [("bull", "Bull: still buy.")]

    assert check_settings({})["depth"] == 1
    assert check_settings({"analysts": ["news"], "depth": 3})["analysts"] == ["news"]
    for bad in [{"analysts": ["astrology"]}, {"depth": 9}]:
        try:
            check_settings(bad)
            assert False, "should have been rejected: " + str(bad)
        except RunError:
            pass
    message = finished_message(7, "CSCO", "Buy", {"final_trade_decision": "x" * 900})
    assert message.startswith("Run #7 CSCO finished: Buy") and "x" * 700 + "..." in message
    assert "finished: Hold" in finished_message(8, "SPY", "Hold", {})
    print("runs ok")


if __name__ == "__main__":
    self_check()
