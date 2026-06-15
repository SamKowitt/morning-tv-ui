import csv
import io
import json
import os
import ssl
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import datetime, timedelta

import certifi


@dataclass
class IndexQuote:
    name: str
    price: str
    history: list[float]


@dataclass
class StockQuote:
    ticker: str
    price: str
    ah_change: str
    history: list[float]


@dataclass
class MarketData:
    indexes: list[IndexQuote]
    stocks: list[StockQuote]


SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

FMP_API_KEY_ENV_NAME = "FMP_API_KEY"
FMP_BASE_URL = "https://financialmodelingprep.com/stable"

FINNHUB_API_KEY_ENV_NAME = "FINNHUB_API_KEY"
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"

TWELVE_DATA_API_KEY_ENV_NAME = "TWELVE_DATA_API_KEY"
TWELVE_DATA_BASE_URL = "https://api.twelvedata.com"

# Twelve Data true index symbols. If one symbol changes or is not covered
# by your Twelve Data plan, the code tries the next candidate.
TWELVE_DATA_INDEX_SYMBOL_CANDIDATES = {
    "^GSPC": ["SPX", "GSPC", "INX"],
    "^DJI": ["DJI", "DJIA"],
    "^IXIC": ["IXIC", "COMP"],
}

STOOQ_QUOTE_BASE_URL = "https://stooq.com/q/l/"
STOOQ_HISTORY_BASE_URL = "https://stooq.com/q/d/l/"

# True index symbols from Stooq. These are index levels, not ETF proxies.
STOOQ_INDEX_SYMBOLS = {
    "^GSPC": "^spx",
    "^DJI": "^dji",
    "^IXIC": "^ixic",
}

YAHOO_CHART_BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

# True Yahoo index symbols. These are index levels, not ETF proxies.
YAHOO_INDEX_SYMBOLS = {
    "^GSPC": "^GSPC",
    "^DJI": "^DJI",
    "^IXIC": "^IXIC",
}


INDEX_SYMBOLS = [
    ("S&P", "^GSPC"),
    ("DOW", "^DJI"),
    ("NAS", "^IXIC"),
]

INDEX_PROXY_SYMBOLS = {
    "^GSPC": "SPY",
    "^DJI": "DIA",
    "^IXIC": "QQQ",
}

STOCK_SYMBOLS = [
    "VRT",
    "SPCX",
    "FITB",
    "AMZN",
]

NASDAQ_ASSETCLASS_PRIORITY = {
    "SPCX": ["etf", "stocks"],
}


def get_fmp_api_key():
    api_key = os.getenv(FMP_API_KEY_ENV_NAME, "").strip()

    if not api_key or api_key in {"paste_your_key_here", "YOUR_REAL_FMP_KEY_HERE"}:
        raise RuntimeError(
            f"Missing real {FMP_API_KEY_ENV_NAME}. Run: export {FMP_API_KEY_ENV_NAME}='your_real_fmp_key'"
        )

    return api_key


def fetch_text(url, timeout=20, headers=None):
    request_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    if headers:
        request_headers.update(headers)

    request = urllib.request.Request(
        url,
        headers=request_headers,
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
            context=SSL_CONTEXT,
        ) as response:
            return response.read().decode("utf-8", errors="ignore")

    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {error.code}: {body[:500]}") from error


def fetch_json(url, timeout=20, headers=None):
    text = fetch_text(url, timeout=timeout, headers=headers)
    return json.loads(text)


def fmp_url(path, params):
    params = dict(params)
    params["apikey"] = get_fmp_api_key()

    return f"{FMP_BASE_URL}/{path}?{urllib.parse.urlencode(params)}"


def get_finnhub_api_key():
    api_key = os.getenv(FINNHUB_API_KEY_ENV_NAME, "").strip()

    if not api_key or api_key in {"paste_your_finnhub_key_here", "YOUR_REAL_FINNHUB_KEY_HERE"}:
        raise RuntimeError(
            f"Missing real {FINNHUB_API_KEY_ENV_NAME}. Run: export {FINNHUB_API_KEY_ENV_NAME}='your_real_finnhub_key'"
        )

    return api_key


def has_finnhub_api_key():
    try:
        get_finnhub_api_key()
        return True
    except Exception:
        return False


