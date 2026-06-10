import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .core.config import DEFAULT_LAT, DEFAULT_LON, DEFAULT_CITY, GOOGLE_CLIENT_ID, FCM_API_KEY, FCM_APP_ID, FCM_SENDER_ID
from .core.database import init_db
from .services.scoring import TIME_PREFS
from .services.notifications import init_firebase, notification_checker_loop
from .api.v1 import auth, runs, forecast, goals, wellness, notifications as notif_api, chat, averages

app = FastAPI(title="PaceClimate", version="1.0.0",
              description="Smart running weather forecasts with personalized ML scoring, push notifications, and AI coaching.",
              docs_url="/docs", redoc_url="/redoc")

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

API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(runs.router, prefix=API_PREFIX)
app.include_router(forecast.router, prefix=API_PREFIX)
app.include_router(goals.router, prefix=API_PREFIX)
app.include_router(wellness.router, prefix=API_PREFIX)
app.include_router(notif_api.router, prefix=API_PREFIX)
app.include_router(chat.router, prefix=API_PREFIX)
app.include_router(averages.router, prefix=API_PREFIX)


@app.on_event("startup")
def startup():
    init_db()
    fcm_ok = init_firebase()
    if fcm_ok:
        import asyncio
        asyncio.create_task(notification_checker_loop())
        print("FCM notification loop started")


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
    return Response(status_code=404)
