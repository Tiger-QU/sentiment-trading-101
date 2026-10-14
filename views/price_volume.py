"""RSI and the price-and-volume reading guide."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from loaders import cached_price
from market_data import READING_GUIDE, MarketDataError
from theme import (
    CRIMSON,
    GOLD,
    NAVY,
    SLATE,
    SRC_VOLUME,
    SRC_WILDER,
    SRC_YAHOO,
    apply_chart_layout,
    brand_header,
    callout,
    page_footer,
    sidebar_controls,
    sources,
)


def render() -> None:
    ticker = sidebar_controls()
    brand_header(
        "Price and volume",
        "RSI locates the price extreme. Volume shows whether participation confirms the move.",
    )
    if not ticker:
        callout("Enter a ticker in the sidebar.")
        page_footer()
        return

    try:
        with st.spinner(f"Loading price and volume for {ticker}…"):
            study = cached_price(ticker)
    except (MarketDataError, Exception) as exc:
        callout(f"Price and volume for {ticker} did not load. {exc}")
        sources([SRC_WILDER, SRC_VOLUME, SRC_YAHOO])
        page_footer()
        return

    _rsi(study)
    _volume(study)
    sources([SRC_WILDER, SRC_VOLUME, SRC_YAHOO])
    page_footer()


def _rsi(study: dict) -> None:
    st.header("Relative strength index")
    value = study["rsi"]
    c1, c2, c3 = st.columns(3)
    c1.metric("RSI, 14-day", f"{value:.1f}" if value == value else "n/a")
    c2.metric("Wilder zone", study["rsi_zone"])
    c3.metric("Last close", f"${study['close']:,.2f}")
    st.caption(f"{study['ticker']} daily closes as of {study['asof']}.")

    if study["rsi_zone"] == "Oversold":
        callout("The 14-day RSI is under 30, Wilder’s oversold zone.")
    elif study["rsi_zone"] == "Overbought":
        callout("The 14-day RSI is over 70, Wilder’s overbought zone.")
    else:
        callout("The 14-day RSI is between 30 and 70, outside Wilder’s oversold and overbought zones.")

    history = study["history"]
    fig = go.Figure()
    fig.add_scatter(
        x=history["date"], y=history["rsi"], mode="lines", name="RSI",
        line=dict(color=NAVY, width=2),
    )
    fig.add_hline(y=30, line_dash="dot", line_color=CRIMSON, annotation_text="30")
    fig.add_hline(y=70, line_dash="dot", line_color=GOLD, annotation_text="70")
    apply_chart_layout(fig, f"{study['ticker']} 14-day RSI", "RSI", height=360)
    fig.update_yaxes(range=[0, 100])
    st.plotly_chart(fig)


def _volume(study: dict) -> None:
    st.header("Volume")
    ret = study["return_20"]
    ratio = study["volume_ratio"]
    c1, c2 = st.columns(2)
    c1.metric("20-day price return", f"{ret * 100:+.1f}%" if ret == ret else "n/a")
    c1.caption(study["price_trend"])
    c2.metric("5-day volume / 20-day volume", f"{ratio:.2f}x" if ratio == ratio else "n/a")
    c2.caption(study["volume_trend"])

    reading = study["reading"]
    if reading:
        callout(
            f"Supplied reading guide. {study['ticker']} is in the {reading['price'].lower()} price, "
            f"{reading['volume'].lower()} volume row. {reading['sentiment']} {reading['action']}"
        )
    else:
        callout(
            "Volume is within 15% of its 20-day average, so the supplied six-row guide does not assign a regime."
        )

    rows = []
    for item in READING_GUIDE:
        current = (
            item["price"] == study["price_trend"] and item["volume"] == study["volume_trend"]
        )
        rows.append(
            {
                "Price trend": item["price"],
                "Volume trend": item["volume"],
                "Market sentiment": item["sentiment"],
                "Possible trade action": item["action"],
                "This ticker": "Yes" if current else "",
            }
        )
    table = pd.DataFrame(rows)

    def _paint(row):
        if row["This ticker"] == "Yes":
            return ["background-color: #F1F5F9; color: #0F172A"] * len(row)
        return [""] * len(row)

    st.dataframe(table.style.apply(_paint, axis=1), hide_index=True)
    st.caption(
        "Price trend uses the close-to-close return over 20 trading days: above +3% is up, "
        "below −3% is down, otherwise stable. Volume trend compares the last 5 sessions with "
        "the last 20: 15% or more above is increasing, 15% or more below is decreasing."
    )

    history = study["history"]
    fig = go.Figure()
    fig.add_bar(
        x=history["date"], y=history["volume"], name="Volume", marker_color=SLATE, opacity=0.85,
    )
    apply_chart_layout(fig, f"{study['ticker']} daily volume", "Shares", height=320)
    st.plotly_chart(fig)

    fig = go.Figure()
    fig.add_scatter(
        x=history["date"], y=history["close"], mode="lines", name="Close",
        line=dict(color=NAVY, width=2),
    )
    apply_chart_layout(fig, f"{study['ticker']} close", "Price", height=320, zero_base=False)
    st.plotly_chart(fig)
