"""Read-only public deployment of the weather dashboard."""

import json
import logging
import os
import threading
from datetime import datetime, timezone
from http import HTTPStatus
from io import BytesIO
from urllib.parse import urlsplit

from paperwhite_weather.config import Settings
from paperwhite_weather.models import WeatherSnapshot
from paperwhite_weather.providers.open_meteo import parse_forecast
from paperwhite_weather.providers.weather_air import WeatherAirProvider, parse_air_quality
from paperwhite_weather.render import render_dashboard
from paperwhite_weather.service import DashboardHandler, DashboardServer, DashboardService


def cloud_settings() -> Settings:
    """Load location from deployment variables; never embed a real location in source."""
    return Settings.model_validate(
        {
            "location": {
                "name": os.environ.get("WEATHER_LOCATION", "Weather"),
                "latitude": os.environ["WEATHER_LATITUDE"],
                "longitude": os.environ["WEATHER_LONGITUDE"],
                "timezone": os.environ.get("WEATHER_TIMEZONE", "Australia/Brisbane"),
            },
            "display": {"skin": "weather-air", "refresh_minutes": 30, "time_format": "24h"},
            "units": {"temperature": "celsius", "wind": "kmh"},
        }
    )


class CloudHandler(DashboardHandler):
    """Expose only images and service health; public visitors cannot change the skin."""

    def do_GET(self) -> None:
        if urlsplit(self.path).path not in {
            "/health",
            "/dashboard.png",
            "/dashboard/landscape.png",
            "/dashboard/portrait.png",
        }:
            self._send(HTTPStatus.NOT_FOUND, "text/plain", b"not found\n")
            return
        super().do_GET()

    def do_POST(self) -> None:
        self._send(HTTPStatus.METHOD_NOT_ALLOWED, "text/plain", b"read-only service\n")


class ClientRenderHandler(CloudHandler):
    """Draw data fetched by the Kindle, without cloud requests to the weather API."""

    def do_GET(self) -> None:
        if urlsplit(self.path).path == "/health":
            self._send(
                HTTPStatus.OK,
                "application/json",
                b'{"service":"paperwhite-weather","status":"ok","mode":"client-render"}',
            )
        else:
            self._send(HTTPStatus.NOT_FOUND, "text/plain", b"use POST /render/landscape.png\n")

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if path not in {"/render/landscape.png", "/render/portrait.png"}:
            self._send(HTTPStatus.NOT_FOUND, "text/plain", b"not found\n")
            return
        self.connection.settimeout(15)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 1024 * 1024:
                self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "text/plain", b"invalid size\n")
                return
            data = json.loads(self.rfile.read(length))
            settings = self.server.service.settings
            moment = datetime.now(timezone.utc)
            snapshot = parse_forecast(
                data["weather"], settings.location, settings.units, fetched_at=moment
            )
            snapshot = WeatherSnapshot.model_validate(
                snapshot.model_dump()
                | {
                    "source": "Open-Meteo / CAMS",
                    "air_quality": parse_air_quality(data["air"], settings.location),
                    "battery_percent": data.get("battery_percent"),
                }
            )
            orientation = "landscape" if path == "/render/landscape.png" else "portrait"
            settings = settings.model_copy(
                update={"display": settings.display.model_copy(update={"orientation": orientation})}
            )
            frame = render_dashboard(snapshot, settings, moment)
            buffer = BytesIO()
            frame.save(buffer, format="PNG", optimize=True)
        except (ValueError, KeyError, TypeError, RuntimeError, OSError):
            self._send(HTTPStatus.BAD_REQUEST, "text/plain", b"invalid weather payload\n")
            return
        self._send_png(buffer.getvalue())


def main() -> None:
    """Bind the hosting provider's port and refresh data while the instance is awake."""
    logging.basicConfig(level=logging.INFO)
    service = DashboardService(cloud_settings(), WeatherAirProvider())
    stop = threading.Event()
    client_render = os.environ.get("WEATHER_FETCH_MODE") == "client"
    if not client_render:
        refresher = threading.Thread(target=service.run_refresh_loop, args=(stop,), daemon=True)
        refresher.start()
    with DashboardServer(("0.0.0.0", int(os.environ.get("PORT", "10000"))), service) as server:
        server.RequestHandlerClass = ClientRenderHandler if client_render else CloudHandler
        try:
            server.serve_forever()
        finally:
            stop.set()


if __name__ == "__main__":
    main()
