"""Market Tape V29: one daily annual series + one intraday series per instrument."""
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from math import isfinite
import threading

_ET = ZoneInfo("America/New_York")
_LOCK = threading.RLock()
_DAILY = {}
_FAILURE_BACKOFF = {}


def _chart(symbol, range_, interval):
    from services.stock_fetcher import fetch_yahoo_json
    payload = fetch_yahoo_json(symbol, {
        "range": range_, "interval": interval,
        "includePrePost": "false",
    })
    chart = payload.get("chart") or {}
    if chart.get("error"):
        raise RuntimeError(f"{symbol}: Yahoo chart error: {chart['error']}")
    result = chart.get("result") or []
    if not result:
        raise RuntimeError(f"{symbol}: Yahoo returned no {range_}/{interval} chart")
    item = result[0]
    quotes = ((item.get("indicators") or {}).get("quote") or [])
    prices = quotes[0] if quotes else {}
    ts = item.get("timestamp") or []
    rows = []
    for i, timestamp in enumerate(ts):
        close = (prices.get("close") or [])
        if i >= len(close) or close[i] is None:
            continue
        try:
            value = float(close[i])
            opening = prices.get("open") or []
            start = float(opening[i]) if i < len(opening) and opening[i] is not None else None
        except (TypeError, ValueError, OverflowError):
            continue
        if value > 0 and isfinite(value):
            rows.append((int(timestamp), value, start))
    return item.get("meta") or {}, sorted(rows)


def _daily(symbol, today):
    # A year of daily data is downloaded once per trading date, not on every refresh.
    with _LOCK:
        entry = _DAILY.get(symbol)
        if entry and entry[0] == today:
            return entry[1]
        retry = _FAILURE_BACKOFF.get(symbol)
        if retry and datetime.now(_ET) < retry:
            return entry[1] if entry else []
    try:
        _, rows = _chart(symbol, "1y", "1d")
        if len(rows) < 100:
            raise RuntimeError(f"{symbol}: only {len(rows)} daily candles")
        with _LOCK:
            _DAILY[symbol] = (today, rows)
            _FAILURE_BACKOFF.pop(symbol, None)
        return rows
    except Exception as error:
        print(f"Market Tape daily cache: {symbol}: {error}", flush=True)
        with _LOCK:
            _FAILURE_BACKOFF[symbol] = datetime.now(_ET) + timedelta(minutes=30)
        return entry[1] if entry else []


def _valid_price(value):
    try:
        value = float(value)
        return value if isfinite(value) and value > 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def fetch_market_data_v29(index_symbols=None, stock_symbols=None, should_cancel=None):
    from services import stock_fetcher as sf
    now = datetime.now(_ET)
    indexes = sf.INDEX_SYMBOLS if index_symbols is None else index_symbols
    stocks = sf.STOCK_SYMBOLS if stock_symbols is None else stock_symbols

    def check():
        if should_cancel is not None and should_cancel():
            raise sf.StockFetchCancelled()

    def get(symbol, display_name, is_index):
        check()
        daily = _daily(symbol, now.date())
        meta, intraday = {}, []
        try:
            meta, intraday = _chart(symbol, "5d", "5m")
        except Exception as error:
            print(f"Market Tape intraday unavailable {symbol}: {error}", flush=True)
        check()
        price = _valid_price(meta.get("regularMarketPrice"))
        last_price = intraday[-1][1] if intraday else None
        if price is None:
            price = last_price
        if price is None and daily:
            price = daily[-1][1]
        if price is None:
            price_text = "—"
        else:
            price_text = (sf.format_index_price(price) if is_index else sf.format_price(price))
        history = [row[1] for row in daily[-65:]] if daily else [1, 1, 1]
        if is_index:
            quote = sf.IndexQuote(display_name, price_text, history)
        else:
            quote = sf.StockQuote(symbol, price_text, "—", history)
        quote._mui_daily_v29 = daily
        quote._mui_intraday_v29 = intraday
        quote._mui_live_v29 = price
        quote._mui_live_time_v30 = meta.get("regularMarketTime")
        quote._mui_fetched_v29 = datetime.now(_ET).isoformat(timespec="seconds")
        print(f"Market Tape V29 {symbol} price={price_text} daily={len(daily)} intraday={len(intraday)}", flush=True)
        return quote

    index_data = []
    for name, symbol in indexes:
        try:
            index_data.append(get(symbol, name, True))
        except sf.StockFetchCancelled:
            raise
        except Exception as error:
            print(f"Market Tape index {symbol} failed: {error}", flush=True)
            index_data.append(sf.IndexQuote(name, "—", [1, 1, 1]))
    stock_data = []
    for symbol in stocks:
        try:
            stock_data.append(get(symbol, symbol, False))
        except sf.StockFetchCancelled:
            raise
        except Exception as error:
            print(f"Market Tape stock {symbol} failed: {error}", flush=True)
            stock_data.append(sf.StockQuote(symbol, "—", "—", [1, 1, 1]))
    check()
    return sf.MarketData(index_data, stock_data)
