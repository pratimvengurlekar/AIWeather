from unittest.mock import Mock, patch

import pytest
import requests

from weather_service import WeatherServiceError, geocode_city, get_weather


def mock_response(payload):
    response = Mock()
    response.json.return_value = payload
    return response


def test_geocode_city_success_and_trims_input():
    location = {"name": "Montréal", "country": "Canada", "latitude": 45.5, "longitude": -73.6}
    with patch("weather_service.requests.get", return_value=mock_response({"results": [location]})) as get:
        assert geocode_city("  Montréal  ") == [location]
    assert get.call_args.kwargs["params"]["name"] == "Montréal"


def test_geocode_city_not_found():
    with patch("weather_service.requests.get", return_value=mock_response({"results": []})):
        assert geocode_city("Nowhereville") == []


def test_geocode_city_multiple_matches():
    locations = [
        {"name": "Springfield", "country": "United States", "latitude": 1, "longitude": 2},
        {"name": "Springfield", "country": "Canada", "latitude": 3, "longitude": 4},
    ]
    with patch("weather_service.requests.get", return_value=mock_response({"results": locations})):
        assert geocode_city("Springfield") == locations


def test_geocode_city_timeout_is_actionable():
    with patch("weather_service.requests.get", side_effect=requests.Timeout):
        with pytest.raises(WeatherServiceError, match="timed out"):
            geocode_city("Mumbai")


def test_geocode_city_http_failure_is_sanitized():
    response = Mock(status_code=503)
    error = requests.HTTPError(response=response)
    with patch("weather_service.requests.get", side_effect=error):
        with pytest.raises(WeatherServiceError, match="Unable to retrieve"):
            geocode_city("Mumbai")


def test_get_weather_success():
    payload = {
        "current": {
            "temperature_2m": 30,
            "relative_humidity_2m": 65,
            "weather_code": 2,
            "wind_speed_10m": 12,
            "time": "2026-10-27T12:00",
        },
        "current_units": {"wind_speed_10m": "km/h"},
        "timezone": "Asia/Kolkata",
    }
    with patch("weather_service.requests.get", return_value=mock_response(payload)):
        weather = get_weather(19.07, 72.88)
    assert weather["temperature"] == 30
    assert weather["unit"] == "°C"
    assert weather["humidity"] == 65
    assert weather["weather_code"] == 2
    assert weather["weather_desc"] == "Partly cloudy"
    assert weather["windspeed"] == 12
    assert weather["observation_time"] == "2026-10-27T12:00"
    assert weather["timezone"] == "Asia/Kolkata"


def test_get_weather_requests_fahrenheit_from_provider():
    payload = {"current": {"temperature_2m": 86, "time": "2026-10-27T12:00"}, "timezone": "UTC"}
    with patch("weather_service.requests.get", return_value=mock_response(payload)) as get:
        weather = get_weather(19.07, 72.88, unit="F")
    assert weather["temperature"] == 86
    assert weather["unit"] == "°F"
    assert get.call_args.kwargs["params"]["temperature_unit"] == "fahrenheit"


def test_get_weather_missing_fields_are_none():
    payload = {"current": {"temperature_2m": 25, "time": "2026-10-27T12:00"}, "timezone": "UTC"}
    with patch("weather_service.requests.get", return_value=mock_response(payload)):
        weather = get_weather(19.07, 72.88)
    assert weather["humidity"] is None
    assert weather["weather_code"] is None
    assert weather["weather_desc"] is None
    assert weather["windspeed"] is None


def test_get_weather_unavailable_response():
    with patch("weather_service.requests.get", return_value=mock_response({})):
        with pytest.raises(WeatherServiceError, match="unavailable"):
            get_weather(19.07, 72.88)


def test_get_weather_timeout():
    with patch("weather_service.requests.get", side_effect=requests.Timeout):
        with pytest.raises(WeatherServiceError, match="timed out"):
            get_weather(19.07, 72.88)


def test_temperature_unit_validation():
    with pytest.raises(WeatherServiceError, match="Choose Celsius or Fahrenheit"):
        get_weather(19.07, 72.88, unit="K")
