import json
import math
import ssl
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import certifi


@dataclass
class WeatherRow:
    temperature: str
    icon: str
    time_label: str
    condition: str
    is_night: bool
    forecast_start: str = ""
    detailed_forecast: str = ""
    wind_speed: str = ""
    precipitation_probability: int | None = None
    precipitation_amount_inches: float | None = None
    solar_event_time: str = ""
    solar_event_label: str = ""
    source: str = "NWS"


ZIP_CODE = "44865"
LOCATION_LABEL = "44865"
LATITUDE = 40.99165
LONGITUDE = -82.68168
TIMEZONE = "America/New_York"

NWS_BASE_URL = "https://api.weather.gov"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def fetch_json(url, timeout=14, nws=False):
    headers = {
        "User-Agent": "MorningTVUI/1.0 local-dashboard",
        "Accept": "application/geo+json, application/json, */*",
    }

    if not nws:
        headers["Accept"] = "application/json, */*"

    request = urllib.request.Request(
        url,
        headers=headers,
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout,
        context=SSL_CONTEXT,
    ) as response:
        data = response.read().decode("utf-8", errors="ignore")
        return json.loads(data)


def fahrenheit_from_celsius(value):
    if value is None:
        return None

    try:
        return round((float(value) * 9 / 5) + 32)
    except Exception:
        return None


def safe_round_temperature(value):
    if value is None:
        return None

    try:
        return str(round(float(value)))
    except Exception:
        return None


def format_hour_label(iso_time):
    if not iso_time:
        return ""

    try:
        value = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        return value.strftime("%-I%p").lower()
    except Exception:
        return ""


def format_clock_time(iso_time, timezone_name=TIMEZONE):
    if not iso_time:
        return ""

    try:
        value = datetime.fromisoformat(str(iso_time).replace("Z", "+00:00"))

        if value.tzinfo is None:
            value = value.replace(tzinfo=ZoneInfo(timezone_name))
        else:
            value = value.astimezone(ZoneInfo(timezone_name))

        return value.strftime("%-I:%M%p").lower()
    except Exception:
        return ""


def local_hour_key(iso_time, timezone_name=TIMEZONE):
    if not iso_time:
        return None

    try:
        value = datetime.fromisoformat(str(iso_time).replace("Z", "+00:00"))

        if value.tzinfo is None:
            value = value.replace(tzinfo=ZoneInfo(timezone_name))
        else:
            value = value.astimezone(ZoneInfo(timezone_name))

        return value.replace(minute=0, second=0, microsecond=0)
    except Exception:
        return None


def fetch_open_meteo_hourly_display_details(location):
    """Return supplemental hourly rain totals and sunrise/sunset display times.

    NWS remains the primary forecast source. This request only fills display
    details that NWS hourly periods do not consistently provide.
    """
    params = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "hourly": "precipitation",
        "daily": "sunrise,sunset",
        "precipitation_unit": "mm",
        "timezone": location.timezone,
        "forecast_days": 3,
    }

    url = OPEN_METEO_URL + "?" + urllib.parse.urlencode(params)
    data = fetch_json(url)

    hourly = data.get("hourly", {}) or {}
    hourly_times = hourly.get("time", []) or []
    hourly_precipitation = hourly.get("precipitation", []) or []

    precipitation_by_hour = {}

    for index, time_value in enumerate(hourly_times):
        hour_key = local_hour_key(time_value, location.timezone)

        if hour_key is None or index >= len(hourly_precipitation):
            continue

        try:
            millimeters = float(hourly_precipitation[index])
        except Exception:
            continue

        if millimeters > 0:
            precipitation_by_hour[hour_key] = millimeters / 25.4

    daily = data.get("daily", {}) or {}
    solar_event_by_hour = {}

    for event_name in ("sunrise", "sunset"):
        for event_time in daily.get(event_name, []) or []:
            hour_key = local_hour_key(event_time, location.timezone)
            display_time = format_clock_time(event_time, location.timezone)

            if hour_key is not None and display_time:
                solar_event_by_hour[hour_key] = (
                    display_time,
                    event_name,
                )

    return precipitation_by_hour, solar_event_by_hour


