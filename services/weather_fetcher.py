import json
import math
import ssl
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime

import certifi


@dataclass
class WeatherRow:
    temperature: str
    icon: str
    time_label: str
    condition: str
    is_night: bool


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


def condition_from_text(text, is_day=True):
    lowered = (text or "").lower()

    if any(word in lowered for word in ["thunderstorm", "t-storm", "tstorm", "lightning"]):
        return "storm", "⚡"

    if any(word in lowered for word in ["rain", "shower", "drizzle", "sprinkle"]):
        return "rain", "🌧️"

    if any(word in lowered for word in ["snow", "sleet", "flurries", "ice", "freezing rain"]):
        return "snow", "🌨️"

    if any(word in lowered for word in ["fog", "mist", "haze", "smoke"]):
        return "fog", "🌫️"

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
        return "fog", "🌫️"

    if code in [2, 3]:
        return "cloud", "☁️"

    if not is_day:
        return "clear", "🌙"

    if code == 1:
        return "clear", "🌤️"

    return "clear", "☀️"


def get_nws_point_metadata():
    point_url = f"{NWS_BASE_URL}/points/{LATITUDE},{LONGITUDE}"
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


def fetch_nws_active_alerts():
    query = urllib.parse.urlencode(
        {
            "point": f"{LATITUDE},{LONGITUDE}",
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
        is_day = bool(period.get("isDay", True))
        short_forecast = period.get("shortForecast", "") or ""
        start_time = period.get("startTime", "")

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

        rows.append(
            WeatherRow(
                temperature=temperature or "--",
                icon=icon,
                time_label=format_hour_label(start_time) or period.get("name", ""),
                condition=condition,
                is_night=not is_day,
            )
        )

    return rows


def fetch_weather_rows_from_nws(max_rows=9):
    print(f"Fetching weather data from NWS for ZIP {ZIP_CODE}...")

    metadata = get_nws_point_metadata()

    alerts = []

    try:
        alerts = fetch_nws_active_alerts()
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

    print(f"Loaded NWS weather rows: {len(rows)}")

    return rows


def fetch_weather_rows_from_open_meteo(max_rows=9):
    print(f"Fetching weather data from Open-Meteo for ZIP {ZIP_CODE}...")

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": "temperature_2m,weather_code,is_day",
        "hourly": "temperature_2m,weather_code,precipitation_probability,is_day",
        "temperature_unit": "fahrenheit",
        "timezone": TIMEZONE,
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

        rows.append(
            WeatherRow(
                temperature=temperature or "--",
                icon=icon,
                time_label=format_hour_label(time_value),
                condition=condition,
                is_night=not is_day,
            )
        )

    print(f"Loaded Open-Meteo weather rows: {len(rows)}")

    return rows


def fetch_weather_rows(max_rows=9):
    try:
        return fetch_weather_rows_from_nws(max_rows=max_rows)
    except Exception as error:
        print(f"NWS weather failed, falling back to Open-Meteo: {error}")

    try:
        return fetch_weather_rows_from_open_meteo(max_rows=max_rows)
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