def finnhub_url(path, params):
    params = dict(params)
    params["token"] = get_finnhub_api_key()

    return f"{FINNHUB_BASE_URL}/{path}?{urllib.parse.urlencode(params)}"


def fetch_finnhub_quote(symbol):
    url = finnhub_url(
        "quote",
        {
            "symbol": symbol,
        },
    )

    payload = fetch_json(url)
    price = parse_float(payload.get("c"))

    if price is None or price <= 0:
        raise RuntimeError(f"No Finnhub quote returned for {symbol}: {payload}")

    return payload


def get_price_from_finnhub_quote(item):
    return item.get("c")


def get_change_from_finnhub_quote(item):
    change = parse_float(item.get("d"))

    if change is not None:
        return change

    current = parse_float(item.get("c"))
    previous_close = parse_float(item.get("pc"))

    if current is not None and previous_close is not None:
        return current - previous_close

    return None


def fetch_finnhub_history(symbol):
    now = datetime.now()
    start = now - timedelta(days=130)

    url = finnhub_url(
        "stock/candle",
        {
            "symbol": symbol,
            "resolution": "D",
            "from": int(start.timestamp()),
            "to": int(now.timestamp()),
        },
    )

    payload = fetch_json(url)
    status = str(payload.get("s", "")).lower()

    if status != "ok":
        raise RuntimeError(f"No Finnhub candle history returned for {symbol}: {payload}")

    close_values = payload.get("c", []) or []
    values = []

    for value in close_values:
        parsed = parse_float(value)

        if parsed is not None:
            values.append(parsed)

    if len(values) < 2:
        raise RuntimeError(
            f"Not enough Finnhub history returned for {symbol}. "
            f"Only found {len(values)} close value(s)."
        )

    return values[-65:]


def parse_float(value):
    if value is None:
        return None

    try:
        cleaned = str(value)
        cleaned = cleaned.replace("$", "")
        cleaned = cleaned.replace(",", "")
        cleaned = cleaned.replace("%", "")
        cleaned = cleaned.replace("+", "")
        cleaned = cleaned.strip()

        if not cleaned or cleaned in {"—", "-", "N/A", "N/D"}:
            return None

        return float(cleaned)

    except Exception:
        return None


def format_price(value, decimals=2):
    value = parse_float(value)

    if value is None:
        return "—"

    return f"${value:,.{decimals}f}"


def format_index_price(value):
    value = parse_float(value)

    if value is None:
        return "—"

    return f"${value:,.2f}"


def format_change(value):
    value = parse_float(value)

    if value is None:
        return "—"

    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}"


def today_range(days_back=130):
    today = datetime.now()
    start = today - timedelta(days=days_back)

    return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")


def get_first_payload(payload):
    if isinstance(payload, list) and payload:
        return payload[0]

    if isinstance(payload, dict):
        return payload

    return {}


def get_price_from_fmp_quote(item):
    return (
        item.get("price")
        or item.get("previousClose")
        or item.get("open")
        or item.get("dayHigh")
        or item.get("dayLow")
    )


def get_change_from_fmp_quote(item):
    return (
        item.get("change")
        or item.get("changes")
    )


def fetch_fmp_quote(symbol):
    url = fmp_url(
        "quote",
        {
            "symbol": symbol,
        },
    )

    payload = fetch_json(url)
    item = get_first_payload(payload)

    if not item:
        raise RuntimeError(f"No FMP quote returned for {symbol}: {payload}")

    return item


def fetch_fmp_history(symbol):
    start_date, end_date = today_range(days_back=130)

    endpoints_to_try = [
        "historical-price-eod/light",
        "historical-price-eod/full",
    ]

    last_error = None

    for endpoint in endpoints_to_try:
        try:
            url = fmp_url(
                endpoint,
                {
                    "symbol": symbol,
                    "from": start_date,
                    "to": end_date,
                },
            )

            payload = fetch_json(url)

            rows = []

            if isinstance(payload, dict):
                if isinstance(payload.get("historical"), list):
                    rows = payload["historical"]
                elif isinstance(payload.get("data"), list):
                    rows = payload["data"]
            elif isinstance(payload, list):
                rows = payload

            if not rows:
                raise RuntimeError(f"No FMP historical rows returned for {symbol}: {payload}")

            rows = sorted(rows, key=lambda row: row.get("date", ""))

            values = []

            for row in rows:
                close = parse_float(
                    row.get("close")
                    or row.get("adjClose")
                    or row.get("price")
                )

                if close is not None:
                    values.append(close)

            if values:
                return values[-65:]

        except Exception as error:
            last_error = error
            print(f"FMP history failed for {symbol} using {endpoint}: {error}")

    raise RuntimeError(f"All FMP history endpoints failed for {symbol}: {last_error}")


