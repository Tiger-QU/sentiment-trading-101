###############################################################################
"""
Options Sentiment Data Layer

Pulls public options-chain data from Yahoo Finance (via yfinance) and turns it
into sentiment metrics:

  - Total options volume   = sum(call volume) + sum(put volume)   [today's trades]
  - Put/Call transaction   = sum(put volume) / sum(call volume)   [today's flow]
  - Put/Call inforce (OI)   = sum(put OI)     / sum(call OI)        [outstanding]

Data caveats (free Yahoo feed):
  - Quotes are ~15 minutes delayed.
  - Daily `volume` resets each trading session.
  - `openInterest` is updated once per day (prior-session settlement).
  - US-listed options only.

Requirements: pip install yfinance pandas
"""

from __future__ import annotations

import os
import shutil
import tempfile
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf

# Default location for the accumulating put/call history log.
DEFAULT_HISTORY_PATH = os.path.join(os.path.dirname(__file__), "pcr_history.csv")
_FALLBACK_HISTORY_PATH = os.path.join(tempfile.gettempdir(), "sentiment_dashboard_pcr_history.csv")

HISTORY_COLUMNS = [
    "timestamp",
    "date",
    "ticker",
    "spot",
    "call_vol",
    "put_vol",
    "call_oi",
    "put_oi",
    "pcr_volume",
    "pcr_oi",
    "iv",
    "hv30",
]


def _writable(path: str) -> bool:
    folder = os.path.dirname(path) or "."
    if os.path.exists(path):
        return os.access(path, os.W_OK)
    return os.path.isdir(folder) and os.access(folder, os.W_OK)


def active_history_path(path: str | None = None) -> str:
    """History file that can be updated. Cloud hosts often ship the app folder read-only."""
    preferred = path or DEFAULT_HISTORY_PATH
    if _writable(preferred):
        return preferred
    if os.path.exists(preferred) and not os.path.exists(_FALLBACK_HISTORY_PATH):
        try:
            shutil.copyfile(preferred, _FALLBACK_HISTORY_PATH)
        except OSError:
            pass
    return _FALLBACK_HISTORY_PATH


def _sum_column(frame, column: str) -> float:
    """Sum a chain column. yfinance returns None instead of an empty frame when a chain is missing."""
    if frame is None or not hasattr(frame, "columns"):
        return 0.0
    if frame.empty or column not in frame.columns:
        return 0.0
    return float(frame[column].fillna(0).sum())


def _safe_ratio(numerator: float, denominator: float) -> float:
    """Put/Call ratio that avoids divide-by-zero (returns NaN when no calls)."""
    if denominator and denominator > 0:
        return float(numerator) / float(denominator)
    return float("nan")


def classify_sentiment(pcr: float) -> str:
    """
    Map a put/call ratio to a rough sentiment label.

    Conventional reading: a high put/call ratio means heavy put activity
    (defensive / bearish), while a low ratio leans bullish.
    """
    if pcr != pcr:  # NaN check
        return "No data"
    if pcr >= 1.0:
        return "Bearish"
    if pcr >= 0.7:
        return "Neutral"
    return "Bullish"


# Below this, yfinance is almost certainly returning a placeholder (e.g. the
# 0.00001 it emits when it cannot compute IV, typically when there are no live
# quotes outside trading hours). Real single-name equity IV is essentially never
# this low, so we treat such values as missing.
MIN_VALID_IV = 0.01


def weighted_iv(
    df: pd.DataFrame,
    spot: float | None = None,
    band: float = 0.10,
    min_iv: float = MIN_VALID_IV,
) -> float:
    """
    At-the-money implied volatility for a chain DataFrame.

    yfinance reports `impliedVolatility` as a decimal fraction (0.30 = 30%).
    Because of the volatility smile, far in/out-of-the-money strikes carry very
    high IV; to get a number comparable to historical vol we restrict to
    near-the-money contracts (|strike/spot - 1| <= band) when a spot price is
    available, then weight by open interest (fallback volume, then simple mean).
    The band widens automatically if nothing falls inside it.

    Implied vols below `min_iv` are dropped as placeholders (see MIN_VALID_IV).
    """
    if df is None or df.empty:
        return float("nan")

    d = df[["strike", "impliedVolatility", "openInterest", "volume"]].copy()
    d = d[d["impliedVolatility"].notna() & (d["impliedVolatility"] >= min_iv)]
    if d.empty:
        return float("nan")

    if spot is not None and spot == spot and spot > 0:
        moneyness = (d["strike"] / spot - 1.0).abs()
        for b in (band, band * 2, band * 4):
            near = d[moneyness <= b]
            if not near.empty:
                d = near
                break

    w = d["openInterest"].fillna(0).astype(float)
    if w.sum() <= 0:
        w = d["volume"].fillna(0).astype(float)
    if w.sum() <= 0:
        return float(d["impliedVolatility"].mean())

    return float((d["impliedVolatility"] * w).sum() / w.sum())


