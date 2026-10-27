# AI Weather Assistant Project Brief

This repository implements a beginner-friendly Streamlit weather application. Users search for a city, select the correct geocoded location when needed, choose Celsius or Fahrenheit, and request a concise AI explanation using their own OpenAI API key.

The app retrieves current observations from Open-Meteo and sends only those observations and the location to the OpenAI Responses API. The OpenAI key is never sent to Open-Meteo, included in the model prompt, written to disk, or logged. Tests mock all external API calls.

See `README.md` for local setup, architecture, testing, costs, security limitations, and Streamlit Community Cloud deployment.
