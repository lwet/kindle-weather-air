"""A calm weather and air quality layout built with the original project's drawing tools."""

from datetime import datetime
from typing import ClassVar

from PIL import Image

from paperwhite_weather.config import Settings
from paperwhite_weather.models import WeatherSnapshot
from paperwhite_weather.skins.base import DARK_GRAY, PALE_GRAY
from paperwhite_weather.skins.common import Canvas


class WeatherAirSkin:
    """Current weather, a five-day forecast, and an explicitly labeled air quality panel."""

    name: ClassVar[str] = "weather-air"

    def compose(
        self, snapshot: WeatherSnapshot, settings: Settings, now: datetime, size: tuple[int, int]
    ) -> Image.Image:
        """Draw a landscape or portrait frame at the requested size."""
        c = Canvas(size, snapshot, settings, now)
        m, w = c.margin, c.content_width
        c.text((m, m), snapshot.location.name or "Weather", "bold", 48)
        c.text((c.width - m, m + c.px(7)), c.date_line(), "regular", 28, anchor="ra")
        c.rule(m, m + c.px(80), w, thickness=3)
        y = m + c.px(115)
        icon = c.px(185 if c.landscape else 220)
        c.icon(snapshot.current.condition, (m, y, m + icon, y + icon), night=c.night)
        x = m + icon + c.px(30)
        c.text((x, y - c.px(20)), c.temperature(snapshot.current.temperature), "bold", 180)
        c.text(
            (m, y + icon + c.px(20)), c.condition_label(snapshot.current.condition), "medium", 42
        )
        c.text((m, y + icon + c.px(80)), c.feels_like_text(), "regular", 30, fill=DARK_GRAY)
        c.text((m, y + icon + c.px(130)), c.range_text(snapshot.today), "regular", 30)
        rain = snapshot.today.precipitation_probability
        wind = snapshot.current.wind_speed
        rain_text = "—" if rain is None else f"{rain:.0f}%"
        wind_text = (
            "—"
            if wind is None
            else f"{wind:.0f} {dict(kmh='km/h', mph='mph', ms='m/s')[snapshot.units.wind]}"
        )
        c.text((m, y + icon + c.px(180)), f"Rain {rain_text}   ·   Wind {wind_text}", "regular", 28)
        if c.landscape:
            left = m + w * 0.56
            self._air(c, left, y, c.width - m - left)
            forecast_y = m + c.px(585)
        else:
            self._air(c, m, m + c.px(590), w)
            forecast_y = m + c.px(960)
        c.rule(m, forecast_y - c.px(25), w, PALE_GRAY, 2)
        c.temperature_bars(
            (m, forecast_y, c.width - m, c.height - m - c.px(70)), snapshot.daily[:5]
        )
        updated = snapshot.fetched_at.astimezone(c.tz).strftime("%d %b %H:%M")
        c.text(
            (c.width - m, c.height - m),
            f"Updated {updated} · Open-Meteo / CAMS · {snapshot.units.temperature_symbol}",
            "regular",
            24,
            fill=DARK_GRAY,
            anchor="rd",
            max_width=w,
        )
        return c.image

    def _air(self, c: Canvas, x: float, y: float, width: float) -> None:
        c.text((x, y), "AIR QUALITY", "medium", 28, fill=DARK_GRAY)
        air = c.snapshot.air_quality
        if air is None:
            c.text((x, y + c.px(75)), "Unavailable", "bold", 50, max_width=width)
            return
        c.text((x, y + c.px(40)), str(round(air.us_aqi)), "bold", 140, max_width=width * 0.6)
        c.text((x + width, y + c.px(135)), "US AQI", "regular", 30, anchor="ra")
        c.text((x, y + c.px(210)), air.category, "medium", 42, max_width=width)
        pm = "—" if air.pm2_5 is None else f"{air.pm2_5:.1f}"
        c.text((x, y + c.px(275)), f"PM2.5  {pm} µg/m³", "regular", 30)
        data_time = air.time.astimezone(c.tz).strftime("%d %b %H:%M")
        c.text((x, y + c.px(330)), f"Modeled · {data_time}", "regular", 24, fill=DARK_GRAY)