def apply_open_meteo_hourly_display_details(rows, location):
    try:
        precipitation_by_hour, solar_event_by_hour = (
            fetch_open_meteo_hourly_display_details(location)
        )
    except Exception as error:
        print(f"Open-Meteo hourly display details unavailable: {error}")
        return rows

    for row in rows:
        hour_key = local_hour_key(
            getattr(row, "forecast_start", ""),
            location.timezone,
        )

        if hour_key is None:
            continue

        condition = str(getattr(row, "condition", "") or "").lower()

        if condition in {"rain", "storm"}:
            row.precipitation_amount_inches = precipitation_by_hour.get(hour_key)

        solar_event = solar_event_by_hour.get(hour_key)

        if solar_event:
            row.solar_event_time = solar_event[0]
            row.solar_event_label = solar_event[1]
        else:
            row.solar_event_time = ""
            row.solar_event_label = ""

    return rows

def is_day_from_nws_period(period):
    nws_is_day = period.get("isDay", None)

    if isinstance(nws_is_day, bool):
        return nws_is_day

    start_time = period.get("startTime", "")

    try:
        value = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        hour = value.hour

        # Conservative fallback only when NWS isDay is missing/bad.
        # Avoid trying to model sunset exactly.
        if 0 <= hour < 6:
            return False
        if 10 <= hour < 17:
            return True

    except Exception:
        pass

    return True

def is_daytime_from_start_time(iso_time, fallback=True):
    if not iso_time:
        return bool(fallback)

    try:
        value = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))

        if value.tzinfo is None:
            value = value.replace(tzinfo=ZoneInfo(TIMEZONE))
        else:
            value = value.astimezone(ZoneInfo(TIMEZONE))

        hour = value.hour

        # General local daytime window for this dashboard.
        # This avoids trusting bad/missing NWS isDay values for overnight rows.
        return 6 <= hour < 21

    except Exception:
        return bool(fallback)

def condition_from_text(text, is_day=True):
    lowered = (text or "").lower()

    if any(word in lowered for word in ["thunderstorm", "t-storm", "tstorm", "lightning"]):
        return "storm", "⚡"

    if any(word in lowered for word in ["rain", "shower", "drizzle", "sprinkle"]):
        return "rain", "🌧️"

    if any(word in lowered for word in ["snow", "sleet", "flurries", "ice", "freezing rain"]):
        return "snow", "🌨️"

    if any(word in lowered for word in ["fog", "mist", "haze", "smoke"]):
        return "fog", "☁️"

    if any(word in lowered for word in ["cloud", "overcast", "partly", "mostly cloudy"]):
        return "cloud", "☁️"

    if any(word in lowered for word in ["clear", "sunny", "fair"]):
        if is_day:
            return "clear", "☀️"
        return "clear", "🌙"

    if is_day:
        return "clear", "🌤️"

    return "clear", "🌙"


def condition_from_open_meteo_code(weather_code, precipitation_probability, is_day):
    try:
        code = int(weather_code)
    except Exception:
        code = 0

    try:
        precip = int(precipitation_probability or 0)
    except Exception:
        precip = 0

    if code in [95, 96, 99]:
        return "storm", "⚡"

    if code in [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82] or precip >= 45:
        return "rain", "🌧️"

    if code in [71, 73, 75, 77, 85, 86]:
        return "snow", "🌨️"

    if code in [45, 48]:
        return "fog", "☁️"

    if code in [2, 3]:
        return "cloud", "☁️"

    if not is_day:
        return "clear", "🌙"

    if code == 1:
        return "clear", "🌤️"

    return "clear", "☀️"


def get_nws_point_metadata(location):
    point_url = f"{NWS_BASE_URL}/points/{location.latitude},{location.longitude}"
    point_data = fetch_json(point_url, nws=True)
    properties = point_data.get("properties", {})

    return {
        "forecast_hourly_url": properties.get("forecastHourly", ""),
        "observation_stations_url": properties.get("observationStations", ""),
        "forecast_office": properties.get("cwa", ""),
        "grid_id": properties.get("gridId", ""),
        "grid_x": properties.get("gridX", ""),
        "grid_y": properties.get("gridY", ""),
    }


def fetch_nws_active_alerts(location):
    query = urllib.parse.urlencode(
        {
            "point": f"{location.latitude},{location.longitude}",
        }
    )

    alerts_url = f"{NWS_BASE_URL}/alerts/active?{query}"
    data = fetch_json(alerts_url, nws=True)

    alerts = []

    for feature in data.get("features", []):
        props = feature.get("properties", {})

        event = props.get("event", "") or ""
        headline = props.get("headline", "") or ""
        severity = props.get("severity", "") or ""
        urgency = props.get("urgency", "") or ""

        combined = f"{event} {headline}".strip()

        if combined:
            alerts.append(
                {
                    "event": event,
                    "headline": headline,
                    "severity": severity,
                    "urgency": urgency,
                    "combined": combined,
                }
            )

    return alerts


