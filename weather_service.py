"""Geocoding and current weather retrieval from Open-Meteo."""

from typing import Any

import requests

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT = 8.0

WEATHER_CODE_MAP = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherServiceError(Exception):
    """An expected, user-displayable weather service failure."""


def _request_error_message(error: requests.RequestException, provider: str) -> str:
    if isinstance(error, requests.Timeout):
        return f"The {provider} request timed out. Please try again."
    if isinstance(error, requests.HTTPError):
        status = error.response.status_code if error.response is not None else None
        if status == 429:
            return f"The {provider} is rate limiting requests. Please try again shortly."
    return f"Unable to retrieve data from {provider}. Check your connection and try again."


def geocode_city(city: str, timeout: float = REQUEST_TIMEOUT) -> list[dict[str, Any]]:
    """Return matching locations for a city name."""
    city = city.strip()
    if not city:
        raise WeatherServiceError("Enter a city name to search.")

    try:
        response = requests.get(
            GEOCODE_URL,
            params={"name": city, "count": 5, "language": "en", "format": "json"},
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as error:
        raise WeatherServiceError(_request_error_message(error, "Open-Meteo geocoding service")) from None
    except ValueError:
        raise WeatherServiceError("Open-Meteo returned an invalid city-search response.") from None

    if not isinstance(data, dict):
        raise WeatherServiceError("Open-Meteo returned an invalid city-search response.")
    results = data.get("results", [])
    if not isinstance(results, list):
        raise WeatherServiceError("Open-Meteo returned an invalid city-search response.")
    return [
        location
        for location in results
        if isinstance(location, dict)
        and isinstance(location.get("latitude"), (int, float))
        and isinstance(location.get("longitude"), (int, float))
        and isinstance(location.get("name"), str)
    ]


def get_weather(
    latitude: float,
    longitude: float,
    unit: str = "C",
    timeout: float = REQUEST_TIMEOUT,
) -> dict[str, Any]:
    """Retrieve current observations for coordinates in Celsius or Fahrenheit."""
    normalized_unit = unit.upper()
    if normalized_unit not in {"C", "F"}:
        raise WeatherServiceError("Choose Celsius or Fahrenheit.")

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,"
            "precipitation,weather_code,cloud_cover,wind_speed_10m,wind_direction_10m,wind_gusts_10m"
        ),
        "temperature_unit": "fahrenheit" if normalized_unit == "F" else "celsius",
        "wind_speed_unit": "kmh",
        "timezone": "auto",
    }

    try:
        response = requests.get(WEATHER_URL, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as error:
        raise WeatherServiceError(_request_error_message(error, "Open-Meteo weather service")) from None
    except ValueError:
        raise WeatherServiceError("Open-Meteo returned an invalid weather response.") from None

    current = data.get("current") if isinstance(data, dict) else None
    if not isinstance(current, dict):
        raise WeatherServiceError("Current weather data is unavailable for this location.")

    weather_code = current.get("weather_code")
    if not isinstance(weather_code, int):
        weather_code = None
    temperature = current.get("temperature_2m")
    if not isinstance(temperature, (int, float)):
        temperature = None
    current_units = data.get("current_units") if isinstance(data, dict) else None
    if not isinstance(current_units, dict):
        current_units = {}

    return {
        "temperature": temperature,
        "unit": "°F" if normalized_unit == "F" else "°C",
        "humidity": current.get("relative_humidity_2m"),
        "weather_code": weather_code,
        "weather_desc": WEATHER_CODE_MAP.get(weather_code) if weather_code is not None else None,
        "windspeed": current.get("wind_speed_10m"),
        "windspeed_unit": current_units.get("wind_speed_10m", "km/h"),
        "observation_time": current.get("time"),
        "timezone": data.get("timezone"),
    }
