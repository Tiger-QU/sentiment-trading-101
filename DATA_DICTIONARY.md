# yfinance Options Data Dictionary

Raw fields returned by Yahoo Finance via `yfinance` (verified against `yfinance 0.2.66`).
This documents the **source data only** — not the derived metrics computed in this project.

Quotes are ~15 minutes delayed (`sourceInterval = 15`). Daily `volume` resets each
trading session; `openInterest` is updated once per day (prior-session settlement).
US-listed options only.

---

## 1. `Ticker.options`

A Python `tuple` of expiration dates available for the symbol.

| Item | Type | Description |
|------|------|-------------|
| each element | `str` | Expiration date, format `YYYY-MM-DD` (e.g. `"2026-06-08"`). |

```python
import yfinance as yf
yf.Ticker("AAPL").options          # -> ('2026-06-08', '2026-06-10', ...)
```

---

## 2. `Ticker.option_chain(expiry)`

Returns a named tuple `Options(calls, puts, underlying)`.

| Field | Type | Description |
|-------|------|-------------|
| `calls` | `pandas.DataFrame` | One row per call contract for that expiry (columns in section 3). |
| `puts` | `pandas.DataFrame` | One row per put contract for that expiry (columns in section 3). |
| `underlying` | `dict` | Snapshot quote/metadata for the underlying security (section 4). |

```python
oc = yf.Ticker("AAPL").option_chain("2026-06-08")
oc.calls          # DataFrame
oc.puts           # DataFrame
oc.underlying     # dict
```

---

## 3. Contract-level columns (`calls` / `puts` DataFrames)

Identical schema for calls and puts. One row = one option contract at a given strike/expiry.

| Column | dtype | Unit / Format | Description |
|--------|-------|---------------|-------------|
| `contractSymbol` | `object` (str) | OCC symbol | Unique contract id, e.g. `AAPL260608C00250000` = ticker + `YYMMDD` + `C`/`P` + strike×1000 (8 digits). |
| `lastTradeDate` | `datetime64[ns, UTC]` | timestamp (UTC) | Time of the most recent trade for this contract. Stale if illiquid. |
| `strike` | `float64` | price (USD) | Strike price of the contract. |
| `lastPrice` | `float64` | price (USD) | Last traded premium (per share; ×100 per contract). |
| `bid` | `float64` | price (USD) | Current best bid premium. `0.0`/`NaN` if none. |
| `ask` | `float64` | price (USD) | Current best ask premium. `0.0`/`NaN` if none. |
| `change` | `float64` | price (USD) | Premium change vs prior close (absolute). |
| `percentChange` | `float64` | percent | Premium change vs prior close (percent). |
| `volume` | `float64` | contracts | **Number of contracts traded today.** `NaN` when none traded yet this session (note: float, not int, because of NaN). |
| `openInterest` | `int64` | contracts | **Open interest = outstanding contracts** not yet closed/exercised. The "inforce" figure; updated once per day. |
| `impliedVolatility` | `float64` | decimal fraction | IV as a fraction (e.g. `1.41` = 141%). Yahoo's own estimate; can be noisy for deep ITM / illiquid strikes. |
| `inTheMoney` | `bool` | flag | `True` if the contract is currently in the money (call: spot > strike; put: spot < strike). |
| `contractSize` | `object` (str) | category | Contract multiplier descriptor; `"REGULAR"` = 100 shares per contract. |
| `currency` | `object` (str) | ISO code | Quote currency, e.g. `"USD"`. |

Notes:
- `volume` and `openInterest` are the two raw fields this project aggregates into the put/call ratios.
- Bid/ask can be `0.0` or `NaN` outside trading hours or for illiquid strikes; prefer `lastPrice` for stale contracts.

---

## 4. `underlying` metadata (selected raw fields)

The `underlying` dict is the underlying equity's quote snapshot (the same payload Yahoo serves
for the stock). It is **not** option statistics, but it provides context (spot price, market state,
data delay). Selected fields most useful alongside options:

| Key | Type | Description |
|-----|------|-------------|
| `symbol` | str | Underlying ticker. |
| `shortName` / `longName` / `displayName` | str | Company name. |
| `currency` / `financialCurrency` | str | Quote currency. |
| `marketState` | str | `PRE` / `REGULAR` / `POST` / `CLOSED`. |
| `regularMarketPrice` | float | Last regular-session price (spot). |
| `regularMarketChange` / `regularMarketChangePercent` | float | Day change (absolute / percent). |
| `regularMarketPreviousClose` | float | Prior session close. |
| `regularMarketOpen` | float | Session open. |
| `regularMarketDayHigh` / `regularMarketDayLow` / `regularMarketDayRange` | float / str | Intraday high, low, and range string. |
| `regularMarketVolume` | int | Shares traded today (underlying stock, not options). |
| `bid` / `ask` / `bidSize` / `askSize` | float / int | Underlying NBBO quote and sizes. |
| `postMarketPrice` / `postMarketChange` / `postMarketChangePercent` | float | Post-market quote (if `hasPrePostMarketData`). |
| `fiftyTwoWeekHigh` / `fiftyTwoWeekLow` / `fiftyTwoWeekRange` | float / str | 52-week extremes. |
| `fiftyDayAverage` / `twoHundredDayAverage` | float | Moving-average price levels. |
| `averageDailyVolume3Month` / `averageDailyVolume10Day` | int | Average underlying share volume. |
| `sharesOutstanding` / `impliedSharesOutstanding` | int | Share count. |
| `marketCap` | int | Market capitalization. |
| `trailingPE` / `forwardPE` / `priceToBook` | float | Valuation ratios. |
| `epsTrailingTwelveMonths` / `epsForward` / `epsCurrentYear` | float | Earnings per share. |
| `dividendRate` / `dividendYield` / `dividendDate` | float / int | Dividend rate, yield, next date (epoch seconds). |
| `earningsTimestamp` / `earningsTimestampStart` / `earningsTimestampEnd` | int | Next earnings date(s), epoch seconds; `isEarningsDateEstimate` flags estimates. |
| `exchange` / `fullExchangeName` / `exchangeTimezoneName` | str | Listing venue and timezone. |
| `quoteType` | str | Security type, e.g. `EQUITY`. |
| `sourceInterval` | int | Data delay in minutes (e.g. `15`). |
| `exchangeDataDelayedBy` | int | Additional exchange delay (seconds). |
| `quoteSourceName` | str | Quote source, e.g. `Nasdaq Real Time Price`. |
| `averageAnalystRating` | str | Consensus rating string, e.g. `2.0 - Buy`. |

Epoch timestamp fields (`dividendDate`, `earningsTimestamp*`, `postMarketTime`, `regularMarketTime`,
`firstTradeDateMilliseconds`) are Unix time — seconds, except `firstTradeDateMilliseconds` which is in
milliseconds. Convert with `datetime.utcfromtimestamp(...)`.

---

## 5. Quick reference: building put/call statistics from raw fields

| Desired statistic | Raw source fields |
|-------------------|-------------------|
| Total options volume | sum of `volume` across all `calls` + `puts` rows / expiries |
| Put/Call transaction (volume) ratio | sum(`puts.volume`) / sum(`calls.volume`) |
| Put/Call inforce (open-interest) ratio | sum(`puts.openInterest`) / sum(`calls.openInterest`) |
| Spot price (for moneyness/context) | `underlying.regularMarketPrice` |
| Per-strike moneyness | `inTheMoney`, or compare `strike` to `underlying.regularMarketPrice` |
