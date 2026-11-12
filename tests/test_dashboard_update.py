import json
from datetime import datetime, timezone
from pathlib import Path

from paperwhite_weather.config import Settings
from paperwhite_weather.providers.open_meteo import OpenMeteoError, parse_forecast
from paperwhite_weather.render import render_dashboard
from paperwhite_weather.skins.weather_air import world_clock


def test_world_clock_daylight_saving():
    winter = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
    summer = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    assert world_clock(winter, "America/New_York") == "7:00 am"
    assert world_clock(summer, "America/New_York") == "8:00 am"
    assert world_clock(winter, "Pacific/Auckland") == "1:00 am"
    assert world_clock(summer, "Pacific/Auckland") == "12:00 am"


def test_precipitation_and_render():
    data = json.loads(
        (Path(__file__).parent / "fixtures/open_meteo_chicago_2026-09-20.json").read_text()
    )
    data["daily"]["precipitation_sum"] = [2.5, 0, 12, None, 1]
    settings = Settings.model_validate(
        {
            "location": {
                "name": "Chicago",
                "latitude": data["latitude"],
                "longitude": data["longitude"],
                "timezone": "America/Chicago",
            },
            "display": {"skin": "weather-air", "orientation": "portrait"},
            "units": {"temperature": "celsius", "wind": "kmh"},
        }
    )
    now = datetime.fromisoformat("2026-11-12T11:15:00+00:00")
    snap = parse_forecast(data, settings.location, settings.units, now)
    assert snap.today.precipitation_sum_mm == 2.5
    assert snap.daily[3].precipitation_sum_mm is None
    image = render_dashboard(snap, settings, now)
    assert image.size == (1072, 1448) and image.mode == "L"
    del data["daily"]["precipitation_sum"]
    assert (
        parse_forecast(data, settings.location, settings.units, now).today.precipitation_sum_mm
        is None
    )
    data["daily"]["precipitation_sum"] = [2.5]
    try:
        parse_forecast(data, settings.location, settings.units, now)
        raise AssertionError("unequal precipitation arrays must be rejected")
    except OpenMeteoError:
        pass


def test_client_render_without_air(monkeypatch):
    import io
    import threading
    from http.client import HTTPConnection

    from PIL import Image

    from paperwhite_weather.cloud import ClientRenderHandler, cloud_settings
    from paperwhite_weather.providers.mock import MockProvider
    from paperwhite_weather.service import DashboardServer, DashboardService

    monkeypatch.setenv("WEATHER_LATITUDE", "41.8781")
    monkeypatch.setenv("WEATHER_LONGITUDE", "-87.6298")
    monkeypatch.setenv("WEATHER_TIMEZONE", "America/Chicago")
    monkeypatch.setenv("WEATHER_LOCATION", "Chicago")
    weather = json.loads(
        (Path(__file__).parent / "fixtures/open_meteo_chicago_2026-09-20.json").read_text()
    )
    weather["daily"]["precipitation_sum"] = [1.5, 0, 0, 0, 0]
    service = DashboardService(cloud_settings(), MockProvider())
    with DashboardServer(("127.0.0.1", 0), service) as server:
        server.RequestHandlerClass = ClientRenderHandler
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            conn = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            body = json.dumps({"weather": weather, "battery_percent": 73})
            conn.request("POST", "/render/portrait.png", body, {"Content-Type": "application/json"})
            response = conn.getresponse()
            assert response.status == 200
            assert Image.open(io.BytesIO(response.read())).size == (1072, 1448)
            conn.close()
        finally:
            server.shutdown()
            thread.join()
