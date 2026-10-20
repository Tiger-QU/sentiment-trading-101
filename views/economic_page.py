"""Economic data: labour market, prices, and growth from the macro report."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from economic_data import EconomicDataError
from loaders import cached_economy
from theme import (
    CRIMSON,
    GOLD,
    NAVY,
    SLATE,
    SRC_FRED,
    apply_chart_layout,
    brand_header,
    callout,
    page_footer,
    sources,
)


def _num(value, digits=1, suffix="") -> str:
    if value != value:
        return "n/a"
    return f"{value:.{digits}f}{suffix}"


def _signed(value, digits=0, suffix="") -> str:
    if value != value:
        return "n/a"
    return f"{value:+.{digits}f}{suffix}"


def render() -> None:
    brand_header(
        "Economic data",
        "The labour market, inflation, and growth series from the US macro report.",
    )
    try:
        with st.spinner("Loading economic series…"):
            report = cached_economy()
    except (EconomicDataError, Exception) as exc:
        callout(f"Economic series did not load. {exc}")
        page_footer()
        return

    _summary(report)
    _labour(report)
    _prices(report)
    _growth(report)
    if report["failures"]:
        st.caption("Some series did not load: " + " ".join(report["failures"][:3]))
    sources([SRC_FRED])
    page_footer()


def _summary(report: dict) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Unemployment", _num(report["unemployment"], 1, "%"))
    c1.caption(report["unemployment_date"][:7])
    c2.metric("Payrolls, 3-month average", _signed(report["nfp_3m"], 0, "k"))
    c2.caption(report["nfp_date"][:7])
    c3.metric("Initial claims, 4-week average", _num(report["claims_4w"], 0, "k"))
    c3.caption(report["claims_date"])
    c4.metric("Core PCE, year-over-year", _num(report["core_pce"], 1, "%"))
    c4.caption(report["core_pce_date"][:7])

    gap = report["core_pce"] - 2
    relation = "above" if gap > 0 else "below"
    callout(
        f"Unemployment was {_num(report['unemployment'], 1)}% in {report['unemployment_date'][:7]}. "
        f"Nonfarm payrolls changed by an average of {_signed(report['nfp_3m'], 0)} thousand a month "
        f"over the three months through {report['nfp_date'][:7]}. "
        f"Initial claims averaged {_num(report['claims_4w'], 0)} thousand over the four weeks "
        f"through {report['claims_date']}. "
        f"Core PCE was {_num(report['core_pce'], 1)}% higher than a year earlier in "
        f"{report['core_pce_date'][:7]}, {abs(gap):.1f} percentage points {relation} "
        f"the Federal Reserve’s 2% longer-run inflation goal."
    )


def _labour(report: dict) -> None:
    st.header("Labour market")
    st.caption(
        "Unemployment and nonfarm payrolls are monthly. Initial claims are weekly. "
        "Payroll changes use the latest revised level, not the first published estimate."
    )

    fig = go.Figure()
    fig.add_scatter(
        x=report["unemployment_history"].index,
        y=report["unemployment_history"],
        mode="lines",
        name="Unemployment rate",
        line=dict(color=NAVY, width=2),
    )
    fig.add_scatter(
        x=report["unemployment_ma3"].index,
        y=report["unemployment_ma3"],
        mode="lines",
        name="3-month average",
        line=dict(color=GOLD, width=2),
    )
    fig.add_scatter(
        x=report["unemployment_low"].index,
        y=report["unemployment_low"],
        mode="lines",
        name="Lowest 3-month average, past 12 months",
        line=dict(color=SLATE, width=1.5, dash="dot"),
    )
    fig.add_hline(y=4, line_dash="dash", line_color=CRIMSON, line_width=1)
    apply_chart_layout(fig, "Unemployment rate", "Percent", height=360, zero_base=False)
    st.plotly_chart(fig)
    st.caption(
        "The dashed line at 4% is a dashboard reference carried from the macro report, not a BLS threshold. "
        f"Latest rate: {_num(report['unemployment'], 1)}% as of {report['unemployment_date'][:7]}."
    )

    fig = go.Figure()
    fig.add_scatter(
        x=report["nfp_history"].index,
        y=report["nfp_history"],
        mode="lines",
        name="Monthly change",
        line=dict(color=NAVY, width=1.5),
    )
    fig.add_scatter(
        x=report["nfp_ma3_history"].index,
        y=report["nfp_ma3_history"],
        mode="lines",
        name="3-month average",
        line=dict(color=GOLD, width=2),
    )
    fig.add_hline(y=200, line_dash="dash", line_color=CRIMSON, line_width=1)
    apply_chart_layout(fig, "Nonfarm payrolls, monthly change", "Thousands", height=360, zero_base=False)
    st.plotly_chart(fig)
    st.caption(
        "The dashed line at 200 thousand is a dashboard reference for a strong month, not a BLS threshold. "
        f"Latest monthly change: {_signed(report['nfp_month'], 0)} thousand. "
        f"Three-month average: {_signed(report['nfp_3m'], 0)} thousand, as of {report['nfp_date'][:7]}."
    )

    fig = go.Figure()
    fig.add_scatter(
        x=report["claims_history"].index,
        y=report["claims_history"],
        mode="lines",
        name="4-week average",
        line=dict(color=NAVY, width=2),
    )
    fig.add_hline(y=300, line_dash="dash", line_color=GOLD, line_width=1)
    fig.add_hline(y=400, line_dash="dash", line_color=CRIMSON, line_width=1)
    apply_chart_layout(fig, "Initial jobless claims, 4-week average", "Thousands", height=340, zero_base=False)
    st.plotly_chart(fig)
    st.caption(
        "Gold marks 300 thousand and crimson marks 400 thousand. Both lines are dashboard references "
        "from the macro report, not an official classification. "
        f"Latest four-week average: {_num(report['claims_4w'], 0)} thousand as of {report['claims_date']}."
    )

    if not report["farm_history"].empty:
        fig = go.Figure()
        fig.add_scatter(
            x=report["farm_history"].index,
            y=report["farm_history"],
            mode="lines",
            name="Monthly change",
            line=dict(color=SLATE, width=1.5),
        )
        fig.add_scatter(
            x=report["farm_ma3_history"].index,
            y=report["farm_ma3_history"],
            mode="lines",
            name="3-month average",
            line=dict(color=GOLD, width=2),
        )
        fig.add_hline(y=0, line_color=NAVY, line_width=1)
        apply_chart_layout(
            fig,
            "Farm employment, monthly change",
            "Thousands",
            height=320,
            zero_base=False,
        )
        st.plotly_chart(fig)
        st.caption(
            "Agriculture and related employment from the household survey, in thousands. "
            f"Three-month average change: {_signed(report['farm_3m'], 0)} thousand "
            f"as of {report['farm_date'][:7]}."
        )


def _prices(report: dict) -> None:
    st.header("Prices")
    history = report["price_history"]
    fig = go.Figure()
    colors = {"Core PCE": NAVY, "PCE": SLATE, "PPI": GOLD}
    for name, color in colors.items():
        if name not in history.columns:
            continue
        fig.add_scatter(
            x=history.index,
            y=history[name],
            mode="lines",
            name=name,
            line=dict(color=color, width=2),
        )
    fig.add_hline(y=2, line_dash="dash", line_color=CRIMSON, line_width=1)
    apply_chart_layout(fig, "Year-over-year price change", "Percent", height=380, zero_base=False)
    st.plotly_chart(fig)
    st.caption(
        "The dashed line is the Federal Reserve’s 2% longer-run inflation goal, measured by the PCE price index. "
        "Core PCE excludes food and energy. PPI here is the all-commodities index, which moves more than consumer prices."
    )

    table = report["price_table"].copy()
    table["Year-over-year"] = table["Year-over-year"].map(
        lambda value: "n/a" if value != value else f"{value:.1f}%"
    )
    st.dataframe(table, hide_index=True)


def _growth(report: dict) -> None:
    st.header("Growth and sentiment")
    c1, c2, c3 = st.columns(3)
    c1.metric("Real GDP, year-over-year", _num(report["real_gdp_yoy"], 1, "%"))
    c1.caption(report["real_gdp_date"][:7] if report["real_gdp_date"] else "")
    c2.metric("Real GDP, quarterly annualized", _num(report["real_gdp_annualized"], 1, "%"))
    c2.caption("Change from the previous quarter, annualized")
    c3.metric("Retail sales, year-over-year", _num(report["retail_yoy"], 1, "%"))
    c3.caption(report["retail_date"][:7] if report["retail_date"] else "")

    if not report["gdp_history"].empty:
        fig = go.Figure()
        fig.add_scatter(
            x=report["gdp_history"].index,
            y=report["gdp_history"],
            mode="lines",
            name="Real GDP, year-over-year",
            line=dict(color=NAVY, width=2),
        )
        fig.add_hline(y=0, line_color=SLATE, line_width=1)
        apply_chart_layout(fig, "Real GDP, year-over-year", "Percent", height=320, zero_base=False)
        st.plotly_chart(fig)
        st.caption("FRED dates each quarter by its first month. The series is inflation-adjusted GDP.")

    if not report["retail_history"].empty:
        fig = go.Figure()
        fig.add_scatter(
            x=report["retail_history"].index,
            y=report["retail_history"],
            mode="lines",
            name="Retail sales, year-over-year",
            line=dict(color=NAVY, width=2),
        )
        apply_chart_layout(fig, "Retail sales, year-over-year", "Percent", height=320, zero_base=False)
        st.plotly_chart(fig)
        st.caption("Advance retail sales, including food services. The change is from the same month a year earlier.")

    if not report["sentiment_history"].empty:
        st.metric("Michigan consumer sentiment", _num(report["sentiment"], 1))
        st.caption(f"Index, 1966 = 100. As of {report['sentiment_date'][:7]}.")
        fig = go.Figure()
        fig.add_scatter(
            x=report["sentiment_history"].index,
            y=report["sentiment_history"],
            mode="lines",
            name="Consumer sentiment",
            line=dict(color=GOLD, width=2),
        )
        apply_chart_layout(fig, "University of Michigan consumer sentiment", "Index", height=320, zero_base=False)
        st.plotly_chart(fig)
