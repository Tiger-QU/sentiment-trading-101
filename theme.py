"""Apex Institute visual system for the Sentiment Dashboard dashboard."""

from __future__ import annotations

import html
from datetime import datetime

import streamlit as st

NAVY = "#0F172A"
WHITE = "#F8FAFC"
GOLD = "#B45309"
SLATE = "#475569"
SAGE = "#15803D"
CRIMSON = "#B91C1C"
GRID = "#E2E8F0"
CALLOUT = "#F1F5F9"
SERIF = "Merriweather, Georgia, serif"
SANS = "Inter, Helvetica Neue, Arial, sans-serif"
MONO = "JetBrains Mono, Courier New, monospace"

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@500&family=Merriweather:wght@600;700&display=swap');

html, body, [class*="css"], .stApp {
  font-family: Inter, "Helvetica Neue", Arial, sans-serif;
  color: #0F172A;
  background-color: #F8FAFC;
}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
  background-color: #F8FAFC;
}
[data-testid="stSidebar"] {
  background-color: #F1F5F9;
  border-right: 1px solid #E2E8F0;
}
[data-testid="stSidebar"] * {
  color: #0F172A;
}
.block-container {
  padding-top: 2.2rem;
  padding-bottom: 3rem;
  max-width: 1180px;
}
h1, [data-testid="stHeading"] h1 {
  font-family: Merriweather, Georgia, serif !important;
  font-weight: 700 !important;
  font-size: 36px !important;
  line-height: 1.2 !important;
  color: #0F172A !important;
  letter-spacing: -0.015em;
}
h2, [data-testid="stHeading"] h2 {
  font-family: Merriweather, Georgia, serif !important;
  font-weight: 600 !important;
  font-size: 24px !important;
  line-height: 1.3 !important;
  color: #0F172A !important;
}
h3, [data-testid="stHeading"] h3 {
  font-family: Inter, "Helvetica Neue", Arial, sans-serif !important;
  font-weight: 700 !important;
  font-size: 18px !important;
  line-height: 1.4 !important;
  color: #0F172A !important;
}
.stMarkdown p, .stMarkdown li {
  font-family: Inter, "Helvetica Neue", Arial, sans-serif;
  font-size: 16px;
  line-height: 1.6;
  color: #0F172A;
}
[data-testid="stCaptionContainer"] p, .stCaption {
  color: #475569 !important;
  font-size: 14px !important;
  line-height: 1.4 !important;
}
[data-testid="stMetricValue"] {
  font-family: "JetBrains Mono", "Courier New", monospace !important;
  font-weight: 500 !important;
  color: #0F172A !important;
}
[data-testid="stMetricLabel"] p, [data-testid="stMetricLabel"] {
  font-family: Inter, "Helvetica Neue", Arial, sans-serif !important;
  color: #475569 !important;
  font-size: 14px !important;
}
.apex-lockup {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 18px;
  padding: 4px 8px 4px 4px;
}
.apex-mark {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #B45309;
  font-size: 26px;
  line-height: 1;
}
.apex-kicker {
  font-family: Merriweather, Georgia, serif;
  font-weight: 700;
  font-size: 15px;
  letter-spacing: 0.12em;
  color: #0F172A;
  line-height: 1.2;
}
.apex-kicker-sub {
  font-family: Inter, "Helvetica Neue", Arial, sans-serif;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #475569;
  line-height: 1.3;
}
.apex-lede {
  font-family: Inter, "Helvetica Neue", Arial, sans-serif;
  font-size: 16px;
  line-height: 1.6;
  color: #475569;
  margin-top: 0;
  max-width: 760px;
}
.apex-callout {
  background: #F1F5F9;
  border-left: 3px solid #B45309;
  padding: 14px 16px;
  margin: 8px 0 18px 0;
  color: #0F172A;
  font-family: Inter, "Helvetica Neue", Arial, sans-serif;
  font-size: 16px;
  line-height: 1.6;
}
.apex-sources {
  margin-top: 28px;
  padding-top: 12px;
  border-top: 1px solid #E2E8F0;
}
.apex-sources-label {
  font-family: "JetBrains Mono", "Courier New", monospace;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #475569;
  margin-bottom: 6px;
}
.apex-sources ul {
  margin: 0;
  padding-left: 18px;
}
.apex-sources li, .apex-sources a {
  font-family: Inter, "Helvetica Neue", Arial, sans-serif;
  font-size: 14px;
  line-height: 1.5;
  color: #475569;
}
.apex-tag {
  font-family: "JetBrains Mono", "Courier New", monospace;
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.02em;
}
.apex-footer {
  margin-top: 28px;
  font-family: Inter, "Helvetica Neue", Arial, sans-serif;
  font-size: 14px;
  line-height: 1.4;
  color: #475569;
  text-align: center;
}
div[data-testid="stDataFrame"] {
  border: 1px solid #E2E8F0;
}
@media (max-width: 768px) {
  h1, [data-testid="stHeading"] h1 { font-size: 28px !important; }
  h2, [data-testid="stHeading"] h2 { font-size: 20px !important; }
  h3, [data-testid="stHeading"] h3 { font-size: 16px !important; }
  .stMarkdown p, .stMarkdown li, .apex-lede, .apex-callout { font-size: 15px; }
}
"""


def apply_theme() -> None:
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def brand_header(title: str, lede: str) -> None:
    st.markdown(
        """
        <div class="apex-lockup">
          <div class="apex-mark" aria-hidden="true">▲</div>
          <div>
            <div class="apex-kicker">APEX INSTITUTE</div>
            <div class="apex-kicker-sub">for Advanced Research</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.title(title)
    st.markdown(f'<p class="apex-lede">{html.escape(lede)}</p>', unsafe_allow_html=True)


