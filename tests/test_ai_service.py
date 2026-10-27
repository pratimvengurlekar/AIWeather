from unittest.mock import MagicMock, Mock, patch

import openai
import pytest

from ai_service import AIServiceError, OPENAI_MODEL, generate_weather_insight


def sample_weather():
    return {
        "temperature": 30,
        "unit": "°C",
        "humidity": 65,
        "weather_desc": "Partly cloudy",
        "windspeed": 12,
        "windspeed_unit": "km/h",
        "observation_time": "2026-10-27T12:00",
        "timezone": "Asia/Kolkata",
    }


def test_generate_weather_insight_missing_key_does_not_call_openai():
    with patch("ai_service.openai.OpenAI") as client:
        with pytest.raises(AIServiceError, match="Enter your OpenAI API key"):
            generate_weather_insight("  ", sample_weather(), "Mumbai, India")
    client.assert_not_called()


@patch("ai_service.openai.OpenAI")
def test_generate_weather_insight_uses_responses_api(mock_openai):
    mock_client = MagicMock()
    mock_client.responses.create.return_value.output_text = "Test AI weather insight."
    mock_openai.return_value = mock_client

    result = generate_weather_insight("sk-test", sample_weather(), "Mumbai, India")

    assert result == "Test AI weather insight."
    mock_openai.assert_called_once_with(api_key="sk-test", timeout=20.0, max_retries=0)
    call = mock_client.responses.create.call_args.kwargs
    assert call["model"] == OPENAI_MODEL
    assert "Never invent temperature" in call["instructions"]
    assert "Mumbai, India" in call["input"]


@patch("ai_service.openai.OpenAI")
def test_authentication_error_does_not_expose_key(mock_openai, caplog):
    secret = "sk-sensitive-test-key"
    mock_client = MagicMock()
    error = openai.AuthenticationError(
        "invalid key",
        response=Mock(status_code=401, request=Mock()),
        body={"message": secret},
    )
    mock_client.responses.create.side_effect = error
    mock_openai.return_value = mock_client

    with pytest.raises(AIServiceError) as caught:
        generate_weather_insight(secret, sample_weather(), "Mumbai, India")

    assert "verify your API key" in str(caught.value)
    assert secret not in str(caught.value)
    assert secret not in caplog.text


@patch("ai_service.openai.OpenAI")
def test_rate_limit_error(mock_openai):
    mock_client = MagicMock()
    mock_client.responses.create.side_effect = openai.RateLimitError(
        "rate limited",
        response=Mock(status_code=429, request=Mock()),
        body={"error": {"message": "rate limited"}},
    )
    mock_openai.return_value = mock_client

    with pytest.raises(AIServiceError, match="rate limit"):
        generate_weather_insight("sk-test", sample_weather(), "Mumbai, India")


@patch("ai_service.openai.OpenAI")
def test_insufficient_quota_error(mock_openai):
    mock_client = MagicMock()
    mock_client.responses.create.side_effect = openai.RateLimitError(
        "quota exceeded",
        response=Mock(status_code=429, request=Mock()),
        body={"error": {"message": "quota exceeded"}},
    )
    mock_client.responses.create.side_effect.code = "insufficient_quota"
    mock_openai.return_value = mock_client

    with pytest.raises(AIServiceError, match="billing, usage, and quota"):
        generate_weather_insight("sk-test", sample_weather(), "Mumbai, India")


@patch("ai_service.openai.OpenAI")
def test_general_api_error_is_sanitized(mock_openai, caplog):
    secret = "sk-never-log-this"
    mock_client = MagicMock()
    mock_client.responses.create.side_effect = openai.APIError(
        message=f"request failed for {secret}", request=Mock(), body=None
    )
    mock_openai.return_value = mock_client

    with pytest.raises(AIServiceError) as caught:
        generate_weather_insight(secret, sample_weather(), "Mumbai, India")

    assert secret not in str(caught.value)
    assert secret not in caplog.text


@patch("ai_service.openai.OpenAI")
def test_unexpected_error_is_sanitized(mock_openai, caplog):
    secret = "sk-unexpected-secret"
    mock_client = MagicMock()
    mock_client.responses.create.side_effect = RuntimeError(f"internal failure with {secret}")
    mock_openai.return_value = mock_client

    with pytest.raises(AIServiceError) as caught:
        generate_weather_insight(secret, sample_weather(), "Mumbai, India")

    assert "unexpected error" in str(caught.value)
    assert secret not in str(caught.value)
    assert secret not in caplog.text
