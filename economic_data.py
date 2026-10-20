"""US economic series used by the macro report, read from FRED.

The API key is taken from the FRED_API_KEY environment variable or from
Streamlit secrets. It is not stored in this project. If no key is set, the
public FRED CSV is tried instead.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from io import StringIO

import pandas as pd

FETCH_START = "2021-01-01"
CHART_START = "2023-01-01"

SERIES = {
    "unemployment": "UNRATE",
    "nonfarm": "PAYEMS",
    "farm": "LNS12034560",
    "claims": "ICSA",
    "pce": "PCEPI",
    "core_pce": "PCEPILFE",
    "ppi": "PPIACO",
    "cpi": "CPIAUCSL",
    "core_cpi": "CPILFESL",
    "real_gdp": "GDPC1",
    "sentiment": "UMCSENT",
    "retail": "RSXFS",
}


class EconomicDataError(Exception):
    """Raised when the economic series cannot be loaded."""


def _api_key() -> str:
    key = os.environ.get("FRED_API_KEY", "").strip()
    if key:
        return key
    try:
        import streamlit as st

        secret = st.secrets.get("FRED_API_KEY", "")
    except Exception:
        secret = ""
    return str(secret or "").strip()


def _read_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "SentimentDashboard/1.0"})
    with urllib.request.urlopen(request, timeout=40) as response:
        return json.loads(response.read().decode())


def _series_from_api(series_id: str, api_key: str) -> pd.Series:
    params = urllib.parse.urlencode(
        {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "observation_start": FETCH_START,
        }
    )
    payload = _read_json("https://api.stlouisfed.org/fred/series/observations?" + params)
    rows = payload.get("observations") or []
    if not rows:
        message = payload.get("error_message") or f"FRED returned no observations for {series_id}."
        raise EconomicDataError(message)
    frame = pd.DataFrame(rows)
    values = pd.to_numeric(frame["value"], errors="coerce")
    series = pd.Series(values.to_numpy(), index=pd.to_datetime(frame["date"]), name=series_id)
    return series.dropna().sort_index()


def _series_from_csv(series_id: str) -> pd.Series:
    params = urllib.parse.urlencode({"id": series_id, "cosd": FETCH_START})
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?" + params
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=25) as response:
        text = response.read().decode()
    frame = pd.read_csv(StringIO(text))
    date_col = "DATE" if "DATE" in frame.columns else frame.columns[0]
    value_col = series_id if series_id in frame.columns else frame.columns[-1]
    values = pd.to_numeric(frame[value_col], errors="coerce")
    series = pd.Series(values.to_numpy(), index=pd.to_datetime(frame[date_col]), name=series_id)
    series = series.dropna().sort_index()
    if series.empty:
        raise EconomicDataError(f"FRED returned no observations for {series_id}.")
    return series


def _load_one(name: str, series_id: str, api_key: str) -> tuple[str, pd.Series]:
    if api_key:
        try:
            return name, _series_from_api(series_id, api_key)
        except Exception as api_error:
            try:
                return name, _series_from_csv(series_id)
            except Exception:
                raise EconomicDataError(f"{series_id} did not load. {api_error}") from api_error
    return name, _series_from_csv(series_id)


def _chart(series: pd.Series) -> pd.Series:
    return series[series.index >= CHART_START]


def _yoy(level: pd.Series, periods: int) -> pd.Series:
    return ((level / level.shift(periods)) - 1) * 100


def _latest(series: pd.Series) -> tuple[float, str]:
    clean = series.dropna()
    if clean.empty:
        return float("nan"), ""
    return float(clean.iloc[-1]), clean.index[-1].strftime("%Y-%m-%d")


def fetch_economic_report() -> dict:
    """Latest labour, price, and growth readings, with history from 2023."""
    api_key = _api_key()
    loaded: dict[str, pd.Series] = {}
    failures: list[str] = []

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [
            pool.submit(_load_one, name, series_id, api_key) for name, series_id in SERIES.items()
        ]
        for future in futures:
            try:
                name, series = future.result()
            except Exception as exc:
                failures.append(str(exc))
                continue
            loaded[name] = series

    required = ("unemployment", "nonfarm", "claims", "core_pce")
    if any(name not in loaded for name in required):
        detail = " ".join(failures[:3]) or "FRED did not return the labour and price series."
        if not api_key:
            detail += (
                " Set FRED_API_KEY in the environment, or in Streamlit secrets, "
                "and refresh."
            )
        raise EconomicDataError(detail)

    unemployment = loaded["unemployment"]
    unemployment_ma3 = unemployment.rolling(3).mean()
    nonfarm_change = loaded["nonfarm"].diff()
    nonfarm_ma3 = (loaded["nonfarm"] - loaded["nonfarm"].shift(3)) / 3
    claims_ma4 = loaded["claims"].rolling(4).mean() / 1000
    farm_change = loaded["farm"].diff() if "farm" in loaded else pd.Series(dtype=float)
    farm_ma3 = (
        (loaded["farm"] - loaded["farm"].shift(3)) / 3 if "farm" in loaded else pd.Series(dtype=float)
    )

    prices = pd.DataFrame(
        {
            "PCE": _yoy(loaded["pce"], 12) if "pce" in loaded else pd.Series(dtype=float),
            "Core PCE": _yoy(loaded["core_pce"], 12),
            "PPI": _yoy(loaded["ppi"], 12) if "ppi" in loaded else pd.Series(dtype=float),
            "CPI": _yoy(loaded["cpi"], 12) if "cpi" in loaded else pd.Series(dtype=float),
            "Core CPI": _yoy(loaded["core_cpi"], 12) if "core_cpi" in loaded else pd.Series(dtype=float),
        }
    ).dropna(how="all")

    real_gdp_yoy = _yoy(loaded["real_gdp"], 4) if "real_gdp" in loaded else pd.Series(dtype=float)
    real_gdp_level = loaded.get("real_gdp", pd.Series(dtype=float))
    real_gdp_annualized = ((real_gdp_level / real_gdp_level.shift(1)) ** 4 - 1) * 100
    retail_yoy = _yoy(loaded["retail"], 12) if "retail" in loaded else pd.Series(dtype=float)
    sentiment = loaded.get("sentiment", pd.Series(dtype=float))

    unemp_value, unemp_date = _latest(unemployment)
    nfp_value, nfp_date = _latest(nonfarm_ma3)
    nfp_month, _ = _latest(nonfarm_change)
    claims_value, claims_date = _latest(claims_ma4)
    farm_value, farm_date = _latest(farm_ma3)
    core_value, core_date = _latest(_yoy(loaded["core_pce"], 12))
    pce_value, pce_date = _latest(_yoy(loaded["pce"], 12) if "pce" in loaded else pd.Series(dtype=float))
    ppi_value, ppi_date = _latest(_yoy(loaded["ppi"], 12) if "ppi" in loaded else pd.Series(dtype=float))
    gdp_value, gdp_date = _latest(real_gdp_yoy)
    gdp_q, _ = _latest(real_gdp_annualized)
    sentiment_value, sentiment_date = _latest(sentiment)
    retail_value, retail_date = _latest(retail_yoy)

    price_rows = []
    for label, series_name in (
        ("Core PCE", "core_pce"),
        ("PCE", "pce"),
        ("Core CPI", "core_cpi"),
        ("CPI", "cpi"),
        ("PPI", "ppi"),
    ):
        if series_name not in loaded:
            continue
        value, date = _latest(_yoy(loaded[series_name], 12))
        price_rows.append({"Indicator": label, "As of": date[:7], "Year-over-year": value})

    return {
        "unemployment": unemp_value,
        "unemployment_date": unemp_date,
        "nfp_3m": nfp_value,
        "nfp_month": nfp_month,
        "nfp_date": nfp_date,
        "claims_4w": claims_value,
        "claims_date": claims_date,
        "farm_3m": farm_value,
        "farm_date": farm_date,
        "core_pce": core_value,
        "core_pce_date": core_date,
        "pce": pce_value,
        "pce_date": pce_date,
        "ppi": ppi_value,
        "ppi_date": ppi_date,
        "real_gdp_yoy": gdp_value,
        "real_gdp_annualized": gdp_q,
        "real_gdp_date": gdp_date,
        "sentiment": sentiment_value,
        "sentiment_date": sentiment_date,
        "retail_yoy": retail_value,
        "retail_date": retail_date,
        "unemployment_history": _chart(unemployment),
        "unemployment_ma3": _chart(unemployment_ma3),
        "unemployment_low": _chart(unemployment_ma3.rolling(12).min()),
        "nfp_history": _chart(nonfarm_change),
        "nfp_ma3_history": _chart(nonfarm_ma3),
        "claims_history": _chart(claims_ma4),
        "farm_history": _chart(farm_change),
        "farm_ma3_history": _chart(farm_ma3),
        "price_history": prices[prices.index >= CHART_START],
        "price_table": pd.DataFrame(price_rows),
        "gdp_history": _chart(real_gdp_yoy),
        "sentiment_history": _chart(sentiment),
        "retail_history": _chart(retail_yoy),
        "failures": failures,
    }