def alert_override_condition(alerts):
    if not alerts:
        return None

    combined = " | ".join(alert.get("combined", "") for alert in alerts).lower()

    storm_words = [
        "severe thunderstorm",
        "thunderstorm warning",
        "thunderstorm watch",
        "tornado",
        "special weather statement",
    ]

    heavy_rain_words = [
        "flash flood",
        "flood warning",
        "flood watch",
        "heavy rain",
    ]

    winter_words = [
        "winter storm",
        "snow squall",
        "snow",
        "ice storm",
    ]

    if any(word in combined for word in storm_words):
        return "storm", "⛈️"

    if any(word in combined for word in heavy_rain_words):
        return "rain", "🌧️"

    if any(word in combined for word in winter_words):
        return "snow", "🌨️"

    return None


def fetch_latest_nws_observation(observation_stations_url):
    if not observation_stations_url:
        return None

    stations_data = fetch_json(observation_stations_url, nws=True)
    station_features = stations_data.get("features", [])

    for station in station_features[:5]:
        props = station.get("properties", {})
        station_id = props.get("stationIdentifier", "")

        if not station_id:
            continue

        latest_url = f"{NWS_BASE_URL}/stations/{station_id}/observations/latest"

        try:
            latest = fetch_json(latest_url, nws=True)
            latest_props = latest.get("properties", {})

            temp_c = latest_props.get("temperature", {}).get("value")
            text_description = latest_props.get("textDescription", "") or ""
            timestamp = latest_props.get("timestamp", "") or ""

            temp_f = fahrenheit_from_celsius(temp_c)

            if temp_f is None and not text_description:
                continue

            return {
                "station_id": station_id,
                "temperature": temp_f,
                "text_description": text_description,
                "timestamp": timestamp,
            }

        except Exception as error:
            print(f"NWS observation failed for station {station_id}: {error}")

    return None


def fetch_nws_hourly_periods(forecast_hourly_url):
    if not forecast_hourly_url:
        return []

    data = fetch_json(forecast_hourly_url, nws=True)
    return data.get("properties", {}).get("periods", [])


def build_rows_from_nws_periods(periods, max_rows, alerts=None, observation=None):
    rows = []

    override = alert_override_condition(alerts or [])

    for index, period in enumerate(periods[:max_rows]):
        temperature = safe_round_temperature(period.get("temperature"))
        nws_is_day = is_day_from_nws_period(period)
        short_forecast = period.get("shortForecast", "") or ""
        start_time = period.get("startTime", "")

        is_day = is_daytime_from_start_time(start_time, fallback=nws_is_day)

        condition, icon = condition_from_text(short_forecast, is_day=is_day)

        # Use latest official station observation for the current row when available.
        if index == 0 and observation:
            observed_temp = observation.get("temperature")
            observed_text = observation.get("text_description", "")

            if observed_temp is not None:
                temperature = str(observed_temp)

            if observed_text:
                condition, icon = condition_from_text(observed_text, is_day=is_day)

        # If NWS has an active storm/rain/snow alert at the point, make the
        # current and near-current rows reflect that instead of showing "partly cloudy."
        if override and index <= 2:
            condition, icon = override

        precipitation_data = period.get("probabilityOfPrecipitation", {}) or {}
        precipitation_probability = precipitation_data.get("value")

        try:
            precipitation_probability = int(precipitation_probability)
        except Exception:
            precipitation_probability = None

        rows.append(
            WeatherRow(
                temperature=temperature or "--",
                icon=icon,
                time_label=format_hour_label(start_time) or period.get("name", ""),
                condition=condition,
                is_night=not is_day,
                forecast_start=start_time,
                detailed_forecast=period.get("detailedForecast", "") or short_forecast,
                wind_speed=period.get("windSpeed", "") or "",
                precipitation_probability=precipitation_probability,
                source="NWS",
            )
        )

    return rows


@dataclass
class WeatherLocation:
    zip_code: str
    label: str
    latitude: float
    longitude: float
    timezone: str = "America/New_York"


