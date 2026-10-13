"""Combined weather and modeled air quality from Open-Meteo/CAMS."""

from datetime import datetime
from typing import Any, ClassVar

from paperwhite_weather.config import Location, Units
from paperwhite_weather.models import AirQuality, WeatherSnapshot
from paperwhite_weather.providers.open_meteo import OpenMeteoError, OpenMeteoProvider

AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


def parse_air_quality(payload: dict[str, Any], location: Location) -> AirQuality:
    """Validate current pollutant values and interpret the timestamp in the requested zone."""
    try:
        current = payload["current"]
        moment = datetime.fromisoformat(current["time"])
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=location.tzinfo)
        return AirQuality(
            time=moment,
            us_aqi=current["us_aqi"],
            pm2_5=current.get("pm2_5"),
            pm10=current.get("pm10"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise OpenMeteoError(f"invalid air quality response: {exc}") from exc


class WeatherAirProvider:
    """Fetch both datasets; an incomplete refresh retains the service's last good snapshot."""

    name: ClassVar[str] = "weather-air"

    def fetch(self, location: Location, units: Units) -> WeatherSnapshot:
        """Fetch weather and air quality at the configured coordinates."""
        snapshot = OpenMeteoProvider().fetch(location, units)
        payload = OpenMeteoProvider(url=AIR_URL)._request(
            {
                "latitude": f"{location.latitude:.4f}",
                "longitude": f"{location.longitude:.4f}",
                "timezone": location.timezone,
                "current": "us_aqi,pm2_5,pm10",
            }
        )
        return snapshot.model_copy(
            update={
                "source": "Open-Meteo / CAMS",
                "air_quality": parse_air_quality(payload, location),
            }
        )
