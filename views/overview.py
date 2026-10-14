"""Overview: market mood, options, and price confirmation on one page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from loaders import cached_fear_greed, cached_market, cached_options, cached_price
from market_data import MarketDataError
from options_data import log_snapshot
from theme import (
    SRC_CBOE,
    SRC_CNN,
    SRC_FIDELITY,
    SRC_PCR,
    SRC_VOLUME,
    SRC_WILDER,
    SRC_YAHOO,
    brand_header,
    callout,
    page_footer,
    rating_color,
    sentiment_color,
    sidebar_controls,
    sources,
    tone,
)


def _fmt_score(value) -> str:
    if value is None or value != value:
        return "n/a"
    return f"{value:.1f}"


def _fmt_ratio(value) -> str:
    if value != value:
        return "n/a"
    return f"{value:.3f}"


def _fmt_pct(value) -> str:
    if value != value:
        return "n/a"
    return f"{value * 100:.1f}%"


def render() -> None:
    ticker = sidebar_controls()
    brand_header(
        "Sentiment Dashboard",
        "A single reading of market mood, options positioning, and whether price and volume confirm it.",
    )

    st.header("Market mood")
    _market_block()

    st.header("Options")
    _options_block(ticker)

    st.header("Price and volume")
    _price_block(ticker)

    sources([SRC_CNN, SRC_CBOE, SRC_FIDELITY, SRC_YAHOO, SRC_PCR, SRC_WILDER, SRC_VOLUME])
    page_footer()


def _market_block() -> None:
    try:
        with st.spinner("Loading market readings…"):
            fear = cached_fear_greed()
            market = cached_market()
    except (MarketDataError, Exception) as exc:
        callout(f"Market readings did not load. {exc}")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Fear & Greed", _fmt_score(fear["score"]))
        tone(fear["rating"], rating_color(fear["rating"]))
    with c2:
        level = market["vix"]
        st.metric("VIX", f"{level:.1f}" if level == level else "n/a")
        st.caption(f"Dashboard convention: {market['vix_regime']}")
    leaders, laggards = _sector_edges(market["sectors"])
    c3.metric("Leading sectors, 3 months", leaders)
    c3.caption(f"Lagging: {laggards}")

    bits = [
        f"CNN Fear & Greed is {fear['score']:.1f} ({fear['rating']})"
        + (f" as of {fear['asof']}" if fear.get("asof") else "")
        + ".",
        (
            f"The VIX is {market['vix']:.1f}, {market['vix_regime'].lower()} on this dashboard’s convention, as of {market['asof']}."
            if market["vix"] == market["vix"]
            else f"The VIX reading was not available as of {market['asof']}."
        ),
    ]
    if market["vix"] == market["vix"] and market["vix_ma50"] == market["vix_ma50"]:
        relation = "above" if market["vix"] > market["vix_ma50"] else "below"
        bits.append(f"It is {relation} its 50-day average of {market['vix_ma50']:.1f}.")
    callout(" ".join(bits))
    st.caption("Open Market mood in the sidebar for the index history, VIX chart, and sector playbook.")


def _sector_edges(sectors: pd.DataFrame) -> tuple[str, str]:
    ranked = sectors.dropna(subset=["rel_3m"]).sort_values("rel_3m", ascending=False)
    if ranked.empty:
        return "n/a", "n/a"

    def _names(frame: pd.DataFrame) -> str:
        return ", ".join(frame["ticker"].tolist())

    return _names(ranked.head(3)), _names(ranked.tail(3))


def _options_block(ticker: str) -> None:
    if not ticker:
        callout("Enter a ticker in the sidebar.")
        return
    expiries = int(st.session_state.get("max_expiries", 8))
    try:
        with st.spinner(f"Loading options for {ticker}…"):
            data = cached_options(ticker, expiries)
            log_snapshot(data)
    except Exception as exc:
        callout(f"Options for {ticker} did not load. {exc}")
        return

    spot = data["spot"]
    spot_str = f"${spot:,.2f}" if spot == spot else "n/a"
    st.subheader(f"{data['ticker']} · spot {spot_str}")
    st.caption(
        f"As of {data['asof'].strftime('%Y-%m-%d %H:%M:%S')} · "
        f"{data['n_expiries']} expiries included"
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Put/call volume", _fmt_ratio(data["pcr_volume"]))
        tone(data["sentiment_volume"], sentiment_color(data["sentiment_volume"]))
    c2.metric("Put/call open interest", _fmt_ratio(data["pcr_oi"]))
    ratio = data["iv_hv_ratio"]
    c3.metric("IV / HV", f"{ratio:.2f}x" if ratio == ratio else "n/a")

    iv = data.get("iv", float("nan"))
    hv = data.get("hv_30", float("nan"))
    ratio = data.get("iv_hv_ratio", float("nan"))
    parts = [
        f"Today’s put volume divided by call volume is {_fmt_ratio(data['pcr_volume'])} "
        f"({data['sentiment_volume'].lower()} on the dashboard convention)."
    ]
    if iv == iv and hv == hv:
        parts.append(
            f"At-the-money implied volatility is {_fmt_pct(iv)} and 30-day historical "
            f"volatility is {_fmt_pct(hv)}."
        )
        if ratio == ratio:
            if ratio >= 1.2:
                parts.append("Implied volatility is above recent realized volatility.")
            elif ratio <= 0.9:
                parts.append("Implied volatility is below recent realized volatility.")
            else:
                parts.append("Implied volatility is close to recent realized volatility.")
    if not data.get("iv_reliable", True):
        parts.append("The implied-volatility figure may be unreliable because few contracts have a live quote.")
    callout(" ".join(parts))
    st.caption("Open Options in the sidebar for expiries, term structure, and the history log.")


def _price_block(ticker: str) -> None:
    if not ticker:
        return
    try:
        with st.spinner(f"Loading price and volume for {ticker}…"):
            study = cached_price(ticker)
    except (MarketDataError, Exception) as exc:
        callout(f"Price and volume for {ticker} did not load. {exc}")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("RSI (14-day)", _fmt_score(study["rsi"]))
    c1.caption(study["rsi_zone"])
    c2.metric("20-day price", _fmt_pct(study["return_20"]))
    c2.caption(study["price_trend"])
    ratio = study["volume_ratio"]
    c3.metric("Volume vs 20-day average", f"{ratio:.2f}x" if ratio == ratio else "n/a")
    c3.caption(study["volume_trend"])

    reading = study["reading"]
    if reading:
        callout(
            f"{study['ticker']} matches the supplied guide row "
            f"{reading['price'].lower()} price and {reading['volume'].lower()} volume. "
            f"{reading['sentiment']} {reading['action']}"
        )
    elif study["volume_trend"] == "Steady":
        callout(
            "Volume is within 15% of its 20-day average, so the supplied six-row guide does not assign a regime."
        )
    st.caption("Open Price and volume in the sidebar for the RSI chart and the full guide.")