def callout(text: str) -> None:
    st.markdown(
        f'<div class="apex-callout">{html.escape(text)}</div>',
        unsafe_allow_html=True,
    )


def sources(entries: list[str]) -> None:
    items = "".join(f"<li>{entry}</li>" for entry in entries)
    st.markdown(
        f'<div class="apex-sources"><p class="apex-sources-label">Sources</p><ul>{items}</ul></div>',
        unsafe_allow_html=True,
    )


def page_footer() -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    st.markdown(
        f'<p class="apex-footer">Apex Institute for Advanced Research · Sentiment Dashboard · {today}</p>',
        unsafe_allow_html=True,
    )


def sentiment_color(label: str) -> str:
    return {
        "Bullish": SAGE,
        "Neutral": SLATE,
        "Bearish": CRIMSON,
        "No data": SLATE,
    }.get(label, SLATE)


def rating_color(rating: str) -> str:
    text = (rating or "").lower()
    if "fear" in text:
        return CRIMSON
    if "greed" in text:
        return GOLD
    return SLATE


def tone(text: str, color: str) -> None:
    st.markdown(
        f"<span class='apex-tag' style='color:{color}'>{html.escape(text)}</span>",
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    """One ticker box for every page. It lives outside the page scripts so navigation does not clear it."""
    st.sidebar.markdown("##### Series")
    if "shared_ticker" not in st.session_state:
        st.session_state.shared_ticker = "AAPL"
    if not str(st.session_state.get("ticker_input", "")).strip():
        st.session_state.ticker_input = st.session_state.shared_ticker

    raw = st.sidebar.text_input("Ticker", key="ticker_input")
    cleaned = raw.strip().upper()
    if cleaned:
        st.session_state.shared_ticker = cleaned

    page = ""
    try:
        page = st.context.url or ""
    except Exception:
        page = ""
    if page.rstrip("/").endswith("/options"):
        expiry_slider()

    if st.sidebar.button("Refresh data", width="stretch"):
        from loaders import clear_caches

        clear_caches()
        st.rerun()
    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Prices, volume, and option chains: Yahoo Finance via yfinance, "
        "about 15 minutes delayed. US-listed names. Daily option volume resets "
        "each session. Open interest updates once a day."
    )


def current_ticker() -> str:
    return (st.session_state.get("shared_ticker") or "AAPL").strip().upper()


def expiry_slider() -> int:
    if "max_expiries" not in st.session_state:
        st.session_state.max_expiries = 8
    return int(
        st.sidebar.slider(
            "Expiries to include (nearest N)",
            min_value=1,
            max_value=30,
            key="max_expiries",
            help="Fewer expiries load faster. Yahoo Finance is queried once per expiry.",
        )
    )


