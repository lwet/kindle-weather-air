# Kindle weather and air quality

A cloud-hosted weather and modeled air quality display for a jailbroken Kindle Paperwhite. Adapted from [Esteban Carisimo’s paperwhite-weather](https://github.com/estcarisimo/paperwhite-weather) under its MIT license. Font licenses are included alongside the bundled fonts.

## Render deployment

Use a Free Python web service with `pip install .` as the build command and `python -m paperwhite_weather.cloud` as the start command. Set `WEATHER_LOCATION`, `WEATHER_LATITUDE`, `WEATHER_LONGITUDE`, and `WEATHER_TIMEZONE` in Render’s environment settings. Location configuration is intentionally absent from this repository.

The Kindle fetches `/dashboard/landscape.png` or `/dashboard/portrait.png`. `/health` reports readiness. The public service allows image and health reads only. Data comes from Open-Meteo weather and CAMS modeled air quality. The displayed index is US AQI, not a local monitoring station measurement.

Free Render instances sleep after inactivity. The Kindle client allows time for startup and retains its previous image if a request fails.
