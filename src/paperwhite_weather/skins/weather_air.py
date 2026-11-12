"""Readable e-ink weather display with local solar times and world clocks."""

from datetime import datetime
from typing import ClassVar
from zoneinfo import ZoneInfo

from PIL import Image

from paperwhite_weather.config import Settings
from paperwhite_weather.models import WeatherSnapshot
from paperwhite_weather.skins.base import DARK_GRAY, PALE_GRAY
from paperwhite_weather.skins.common import Canvas

CITIES = (
    ("Mexico City", "America/Mexico_City"),
    ("Washington DC", "America/New_York"),
    ("London", "Europe/London"),
    ("Pretoria", "Africa/Johannesburg"),
    ("Auckland", "Pacific/Auckland"),
)


def date_title(now: datetime) -> str:
    """Format an abbreviated weekday and an English ordinal date."""
    weekdays = ("Mon", "Tues", "Wed", "Thurs", "Fri", "Sat", "Sun")
    day = now.day
    suffix = "th" if 11 <= day % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{weekdays[now.weekday()]}, {now:%B} {day}{suffix}"


def world_clock(now: datetime, zone: str) -> str:
    """Return a local 12-hour time, accounting for daylight saving."""
    local = now.astimezone(ZoneInfo(zone))
    return f"{local.hour % 12 or 12}:{local.minute:02d} {'am' if local.hour < 12 else 'pm'}"


class WeatherAirSkin:
    """Weather and clocks, optimized for the portrait display."""

    name: ClassVar[str] = "weather-air"

    def compose(
        self, snapshot: WeatherSnapshot, settings: Settings, now: datetime, size: tuple[int, int]
    ) -> Image.Image:
        """Draw a weather frame at the requested dimensions."""
        c = Canvas(size, snapshot, settings, now)
        m = c.px(35)
        width = c.width - 2 * m
        y = c.px
        date = date_title(now)
        c.text((m, y(8)), date, "bold", 80, max_width=width)
        sun = snapshot.sun
        sunrise = sun.sunrise.astimezone(c.tz).strftime("%H:%M")
        sunset = sun.sunset.astimezone(c.tz).strftime("%H:%M")
        location = snapshot.location.name or "Weather"
        if location.lower() == "alderley":
            location = "Alderley, QLD"
        c.text(
            (m, y(104)),
            f"{location}.  Sunrise: {sunrise}  Sunset: {sunset}",
            "regular",
            39,
            max_width=width,
        )
        c.text(
            (m, y(205)),
            c.temperature(snapshot.current.temperature),
            "bold",
            190,
            max_width=width * 0.48,
        )
        c.text(
            (m, y(390)),
            c.condition_label(snapshot.current.condition),
            "bold",
            58,
            max_width=width * 0.48,
        )
        c.text(
            (m, y(465)), c.feels_like_text(), "regular", 45, fill=DARK_GRAY, max_width=width * 0.48
        )
        c.text((m, y(525)), c.range_text(snapshot.today), "regular", 44, max_width=width * 0.48)
        rain = snapshot.today.precipitation_probability
        wind = snapshot.current.wind_speed
        rain_text = "—" if rain is None else f"{rain:.0f}%"
        wind_text = (
            "—"
            if wind is None
            else f"{wind:.0f} {dict(kmh='km/h', mph='mph', ms='m/s')[snapshot.units.wind]}"
        )
        c.text(
            (m, y(590)),
            f"Rain {rain_text}  ·  Wind {wind_text}",
            "regular",
            37,
            max_width=width * 0.49,
        )
        left = m + width * 0.52
        right = c.width - m
        for i, (city, zone) in enumerate(CITIES):
            row_y = y(220 + i * 77)
            c.text((left, row_y), city, "bold", 36, max_width=width * 0.29)
            c.text(
                (right, row_y),
                world_clock(now, zone),
                "regular",
                36,
                anchor="ra",
                max_width=width * 0.18,
            )
            if i < len(CITIES) - 1:
                c.rule(left, row_y + y(58), right - left, PALE_GRAY, 1)
        c.rule(m, y(670), width, PALE_GRAY, 2)
        c.text((m, y(690)), "Humidity", "regular", 42, fill=DARK_GRAY)
        humidity = snapshot.current.humidity_percent
        c.text((m, y(745)), "—" if humidity is None else f"{humidity:.0f}%", "bold", 70)
        split = m + width * 0.52
        c.text(
            (split, y(690)),
            "Today's precipitation",
            "regular",
            39,
            fill=DARK_GRAY,
            max_width=width * 0.48,
        )
        amount = snapshot.today.precipitation_sum_mm
        c.text(
            (split, y(745)),
            "— mm" if amount is None else f"{amount:g} mm",
            "bold",
            70,
            max_width=width * 0.48,
        )
        c.text((split, y(825)), "Forecast total", "regular", 24, fill=DARK_GRAY)
        c.rule(m, y(865), width, PALE_GRAY, 2)
        c.temperature_bars((m, y(885), c.width - m, y(1332)), snapshot.daily[:5])
        updated = snapshot.fetched_at.astimezone(c.tz).strftime("%d %b %H:%M")
        battery = (
            "" if snapshot.battery_percent is None else f" · Battery {snapshot.battery_percent}%"
        )
        c.text(
            (c.width / 2, c.height - y(30)),
            f"Updated {updated}{battery}",
            "regular",
            32,
            fill=DARK_GRAY,
            anchor="md",
            max_width=width,
        )
        return c.image
