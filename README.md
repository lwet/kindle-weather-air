# Kindle weather and air quality

A weather and CAMS modeled air quality display adapted from [Esteban Carisimo’s paperwhite-weather](https://github.com/estcarisimo/paperwhite-weather), under MIT. Original and bundled font licenses are retained.

Deploy a Free Render Python web service: build `pip install .`, start `python -m paperwhite_weather.cloud`. Set `WEATHER_FETCH_MODE=client`, `WEATHER_LOCATION`, `WEATHER_LATITUDE`, `WEATHER_LONGITUDE`, `WEATHER_TIMEZONE` in Render; location configuration is absent from public source.

The Kindle downloads public weather and air quality directly over its Wi-Fi connection, then POSTs both JSON responses to `/render/landscape.png` or `/render/portrait.png`. Render returns a 1072×1448 grayscale PNG without cloud weather API requests or persistent payload storage. Request bodies are capped at 1 MiB, malformed data is rejected, and remote skin changes are disabled. `/health` reports renderer readiness.

This avoids free API quota collisions from shared hosting addresses. Kindle configuration uses `CLOUD_RENDER=yes`, the two API URLs, and the HTTPS Render URL. The client verifies certificates, allows 120 seconds for free service startup, and keeps its previous image if any request fails. It refreshes every 5 minutes independently of the laptop. AQI is the US AQI model output, not a local monitoring station reading.

Validation: 372 tests, Ruff, Mypy, and shell syntax checks passed.

The footer shows the Kindle's battery percentage beside its updated time. The client reads the battery at each refresh and waits for Wi-Fi before closing the Library after USB mode. Configure `REFRESH_MINUTES="5"` on the Kindle for the five-minute schedule.

The portrait dashboard shows current conditions, humidity, the day's forecast precipitation
in millimeters, local sunrise and sunset, five world clocks, and a five-day forecast.
World clocks use IANA time zones and account for daylight saving. They reflect the frame
update time shown in the footer. The client requests `precipitation_sum` from Open-Meteo;
if unavailable the amount is displayed as a dash.