def compute_historical_volatility(
    ticker, window: int = 30, trading_periods: int = 252
) -> float:
    """
    Annualized historical (realized) volatility from daily close-to-close returns.

    HV = stdev(log returns over the last `window` trading days) * sqrt(252),
    expressed as a decimal fraction so it is directly comparable to implied vol.

    Args:
        ticker: A symbol string or an existing yf.Ticker.
        window: Number of trailing trading days (default 30).
        trading_periods: Annualization factor (default 252).
    """
    tk = ticker if isinstance(ticker, yf.Ticker) else yf.Ticker(ticker)
    try:
        hist = tk.history(period="6mo")
    except Exception:
        return float("nan")

    if hist.empty or "Close" not in hist or len(hist) < window + 1:
        return float("nan")

    log_ret = np.log(hist["Close"] / hist["Close"].shift(1)).dropna()
    if len(log_ret) < window:
        return float("nan")

    daily_std = log_ret.tail(window).std(ddof=1)
    return float(daily_std * np.sqrt(trading_periods))


def _get_spot_price(tk: yf.Ticker) -> float:
    """Best-effort current/last price without an extra heavy download."""
    try:
        fast = tk.fast_info
        price = fast.get("last_price") or fast.get("lastPrice")
        if price:
            return float(price)
    except Exception:
        pass
    try:
        hist = tk.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return float("nan")


def fetch_option_metrics(ticker: str, max_expiries: int | None = None) -> dict:
    """
    Fetch and aggregate options data for a single ticker.

    Args:
        ticker: Stock symbol, e.g. "AAPL".
        max_expiries: If set, only the nearest N expiries are fetched (keeps the
            request fast). None fetches every listed expiry.

    Returns:
        A dict with:
            ticker, spot, asof (datetime), n_expiries,
            call_vol, put_vol, total_vol,
            call_oi, put_oi, total_oi,
            pcr_volume, pcr_oi,
            sentiment_volume, sentiment_oi,
            per_expiry (pandas DataFrame, one row per expiry).
    """
    ticker = (ticker or "").strip().upper()
    if not ticker:
        raise ValueError("Ticker symbol is required.")

    tk = yf.Ticker(ticker)
    expiries = list(tk.options or [])
    if not expiries:
        raise ValueError(
            f"No options data found for '{ticker}'. "
            "Check the symbol (US-listed optionable stocks only)."
        )

    if max_expiries is not None and max_expiries > 0:
        expiries = expiries[:max_expiries]

    spot = _get_spot_price(tk)

    rows = []
    total_contracts = 0
    quoted_contracts = 0
    for exp in expiries:
        try:
            chain = tk.option_chain(exp)
            calls, puts = chain.calls, chain.puts
            c_vol = _sum_column(calls, "volume")
            p_vol = _sum_column(puts, "volume")
            c_oi = _sum_column(calls, "openInterest")
            p_oi = _sum_column(puts, "openInterest")
        except Exception:
            # Skip an expiry that fails to download rather than aborting.
            continue

        # Track how many contracts have a live two-sided quote. When the market
        # is closed/pre-market these collapse to zero and Yahoo's IV is unreliable.
        for leg in (calls, puts):
            if leg is not None and hasattr(leg, "empty") and not leg.empty and "bid" in leg.columns:
                total_contracts += len(leg)
                quoted_contracts += int(
                    ((leg["bid"].fillna(0) > 0) | (leg["ask"].fillna(0) > 0)).sum()
                )

        frames = [leg for leg in (calls, puts) if leg is not None and hasattr(leg, "empty") and not leg.empty]
        combined = pd.concat(frames) if frames else pd.DataFrame()
        rows.append(
            {
                "expiry": exp,
                "call_vol": c_vol,
                "put_vol": p_vol,
                "call_oi": c_oi,
                "put_oi": p_oi,
                "pcr_volume": _safe_ratio(p_vol, c_vol),
                "pcr_oi": _safe_ratio(p_oi, c_oi),
                "iv": weighted_iv(combined, spot=spot),
            }
        )

    if not rows:
        raise ValueError(f"Could not download any option chains for '{ticker}'.")

    per_expiry = pd.DataFrame(rows)

    call_vol = float(per_expiry["call_vol"].sum())
    put_vol = float(per_expiry["put_vol"].sum())
    call_oi = float(per_expiry["call_oi"].sum())
    put_oi = float(per_expiry["put_oi"].sum())

    pcr_volume = _safe_ratio(put_vol, call_vol)
    pcr_oi = _safe_ratio(put_oi, call_oi)

    # Overall implied volatility: per-expiry IV weighted by that expiry's total OI.
    oi_total = per_expiry["call_oi"] + per_expiry["put_oi"]
    iv_valid = per_expiry["iv"].notna()
    if (oi_total[iv_valid].sum() if iv_valid.any() else 0) > 0:
        iv = float(
            (per_expiry.loc[iv_valid, "iv"] * oi_total[iv_valid]).sum()
            / oi_total[iv_valid].sum()
        )
    elif iv_valid.any():
        iv = float(per_expiry.loc[iv_valid, "iv"].mean())
    else:
        iv = float("nan")

    hv_30 = compute_historical_volatility(tk, window=30)
    iv_hv_ratio = (iv / hv_30) if (hv_30 and hv_30 == hv_30 and hv_30 > 0) else float("nan")

    quote_coverage = (quoted_contracts / total_contracts) if total_contracts else 0.0
    # Need both live quotes and a usable IV for the implied-vol read to be trusted.
    iv_reliable = bool(quote_coverage >= 0.20 and iv == iv)

    return {
        "ticker": ticker,
        "spot": spot,
        "asof": datetime.now(),
        "n_expiries": len(per_expiry),
        "call_vol": call_vol,
        "put_vol": put_vol,
        "total_vol": call_vol + put_vol,
        "call_oi": call_oi,
        "put_oi": put_oi,
        "total_oi": call_oi + put_oi,
        "pcr_volume": pcr_volume,
        "pcr_oi": pcr_oi,
        "sentiment_volume": classify_sentiment(pcr_volume),
        "sentiment_oi": classify_sentiment(pcr_oi),
        "iv": iv,
        "hv_30": hv_30,
        "iv_hv_ratio": iv_hv_ratio,
        "quote_coverage": quote_coverage,
        "iv_reliable": iv_reliable,
        "per_expiry": per_expiry,
    }


