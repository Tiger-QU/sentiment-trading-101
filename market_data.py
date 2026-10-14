"""
Market, sector, and price readings for Sentiment Dashboard.

Fear & Greed comes from the chart feed CNN's own page uses.
VIX, sector ETFs, and price history come from Yahoo Finance via yfinance.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf

CNN_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
CNN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.cnn.com/markets/fear-and-greed",
    "Origin": "https://www.cnn.com",
}

# The seven components CNN describes. Duplicate series in the feed
# (125-day momentum and the VIX 50-day score) are not shown separately.
CNN_COMPONENTS = [
    ("market_momentum_sp500", "Market momentum"),
    ("stock_price_strength", "Stock price strength"),
    ("stock_price_breadth", "Stock price breadth"),
    ("put_call_options", "Put/call options"),
    ("market_volatility_vix", "Market volatility (VIX)"),
    ("junk_bond_demand", "Junk bond demand"),
    ("safe_haven_demand", "Safe haven demand"),
]

# CNN's own description of how each component is scored.
COMPONENT_NOTES = {
    "Market momentum": (
        "CNN compares the S&P 500 with its 125-day moving average. "
        "A level above that average is scored toward greed. A level below it is scored toward fear."
    ),
    "Stock price strength": (
        "CNN counts New York Stock Exchange shares at 52-week highs and at 52-week lows. "
        "More highs than lows is scored toward greed."
    ),
    "Stock price breadth": (
        "CNN uses the McClellan Volume Summation Index, which compares the volume of advancing "
        "shares with the volume of declining shares. More advancing volume is scored toward greed."
    ),
    "Put/call options": (
        "CNN uses the five-day average put/call ratio. More put activity relative to calls "
        "is scored toward fear."
    ),
    "Market volatility (VIX)": (
        "CNN compares the VIX with its 50-day moving average. A VIX above that average "
        "is scored toward fear."
    ),
    "Junk bond demand": (
        "CNN uses the yield spread between junk bonds and investment-grade bonds. "
        "A wider spread, meaning investors demand more yield to hold the riskier bonds, "
        "is scored toward fear."
    ),
    "Safe haven demand": (
        "CNN compares recent stock returns with Treasury bond returns. "
        "Bonds outperforming stocks is scored toward fear."
    ),
}

SECTORS = [
    ("XLC", "Communication services"),
    ("XLY", "Consumer discretionary"),
    ("XLP", "Consumer staples"),
    ("XLE", "Energy"),
    ("XLF", "Financials"),
    ("XLV", "Health care"),
    ("XLI", "Industrials"),
    ("XLB", "Materials"),
    ("XLRE", "Real estate"),
    ("XLK", "Information technology"),
    ("XLU", "Utilities"),
]

# Leader sets follow Fidelity's business-cycle papers. Mid cycle is omitted
# because that research treats mid-cycle leadership as inconsistent.
PHASES = [
    {
        "id": "Early cycle",
        "leaders": ["XLY", "XLF", "XLRE", "XLI", "XLK"],
        "summary": (
            "Fidelity’s business-cycle research finds that early cycle — a recession "
            "ending, with low interest rates and the first evidence of recovery — has "
            "historically favored consumer discretionary, financials, real estate, "
            "industrials, and information technology. Defensive sectors have tended to lag."
        ),
    },
    {
        "id": "Mid cycle",
        "leaders": [],
        "summary": (
            "Fidelity characterizes mid cycle as the longest phase and the one in which "
            "relative sector performance is least consistent. This dashboard does not "
            "highlight a leader set for mid cycle, because the cited research does not "
            "treat one group as reliable."
        ),
    },
    {
        "id": "Late cycle",
        "leaders": ["XLE", "XLB", "XLP", "XLV", "XLU"],
        "summary": (
            "As an expansion matures and inflation pressures build, Fidelity finds that "
            "energy and materials have tended to lead, with consumer staples, health care, "
            "and utilities holding up as investors shift toward less economically sensitive "
            "businesses. Information technology and consumer discretionary have tended to lag."
        ),
    },
    {
        "id": "Recession",
        "leaders": ["XLP", "XLU", "XLV"],
        "summary": (
            "During recessions, Fidelity finds that consumer staples, utilities, and health "
            "care have tended to hold up better than the broad market. Fidelity reports that "
            "consumer staples outperformed the broader market throughout the recession phases "
            "in its historical sample. Industrials, information technology, and real estate "
            "have tended to lag."
        ),
    },
]

READING_GUIDE = [
    {
        "price": "Up",
        "volume": "Increasing",
        "sentiment": "Strongly bullish (high-conviction buying).",
        "action": (
            "Buy / hold. Rising price with rising volume is consistent with accumulation "
            "and with institutions sustaining the move."
        ),
    },
    {
        "price": "Up",
        "volume": "Decreasing",
        "sentiment": "Weak / divergent (lack of buyer interest).",
        "action": (
            "Take profits / wait. A rising price on falling volume suggests the move is "
            "losing participation, and a reversal is more likely."
        ),
    },
    {
        "price": "Down",
        "volume": "Increasing",
        "sentiment": "Strongly bearish (heavy selling).",
        "action": (
            "Sell / short / avoid. Rising volume on a falling price is consistent with "
            "capitulation. The guide says to wait for selling pressure to ease before "
            "buying a decline."
        ),
    },
    {
        "price": "Down",
        "volume": "Decreasing",
        "sentiment": "Normal consolidation (orderly pullback).",
        "action": (
            "Watch for a reversal. Price is falling without a surge in volume, which the "
            "guide treats as profit-taking rather than panic."
        ),
    },
    {
        "price": "Stable",
        "volume": "Increasing",
        "sentiment": "Accumulation or distribution (activity before a break).",
        "action": (
            "Set bracket orders. Price is in a range while volume is rising, which the "
            "guide treats as a setup for a break of resistance or support."
        ),
    },
    {
        "price": "Stable",
        "volume": "Decreasing",
        "sentiment": "Apathetic / flat (no catalyst).",
        "action": (
            "Do nothing / stay in cash. Flat price and falling volume indicate little "
            "participation."
        ),
    },
]


class MarketDataError(Exception):
    """A reading could not be assembled from its source."""


def _title_rating(rating: str) -> str:
    return (rating or "No rating").replace("_", " ").strip().title()


def _ms_to_date(ms) -> str:
    return datetime.fromtimestamp(float(ms) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def fetch_fear_greed() -> dict:
    """Current CNN Fear & Greed score, components, and about one year of history."""
    request = urllib.request.Request(CNN_URL, headers=CNN_HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except Exception as exc:
        raise MarketDataError(f"CNN Fear & Greed did not respond ({exc}).") from exc

    current = payload.get("fear_and_greed") or {}
    if "score" not in current:
        raise MarketDataError("CNN Fear & Greed returned no score.")

    history_rows = (payload.get("fear_and_greed_historical") or {}).get("data") or []
    history = pd.DataFrame(
        [
            {
                "date": _ms_to_date(row["x"]),
                "score": float(row["y"]),
                "rating": _title_rating(row.get("rating", "")),
            }
            for row in history_rows
            if row.get("x") is not None and row.get("y") is not None
        ]
    )
    if not history.empty:
        history = history.drop_duplicates("date").sort_values("date")

    components = []
    for key, label in CNN_COMPONENTS:
        block = payload.get(key) or {}
        if block.get("score") is None:
            continue
        components.append(
            {
                "component": label,
                "score": float(block["score"]),
                "rating": _title_rating(block.get("rating", "")),
            }
        )

    asof = current.get("timestamp") or ""
    if isinstance(asof, str) and "T" in asof:
        asof = asof[:10]
    elif asof:
        asof = _ms_to_date(asof)

    return {
        "score": float(current["score"]),
        "rating": _title_rating(current.get("rating", "")),
        "asof": asof,
        "previous_close": _float_or_none(current.get("previous_close")),
        "previous_week": _float_or_none(current.get("previous_1_week")),
        "previous_month": _float_or_none(current.get("previous_1_month")),
        "previous_year": _float_or_none(current.get("previous_1_year")),
        "history": history,
        "components": pd.DataFrame(components),
    }


def _float_or_none(value):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def vix_regime(level: float) -> str:
    """Dashboard convention. Not a Cboe classification."""
    if level != level:
        return "No data"
    if level < 15:
        return "Calm"
    if level < 20:
        return "Normal"
    if level < 30:
        return "Elevated"
    return "Stressed"


def _close_frame(raw: pd.DataFrame) -> pd.DataFrame:
    if raw is None or raw.empty:
        raise MarketDataError("Yahoo Finance returned no prices.")
    if isinstance(raw.columns, pd.MultiIndex):
        closes = raw["Close"].copy()
    else:
        closes = raw[["Close"]].copy()
    closes = closes.dropna(how="all")
    closes = closes.loc[closes["SPY"].notna()] if "SPY" in closes.columns else closes.dropna()
    if closes.empty:
        raise MarketDataError("Yahoo Finance returned no usable closing prices.")
    return closes


def _window_return(series: pd.Series, sessions: int) -> float:
    clean = series.dropna()
    if len(clean) <= sessions:
        return float("nan")
    start = float(clean.iloc[-(sessions + 1)])
    end = float(clean.iloc[-1])
    if start <= 0:
        return float("nan")
    return end / start - 1.0


def fetch_market_snapshot() -> dict:
    """VIX, 3-month VIX, and SPDR sector returns versus SPY."""
    symbols = ["SPY", "^VIX", "^VIX3M"] + [ticker for ticker, _name in SECTORS]
    try:
        raw = yf.download(
            symbols,
            period="2y",
            auto_adjust=True,
            progress=False,
            threads=False,
        )
    except Exception as exc:
        raise MarketDataError(f"Yahoo Finance did not return market prices ({exc}).") from exc

    closes = _close_frame(raw)
    asof = pd.Timestamp(closes.index[-1]).strftime("%Y-%m-%d")

    vix = closes["^VIX"].dropna()
    vix3m = closes["^VIX3M"].dropna() if "^VIX3M" in closes.columns else pd.Series(dtype=float)
    if vix.empty:
        raise MarketDataError("Yahoo Finance returned no VIX history.")

    level = float(vix.iloc[-1])
    ma50 = float(vix.tail(50).mean()) if len(vix) >= 50 else float("nan")
    three_month = float(vix3m.iloc[-1]) if not vix3m.empty else float("nan")

    history = pd.DataFrame({"date": vix.index, "vix": vix.values})
    history["date"] = pd.to_datetime(history["date"]).dt.strftime("%Y-%m-%d")
    history["ma50"] = vix.rolling(50).mean().values
    history = history.tail(252).reset_index(drop=True)

    spy = closes["SPY"]
    rows = []
    for ticker, name in SECTORS:
        if ticker not in closes.columns:
            continue
        series = closes[ticker]
        rows.append(
            {
                "ticker": ticker,
                "name": name,
                "rel_1m": _window_return(series, 21) - _window_return(spy, 21),
                "rel_3m": _window_return(series, 63) - _window_return(spy, 63),
                "rel_6m": _window_return(series, 126) - _window_return(spy, 126),
            }
        )
    sectors = pd.DataFrame(rows)
    if sectors.empty:
        raise MarketDataError("Yahoo Finance returned no sector prices.")

    return {
        "asof": asof,
        "vix": level,
        "vix_ma50": ma50,
        "vix3m": three_month,
        "vix_regime": vix_regime(level),
        "vix_history": history,
        "sectors": sectors,
    }


def wilder_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder RSI. The first average is smoothed with alpha = 1/period."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def classify_price(return_20: float) -> str:
    if return_20 != return_20:
        return "No data"
    if return_20 > 0.03:
        return "Up"
    if return_20 < -0.03:
        return "Down"
    return "Stable"


def classify_volume(ratio: float) -> str:
    if ratio != ratio:
        return "No data"
    if ratio >= 1.15:
        return "Increasing"
    if ratio <= 0.85:
        return "Decreasing"
    return "Steady"


def rsi_zone(value: float) -> str:
    if value != value:
        return "No data"
    if value < 30:
        return "Oversold"
    if value > 70:
        return "Overbought"
    return "Mid-range"


def match_reading(price_trend: str, volume_trend: str) -> dict | None:
    for row in READING_GUIDE:
        if row["price"] == price_trend and row["volume"] == volume_trend:
            return row
    return None


def fetch_price_study(ticker: str) -> dict:
    """14-day RSI and the 20-day price / volume regime for one ticker."""
    symbol = (ticker or "").strip().upper()
    if not symbol:
        raise MarketDataError("Enter a ticker.")

    try:
        hist = yf.Ticker(symbol).history(period="1y", auto_adjust=True)
    except Exception as exc:
        raise MarketDataError(f"Yahoo Finance did not return prices for {symbol} ({exc}).") from exc

    if hist is None or hist.empty or "Close" not in hist.columns:
        raise MarketDataError(f"No price history for {symbol}.")

    hist = hist.dropna(subset=["Close"])
    if len(hist) < 21:
        raise MarketDataError(f"{symbol} does not have 21 trading days of prices.")

    close = hist["Close"].astype(float)
    volume = hist["Volume"].astype(float) if "Volume" in hist.columns else pd.Series(0, index=hist.index)
    rsi = wilder_rsi(close)
    return_20 = float(close.iloc[-1] / close.iloc[-21] - 1.0)
    vol_5 = float(volume.tail(5).mean())
    vol_20 = float(volume.tail(20).mean())
    vol_ratio = (vol_5 / vol_20) if vol_20 > 0 else float("nan")
    price_trend = classify_price(return_20)
    volume_trend = classify_volume(vol_ratio)
    rsi_value = float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else float("nan")

    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(hist.index).strftime("%Y-%m-%d"),
            "close": close.values,
            "volume": volume.values,
            "rsi": rsi.values,
        }
    )

    return {
        "ticker": symbol,
        "asof": frame["date"].iloc[-1],
        "close": float(close.iloc[-1]),
        "return_20": return_20,
        "volume_ratio": vol_ratio,
        "price_trend": price_trend,
        "volume_trend": volume_trend,
        "rsi": rsi_value,
        "rsi_zone": rsi_zone(rsi_value),
        "reading": match_reading(price_trend, volume_trend),
        "history": frame,
    }
