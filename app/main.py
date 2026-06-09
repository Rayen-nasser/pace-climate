import os
from dotenv import load_dotenv

load_dotenv()

import os
from fastapi import FastAPI, Request, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .weather import fetch_forecast, fetch_historical_weather
from .scoring import score_day, TIME_PREFS
from .database import get_db, init_db
from .history import log_run, get_history, get_run_count, update_run_rating, get_training_load, compute_recovery
from .models import UserGoal
from .trainer import train_model, predict_score, _get_user_averages, TOUGH_REASONS
from .chat import answer_question
from .auth import get_current_user, register_with_password, login_with_password, login_with_google
from .models import User, DeviceToken, ScheduledNotification
from .notifications import init_firebase, notification_checker_loop, send_push

app = FastAPI(title="PaceClimate")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="app/templates")

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

DEFAULT_LAT = 34.425
DEFAULT_LON = 8.784
DEFAULT_CITY = "Gafsa, Tunisia"


@app.on_event("startup")
def startup():
    init_db()
    fcm_ok = init_firebase()
    if fcm_ok:
        import asyncio
        asyncio.create_task(notification_checker_loop())
        print("FCM notification loop started")


GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
FCM_API_KEY = os.environ.get("FCM_API_KEY", "")
FCM_APP_ID = os.environ.get("FCM_APP_ID", "")
FCM_SENDER_ID = os.environ.get("FCM_SENDER_ID", "117274993002466647057")


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
            "fcm_api_key": FCM_API_KEY,
            "fcm_app_id": FCM_APP_ID,
            "fcm_sender_id": FCM_SENDER_ID,
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
    run_type: str = Query(None),
    perceived_effort: int = Query(None),
    pre_run_energy: int = Query(None),
    sleep_hours: float = Query(None),
    muscle_soreness: int = Query(None),
    lat: float = Query(34.425),
    lon: float = Query(8.784),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    weather = await fetch_historical_weather(lat, lon, date)
    log = log_run(db, user.id, date, distance_km, duration_min, rating, notes, weather, avg_hr, max_hr, elevation_gain, tough_reasons, run_type, perceived_effort, pre_run_energy, sleep_hours, muscle_soreness)
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
                "run_type": r.run_type,
                "perceived_effort": r.perceived_effort,
                "pre_run_energy": r.pre_run_energy,
                "sleep_hours": r.sleep_hours,
                "muscle_soreness": r.muscle_soreness,
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
    week_km, week_cnt, month_km, month_cnt = get_training_load(db, user.id)
    goal = db.query(UserGoal).filter_by(user_id=user.id).first()
    return {
        "run_count": count, "min_runs": 20, "ready_for_ml": count >= 20,
        "week_km": round(week_km, 1), "week_runs": week_cnt,
        "month_km": round(month_km, 1), "month_runs": month_cnt,
        "goal_week_km": goal.weekly_distance_km if goal else 0,
        "goal_week_runs": goal.weekly_runs if goal else 0,
    }


@app.get("/api/wellness")
async def api_wellness(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return compute_recovery(db, user.id)


@app.put("/api/goals")
async def api_set_goals(
    weekly_distance_km: float = Query(0),
    weekly_runs: int = Query(0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goal = db.query(UserGoal).filter_by(user_id=user.id).first()
    if goal:
        goal.weekly_distance_km = weekly_distance_km
        goal.weekly_runs = weekly_runs
    else:
        goal = UserGoal(user_id=user.id, weekly_distance_km=weekly_distance_km, weekly_runs=weekly_runs)
        db.add(goal)
    db.commit()
    return {"weekly_distance_km": weekly_distance_km, "weekly_runs": weekly_runs}


@app.get("/api/goals")
async def api_get_goals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = db.query(UserGoal).filter_by(user_id=user.id).first()
    if goal:
        return {"weekly_distance_km": goal.weekly_distance_km, "weekly_runs": goal.weekly_runs}
    return {"weekly_distance_km": 0, "weekly_runs": 0}


@app.get("/api/averages")
async def api_averages(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_user_averages(db, user.id)


@app.post("/api/notifications/register")
async def api_register_device(
    token: str = Query(...),
    platform: str = Query("web"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(DeviceToken).filter_by(token=token).first()
    if existing:
        existing.user_id = user.id
        existing.platform = platform
    else:
        db.add(DeviceToken(user_id=user.id, token=token, platform=platform))
    db.commit()
    return {"ok": True}


@app.post("/api/notifications/schedule")
async def api_schedule_notification(
    date: str = Query(...),
    title: str = Query(...),
    body: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    n = ScheduledNotification(user_id=user.id, date=date, title=title, body=body)
    db.add(n)
    db.commit()
    return {"id": n.id, "date": date, "title": title}


@app.get("/api/notifications/scheduled")
async def api_list_scheduled(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notes = db.query(ScheduledNotification).filter_by(user_id=user.id, sent=0).order_by(ScheduledNotification.date).all()
    return {"notifications": [{"id": n.id, "date": n.date, "title": n.title, "body": n.body} for n in notes]}


@app.delete("/api/notifications/schedule/{note_id}")
async def api_delete_scheduled(note_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.query(ScheduledNotification).filter_by(id=note_id, user_id=user.id).first()
    if n:
        db.delete(n)
        db.commit()
    return {"ok": True}


@app.get("/firebase-messaging-sw.js")
async def service_worker():
    sw_path = os.path.join(os.path.dirname(__file__), "static", "firebase-messaging-sw.js")
    if os.path.exists(sw_path):
        with open(sw_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace("__FCM_API_KEY__", FCM_API_KEY)
        content = content.replace("__FCM_APP_ID__", FCM_APP_ID)
        content = content.replace("__FCM_SENDER_ID__", FCM_SENDER_ID)
        return Response(content=content, media_type="application/javascript")
    return JSONResponse(status_code=404, content={"detail": "Not found"})


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
