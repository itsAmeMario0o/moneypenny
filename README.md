# Moneypenny

A personal trading research desk that runs on your own machine. One dashboard sits in
front of three things:

- **A thesis pipeline.** Pulls the day's headlines for a ticker, has Claude score the
  sentiment, and writes a short thesis with a recommendation.
- **[TradingAgents](https://github.com/TauricResearch/TradingAgents).** A team of AI
  agents (analysts, bull and bear researchers, a trader, risk reviewers, a portfolio
  manager) that debate a ticker and produce a rating. The dashboard starts runs and
  shows each agent's report as it arrives.
- **[LuxAlgo trade journal](https://github.com/LuxAlgo/trade-journal).** Keeps the trade
  records and works out the performance numbers (win rate, profit factor, drawdown,
  equity curve). The dashboard shows them on its front page.

It is a proof of concept for research. **It does not place trades**, and nothing it
produces is financial advice.

## What you need

- Docker with Compose (Docker Desktop, or Colima on a Mac)
- A Claude API key from <https://platform.claude.com/>
- Optional: a Telegram bot token, a FRED API key

## Start it

    cp .env.example .env        # then put your Claude API key in .env
    docker compose up -d --build

The first build takes a while because the trade journal is built from source. After
that, open <http://localhost:5173>. The API needs about 20 seconds to start.

| Service | Address | What it is |
|---|---|---|
| `web` | <http://localhost:5173> | The dashboard (React, served by nginx) |
| `api` | <http://localhost:8000> | FastAPI: theses, agent runs, token usage, Telegram |
| `journal` | <http://localhost:3000> | The LuxAlgo trade journal |

All three listen on localhost only. The journal has no password for that reason, so
do not expose these ports to a network.

To stop and start again later:

    docker compose stop
    docker compose up -d

Data lives in two Docker volumes (`data` and `journal_data`), so it survives restarts
and rebuilds.

## Settings

Everything is set in `.env`. See `.env.example` for the full list.

| Variable | What it does |
|---|---|
| `ANTHROPIC_API_KEY` | Required. Your Claude API key. |
| `DESK_MODEL` | Model for the thesis pipeline. |
| `TA_DEEP_MODEL`, `TA_QUICK_MODEL` | Models TradingAgents uses for hard and easy steps. |
| `DAILY_TOKEN_BUDGET` | The daily amount the token meter fills up against. |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Optional. Turns on the Telegram bot. |
| `FRED_API_KEY` | Optional. Macro data for TradingAgents. |

A full agent run uses a lot of tokens and can cost a few dollars. The Token usage page
shows what each run spent.

## Telegram

Create a bot with @BotFather, put its token and your own chat id in `.env`, and restart
the API. The bot only obeys messages from that one chat.

- `/thesis TICKER` pulls today's news and forms a thesis
- `/research TICKER` starts a full TradingAgents run

It messages you when a run finishes, with the rating and a summary, or with the error
if the run failed.

## Demo data

To fill the journal with simulated trades for a demo:

    docker compose exec -T api python - < scripts/simulate_trades.py

It creates an account called "Simulated account" with about twelve months of day
trades. Prices sit inside each day's real range and monthly results follow the real
market, but **none of these trades happened**. Running it again replaces the account.

## TradingView (optional)

A thesis can include a strategy written in Pine Script. If you use Claude Code with a
TradingView MCP server, the command in `.claude/commands/chart-thesis.md` draws the
strategy's levels on your chart and backtests the script.

## Networks that inspect HTTPS

If Claude calls fail with "Connection error" on a work network, see
`api/certs/README.md`.

## Layout

    api/        FastAPI app, thesis pipeline, TradingAgents runner, Telegram bot
    web/        React dashboard and the nginx config that serves it
    scripts/    simulate_trades.py
    compose.yaml

## Credits and license

Moneypenny's own code is under the MIT license (see `LICENSE`). It builds on, but does
not include the source of:

- TradingAgents by Tauric Research, Apache-2.0
- trade-journal by LuxAlgo, MIT

Both are pinned to a specific commit, in `api/requirements.txt` and `compose.yaml`.
