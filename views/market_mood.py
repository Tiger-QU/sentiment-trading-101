"""Market mood: Fear & Greed, VIX, and sector rotation."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from loaders import cached_fear_greed, cached_market
from market_data import PHASES, MarketDataError
from theme import (
    CRIMSON,
    GOLD,
    NAVY,
    SLATE,
    SRC_CBOE,
    SRC_CNN,
    SRC_FIDELITY,
    apply_chart_layout,
    brand_header,
    callout,
    page_footer,
    rating_color,
    sidebar_controls,
    sources,
    tone,
)


def _fmt(value) -> str:
    if value is None or value != value:
        return "n/a"
    return f"{value:.1f}"


def _pct(value) -> str:
    if value != value:
        return "—"
    return f"{value * 100:+.1f}%"


def render() -> None:
    sidebar_controls()
    brand_header(
        "Market mood",
        "Fear & Greed, the VIX, and which sectors have tended to lead at each stage of the business cycle.",
    )

    _fear_section()
    market = _load_market()
    if market is not None:
        _vix_section(market)
        _sector_section(market)

    sources([SRC_CNN, SRC_CBOE, SRC_FIDELITY])
    page_footer()


def _fear_section() -> None:
    st.header("Fear & Greed")
    try:
        with st.spinner("Loading the Fear & Greed Index…"):
            fear = cached_fear_greed()
    except (MarketDataError, Exception) as exc:
        callout(f"Fear & Greed did not load. {exc} VIX and sectors below still use Yahoo Finance.")
        return

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Score", _fmt(fear["score"]))
        tone(fear["rating"], rating_color(fear["rating"]))
    c2.metric("Previous close", _fmt(fear["previous_close"]))
    c3.metric("One week ago", _fmt(fear["previous_week"]))
    c4.metric("One month ago", _fmt(fear["previous_month"]))
    c5.metric("One year ago", _fmt(fear["previous_year"]))
    if fear.get("asof"):
        st.caption(f"CNN score as of {fear['asof']}.")

    score = fear["score"]
    if score <= 25 or score >= 75:
        callout(
            "The index is in an extreme band. CNN’s framing is that excessive fear has tended "
            "to coincide with depressed share prices, and excessive greed with the opposite."
        )
    else:
        callout(
            "CNN describes the index as a gauge of whether fear or greed is driving prices. "
            "Excessive fear has tended to push share prices down, and excessive greed the other way."
        )

    history = fear["history"]
    if not history.empty:
        fig = go.Figure()
        fig.add_scatter(
            x=history["date"],
            y=history["score"],
            mode="lines",
            name="Fear & Greed",
            line=dict(color=NAVY, width=2),
        )
        fig.add_hline(y=25, line_dash="dot", line_color=CRIMSON, annotation_text="25")
        fig.add_hline(y=75, line_dash="dot", line_color=GOLD, annotation_text="75")
        apply_chart_layout(fig, "Fear & Greed over the past year", "Score", height=360)
        fig.update_yaxes(range=[0, 100])
        st.plotly_chart(fig)
        st.caption("Dotted lines mark CNN’s extreme-fear and extreme-greed thresholds.")

    components = fear["components"]
    if not components.empty:
        st.subheader("Seven components")
        styled = components.rename(
            columns={"component": "Component", "score": "Score", "rating": "CNN rating"}
        )
        st.dataframe(
            styled.style.format({"Score": "{:.1f}"}),
            hide_index=True,
        )


def _load_market():
    try:
        with st.spinner("Loading the VIX and sector returns…"):
            return cached_market()
    except (MarketDataError, Exception) as exc:
        callout(f"VIX and sector prices did not load. {exc}")
        return None


def _vix_section(market: dict) -> None:
    st.header("VIX")
    level = market["vix"]
    ma50 = market["vix_ma50"]
    three_month = market["vix3m"]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("VIX", f"{level:.1f}" if level == level else "n/a")
        tone(market["vix_regime"], GOLD if market["vix_regime"] in {"Elevated", "Stressed"} else SLATE)
    c2.metric("50-day average", _fmt(ma50))
    c3.metric("3-month VIX", _fmt(three_month))
    st.caption(f"Closes as of {market['asof']}. The level band is a dashboard convention, not a Cboe classification.")

    sentences = [
        (
            f"The VIX closed at {level:.1f}, which this dashboard labels {market['vix_regime'].lower()}."
            if level == level
            else "The VIX close was not available."
        )
    ]
    if ma50 == ma50:
        relation = "above" if level > ma50 else "below"
        sentences.append(f"It is {relation} its 50-day average of {ma50:.1f}.")
    if three_month == three_month:
        if level > three_month:
            sentences.append("Near-term implied volatility is above the 3-month reading.")
        else:
            sentences.append("Near-term implied volatility is below the 3-month reading.")
    callout(" ".join(sentences))

    history = market["vix_history"]
    fig = go.Figure()
    fig.add_scatter(
        x=history["date"], y=history["vix"], mode="lines", name="VIX",
        line=dict(color=NAVY, width=2),
    )
    fig.add_scatter(
        x=history["date"], y=history["ma50"], mode="lines", name="50-day average",
        line=dict(color=SLATE, width=1.5, dash="dot"),
    )
    apply_chart_layout(fig, "VIX and its 50-day average", "VIX", height=360)
    st.plotly_chart(fig)


def _sector_section(market: dict) -> None:
    st.header("Sector rotation")
    labels = [phase["id"] for phase in PHASES]
    selected = st.radio("Phase to review", labels, horizontal=True, key="cycle_phase")
    phase = next(item for item in PHASES if item["id"] == selected)
    callout(phase["summary"])

    sectors = market["sectors"].copy()
    leaders = set(phase["leaders"])
    sectors["role"] = sectors["ticker"].map(
        lambda ticker: "Tended to lead" if ticker in leaders else "—"
    )
    sectors = sectors.sort_values("rel_3m", ascending=True)

    colors = [GOLD if ticker in leaders else NAVY for ticker in sectors["ticker"]]
    fig = go.Figure()
    fig.add_bar(
        y=sectors["name"] + " (" + sectors["ticker"] + ")",
        x=sectors["rel_3m"] * 100,
        orientation="h",
        marker_color=colors,
        text=sectors["rel_3m"].map(lambda value: _pct(value)),
        textposition="outside",
        cliponaxis=False,
        name="3-month return vs SPY",
        hovertemplate="%{y}<br>%{x:.1f} percentage points<extra></extra>",
    )
    apply_chart_layout(
        fig,
        "Three-month return versus SPY",
        "Percentage points",
        height=460,
        numeric_axis="x",
    )
    fig.update_layout(showlegend=False, margin=dict(l=8, r=48, t=72, b=8))
    st.plotly_chart(fig)
    note = (
        f"Each bar is the last 63 trading days’ total return minus SPY’s return, "
        f"from Yahoo Finance closes as of {market['asof']}."
    )
    if leaders:
        note = (
            f"Gold bars are sectors Fidelity’s research has found tended to lead in {phase['id'].lower()}. "
            + note
        )
    else:
        note = "This phase has no highlighted leaders in the cited Fidelity research. " + note
    st.caption(note)

    table = sectors.sort_values("rel_3m", ascending=False).rename(
        columns={
            "name": "Sector",
            "ticker": "ETF",
            "rel_1m": "1 month vs SPY",
            "rel_3m": "3 months vs SPY",
            "rel_6m": "6 months vs SPY",
            "role": "Selected phase",
        }
    )
    for column in ("1 month vs SPY", "3 months vs SPY", "6 months vs SPY"):
        table[column] = table[column].map(lambda value: "—" if value != value else f"{value * 100:+.1f}%")
    st.dataframe(table, hide_index=True)
    st.caption(
        "One month is 21 trading days, three months is 63, and six months is 126. "
        "Figures are price returns, not total returns."
    )