def nasdaq_headers(include_origin=False):
    headers = {
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://www.nasdaq.com/",
    }

    # Do not send Origin for charting.nasdaq.com history.
    # Nasdaq was rejecting it with:
    # Cross-Origin Resource Sharing forbidden: Origin 'https://www.nasdaq.com' is not allowed
    if include_origin:
        headers["Origin"] = "https://www.nasdaq.com"

    return headers


def get_nasdaq_assetclasses(symbol):
    return NASDAQ_ASSETCLASS_PRIORITY.get(symbol.upper(), ["stocks", "etf"])


def fetch_nasdaq_quote_with_assetclass(symbol, assetclass):
    encoded_symbol = urllib.parse.quote(symbol.lower(), safe="")
    url = (
        f"https://api.nasdaq.com/api/quote/{encoded_symbol}/info"
        f"?assetclass={urllib.parse.quote(assetclass)}"
    )

    payload = fetch_json(
        url,
        timeout=20,
        headers=nasdaq_headers(include_origin=False),
    )

    data = payload.get("data", {})
    primary = data.get("primaryData", {}) or {}

    price = (
        primary.get("lastSalePrice")
        or primary.get("lastSale")
        or primary.get("price")
    )

    change = (
        primary.get("netChange")
        or primary.get("change")
        or primary.get("deltaIndicator")
    )

    if not price:
        raise RuntimeError(f"No Nasdaq price returned for {symbol}/{assetclass}: {payload}")

    return price, change


def fetch_nasdaq_quote(symbol):
    last_error = None

    for assetclass in get_nasdaq_assetclasses(symbol):
        try:
            price, change = fetch_nasdaq_quote_with_assetclass(symbol, assetclass)
            print(f"Loaded Nasdaq quote {symbol}/{assetclass}: {price} DAY {change}")
            return price, change

        except Exception as error:
            last_error = error
            print(f"Nasdaq quote failed for {symbol}/{assetclass}: {error}")

    raise RuntimeError(f"All Nasdaq quote attempts failed for {symbol}: {last_error}")


def collect_numeric_close_values(obj):
    values = []

    if isinstance(obj, list):
        for item in obj:
            values.extend(collect_numeric_close_values(item))

    elif isinstance(obj, dict):
        # Nasdaq historical payloads usually come back as:
        # {"marketData": [{"Date": "...", "Close": 302.87, ...}]}
        if isinstance(obj.get("marketData"), list):
            rows = obj.get("marketData", [])

            rows = sorted(
                rows,
                key=lambda row: str(row.get("Date", "")),
            )

            for row in rows:
                close = parse_float(
                    row.get("Close")
                    or row.get("close")
                    or row.get("Last")
                    or row.get("last")
                )

                if close is not None:
                    values.append(close)

            return values

        close_candidates = [
            obj.get("Close"),
            obj.get("close"),
            obj.get("Last"),
            obj.get("last"),
            obj.get("c"),
            obj.get("value"),
            obj.get("y"),
        ]

        for candidate in close_candidates:
            parsed = parse_float(candidate)
            if parsed is not None:
                values.append(parsed)
                break

        for value in obj.values():
            if isinstance(value, (list, dict)):
                values.extend(collect_numeric_close_values(value))

    return values


