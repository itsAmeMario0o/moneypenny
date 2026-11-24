---
description: Mark up a thesis's strategy on the live TradingView chart and backtest its Pine Script
argument-hint: <thesis id>
---

Chart thesis #$ARGUMENTS from Moneypenny in TradingView Desktop, using the `tradingview` MCP tools.

1. `curl -s http://localhost:8000/api/theses/$ARGUMENTS` and read `ticker` and `strategy`
   (`chart_timeframe`, `levels`, `pine_script`). If `strategy` is null, stop and say the strategy
   step hasn't been run in the web UI yet.
2. `tv_health_check`. If TradingView isn't reachable, use `tv_launch`.
3. `chart_set_symbol` to the ticker and `chart_set_timeframe` to `chart_timeframe`.
4. Draw every entry in `strategy.levels` with `draw_shape` as a `horizontal_line` at its price, with the
   label as text. Colors: entry blue, stop red, target green, support/resistance gray.
   Don't call `draw_clear`; the chart may hold the user's own drawings.
5. `pine_new` a strategy, `pine_set_source` with `pine_script`, then `pine_smart_compile`.
   If it fails, read `pine_get_errors`, fix the script, and recompile (at most 3 tries).
   Keep the levels and rules unchanged; only fix syntax.
6. Read `data_get_strategy_results` and `data_get_trades`, then `capture_screenshot` of the chart.
7. Post the outcome back so the web UI shows it:
   `curl -s -X POST http://localhost:8000/api/theses/$ARGUMENTS/chart -H 'Content-Type: application/json' -d '<json>'`
   with `{"symbol", "timeframe", "compiled": true|false, "pine_fixes": "...", "results": {...}, "trades": <count>}`.
8. Show the screenshot and report: net profit, win rate, trade count, max drawdown, and whether the
   Pine Script needed fixes. Don't create alerts or place orders.
