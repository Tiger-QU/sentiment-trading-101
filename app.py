"""
Sentiment Dashboard

Overview, then market mood, options, and price confirmation.

Run from this folder:
    streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from theme import apply_theme
from views.market_mood import render as render_market
from views.options_page import render as render_options
from views.overview import render as render_overview
from views.price_volume import render as render_price

st.set_page_config(
    page_title="Sentiment Dashboard",
    page_icon="▲",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()

navigation = st.navigation(
    [
        st.Page(render_overview, title="Overview", url_path="overview", default=True),
        st.Page(render_market, title="Market mood", url_path="market-mood"),
        st.Page(render_options, title="Options", url_path="options"),
        st.Page(render_price, title="Price and volume", url_path="price-and-volume"),
    ],
    position="sidebar",
)
navigation.run()