def fetch_nasdaq_history(symbol):
    start_date, end_date = today_range(days_back=130)

    encoded_symbol = urllib.parse.quote(symbol.upper(), safe="")
    encoded_date = urllib.parse.quote(f"{start_date}~{end_date}", safe="~")

    url = (
        "https://charting.nasdaq.com/data/charting/historical"
        f"?symbol={encoded_symbol}&date={encoded_date}&"
    )

    payload = fetch_json(
        url,
        timeout=20,
        headers={
            **nasdaq_headers(include_origin=False),
            "Referer": "https://charting.nasdaq.com/dynamic/chart.html",
        },
    )

    values = collect_numeric_close_values(payload)

    clean_values = []

    for value in values:
        if value is None:
            continue

        if not clean_values or clean_values[-1] != value:
            clean_values.append(value)

    if len(clean_values) < 2:
        raise RuntimeError(
            f"Not enough Nasdaq history returned for {symbol}. "
            f"Only found {len(clean_values)} close value(s)."
        )

    return clean_values[-65:]


def placeholder_history_from_price(price):
    value = parse_float(price)

    if value is None:
        return [1, 1, 1]

    return [value for _ in range(65)]



def get_twelve_data_api_key():
    api_key = os.getenv(TWELVE_DATA_API_KEY_ENV_NAME, "").strip()

    if not api_key:
        raise RuntimeError(
            f"Missing {TWELVE_DATA_API_KEY_ENV_NAME}. "
            "Set it before launching the app."
        )

    return api_key


def has_twelve_data_api_key():
    return bool(os.getenv(TWELVE_DATA_API_KEY_ENV_NAME, "").strip())


def twelve_data_url(path, params):
    api_key = get_twelve_data_api_key()
    full_params = dict(params)
    full_params["apikey"] = api_key

    return (
        f"{TWELVE_DATA_BASE_URL}{path}?"
        + urllib.parse.urlencode(full_params)
    )


def fetch_twelve_data_json(path, params, timeout=12):
    url = twelve_data_url(path, params)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "MorningTVUI/1.0",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8", errors="ignore")
    except Exception as first_error:
        if "CERTIFICATE_VERIFY_FAILED" not in str(first_error):
            raise

        print(f"Twelve Data SSL verification failed for {url}; retrying with relaxed SSL context.")
        relaxed_context = ssl._create_unverified_context()

        with urllib.request.urlopen(
            request,
            timeout=timeout,
            context=relaxed_context,
        ) as response:
            payload = response.read().decode("utf-8", errors="ignore")

    data = json.loads(payload)

    if isinstance(data, dict) and data.get("status") == "error":
        message = data.get("message") or data.get("code") or "Unknown Twelve Data error"
        raise RuntimeError(str(message))

    return data


def fetch_twelve_data_quote(symbol):
    return fetch_twelve_data_json(
        "/quote",
        {
            "symbol": symbol,
        },
    )


def get_price_from_twelve_data_quote(item):
    for key in ["close", "price", "previous_close"]:
        value = item.get(key)

        if value in [None, ""]:
            continue

        try:
            return float(value)
        except Exception:
            continue

    raise RuntimeError(f"Twelve Data quote did not include a usable price: {item}")


def fetch_twelve_data_history(symbol, fallback_price=None):
    try:
        data = fetch_twelve_data_json(
            "/time_series",
            {
                "symbol": symbol,
                "interval": "1day",
                "outputsize": 65,
            },
            timeout=14,
        )

        values = data.get("values", []) if isinstance(data, dict) else []
        history = []

        # Twelve Data usually returns newest first. Reverse so the chart trends left-to-right.
        for row in reversed(values):
            close_value = row.get("close")

            if close_value in [None, ""]:
                continue

            try:
                history.append(float(close_value))
            except Exception:
                continue

        if history:
            return history

    except Exception as error:
        print(f"Twelve Data history failed for {symbol}: {error}")

    if fallback_price is not None:
        return [float(fallback_price)] * 65

    return []


def fetch_twelve_data_index_quote(display_name, original_symbol):
    if not has_twelve_data_api_key():
        return None

    candidates = TWELVE_DATA_INDEX_SYMBOL_CANDIDATES.get(original_symbol, [original_symbol])

    for twelve_symbol in candidates:
        try:
            print(f"Fetching true index quote from Twelve Data: {display_name} -> {twelve_symbol}")
            quote = fetch_twelve_data_quote(twelve_symbol)
            price = get_price_from_twelve_data_quote(quote)

            # Guard against symbol collisions. For example, DJIA or COMP can
            # resolve to low-priced securities instead of the real index.
            if original_symbol in ["^GSPC", "^DJI", "^IXIC"] and price < 1000:
                raise RuntimeError(
                    f"Twelve Data symbol {twelve_symbol} returned {price}, "
                    "which is too low to be the actual index level."
                )

            history = fetch_twelve_data_history(twelve_symbol, price)

            return IndexQuote(
                name=display_name,
                price=format_index_price(price),
                history=history,
            )

        except Exception as error:
            print(f"Twelve Data index quote failed for {display_name} / {twelve_symbol}: {error}")

    return None



