"""Moneypenny web API. Each route is a thin wrapper around a function in another file.

Theses (the five-step pipeline, see pipeline.py)
  GET  /api/theses                  short list for the dashboard
  GET  /api/theses/{id}             everything about one thesis
  POST /api/theses                  steps 1+2: news -> sentiment -> thesis
  POST /api/theses/{id}/research    step 3: start a TradingAgents run for the thesis
  POST /api/theses/{id}/strategy    step 4: build the strategy
  POST /api/theses/{id}/chart       step 5: save TradingView results (sent by Claude Code)

TradingAgents runs (see runs.py)
  GET  /api/runs                    run history
  POST /api/runs                    start a run with chosen settings
  GET  /api/runs/{id}               one run, with every agent's messages so far

Tools (see the tools/ folder)
  GET  /api/tools                   the tools that exist
  POST /api/tools/{name}            run one tool on a ticker

Other
  GET  /api/health                  is the API key set? is Telegram on? run defaults
  GET  /api/bars/{ticker}           price bars for the web chart
  GET  /api/usage                   token meter
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import claude_client
import database
import market_data
import pipeline
import runs
import telegram
import tools
import usage

app = FastAPI(title="Moneypenny")

database.create_tables()
database.fail_interrupted_work()
telegram.start_listening(pipeline.handle_telegram_command)


class NewThesisRequest(BaseModel):
    ticker: str


class NewRunRequest(BaseModel):
    ticker: str
    trade_date: str = ""
    analysts: list[str] = []
    depth: int = 1
    deep_model: str = ""
    quick_model: str = ""


class ToolRequest(BaseModel):
    ticker: str


def run_step(step_function, *arguments):
    """Call a function and turn its 'explainable' errors into an HTTP 400 with the message."""
    try:
        return step_function(*arguments)
    except (pipeline.PipelineError, runs.RunError) as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "api_key_set": claude_client.has_api_key(),
        "telegram_on": telegram.is_enabled(),
        "model": claude_client.MODEL,
        "run_defaults": runs.default_settings(),
        "agents": runs.AGENTS,
    }


# ---------- theses ----------

@app.get("/api/theses")
def list_theses():
    """A short summary of each thesis (the full reports are large)."""
    summaries = []
    for thesis in database.list_theses():
        summary = {
            "id": thesis["id"],
            "ticker": thesis["ticker"],
            "created": thesis["created"],
            "status": thesis["status"],
            "direction": None,
            "sentiment": None,
            "signal": None,
            "setup": None,
        }
        if thesis["analysis"]:
            summary["direction"] = thesis["analysis"]["thesis"]["direction"]
            summary["sentiment"] = thesis["analysis"]["overall_sentiment"]
        if thesis["research"]:
            summary["signal"] = thesis["research"]["signal"]
        if thesis["strategy"]:
            summary["setup"] = thesis["strategy"]["setup"]
        summaries.append(summary)
    return summaries


@app.get("/api/theses/{thesis_id}")
def get_thesis(thesis_id: int):
    thesis = run_step(pipeline.require_thesis, thesis_id)
    thesis["latest_run_id"] = database.latest_run_id_for_thesis(thesis_id)
    return thesis


@app.post("/api/theses")
def create_thesis(request: NewThesisRequest):
    return run_step(pipeline.create_thesis, request.ticker)


@app.post("/api/theses/{thesis_id}/research")
def start_research(thesis_id: int):
    run_id = run_step(pipeline.start_research, thesis_id)
    return {"run_id": run_id}


@app.post("/api/theses/{thesis_id}/strategy")
def build_strategy(thesis_id: int):
    return run_step(pipeline.build_strategy, thesis_id)


@app.post("/api/theses/{thesis_id}/chart")
def save_chart_result(thesis_id: int, result: dict):
    run_step(pipeline.save_chart_result, thesis_id, result)
    return {"ok": True}


# ---------- TradingAgents runs ----------

@app.get("/api/runs")
def list_runs():
    """Run history without the long reports."""
    summaries = []
    for run in database.list_runs():
        del run["reports"]
        summaries.append(run)
    return summaries


@app.post("/api/runs")
def start_run(request: NewRunRequest):
    run_step(pipeline.require_api_key)
    settings = {
        "analysts": request.analysts,
        "depth": request.depth,
        "deep_model": request.deep_model,
        "quick_model": request.quick_model,
    }
    run_id = run_step(runs.start_run, request.ticker, request.trade_date, settings)
    return {"run_id": run_id}


@app.get("/api/runs/{run_id}")
def get_run(run_id: int):
    run = database.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run #" + str(run_id) + " does not exist.")
    run["events"] = database.list_run_events(run_id)
    return run


# ---------- tools ----------

@app.get("/api/tools")
def list_tools():
    return tools.list_tools()


@app.post("/api/tools/{name}")
def run_tool(name: str, request: ToolRequest):
    if name not in tools.TOOLS:
        raise HTTPException(status_code=404, detail="No tool named " + name)
    ticker = request.ticker.strip().upper()
    if ticker == "":
        raise HTTPException(status_code=400, detail="Enter a ticker.")
    try:
        result = tools.TOOLS[name].run(ticker)
    except Exception as error:
        raise HTTPException(status_code=400, detail="Tool failed: " + str(error))
    return {"tool": name, "ticker": ticker, "result": result}


# ---------- other ----------

@app.get("/api/bars/{ticker}")
def get_bars(ticker: str, interval: str = "1d"):
    if interval not in market_data.PERIOD_FOR_INTERVAL:
        raise HTTPException(status_code=400, detail="interval must be one of 1d, 60m, 15m, 5m")
    return market_data.bars_for_chart(ticker.upper(), interval)


@app.get("/api/usage")
def get_usage():
    return usage.current_summary()