def validate_zip_code(zip_code):
    cleaned_zip = "".join(ch for ch in str(zip_code or "") if ch.isdigit())

    if len(cleaned_zip) != 5:
        raise ValueError("Enter a valid 5-digit ZIP code.")

    url = f"https://api.zippopotam.us/us/{cleaned_zip}"

    try:
        data = fetch_json(url, timeout=5)
    except Exception:
        raise ValueError(f"ZIP code {cleaned_zip} was not found.")

    places = data.get("places", [])

    if not places:
        raise ValueError(f"ZIP code {cleaned_zip} was not found.")

    place = places[0]

    try:
        latitude = float(place.get("latitude"))
        longitude = float(place.get("longitude"))
    except Exception:
        raise ValueError(f"ZIP code {cleaned_zip} did not return a usable location.")

    city = place.get("place name", "")
    state = place.get("state abbreviation", "")
    label = cleaned_zip

    if city and state:
        label = f"{cleaned_zip} — {city}, {state}"

    return WeatherLocation(
        zip_code=cleaned_zip,
        label=label,
        latitude=latitude,
        longitude=longitude,
        timezone="America/New_York",
    )

def fetch_weather_rows_from_nws(max_rows=9, location=None):
    location = location or validate_zip_code(ZIP_CODE)

    print(f"Fetching weather data from NWS for ZIP {location.zip_code}...")

    metadata = get_nws_point_metadata(location)

    alerts = []

    try:
        alerts = fetch_nws_active_alerts(location)
        if alerts:
            print("NWS active alerts found:")
            for alert in alerts[:3]:
                print(f"- {alert.get('event')}: {alert.get('headline')}")
        else:
            print("No NWS active alerts for this point.")
    except Exception as error:
        print(f"NWS alerts lookup failed: {error}")

    observation = None

    try:
        observation = fetch_latest_nws_observation(metadata.get("observation_stations_url", ""))
        if observation:
            print(
                "NWS latest observation: "
                f"{observation.get('station_id')} "
                f"{observation.get('temperature')}° "
                f"{observation.get('text_description')}"
            )
    except Exception as error:
        print(f"NWS latest observation lookup failed: {error}")

    periods = fetch_nws_hourly_periods(metadata.get("forecast_hourly_url", ""))

    if not periods:
        raise RuntimeError("NWS hourly forecast returned no periods")

    rows = build_rows_from_nws_periods(
        periods=periods,
        max_rows=max_rows,
        alerts=alerts,
        observation=observation,
    )

    rows = apply_open_meteo_hourly_display_details(rows, location)

    print(f"Loaded NWS weather rows for {location.zip_code}: {len(rows)}")

    return rows


def fetch_weather_rows_from_open_meteo(max_rows=9, location=None):
    location = location or validate_zip_code(ZIP_CODE)

    print(f"Fetching weather data from Open-Meteo for ZIP {location.zip_code}...")

    params = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "current": "temperature_2m,weather_code,is_day",
        "hourly": "temperature_2m,weather_code,precipitation_probability,is_day,wind_speed_10m",
        "temperature_unit": "fahrenheit",
        "timezone": location.timezone,
        "forecast_days": 2,
    }

    url = OPEN_METEO_URL + "?" + urllib.parse.urlencode(params)
    data = fetch_json(url)

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    temperatures = hourly.get("temperature_2m", [])
    weather_codes = hourly.get("weather_code", [])
    precipitation_probabilities = hourly.get("precipitation_probability", [])
    is_day_values = hourly.get("is_day", [])
    wind_speeds = hourly.get("wind_speed_10m", [])

    rows = []

    for index, time_value in enumerate(times[:max_rows]):
        temperature = safe_round_temperature(
            temperatures[index] if index < len(temperatures) else None
        )

        weather_code = weather_codes[index] if index < len(weather_codes) else 0
        precipitation_probability = (
            precipitation_probabilities[index]
            if index < len(precipitation_probabilities)
            else 0
        )

        is_day = bool(is_day_values[index]) if index < len(is_day_values) else True

        condition, icon = condition_from_open_meteo_code(
            weather_code=weather_code,
            precipitation_probability=precipitation_probability,
            is_day=is_day,
        )

        wind_speed = (
            wind_speeds[index]
            if index < len(wind_speeds)
            else None
        )

        try:
            local_start = datetime.fromisoformat(time_value).replace(
                tzinfo=ZoneInfo(location.timezone)
            ).isoformat()
        except Exception:
            local_start = str(time_value or "")

        rows.append(
            WeatherRow(
                temperature=temperature or "--",
                icon=icon,
                time_label=format_hour_label(time_value),
                condition=condition,
                is_night=not is_day,
                forecast_start=local_start,
                detailed_forecast="Open-Meteo hourly forecast",
                wind_speed=(
                    f"{round(float(wind_speed))} mph"
                    if wind_speed is not None
                    else ""
                ),
                precipitation_probability=(
                    int(precipitation_probability)
                    if precipitation_probability is not None
                    else None
                ),
                source="Open-Meteo",
            )
        )

    rows = apply_open_meteo_hourly_display_details(rows, location)

    print(f"Loaded Open-Meteo weather rows for {location.zip_code}: {len(rows)}")

    return rows