def stooq_url(base_url, params):
    return base_url + "?" + urllib.parse.urlencode(params)


def fetch_stooq_text(base_url, params, timeout=14):
    url = stooq_url(base_url, params)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "MorningTVUI/1.0",
            "Accept": "text/csv,text/plain,*/*",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="ignore")
    except Exception as first_error:
        if "CERTIFICATE_VERIFY_FAILED" not in str(first_error):
            raise

        print(f"Stooq SSL verification failed for {url}; retrying with relaxed SSL context.")
        relaxed_context = ssl._create_unverified_context()

        with urllib.request.urlopen(
            request,
            timeout=timeout,
            context=relaxed_context,
        ) as response:
            return response.read().decode("utf-8", errors="ignore")


def fetch_stooq_index_history(stooq_symbol):
    csv_text = fetch_stooq_text(
        STOOQ_HISTORY_BASE_URL,
        {
            "s": stooq_symbol,
            "i": "d",
        },
        timeout=16,
    )

    rows = list(csv.DictReader(io.StringIO(csv_text)))
    closes = []

    for row in rows[-65:]:
        close_value = row.get("Close") or row.get("close")

        if not close_value or close_value.upper() == "N/D":
            continue

        try:
            closes.append(float(close_value))
        except Exception:
            continue

    return closes


def fetch_stooq_index_quote(display_name, original_symbol):
    stooq_symbol = STOOQ_INDEX_SYMBOLS.get(original_symbol)

    if not stooq_symbol:
        raise RuntimeError(f"No Stooq symbol configured for {display_name}/{original_symbol}")

    print(f"Fetching true index quote from Stooq: {display_name} -> {stooq_symbol}")

    csv_text = fetch_stooq_text(
        STOOQ_QUOTE_BASE_URL,
        {
            "s": stooq_symbol,
            "f": "sd2t2ohlcv",
            "h": "",
            "e": "csv",
        },
        timeout=14,
    )

    rows = list(csv.DictReader(io.StringIO(csv_text)))

    if not rows:
        raise RuntimeError(f"No Stooq quote rows returned for {display_name}/{stooq_symbol}")

    row = rows[0]
    close_value = row.get("Close") or row.get("close")

    if not close_value or close_value.upper() == "N/D":
        raise RuntimeError(f"No usable Stooq close value returned for {display_name}/{stooq_symbol}: {row}")

    price = float(close_value)

    if price < 1000:
        raise RuntimeError(
            f"Stooq symbol {stooq_symbol} returned {price}, "
            "which is too low to be the actual major index level."
        )

    history = fetch_stooq_index_history(stooq_symbol)

    if not history:
        history = [price] * 65

    return IndexQuote(
        name=display_name,
        price=format_index_price(price),
        history=history,
    )



def yahoo_chart_url(symbol, params):
    encoded_symbol = urllib.parse.quote(symbol, safe="")
    return (
        f"{YAHOO_CHART_BASE_URL}/{encoded_symbol}?"
        + urllib.parse.urlencode(params)
    )