def log_snapshot(summary: dict, path: str | None = None) -> None:
    """
    Append one snapshot row to the history CSV.

    De-duplicates on (ticker, date): if a row already exists for the same ticker
    and calendar day it is replaced with the latest values, so the file grows by
    at most one row per ticker per day while always holding the freshest read.
    """
    asof: datetime = summary.get("asof") or datetime.now()
    row = {
        "timestamp": asof.strftime("%Y-%m-%d %H:%M:%S"),
        "date": asof.strftime("%Y-%m-%d"),
        "ticker": summary["ticker"],
        "spot": round(summary.get("spot", float("nan")), 4),
        "call_vol": summary["call_vol"],
        "put_vol": summary["put_vol"],
        "call_oi": summary["call_oi"],
        "put_oi": summary["put_oi"],
        "pcr_volume": summary["pcr_volume"],
        "pcr_oi": summary["pcr_oi"],
        # Only persist IV when it is trustworthy, so the history chart is not
        # polluted by placeholder values from closed-market snapshots.
        "iv": summary.get("iv", float("nan")) if summary.get("iv_reliable", True) else float("nan"),
        "hv30": summary.get("hv_30", float("nan")),
    }

    path = active_history_path(path)

    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
        except Exception:
            df = pd.DataFrame(columns=HISTORY_COLUMNS)
    else:
        df = pd.DataFrame(columns=HISTORY_COLUMNS)

    new_row = pd.DataFrame([row], columns=HISTORY_COLUMNS)

    if df.empty:
        df = new_row
    else:
        # Drop any existing row for this ticker + day, then append the fresh one.
        mask = (df["ticker"] == row["ticker"]) & (df["date"] == row["date"])
        df = pd.concat([df[~mask], new_row], ignore_index=True)

    df = df[HISTORY_COLUMNS]
    df.to_csv(path, index=False)


def load_history(path: str | None = None, ticker: str | None = None) -> pd.DataFrame:
    """
    Load the put/call history log, optionally filtered to one ticker.

    Returns an empty (correctly-columned) DataFrame when no log exists yet.
    """
    path = active_history_path(path)

    if not os.path.exists(path):
        return pd.DataFrame(columns=HISTORY_COLUMNS)

    try:
        df = pd.read_csv(path)
    except Exception:
        return pd.DataFrame(columns=HISTORY_COLUMNS)

    if df.empty:
        return df

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.sort_values("timestamp")

    if ticker:
        df = df[df["ticker"] == ticker.strip().upper()]

    return df.reset_index(drop=True)


if __name__ == "__main__":
    # Quick smoke test from the command line.
    import sys

    sym = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    data = fetch_option_metrics(sym, max_expiries=8)
    print(f"{data['ticker']}  spot={data['spot']:.2f}  expiries={data['n_expiries']}")
    print(f"  Total volume : {data['total_vol']:,.0f}")
    print(f"  P/C volume   : {data['pcr_volume']:.3f}  ({data['sentiment_volume']})")
    print(f"  P/C open int : {data['pcr_oi']:.3f}  ({data['sentiment_oi']})")
    print(f"  Implied vol  : {data['iv'] * 100:.1f}%")
    print(f"  Hist vol 30d : {data['hv_30'] * 100:.1f}%")
    print(f"  IV / HV      : {data['iv_hv_ratio']:.2f}")
    log_snapshot(data)
    print("Logged snapshot ->", DEFAULT_HISTORY_PATH)
