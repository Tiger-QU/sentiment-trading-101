"""Cached reads shared by every page. Cache lifetime is 10 minutes."""

from __future__ import annotations

import streamlit as st

from economic_data import fetch_economic_report
from market_data import fetch_fear_greed, fetch_market_snapshot, fetch_price_study
from options_data import fetch_option_metrics


@st.cache_data(ttl=600, show_spinner=False)
def cached_fear_greed():
    return fetch_fear_greed()


@st.cache_data(ttl=600, show_spinner=False)
def cached_market():
    return fetch_market_snapshot()


@st.cache_data(ttl=600, show_spinner=False)
def cached_price(ticker: str):
    return fetch_price_study(ticker)


@st.cache_data(ttl=600, show_spinner=False)
def cached_options(ticker: str, max_expiries: int):
    return fetch_option_metrics(ticker, max_expiries=max_expiries)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_economy():
    return fetch_economic_report()


def clear_caches() -> None:
    cached_fear_greed.clear()
    cached_market.clear()
    cached_price.clear()
    cached_options.clear()
    cached_economy.clear()
