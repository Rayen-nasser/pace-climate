import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .weather import fetch_forecast, fetch_historical_weather
from .scoring import score_day, TIME_PREFS
from .database import get_db, init_db
from .history import log_run, get_history, get_run_count, update_run_rating
from .trainer import train_model, predict_score, _get_user_averages, TOUGH_REASONS
from .chat import answer_question
from .auth import get_current_user, register_with_password, login_with_password, login_with_google
from .models import User

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


@app.on_event("startup")
def startup():
    init_db()


GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")


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
            "google_client_id": GOOGLE_CLIENT_ID,
        },
    )


@app.post("/api/auth/register")
async def api_register(email: str = Query(...), password: str = Query(...), db: Session = Depends(get_db)):
    return register_with_password(db, email, password)


@app.post("/api/auth/login")
async def api_login(email: str = Query(...), password: str = Query(...), db: Session = Depends(get_db)):
    return login_with_password(db, email, password)


@app.post("/api/auth/google")
async def api_google_login(credential: str = Query(...), db: Session = Depends(get_db)):
    return login_with_google(db, credential)


@app.get("/api/me")
async def api_me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "username": user.username}


@app.get("/api/forecast")
async def api_forecast(
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
    time_pref: str = "evening",
    planned_distance: float = Query(None),
    planned_duration: int = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    raw_days = await fetch_forecast(lat, lon)
    scored = []
    for day in raw_days:
        result = score_day(day, time_pref)
        ml_score = predict_score(db, user.id, day, planned_distance, planned_duration)
        if ml_score is not None:
            result["score"] = round((result["score"] * 0.3 + ml_score * 0.7))
            if result["score"] >= 80:
                result["label"] = "Great"
            elif result["score"] >= 60:
                result["label"] = "Good"
            elif result["score"] >= 40:
                result["label"] = "Okay"
            else:
                result["label"] = "Skip"
        scored.append({**day, **result})
    scored.sort(key=lambda d: d["score"], reverse=True)

    time_pref_label = TIME_PREFS.get(time_pref, TIME_PREFS["evening"])["label"]
    run_count = get_run_count(db, user.id)

    return {
        "location": {"lat": lat, "lon": lon},
        "time_pref": time_pref_label,
        "days": scored,
        "run_count": run_count,
    }


@app.post("/api/runs")
async def api_log_run(
    date: str = Query(...),
    distance_km: float = Query(...),
    duration_min: int = Query(...),
    rating: int = Query(...),
    notes: str = Query(None),
    avg_hr: int = Query(None),
    max_hr: int = Query(None),
    elevation_gain: float = Query(None),
    tough_reasons: str = Query(None),
    lat: float = Query(34.425),
    lon: float = Query(8.784),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    weather = await fetch_historical_weather(lat, lon, date)
    log = log_run(db, user.id, date, distance_km, duration_min, rating, notes, weather, avg_hr, max_hr, elevation_gain, tough_reasons)
    count = get_run_count(db, user.id)
    trained = False
    if count >= 20 and count % 5 == 0:
        train_model(db, user.id)
        trained = True
    return {"id": log.id, "run_count": count, "model_trained": trained}


@app.get("/api/runs")
async def api_get_runs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    runs = get_history(db, user.id)
    return {
        "runs": [
            {
                "id": r.id,
                "date": r.date,
                "distance_km": r.distance_km,
                "duration_min": r.duration_min,
                "rating": r.rating,
                "avg_hr": r.avg_hr,
                "max_hr": r.max_hr,
                "elevation_gain": r.elevation_gain,
                "notes": r.notes,
                "tough_reasons": r.tough_reasons,
                "created_at": str(r.created_at),
            }
            for r in runs
        ],
        "count": len(runs),
    }


@app.patch("/api/runs/{run_id}/rate")
async def api_rate_run(
    run_id: int,
    rating: int = Query(...),
    tough_reasons: str = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    log = update_run_rating(db, user.id, run_id, rating, tough_reasons)
    if not log:
        return JSONResponse(status_code=404, content={"detail": "Run not found"})
    count = get_run_count(db, user.id)
    trained = False
    if count >= 20 and count % 5 == 0:
        train_model(db, user.id)
        trained = True
    return {"id": log.id, "rating": log.rating, "run_count": count, "model_trained": trained}


@app.get("/api/stats")
async def api_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = get_run_count(db, user.id)
    return {"run_count": count, "min_runs": 20, "ready_for_ml": count >= 20}


@app.get("/api/averages")
async def api_averages(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_user_averages(db, user.id)


@app.get("/api/chat")
async def api_chat(
    q: str = Query(...),
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    raw_days = await fetch_forecast(lat, lon)
    scored = []
    for day in raw_days:
        result = score_day(day)
        scored.append({**day, **result})
    run_count = get_run_count(db, user.id)
    answer = answer_question(q, scored, run_count)
    return {"answer": answer}