def fetch_yahoo_json(symbol, params, timeout=14):
    url = yahoo_chart_url(symbol, params)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json,text/plain,*/*",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8", errors="ignore")
    except Exception as first_error:
        if "CERTIFICATE_VERIFY_FAILED" not in str(first_error):
            raise

        print(f"Yahoo SSL verification failed for {url}; retrying with relaxed SSL context.")
        relaxed_context = ssl._create_unverified_context()

        with urllib.request.urlopen(
            request,
            timeout=timeout,
            context=relaxed_context,
        ) as response:
            payload = response.read().decode("utf-8", errors="ignore")

    return json.loads(payload)


def fetch_yahoo_index_quote(display_name, original_symbol):
    yahoo_symbol = YAHOO_INDEX_SYMBOLS.get(original_symbol)

    if not yahoo_symbol:
        raise RuntimeError(f"No Yahoo symbol configured for {display_name}/{original_symbol}")

    print(f"Fetching true index quote from Yahoo chart API: {display_name} -> {yahoo_symbol}")

    data = fetch_yahoo_json(
        yahoo_symbol,
        {
            "range": "3mo",
            "interval": "1d",
            "includePrePost": "false",
        },
    )

    chart = data.get("chart", {})
    error = chart.get("error")

    if error:
        raise RuntimeError(f"Yahoo chart error for {display_name}: {error}")

    results = chart.get("result") or []

    if not results:
        raise RuntimeError(f"No Yahoo chart result returned for {display_name}/{yahoo_symbol}")

    result = results[0]
    meta = result.get("meta", {})
    current_price = meta.get("regularMarketPrice")

    indicators = result.get("indicators", {})
    quote_rows = indicators.get("quote") or []
    quote = quote_rows[0] if quote_rows else {}
    closes = quote.get("close") or []

    history = []

    for value in closes[-65:]:
        if value is None:
            continue

        try:
            history.append(float(value))
        except Exception:
            continue

    if current_price is None:
        if history:
            current_price = history[-1]
        else:
            raise RuntimeError(f"No usable Yahoo index price returned for {display_name}")

    price = float(current_price)

    if price < 1000:
        raise RuntimeError(
            f"Yahoo symbol {yahoo_symbol} returned {price}, "
            "which is too low to be the actual major index level."
        )

    if not history:
        history = [price] * 65

    return IndexQuote(
        name=display_name,
        price=format_index_price(price),
        history=history,
    )


def fetch_index_quote(display_name, symbol):
    # Use Yahoo's true index symbols for the three major indexes.
    # No ETF proxy fallback.
    try:
        return fetch_yahoo_index_quote(display_name, symbol)
    except Exception as error:
        print(f"Yahoo true index quote failed for {display_name}/{symbol}: {error}")

    return IndexQuote(
        name=display_name,
        price="—",
        history=[1, 1, 1],
    )



def fetch_stock_quote(symbol):
    try:
        item = fetch_finnhub_quote(symbol)

        price = get_price_from_finnhub_quote(item)
        change = get_change_from_finnhub_quote(item)

        stock = StockQuote(
            ticker=symbol,
            price=format_price(price),
            ah_change=format_change(change),
            history=placeholder_history_from_price(price),
        )

        print(f"Loaded Finnhub stock quote {symbol}: {stock.price} DAY {stock.ah_change}")
        return stock

    except Exception as error:
        print(f"Finnhub stock quote failed for {symbol}, trying FMP: {error}")

    try:
        item = fetch_fmp_quote(symbol)

        price = get_price_from_fmp_quote(item)
        change = get_change_from_fmp_quote(item)

        stock = StockQuote(
            ticker=symbol,
            price=format_price(price),
            ah_change=format_change(change),
            history=placeholder_history_from_price(price),
        )

        print(f"Loaded FMP stock quote {symbol}: {stock.price} DAY {stock.ah_change}")
        return stock

    except Exception as error:
        print(f"FMP stock quote failed for {symbol}, trying Nasdaq fallback: {error}")

    price, change = fetch_nasdaq_quote(symbol)

    stock = StockQuote(
        ticker=symbol,
        price=format_price(price),
        ah_change=format_change(change),
        history=placeholder_history_from_price(price),
    )

    print(f"Loaded Nasdaq stock quote {symbol}: {stock.price} DAY {stock.ah_change}")
    return stock


def fetch_stock_history(symbol, current_price):
    try:
        history = fetch_finnhub_history(symbol)
        print(f"Loaded Finnhub history {symbol}: {len(history)} points")
        return history

    except Exception as error:
        print(f"Finnhub history unavailable for {symbol}, trying FMP: {error}")

    try:
        history = fetch_fmp_history(symbol)
        print(f"Loaded FMP history {symbol}: {len(history)} points")
        return history

    except Exception as error:
        print(f"FMP history unavailable for {symbol}, trying Nasdaq fallback: {error}")

    try:
        history = fetch_nasdaq_history(symbol)
        print(f"Loaded Nasdaq history {symbol}: {len(history)} points")
        return history

    except Exception as error:
        print(f"Nasdaq history unavailable for {symbol}: {error}")

    return placeholder_history_from_price(current_price)


def fallback_market_data():
    return MarketData(
        indexes=[
            IndexQuote("S&P", "—", [1, 1, 1]),
            IndexQuote("DOW", "—", [1, 1, 1]),
            IndexQuote("NAS", "—", [1, 1, 1]),
        ],
        stocks=[
            StockQuote("VRT", "—", "—", [1, 1, 1]),
            StockQuote("SPCX", "—", "—", [1, 1, 1]),
            StockQuote("FITB", "—", "—", [1, 1, 1]),
            StockQuote("AMZN", "—", "—", [1, 1, 1]),
        ],
    )


def fetch_market_data():
    print("Fetching stock data from Finnhub with FMP/Nasdaq fallback...")

    if not has_finnhub_api_key():
        print(f"Finnhub setup warning: missing {FINNHUB_API_KEY_ENV_NAME}. FMP/Nasdaq fallbacks will be used.")

    try:
        get_fmp_api_key()
    except Exception as error:
        print(f"FMP setup warning: {error}")

    indexes = []

    for display_name, symbol in INDEX_SYMBOLS:
        try:
            quote = fetch_index_quote(display_name, symbol)
            print(f"Loaded index {display_name}/{symbol}: {quote.price}")
            indexes.append(quote)

        except Exception as error:
            print(f"Index fetch failed for {display_name}/{symbol}: {error}")
            indexes.append(IndexQuote(display_name, "—", [1, 1, 1]))

    stocks = []

    for symbol in STOCK_SYMBOLS:
        try:
            stock = fetch_stock_quote(symbol)
            print(f"Loaded stock quote {symbol}: {stock.price} DAY {stock.ah_change}")
            stocks.append(stock)

        except Exception as error:
            print(f"Stock quote failed for {symbol}: {error}")
            stocks.append(StockQuote(symbol, "—", "—", [1, 1, 1]))

    for index, stock in enumerate(stocks):
        if stock.price == "—":
            continue

        history = fetch_stock_history(stock.ticker, stock.price)
        stocks[index].history = history

    return MarketData(indexes=indexes, stocks=stocks)


def fallback_market_data_for_symbols(index_symbols=None, stock_symbols=None):
    index_symbols = index_symbols or INDEX_SYMBOLS
    stock_symbols = stock_symbols or STOCK_SYMBOLS

    return MarketData(
        indexes=[
            IndexQuote(display_name, "—", [1, 1, 1])
            for display_name, symbol in index_symbols
        ],
        stocks=[
            StockQuote(symbol, "—", "—", [1, 1, 1])
            for symbol in stock_symbols
        ],
    )


def fetch_market_data_for_symbols(index_symbols=None, stock_symbols=None):
    print("Fetching configurable stock data from Finnhub with FMP/Nasdaq fallback...")

    index_symbols = index_symbols or INDEX_SYMBOLS
    stock_symbols = stock_symbols or STOCK_SYMBOLS

    if not has_finnhub_api_key():
        print(f"Finnhub setup warning: missing {FINNHUB_API_KEY_ENV_NAME}. FMP/Nasdaq fallbacks will be used.")

    try:
        get_fmp_api_key()
    except Exception as error:
        print(f"FMP setup warning: {error}")

    indexes = []

    for display_name, symbol in index_symbols:
        try:
            quote = fetch_index_quote(display_name, symbol)
            print(f"Loaded index {display_name}/{symbol}: {quote.price}")
            indexes.append(quote)
        except Exception as error:
            print(f"Index fetch failed for {display_name}/{symbol}: {error}")
            indexes.append(IndexQuote(display_name, "—", [1, 1, 1]))

    stocks = []

    for symbol in stock_symbols:
        try:
            stock = fetch_stock_quote(symbol)
            stock.history = fetch_stock_history(symbol, stock.price)
            print(f"Loaded stock quote {symbol}: {stock.price} DAY {stock.ah_change}")
            stocks.append(stock)
        except Exception as error:
            print(f"Stock fetch failed for {symbol}: {error}")
            stocks.append(StockQuote(symbol, "—", "—", [1, 1, 1]))

    return MarketData(indexes=indexes, stocks=stocks)
