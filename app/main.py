from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from .weather import fetch_forecast
from .scoring import score_day, TIME_PREFS

app = FastAPI(title="PaceClimate")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="app/templates")

DEFAULT_LAT = 34.425
DEFAULT_LON = 8.784
DEFAULT_CITY = "Gafsa, Tunisia"


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "default_lat": DEFAULT_LAT,
            "default_lon": DEFAULT_LON,
            "default_city": DEFAULT_CITY,
            "time_prefs": TIME_PREFS,
        },
    )


@app.get("/api/forecast")
async def api_forecast(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON, time_pref: str = "evening"):
    raw_days = await fetch_forecast(lat, lon)
    scored = []
    for day in raw_days:
        result = score_day(day, time_pref)
        scored.append({**day, **result})
    scored.sort(key=lambda d: d["score"], reverse=True)

    time_pref_label = TIME_PREFS.get(time_pref, TIME_PREFS["evening"])["label"]

    return {
        "location": {"lat": lat, "lon": lon},
        "time_pref": time_pref_label,
        "days": scored,
    }
