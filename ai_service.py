"""Generate concise weather explanations with the OpenAI Responses API."""

import logging
from typing import Any

import openai

OPENAI_MODEL = "gpt-4o-mini"
logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """An expected, user-displayable OpenAI failure."""


def generate_weather_insight(
    api_key: str,
    weather: dict[str, Any],
    location: str,
) -> str:
    """Generate an insight from actual observations without persisting the key."""
    if not api_key.strip():
        raise AIServiceError("Enter your OpenAI API key to generate AI insights.")

    unit = weather.get("unit", "")
    observations = {
        "location": location,
        "temperature": weather.get("temperature"),
        "temperature_unit": unit,
        "condition": weather.get("weather_desc"),
        "relative_humidity_percent": weather.get("humidity"),
        "wind_speed": weather.get("windspeed"),
        "wind_speed_unit": weather.get("windspeed_unit", "km/h"),
        "observation_time": weather.get("observation_time"),
        "timezone": weather.get("timezone"),
    }
    instructions = (
        "You are a concise, friendly weather assistant. Use only the supplied observations "
        "for factual claims about current conditions. Never invent temperature, humidity, "
        "wind speed, or observation times. Clearly acknowledge unavailable measurements. "
        "Do not make predictions because these are current observations only. Explain the "
        "temperature in everyday terms without claiming an actual feels-like measurement "
        "unless one is supplied. Offer practical clothing or outdoor-activity suggestions, "
        "relevant precautions supported by the observations, and a concise conversational conclusion."
    )

    try:
        client = openai.OpenAI(api_key=api_key, timeout=20.0, max_retries=0)
        response = client.responses.create(
            model=OPENAI_MODEL,
            instructions=instructions,
            input=f"Current weather observations (JSON): {observations!r}",
            max_output_tokens=220,
        )
        text = response.output_text
        if not isinstance(text, str) or not text.strip():
            raise AIServiceError("OpenAI returned an empty weather explanation. Please try again.")
        return text.strip()
    except AIServiceError:
        raise
    except openai.AuthenticationError:
        logger.warning("OpenAI authentication failed.")
        raise AIServiceError("OpenAI authentication failed. Please verify your API key.") from None
    except openai.RateLimitError as error:
        logger.warning("OpenAI rate limit or quota error (%s).", getattr(error, "code", None))
        if getattr(error, "code", None) == "insufficient_quota":
            raise AIServiceError(
                "OpenAI could not complete the request. Check your API billing, usage, and quota."
            ) from None
        raise AIServiceError("OpenAI rate limit reached. Please wait a moment and try again.") from None
    except openai.APITimeoutError:
        logger.warning("OpenAI request timed out.")
        raise AIServiceError("The OpenAI request timed out. Please try again.") from None
    except openai.APIConnectionError:
        logger.warning("Could not connect to OpenAI.")
        raise AIServiceError("Could not connect to OpenAI. Check your connection and try again.") from None
    except openai.InternalServerError:
        logger.warning("OpenAI service is temporarily unavailable.")
        raise AIServiceError("OpenAI is temporarily unavailable. Please try again later.") from None
    except openai.BadRequestError as error:
        logger.warning("OpenAI rejected the request (%s).", getattr(error, "code", None))
        if getattr(error, "code", None) == "model_not_found":
            raise AIServiceError(
                "The configured OpenAI model is unavailable. Set OPENAI_MODEL in ai_service.py "
                "to a model enabled for your account."
            ) from None
        raise AIServiceError("OpenAI could not process this request. Check the configured model.") from None
    except openai.OpenAIError as error:
        logger.warning("OpenAI API request failed (%s).", type(error).__name__)
        raise AIServiceError("The OpenAI request could not be completed. Check your API usage and settings.") from None
    except Exception as error:
        logger.warning("Unexpected weather insight failure (%s).", type(error).__name__)
        raise AIServiceError("An unexpected error occurred while generating AI insights. Please try again.") from None