@dataclass
class WeatherLocation:
    zip_code: str
    label: str
    latitude: float
    longitude: float
    timezone: str = "America/New_York"
    address: str = ""


ARCGIS_GEOCODER_URL = (
    "https://geocode.arcgis.com/arcgis/rest/services/"
    "World/GeocodeServer/findAddressCandidates"
)


def _request_location_json(url, params, timeout=6):
    request_url = url + "?" + urllib.parse.urlencode(params)

    request = urllib.request.Request(
        request_url,
        headers={
            "User-Agent": "MorningTVUI/1.0 local-dashboard",
            "Accept": "application/json,*/*",
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout,
        context=SSL_CONTEXT,
    ) as response:
        return json.loads(
            response.read().decode("utf-8", errors="ignore")
        )


def _clean_location_query_variants(query):
    query = " ".join(str(query or "").strip().split())

    if not query:
        return []

    variants = [query]

    lowered = query.lower()

    # A typed apartment/unit suffix often prevents a street-address match.
    # Keep the original first, then try the street/city/state without it.
    removable_suffixes = (
        " apt ",
        " apartment ",
        " unit ",
        " suite ",
        " #",
    )

    for suffix in removable_suffixes:
        position = lowered.rfind(suffix)

        if position > 0:
            simplified = query[:position].strip()

            if simplified and simplified not in variants:
                variants.append(simplified)

            break

    # Also handle a final one-to-four digit unit written without "apt".
    parts = query.split()

    if (
        len(parts) >= 5
        and parts[-1].isdigit()
        and len(parts[-1]) <= 4
    ):
        simplified = " ".join(parts[:-1]).strip()

        if simplified and simplified not in variants:
            variants.append(simplified)

    return variants[:3]


def _location_from_arcgis_candidate(candidate):
    location_data = candidate.get("location", {}) or {}
    attributes = candidate.get("attributes", {}) or {}

    try:
        longitude = float(location_data.get("x"))
        latitude = float(location_data.get("y"))
    except Exception:
        raise ValueError("Address result did not include usable coordinates.")

    address = str(
        candidate.get("address")
        or attributes.get("Match_addr")
        or ""
    ).strip()

    if not address:
        raise ValueError("Address result did not include a display label.")

    postcode = str(
        attributes.get("Postal")
        or attributes.get("ZIP")
        or ""
    ).strip()

    zip_digits = "".join(
        character
        for character in postcode
        if character.isdigit()
    )[:5]

    return WeatherLocation(
        zip_code=zip_digits,
        label=address,
        address=address,
        latitude=latitude,
        longitude=longitude,
        timezone=TIMEZONE,
    )


def _location_from_nominatim_item(item):
    display_name = str(item.get("display_name", "") or "").strip()

    try:
        latitude = float(item.get("lat"))
        longitude = float(item.get("lon"))
    except Exception:
        raise ValueError("Address result did not include usable coordinates.")

    address_data = item.get("address", {}) or {}
    postcode = str(address_data.get("postcode", "") or "").strip()

    zip_digits = "".join(
        character
        for character in postcode
        if character.isdigit()
    )[:5]

    if not display_name:
        raise ValueError("Address result did not include a display label.")

    return WeatherLocation(
        zip_code=zip_digits,
        label=display_name,
        address=display_name,
        latitude=latitude,
        longitude=longitude,
        timezone=TIMEZONE,
    )


def _fetch_arcgis_address_suggestions(query, max_results):
    results = []

    for query_variant in _clean_location_query_variants(query):
        try:
            payload = _request_location_json(
                ARCGIS_GEOCODER_URL,
                {
                    "SingleLine": query_variant,
                    "countryCode": "USA",
                    "maxLocations": max_results,
                    "outFields": "Match_addr,Postal,Addr_type",
                    "f": "json",
                },
            )
        except Exception as error:
            print(f"ArcGIS address lookup failed: {error}")
            continue

        for candidate in payload.get("candidates", []) or []:
            try:
                location = _location_from_arcgis_candidate(candidate)
            except Exception:
                continue

            if location.label:
                results.append(location)

        if results:
            break

    return results


def _fetch_nominatim_address_suggestions(query, max_results):
    results = []

    for query_variant in _clean_location_query_variants(query):
        params = {
            "q": query_variant,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": max_results,
            "countrycodes": "us",
            "dedupe": 1,
        }

        try:
            payload = _request_location_json(
                "https://nominatim.openstreetmap.org/search",
                params,
            )
        except Exception as error:
            print(f"Nominatim address lookup failed: {error}")
            continue

        for item in payload if isinstance(payload, list) else []:
            try:
                location = _location_from_nominatim_item(item)
            except Exception:
                continue

            if location.label:
                results.append(location)

        if results:
            break

    return results


def fetch_address_suggestions(query, max_results=6):
    """Return selectable U.S. address/place suggestions with coordinates."""
    query = str(query or "").strip()

    if len(query) < 3:
        return []

    max_results = max(1, min(int(max_results), 8))

    suggestions = _fetch_arcgis_address_suggestions(
        query,
        max_results,
    )

    if not suggestions:
        suggestions = _fetch_nominatim_address_suggestions(
            query,
            max_results,
        )

    unique = {}
    for location in suggestions:
        key = (
            round(float(location.latitude), 6),
            round(float(location.longitude), 6),
            str(location.label).strip().lower(),
        )

        if key not in unique:
            unique[key] = location

    final_results = list(unique.values())[:max_results]

    print(
        f"Address suggestions for {query!r}: "
        f"{len(final_results)} result(s)"
    )

    return final_results


def validate_zip_code(zip_code):
    """Legacy ZIP validation retained for older saved settings."""
    cleaned_zip = "".join(ch for ch in str(zip_code or "") if ch.isdigit())

    if len(cleaned_zip) != 5:
        raise ValueError("Enter a valid 5-digit ZIP code.")

    url = f"https://api.zippopotam.us/us/{cleaned_zip}"

    try:
        data = fetch_json(url, timeout=5)
    except Exception:
        raise ValueError(f"ZIP code {cleaned_zip} was not found.")

    places = data.get("places", [])

    if not places:
        raise ValueError(f"ZIP code {cleaned_zip} was not found.")

    place = places[0]

    try:
        latitude = float(place.get("latitude"))
        longitude = float(place.get("longitude"))
    except Exception:
        raise ValueError(
            f"ZIP code {cleaned_zip} did not return a usable location."
        )

    city = str(place.get("place name", "") or "").strip()
    state = str(place.get("state abbreviation", "") or "").strip()

    label = f"{city}, {state}".strip(", ")

    if not label:
        label = cleaned_zip

    return WeatherLocation(
        zip_code=cleaned_zip,
        label=label,
        address=label,
        latitude=latitude,
        longitude=longitude,
        timezone=TIMEZONE,
    )


def fetch_weather_rows(max_rows=9, zip_code=None, location=None):
    location = location or validate_zip_code(zip_code or ZIP_CODE)

    try:
        return fetch_weather_rows_from_nws(
            max_rows=max_rows,
            location=location,
        )
    except Exception as error:
        print(f"NWS weather failed, falling back to Open-Meteo: {error}")

    try:
        return fetch_weather_rows_from_open_meteo(
            max_rows=max_rows,
            location=location,
        )
    except Exception as error:
        print(f"Open-Meteo weather failed: {error}")

    return [
        WeatherRow("--", "🌤️", "now", "clear", False),
        WeatherRow("--", "☁️", "1pm", "cloud", False),
        WeatherRow("--", "☁️", "2pm", "cloud", False),
        WeatherRow("--", "🌧️", "3pm", "rain", False),
        WeatherRow("--", "🌧️", "4pm", "rain", False),
        WeatherRow("--", "☁️", "5pm", "cloud", False),
        WeatherRow("--", "🌙", "6pm", "clear", True),
        WeatherRow("--", "🌙", "7pm", "clear", True),
        WeatherRow("--", "🌙", "8pm", "clear", True),
    ][:max_rows]