def apply_chart_layout(
    fig,
    title: str,
    y_title: str,
    height: int = 380,
    numeric_axis: str = "y",
    zero_base: bool = True,
) -> None:
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(family=SERIF, size=20, color=NAVY),
            x=0,
            xanchor="left",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=SANS, color=NAVY, size=13),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(family=SANS, size=12, color=SLATE),
        ),
        margin=dict(l=8, r=16, t=72, b=8),
        height=height,
        hoverlabel=dict(font_family=SANS, font_size=13),
    )
    axis_font = dict(family=MONO, size=11, color=SLATE)
    fig.update_xaxes(showgrid=False, zeroline=False, title_text=None, tickfont=axis_font)
    fig.update_yaxes(showgrid=False, zeroline=False, title_text=None, tickfont=axis_font)
    updates = dict(
        showgrid=True,
        gridcolor=GRID,
        gridwidth=1,
        zeroline=True,
        zerolinecolor=GRID,
        title_text=y_title,
        title_font=dict(family=SANS, size=12, color=SLATE),
        tickfont=axis_font,
    )
    if zero_base:
        updates["rangemode"] = "tozero"
    if numeric_axis == "x":
        fig.update_xaxes(**updates)
    else:
        fig.update_yaxes(**updates)
    return fig


SRC_CNN = (
    'CNN, <a href="https://www.cnn.com/markets/fear-and-greed">Fear &amp; Greed Index</a>. '
    "The score, rating, history, and seven components are CNN’s. "
    "Bands used with the published rating: 0–25 extreme fear, 25–45 fear, 45–55 neutral, "
    "55–75 greed, 75–100 extreme greed."
)
SRC_CBOE = (
    'Cboe, <a href="https://www.cboe.com/tradable-products/vix/">VIX Index</a>. '
    "The VIX is a 30-day implied-volatility reading for the S&amp;P 500, quoted as an annualized percentage. "
    "Level bands on this dashboard (under 15 calm, 15–20 normal, 20–30 elevated, above 30 stressed) "
    "are dashboard conventions, not a Cboe classification. "
    "The comparison with the 50-day average follows the volatility component of CNN’s index."
)
SRC_FIDELITY = (
    'Dirk Hofschire, Cait Dourney, and Jacob Weinstein, '
    '"<a href="https://institutional.fidelity.com/advisors/insights/topics/portfolio-construction/the-business-cycle-approach-to-equity-sector-investing">The Business Cycle Approach to Equity Sector Investing</a>," '
    "Fidelity Institutional, updated 2025-02-10. "
    'See also Fidelity, "<a href="https://www.fidelity.com/viewpoints/investing-ideas/sector-investing-business-cycle">The business cycle: Equity sector investing</a>," '
    'and <a href="https://www.fidelity.com/bin-public/060_www_fidelity_com/documents/fixed-income/Business_Cycle_Sector_Approach.pdf">The Business Cycle Approach to Equity Sector Investing</a> (PDF). '
    "Sector returns on this dashboard use Yahoo Finance prices for the SPDR sector ETFs and SPY."
)
SRC_YAHOO = (
    "Option chains, prices, and volume: Yahoo Finance via the yfinance library. "
    "Option field definitions are in DATA_DICTIONARY.md in this project. "
    "Quotes are about 15 minutes delayed. US-listed options only."
)
SRC_PCR = (
    "Put/call labels are a dashboard convention: below 0.7 bullish, 0.7 to 1.0 neutral, "
    "and 1.0 or above bearish. Implied-volatility comments use a second convention: "
    "an IV/HV ratio of 1.2 or above is described as elevated relative to the last 30 trading days, "
    "and a ratio of 0.9 or below as low relative to those days."
)
SRC_WILDER = (
    "J. Welles Wilder Jr., <em>New Concepts in Technical Trading Systems</em> "
    "(Trend Research, 1978). RSI uses Wilder’s 14-day smoothing. "
    "Readings under 30 are oversold and readings over 70 are overbought in that framework."
)
SRC_VOLUME = (
    "The six-row price-and-volume reading guide was supplied for this project. "
    "It is shown as a reading guide, not as an Apex Institute recommendation. "
    "Price trend is the close-to-close return over the last 20 trading days: "
    "above +3% is up, below −3% is down, otherwise stable. "
    "Volume trend compares the average of the last 5 sessions with the average of the last 20: "
    "at least 15% higher is increasing, at least 15% lower is decreasing, otherwise steady."
)
