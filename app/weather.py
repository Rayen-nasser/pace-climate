import httpx

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
    days = []
    for i in range(len(daily.get("time", []))):
        days.append({
            "date": daily["time"][i],
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
        })
    return days
