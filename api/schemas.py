"""The shapes of the answers we ask Claude for.

Claude must return JSON matching these classes, so the rest of the code can
rely on every field being present and of the right type.
"""
from typing import Literal

from pydantic import BaseModel, Field


# ---------- step 2: news analysis ----------

class Headline(BaseModel):
    title: str
    sentiment: float = Field(description="-1 very bearish .. +1 very bullish for this ticker")
    relevance: float = Field(description="0..1, how much this matters for the stock price")


class Thesis(BaseModel):
    direction: Literal["long", "short", "neutral"]
    catalyst: str = Field(description="the specific news item(s) driving the idea")
    statement: str = Field(description="2-3 sentence trading thesis")
    timeframe: Literal["intraday", "swing", "position"]
    invalidation: str = Field(description="what would prove the thesis wrong")


class NewsAnalysis(BaseModel):
    headlines: list[Headline]
    overall_sentiment: float = Field(description="-1 .. +1 across all headlines")
    thesis: Thesis


# ---------- step 4: strategy ----------

class Level(BaseModel):
    label: str
    price: float
    kind: Literal["entry", "stop", "target", "support", "resistance"]


class Strategy(BaseModel):
    name: str
    setup: str = Field(description="setup type, e.g. ORB breakout, PDH reclaim, gap fade")
    direction: Literal["long", "short"]
    chart_timeframe: Literal["1", "5", "15", "60", "D"] = Field(description="TradingView resolution")
    entry_rule: str
    exit_rule: str
    entry: float
    stop: float
    targets: list[float]
    levels: list[Level]
    risk_notes: str
    pine_script: str = Field(description="complete Pine Script v6 strategy() source")
