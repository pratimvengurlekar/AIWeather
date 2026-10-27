"""Streamlit interface for the AI Weather Assistant."""

import streamlit as st

from ai_service import AIServiceError, generate_weather_insight
from weather_service import WeatherServiceError, geocode_city, get_weather


def location_label(location: dict) -> str:
    parts = [location["name"]]
    for field in ("admin1", "country"):
        value = location.get(field)
        if value and value not in parts:
            parts.append(value)
    return ", ".join(parts)


st.set_page_config(page_title="AI Weather Assistant", page_icon="🌦️", layout="centered")
st.title("AI Weather Assistant")
st.write("Discover current weather conditions and get intelligent weather insights powered by AI.")

with st.form("city_search_form"):
    city_input = st.text_input(
        "Enter City Name",
        placeholder="e.g., Mumbai, London, Singapore",
    )
    unit_choice = st.selectbox(
        "Temperature Unit",
        options=["Celsius (°C)", "Fahrenheit (°F)"],
        index=0,
    )
    search_submitted = st.form_submit_button("Find City")

if search_submitted:
    city = city_input.strip()
    st.session_state.pop("weather_locations", None)
    st.session_state.pop("weather_result", None)
    st.session_state.pop("weather_insight", None)
    if not city:
        st.error("Please enter a city name.")
    else:
        with st.spinner("Searching for the city..."):
            try:
                locations = geocode_city(city)
            except WeatherServiceError as error:
                st.error(str(error))
                locations = []
        if not locations:
            st.error("Unable to locate this city. Please check the spelling or search for another location.")
        else:
            st.session_state["weather_locations"] = locations
            st.session_state["weather_city"] = city
            st.session_state["weather_unit"] = unit_choice

locations = st.session_state.get("weather_locations", [])
if locations:
    if len(locations) > 1:
        st.info("Several locations match. Select the correct city and country.")
    else:
        st.markdown(f"**Location:** {location_label(locations[0])}")

    with st.form("weather_request_form", clear_on_submit=True):
        if len(locations) > 1:
            selected_index = st.selectbox(
                "Select a location",
                options=range(len(locations)),
                format_func=lambda index: location_label(locations[index]),
            )
        else:
            selected_index = 0

        api_key = st.text_input(
            "Enter Your OpenAI API Key",
            type="password",
            help=(
                "Use an OpenAI API key with API access and available billing or credits. "
                "The key is sent only to OpenAI and is cleared from this form after submission."
            ),
        )
        st.caption(
            "OpenAI API usage may incur charges. ChatGPT subscriptions and API billing are separate."
        )
        request_submitted = st.form_submit_button("Get Weather Insights")

    if request_submitted:
        st.session_state.pop("weather_result", None)
        st.session_state.pop("weather_insight", None)
        location = locations[selected_index]
        unit = "F" if st.session_state["weather_unit"].startswith("Fahrenheit") else "C"
        with st.spinner("Retrieving current weather..."):
            try:
                weather = get_weather(location["latitude"], location["longitude"], unit=unit)
            except WeatherServiceError as error:
                st.error(str(error))
                weather = None

        if weather is not None:
            location_name = location_label(location)
            st.session_state["weather_result"] = (location_name, weather)
            if api_key.strip():
                with st.spinner("Generating AI Weather Insights..."):
                    try:
                        insight = generate_weather_insight(api_key, weather, location_name)
                    except AIServiceError as error:
                        st.error(str(error))
                    else:
                        st.session_state["weather_insight"] = insight

    result = st.session_state.get("weather_result")
    if result:
        location_name, weather = result
        st.markdown(f"### {location_name}")
        temperature = weather.get("temperature")
        temperature_display = f"{temperature:g} {weather['unit']}" if isinstance(temperature, (int, float)) else "Unavailable"
        humidity = weather.get("humidity")
        humidity_display = f"{humidity}%" if humidity is not None else "Unavailable"
        wind_speed = weather.get("windspeed")
        wind_display = (
            f"{wind_speed:g} {weather['windspeed_unit']}"
            if isinstance(wind_speed, (int, float))
            else "Unavailable"
        )

        temperature_column, condition_column, humidity_column = st.columns(3)
        temperature_column.metric("Current Temperature", temperature_display)
        condition_column.metric("Weather Condition", weather.get("weather_desc") or "Unavailable")
        humidity_column.metric("Relative Humidity", humidity_display)
        st.write(f"**Wind Speed:** {wind_display}")
        observed_at = weather.get("observation_time") or "Unavailable"
        timezone = weather.get("timezone") or "timezone unavailable"
        st.write(f"**Local Observation Time:** {observed_at} ({timezone})")

        insight = st.session_state.get("weather_insight")
        if insight:
            st.subheader("AI Weather Insights")
            st.write(insight)
        else:
            st.info("Enter your OpenAI API key above and submit to generate AI Weather Insights.")