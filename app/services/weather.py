import httpx
import asyncio

BASE_URL = "https://api.open-meteo.com/v1/forecast"

DAILY_PARAMS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "weather_code",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "sunrise",
    "sunset",
    "uv_index_max",
    "dew_point_2m_max",
]

WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def weather_description(code):
    return WMO_CODES.get(code, "Unknown")


ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


async def fetch_air_quality(lat, lon, start_date, end_date):
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "european_aqi",
        "timezone": "auto",
        "start_date": start_date,
        "end_date": end_date,
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(AIR_QUALITY_URL, params=params, timeout=10)
            if resp.status_code != 200:
                return {}
            data = resp.json()
        daily = data.get("daily", {})
        times = daily.get("time", [])
        aqi_vals = daily.get("european_aqi", [])
        return {times[i]: aqi_vals[i] for i in range(len(times)) if aqi_vals[i] is not None}
    except Exception:
        return {}


async def fetch_historical_weather(lat, lon, date_str):
    async def _weather():
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": date_str,
            "end_date": date_str,
            "daily": "temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,precipitation_sum,precipitation_probability_max,weather_code,wind_speed_10m_max,uv_index_max,dew_point_2m_max",
            "timezone": "auto",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(ARCHIVE_URL, params=params, timeout=10)
            if resp.status_code != 200:
                return {}
            return resp.json()

    weather_task = _weather()
    aqi_task = fetch_air_quality(lat, lon, date_str, date_str)
    data, aqi_data = await asyncio.gather(weather_task, aqi_task)

    daily = data.get("daily", {}) if data else {}
    if not daily.get("time"):
        return {}

    return {
        "temp_max": daily["temperature_2m_max"][0],
        "temp_min": daily["temperature_2m_min"][0],
        "apparent_max": daily.get("apparent_temperature_max", [daily["temperature_2m_max"][0]])[0],
        "apparent_min": daily.get("apparent_temperature_min", [daily["temperature_2m_min"][0]])[0],
        "precip_sum": daily["precipitation_sum"][0],
        "precip_prob": daily.get("precipitation_probability_max", [0])[0] or 0,
        "wind_max": daily["wind_speed_10m_max"][0],
        "weather_code": daily["weather_code"][0],
        "uv_index": daily.get("uv_index_max", [0])[0] or 0,
        "dew_point": daily.get("dew_point_2m_max", [0])[0] or 0,
        "aqi": aqi_data.get(date_str, 0) or 0,
    }


async def fetch_forecast(lat, lon, forecast_days=7):
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ",".join(DAILY_PARAMS),
        "timezone": "auto",
        "forecast_days": forecast_days,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

    daily = data.get("daily", {})
    if not daily.get("time"):
        return []

    start = daily["time"][0]
    end = daily["time"][-1]

    aqi_data = await fetch_air_quality(lat, lon, start, end)

    days = []
    for i in range(len(daily["time"])):
        date = daily["time"][i]
        days.append({
            "date": date,
            "temp_max": daily["temperature_2m_max"][i],
            "temp_min": daily["temperature_2m_min"][i],
            "apparent_max": daily["apparent_temperature_max"][i],
            "apparent_min": daily["apparent_temperature_min"][i],
            "precip_sum": daily["precipitation_sum"][i],
            "precip_prob": daily["precipitation_probability_max"][i],
            "weather_code": daily["weather_code"][i],
            "weather_desc": weather_description(daily["weather_code"][i]),
            "wind_max": daily["wind_speed_10m_max"][i],
            "wind_gust_max": daily["wind_gusts_10m_max"][i],
            "sunrise": daily["sunrise"][i],
            "sunset": daily["sunset"][i],
            "uv_index": daily.get("uv_index_max", [0])[i] or 0,
            "dew_point": daily.get("dew_point_2m_max", [0])[i] or 0,
            "aqi": aqi_data.get(date, 0) or 0,
        })
    return days
