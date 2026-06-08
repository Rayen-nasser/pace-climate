TIME_PREFS = {
    "morning": {"label": "Morning (6-9 AM)", "weight_temp": "min"},
    "afternoon": {"label": "Afternoon (12-3 PM)", "weight_temp": "max"},
    "evening": {"label": "Evening (5-8 PM)", "weight_temp": "avg"},
}

WEATHER_CODE_BAD = {45, 48, 56, 57, 66, 67, 71, 73, 75, 77, 85, 86, 95, 96, 99}
WEATHER_CODE_OK = {51, 53, 55, 61, 63, 65, 80, 81, 82}
WEATHER_CODE_GOOD = {0, 1}


def _temp_score(temp, time_pref):
    if time_pref == "min":
        t = temp["temp_min"]
    elif time_pref == "max":
        t = temp["temp_max"]
    else:
        t = (temp["temp_min"] + temp["temp_max"]) / 2

    if 15 <= t <= 28:
        return 100
    if t < 0 or t > 40:
        return 0
    if t < 15:
        return max(0, (t - 0) / (15 - 0) * 100)
    return max(0, (40 - t) / (40 - 28) * 100)


def _precip_prob_score(prob):
    return max(0, 100 - prob)


def _wind_score(wind_kmh):
    if wind_kmh <= 10:
        return 100
    if wind_kmh >= 40:
        return 0
    return max(0, 100 - (wind_kmh - 10) / (40 - 10) * 100)


def _weather_code_score(code):
    if code in WEATHER_CODE_GOOD:
        return 100
    if code in WEATHER_CODE_OK:
        return 40
    if code in WEATHER_CODE_BAD:
        return 5
    return 60


def _precip_sum_score(mm):
    if mm <= 0.5:
        return 100
    if mm >= 15:
        return 0
    return max(0, 100 - (mm - 0.5) / (15 - 0.5) * 100)


def _build_explanation(scores, temp_used, desc):
    parts = []
    if scores["temp"] >= 80:
        parts.append(f"{temp_used:.0f}°C feels pleasant")
    elif scores["temp"] >= 50:
        parts.append(f"{temp_used:.0f}°C is manageable")
    else:
        parts.append(f"{temp_used:.0f}°C is tough for running")

    if desc in ("Clear sky", "Mainly clear", "Partly cloudy"):
        parts.append("sky is clear")
    elif "rain" in desc.lower() or "drizzle" in desc.lower() or "shower" in desc.lower():
        parts.append(f"{desc.lower()} expected")
    elif "snow" in desc.lower():
        parts.append("snowy — not ideal")
    elif "fog" in desc.lower():
        parts.append("foggy — reduced visibility")
    elif "thunder" in desc.lower():
        parts.append("thunderstorms — stay indoors")
    else:
        parts.append(desc.lower())

    if scores["wind"] < 50:
        parts.append("windy")
    elif scores["wind"] >= 80:
        parts.append("light wind")

    return " · ".join(parts)


def score_day(day, time_pref="evening"):
    pref = TIME_PREFS.get(time_pref, TIME_PREFS["evening"])

    scores = {
        "temp": _temp_score(day, pref["weight_temp"]),
        "precip_prob": _precip_prob_score(day["precip_prob"]),
        "wind": _wind_score(day["wind_max"]),
        "weather_code": _weather_code_score(day["weather_code"]),
        "precip_sum": _precip_sum_score(day["precip_sum"]),
    }

    weights = {"temp": 0.30, "precip_prob": 0.25, "wind": 0.20, "weather_code": 0.15, "precip_sum": 0.10}

    total = sum(scores[k] * weights[k] for k in weights)

    if total >= 80:
        label = "Great"
    elif total >= 60:
        label = "Good"
    elif total >= 40:
        label = "Okay"
    else:
        label = "Skip"

    if pref["weight_temp"] == "min":
        temp_used = day["temp_min"]
    elif pref["weight_temp"] == "max":
        temp_used = day["temp_max"]
    else:
        temp_used = (day["temp_min"] + day["temp_max"]) / 2

    explanation = _build_explanation(scores, temp_used, day["weather_desc"])

    return {
        "score": round(total),
        "label": label,
        "explanation": explanation,
        "scores": scores,
        "temp_used": round(temp_used, 1),
    }
