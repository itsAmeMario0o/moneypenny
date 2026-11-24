"""The five-step pipeline: news -> thesis -> research -> strategy -> chart.

Each function here does one step and saves its result on the thesis row.
The web API (app.py) and the Telegram bot both call these functions.

Step 5 (marking up TradingView) does not happen here. It runs on the Mac with
Claude Code and the TradingView MCP, then posts its results back to the API.
"""
import json

import claude_client
import database
import market_data
import runs
import schemas
import telegram
from levels import key_levels


class PipelineError(Exception):
    """A problem we can explain to the user, e.g. 'no news found'."""


def require_api_key():
    if not claude_client.has_api_key():
        raise PipelineError(
            "No Anthropic API key. Add ANTHROPIC_API_KEY to the .env file, then run: docker compose up -d"
        )


def require_thesis(thesis_id):
    thesis = database.get_thesis(thesis_id)
    if thesis is None:
        raise PipelineError("Thesis #" + str(thesis_id) + " does not exist.")
    return thesis


# ---------- steps 1 and 2: news, sentiment, thesis ----------

def create_thesis(ticker):
    """Pull the news for a ticker, score its sentiment, and write a thesis."""
    require_api_key()
    ticker = ticker.strip().upper()
    news = market_data.fetch_news(ticker)
    if len(news) == 0:
        raise PipelineError("No news found for " + ticker + ". Check the ticker symbol.")

    thesis_id = database.insert_thesis(ticker)
    database.update_thesis(thesis_id, news=news)

    prompt = (
        "You are a trading analyst. Recent news for " + ticker + ":\n\n"
        + json.dumps(news, indent=1) + "\n\n"
        "Score each headline's sentiment and relevance for the stock, in the same order as given. "
        "Then form one trading thesis driven by the most important news. "
        "Say neutral if the news doesn't support a trade."
    )
    try:
        analysis = claude_client.ask_claude(prompt, schemas.NewsAnalysis, thesis_id, "thesis")
    except Exception as error:
        database.update_thesis(thesis_id, status="error", error=str(error))
        raise PipelineError("Claude call failed: " + str(error))

    database.update_thesis(thesis_id, analysis=analysis.model_dump(), status="thesis")
    telegram.send_message(
        "Thesis #" + str(thesis_id) + " " + ticker + " (" + analysis.thesis.direction + ")\n"
        + analysis.thesis.statement
    )
    return database.get_thesis(thesis_id)


# ---------- step 3: research with TradingAgents (takes several minutes) ----------

def start_research(thesis_id):
    """Start a TradingAgents run attached to this thesis. Returns the run id.

    When the run finishes, runs.py saves its reports on the thesis.
    """
    require_api_key()
    thesis = require_thesis(thesis_id)
    if thesis["status"] == "researching":
        raise PipelineError("Research is already running for this thesis.")
    database.update_thesis(thesis_id, status="researching", error=None)
    return runs.start_run(thesis["ticker"], thesis_id=thesis_id)


# ---------- step 4: strategy ----------

def build_strategy(thesis_id):
    """Ask Claude for one rules-based strategy built on measured price levels."""
    require_api_key()
    thesis = require_thesis(thesis_id)
    if not thesis["analysis"]:
        raise PipelineError("This thesis has no analysis yet.")
    ticker = thesis["ticker"]

    daily_bars = market_data.fetch_bars(ticker, "1d")
    if len(daily_bars) < 21:
        raise PipelineError("Not enough price history for " + ticker + ".")
    measured = key_levels(daily_bars, market_data.fetch_bars(ticker, "5m"))

    research = thesis["research"] or {}
    verdict = research.get("signal", "not run")
    decision = research.get("final_trade_decision") or "Research step not run; rely on the thesis."

    prompt = (
        "Design one concrete, rules-based trading strategy for " + ticker + ".\n\n"
        "Thesis: " + json.dumps(thesis["analysis"]["thesis"]) + "\n\n"
        "Research verdict (" + str(verdict) + "):\n" + decision + "\n\n"
        "Measured price levels (use these numbers; do not invent levels):\n" + json.dumps(measured) + "\n\n"
        "Requirements:\n"
        "- Prefer a well-known setup (opening range breakout, prior-day high/low break or reclaim, "
        "20-day breakout, gap fade).\n"
        "- entry, stop and targets must come from or be derived from the measured levels/ATR. "
        "Risk:reward at least 1.5.\n"
        "- levels: every line worth drawing on the chart (entry, stop, each target, key support/resistance).\n"
        "- pine_script: a complete Pine Script v6 strategy() that compiles in TradingView. Put entry/stop/targets "
        "in input.float() with the numbers above as defaults, draw them with hline or plot, and use "
        "strategy.entry / strategy.exit so the Strategy Tester shows trades.\n"
        "- If the thesis direction is neutral, still choose the better-supported side and say why in risk_notes."
    )
    try:
        strategy = claude_client.ask_claude(prompt, schemas.Strategy, thesis_id, "strategy", effort="high")
    except Exception as error:
        database.update_thesis(thesis_id, error=str(error))
        raise PipelineError("Claude call failed: " + str(error))

    saved = strategy.model_dump()
    saved["measured_levels"] = measured
    database.update_thesis(thesis_id, strategy=saved, status="strategy", error=None)
    telegram.send_message(
        "Strategy for #" + str(thesis_id) + " " + ticker + ": " + strategy.name + "\n"
        + strategy.direction + " entry " + str(strategy.entry) + ", stop " + str(strategy.stop)
        + ", targets " + str(strategy.targets)
    )
    return database.get_thesis(thesis_id)


# ---------- step 5: results posted back from the TradingView run ----------

def save_chart_result(thesis_id, result):
    require_thesis(thesis_id)
    result["at"] = database.now_text()
    database.update_thesis(thesis_id, chart=result, status="charted")
    telegram.send_message("TradingView backtest saved for thesis #" + str(thesis_id))


# ---------- Telegram commands ----------

def handle_telegram_command(command, argument):
    """Return the reply text for one Telegram command."""
    if command == "/thesis" and argument != "":
        try:
            thesis = create_thesis(argument)
        except PipelineError as error:
            return str(error)
        return "Open http://localhost:5173 to continue with thesis #" + str(thesis["id"]) + "."
    if command == "/research" and argument != "":
        try:
            require_api_key()
            run_id = runs.start_run(argument)
        except (PipelineError, runs.RunError) as error:
            return str(error)
        return ("Started agent run #" + str(run_id) + " on " + argument
                + ". It takes several minutes; I will message you when it finishes.")
    return ("Commands:\n"
            "/thesis TICKER  pull today's news and form a thesis\n"
            "/research TICKER  start a full TradingAgents run")
