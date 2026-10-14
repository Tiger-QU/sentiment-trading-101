"""Options positioning: put/call ratios and implied versus historical volatility."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from loaders import cached_options
from options_data import DEFAULT_HISTORY_PATH, load_history, log_snapshot
from theme import (
    CRIMSON,
    GOLD,
    NAVY,
    SAGE,
    SLATE,
    SRC_PCR,
    SRC_YAHOO,
    apply_chart_layout,
    brand_header,
    callout,
    page_footer,
    sentiment_color,
    sidebar_controls,
    sources,
    tone,
)


def _num(value, digits=0) -> str:
    if value != value:
        return "n/a"
    if digits == 0:
        return f"{value:,.0f}"
    return f"{value:,.{digits}f}"


def _pct(value) -> str:
    if value != value:
        return "n/a"
    return f"{value * 100:.1f}%"


def render() -> None:
    ticker = sidebar_controls(show_expiries=True)
    brand_header(
        "Options",
        "Put/call activity and whether implied volatility sits above or below recent realized volatility.",
    )
    if not ticker:
        callout("Enter a ticker in the sidebar.")
        page_footer()
        return

    expiries = int(st.session_state.get("max_expiries", 8))
    try:
        with st.spinner(f"Loading options for {ticker}…"):
            data = cached_options(ticker, expiries)
            log_snapshot(data)
    except Exception as exc:
        callout(f"Options for {ticker} did not load. {exc}")
        page_footer()
        return

    _headline(data)
    _volatility(data)
    _expiries(data)
    _history(data)

    sources([SRC_YAHOO, SRC_PCR])
    page_footer()


def _headline(data: dict) -> None:
    spot = data["spot"]
    spot_str = f"${spot:,.2f}" if spot == spot else "n/a"
    st.subheader(f"{data['ticker']} · spot {spot_str}")
    st.caption(
        f"As of {data['asof'].strftime('%Y-%m-%d %H:%M:%S')} · "
        f"{data['n_expiries']} expiries included"
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Total options volume today", _num(data["total_vol"]))
    with c2:
        st.metric("Put/call volume", f"{data['pcr_volume']:.3f}" if data["pcr_volume"] == data["pcr_volume"] else "n/a")
        tone(data["sentiment_volume"], sentiment_color(data["sentiment_volume"]))
    with c3:
        st.metric("Put/call open interest", f"{data['pcr_oi']:.3f}" if data["pcr_oi"] == data["pcr_oi"] else "n/a")
        tone(data["sentiment_oi"], sentiment_color(data["sentiment_oi"]))

    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Call volume", _num(data["call_vol"]))
    b2.metric("Put volume", _num(data["put_vol"]))
    b3.metric("Call open interest", _num(data["call_oi"]))
    b4.metric("Put open interest", _num(data["put_oi"]))
    st.caption(
        "Dashboard convention: a put/call ratio below 0.7 is labeled bullish, "
        "0.7 to 1.0 neutral, and 1.0 or above bearish."
    )


def _volatility(data: dict) -> None:
    st.header("Implied and historical volatility")
    iv = data.get("iv", float("nan"))
    hv = data.get("hv_30", float("nan"))
    ratio = data.get("iv_hv_ratio", float("nan"))

    if not data.get("iv_reliable", True):
        coverage = data.get("quote_coverage", 0.0)
        callout(
            f"Implied volatility may be unreliable: {coverage * 100:.0f}% of contracts have a live bid or ask. "
            "Yahoo Finance often returns placeholder implied volatilities when quotes are absent. "
            "Historical volatility uses daily closes and is unaffected. "
            "US regular hours are 09:30–16:00 America/New_York."
        )

    c1, c2, c3 = st.columns(3)
    c1.metric("Implied volatility (at the money)", _pct(iv))
    c2.metric("Historical volatility (30-day)", _pct(hv))
    c3.metric("IV / HV", f"{ratio:.2f}x" if ratio == ratio else "n/a")

    if iv == iv and hv == hv and ratio == ratio:
        spread = (iv - hv) * 100
        if ratio >= 1.2:
            sentence = "Implied volatility is above recent realized volatility."
        elif ratio <= 0.9:
            sentence = "Implied volatility is below recent realized volatility."
        else:
            sentence = "Implied volatility is close to recent realized volatility."
        callout(
            f"{sentence} The gap is {spread:+.1f} percentage points. "
            "At-the-money implied volatility is an open-interest-weighted average of contracts "
            "near the spot price. Historical volatility is the annualized standard deviation of "
            "the last 30 daily log returns."
        )


def _expiries(data: dict) -> None:
    st.header("By expiry")
    pe = data["per_expiry"]
    hv = data.get("hv_30", float("nan"))

    left, right = st.columns(2)
    with left:
        fig = go.Figure()
        fig.add_bar(x=pe["expiry"], y=pe["call_vol"], name="Call volume", marker_color=NAVY)
        fig.add_bar(x=pe["expiry"], y=pe["put_vol"], name="Put volume", marker_color=CRIMSON)
        apply_chart_layout(fig, "Volume by expiry", "Contracts")
        st.plotly_chart(fig)
    with right:
        fig = go.Figure()
        fig.add_bar(x=pe["expiry"], y=pe["call_oi"], name="Call open interest", marker_color=NAVY)
        fig.add_bar(x=pe["expiry"], y=pe["put_oi"], name="Put open interest", marker_color=CRIMSON)
        apply_chart_layout(fig, "Open interest by expiry", "Contracts")
        st.plotly_chart(fig)

    if pe["iv"].notna().any():
        fig = go.Figure()
        fig.add_scatter(
            x=pe["expiry"],
            y=pe["iv"] * 100,
            mode="lines+markers",
            name="At-the-money implied volatility",
            line=dict(color=NAVY, width=2),
        )
        if hv == hv:
            fig.add_hline(
                y=hv * 100,
                line_dash="dot",
                line_color=GOLD,
                annotation_text=f"30-day historical {hv * 100:.1f}%",
                annotation_font_color=SLATE,
            )
        apply_chart_layout(fig, "Implied volatility by expiry", "Percent, annualized", height=360)
        st.plotly_chart(fig)

    with st.expander("Per-expiry table"):
        table = pe.assign(**{"ATM IV %": pe["iv"] * 100}).drop(columns=["iv"]).rename(
            columns={
                "expiry": "Expiry",
                "call_vol": "Call vol",
                "put_vol": "Put vol",
                "call_oi": "Call OI",
                "put_oi": "Put OI",
                "pcr_volume": "P/C vol",
                "pcr_oi": "P/C OI",
            }
        )
        st.dataframe(
            table.style.format(
                {
                    "Call vol": "{:,.0f}",
                    "Put vol": "{:,.0f}",
                    "Call OI": "{:,.0f}",
                    "Put OI": "{:,.0f}",
                    "P/C vol": "{:.3f}",
                    "P/C OI": "{:.3f}",
                    "ATM IV %": "{:.1f}",
                },
                na_rep="—",
            ),
            hide_index=True,
        )


def _history(data: dict) -> None:
    st.header("History from this dashboard")
    hist = load_history(DEFAULT_HISTORY_PATH, ticker=data["ticker"])
    if len(hist) < 2:
        callout(
            "One snapshot is stored for this ticker so far. The charts gain a point each day you open it."
        )
    else:
        fig = go.Figure()
        fig.add_scatter(
            x=hist["timestamp"], y=hist["pcr_volume"], mode="lines+markers",
            name="Put/call volume", line=dict(color=NAVY, width=2),
        )
        fig.add_scatter(
            x=hist["timestamp"], y=hist["pcr_oi"], mode="lines+markers",
            name="Put/call open interest", line=dict(color=SLATE, width=2),
        )
        fig.add_hline(y=1.0, line_dash="dot", line_color=CRIMSON, annotation_text="1.0")
        fig.add_hline(y=0.7, line_dash="dot", line_color=SAGE, annotation_text="0.7")
        apply_chart_layout(fig, f"{data['ticker']} put/call ratio", "Put/call ratio", height=400)
        st.plotly_chart(fig)
        st.caption("Dotted lines are the dashboard conventions at 0.7 and 1.0.")

    st.subheader("Implied and historical volatility over time")
    if "iv" in hist.columns and hist["iv"].notna().sum() >= 2:
        fig = go.Figure()
        fig.add_scatter(
            x=hist["timestamp"], y=hist["iv"] * 100, mode="lines+markers",
            name="Implied volatility", line=dict(color=NAVY, width=2),
        )
        fig.add_scatter(
            x=hist["timestamp"], y=hist["hv30"] * 100, mode="lines+markers",
            name="Historical volatility, 30-day", line=dict(color=GOLD, width=2),
        )
        apply_chart_layout(fig, f"{data['ticker']} volatility", "Percent, annualized", height=400)
        st.plotly_chart(fig)
    else:
        callout("Volatility history gains a point each day you open this ticker during conditions with usable quotes.")

    st.caption(f"History file: {DEFAULT_HISTORY_PATH}")
