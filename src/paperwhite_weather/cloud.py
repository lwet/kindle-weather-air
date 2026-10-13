"""Read-only public deployment of the weather dashboard."""

import logging
import os
import threading
from http import HTTPStatus
from urllib.parse import urlsplit

from paperwhite_weather.config import Settings
from paperwhite_weather.providers.weather_air import WeatherAirProvider
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


def main() -> None:
    """Bind the hosting provider's port and refresh data while the instance is awake."""
    logging.basicConfig(level=logging.INFO)
    service = DashboardService(cloud_settings(), WeatherAirProvider())
    stop = threading.Event()
    refresher = threading.Thread(target=service.run_refresh_loop, args=(stop,), daemon=True)
    refresher.start()
    with DashboardServer(("0.0.0.0", int(os.environ.get("PORT", "10000"))), service) as server:
        server.RequestHandlerClass = CloudHandler
        try:
            server.serve_forever()
        finally:
            stop.set()


if __name__ == "__main__":
    main()
