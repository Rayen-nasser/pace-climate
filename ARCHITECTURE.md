# PaceClimate Architecture

## Tech Stack
- **Backend**: Python + FastAPI (v1.0.0)
- **Frontend**: HTML + Tailwind CSS (served via Jinja2)
- **Weather Data**: Open-Meteo + Open-Meteo Air Quality (free, no API key)
- **Database**: PostgreSQL (Supabase) + SQLAlchemy (SQLite for local dev)
- **ML**: scikit-learn (Random Forest Regressor, 37 features)
- **Push**: Firebase Cloud Messaging (FCM)
- **AI Coach**: Groq API (Llama 3.1 8B)
- **Auth**: JWT (python-jose) + bcrypt / Google Sign-In (GSI)

## Project Structure
```
PaceClimate/
├── app/
│   ├── __init__.py
│   ├── main.py              # App factory, CORS, rate limiter, lifespan, web routes
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Environment variables + defaults
│   │   ├── database.py      # SQLAlchemy engine + session
│   │   └── limiter.py       # Shared slowapi rate limiter instance
│   ├── models/
│   │   ├── __init__.py      # DB schema (User, RunLog, MlModel, UserGoal, DeviceToken, ScheduledNotification)
│   │   └── ...
│   ├── services/
│   │   ├── auth.py          # JWT helpers, password hashing, Google verify
│   │   ├── weather.py       # Open-Meteo API client (weather + AQI)
│   │   ├── scoring.py       # Rule-based + blend with ML scoring
│   │   ├── run_history.py   # Run log CRUD + training load + recovery
│   │   ├── trainer.py       # Per-user ML model (37 features)
│   │   ├── chat.py          # Groq-powered Q&A engine
│   │   └── notifications.py # FCM init, push send, background checker
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py      # POST /auth/register, /auth/login, /auth/google, GET /me
│   │       ├── runs.py      # POST/GET /runs, PATCH /runs/{id}/rate
│   │       ├── forecast.py  # GET /forecast (rate-limited: 60/min)
│   │       ├── goals.py     # PUT/GET /goals
│   │       ├── wellness.py  # GET /wellness, GET /stats
│   │       ├── notifications.py  # register, schedule, list, delete, test
│   │       ├── chat.py      # GET /chat (AI coach)
│   │       └── averages.py  # GET /averages
│   ├── static/              # Static assets (SW, icons)
│   └── templates/
│       └── index.html       # Single-page dashboard
├── alembic/                 # Alembic migrations directory
│   ├── env.py               # Points to DATABASE_URL + Base.metadata
│   ├── script.py.mako       # Migration template
│   └── versions/            # Migration scripts
├── alembic.ini              # Alembic configuration
├── scripts/
│   └── migrate_to_pg.py     # One-time SQLite → Supabase migration
├── tests/
│   ├── conftest.py          # Fixtures (test client, auth, DB)
│   └── test_api.py          # 28 API endpoint tests + OpenAPI spec validation
├── data/                    # Local DB + model files (gitignored)
├── ARCHITECTURE.md
├── DEPLOY.md
├── Dockerfile
├── .dockerignore
├── requirements.txt
└── ROADMAP.md
```

## API Endpoints (v1)

All API endpoints are prefixed with `/api/v1`. Auto-documented at `/docs` (Swagger) and `/redoc` (ReDoc).

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Register with email + password |
| POST | `/auth/login` | Login, returns JWT token |
| POST | `/auth/google` | Login with Google credential |
| GET | `/me` | Get current user info |

### Runs
| Method | Path | Description |
|--------|------|-------------|
| POST | `/runs` | Log a new run (weather + session feedback + tough reasons) |
| GET | `/runs` | Get run history |
| PATCH | `/runs/{id}/rate` | Update rating + tough reasons |

### Forecast
| Method | Path | Description |
|--------|------|-------------|
| GET | `/forecast` | 7-day forecast with scores, AQI, UV, dew point |

### Goals
| Method | Path | Description |
|--------|------|-------------|
| PUT | `/goals` | Set weekly goals |
| GET | `/goals` | Get current goals |

### Wellness
| Method | Path | Description |
|--------|------|-------------|
| GET | `/wellness` | Recovery recommendation (rest/easy/ready) |
| GET | `/stats` | Training stats + goal progress |

### Notifications
| Method | Path | Description |
|--------|------|-------------|
| POST | `/notifications/register` | Register FCM device token |
| POST | `/notifications/schedule` | Schedule a reminder (date + time) |
| GET | `/notifications/scheduled` | List pending reminders |
| DELETE | `/notifications/schedule/{id}` | Cancel a reminder |
| POST | `/notifications/test` | Send test push |

### Chat
| Method | Path | Description |
|--------|------|-------------|
| GET | `/chat` | Ask AI coach a question |

### Averages
| Method | Path | Description |
|--------|------|-------------|
| GET | `/averages` | User's average run stats |

## ML Feature Vector (37 features)
```
[temp_max, temp_min, precip_sum, precip_prob, wind_max, weather_code,
 distance_km, duration_min, pace, avg_hr, max_hr, elevation_gain,
 8 tough_reasons (binary),
 6 run_type one-hot (easy, tempo, interval, long_run, race, recovery),
 perceived_effort, pre_run_energy, sleep_hours, muscle_soreness,
 days_since_last_run, recent_7d_distance, recent_7d_run_count, heat_index,
 aqi, uv_index, dew_point]
```

## Key Design Notes

### Authentication
- JWT tokens with 30-day expiry, stored in localStorage
- `Depends(get_current_user)` on write endpoints (runs, goals, notifications)
- `Depends(get_current_user_optional)` on read endpoints (forecast, chat) — anonymous users get rule-based scores
- Google Sign-In via GSI declarative mode (blocked: COOP issue)

### Database
- PostgreSQL on Supabase (free tier, never sleeps) in production
- SQLite for local development (set `DATABASE_URL` in `.env`)
- Schema migrations via **Alembic** — run automatically on every startup via `init_db()`

#### Migration workflow
```bash
# After editing app/models/__init__.py:
alembic revision --autogenerate -m "describe change"
alembic upgrade head              # test locally
git push                           # Render runs upgrade on deploy
```

### Push Notifications
- Firebase Admin SDK (backend) ↔ FCM JS SDK v10 (frontend)
- Background checker loop runs every 60s inside FastAPI
- Service worker served dynamically with injected config

### ML Training
- Trains after 20 runs, retrains every 5 runs
- Model stored as pickle blob in DB (future: filesystem/S3)
- Score = 30% rule-based + 70% ML prediction

### Rate Limiting
- `/api/v1/forecast` limited to 60 requests/minute (protects Open-Meteo quota)
- Implemented via `slowapi` with shared limiter instance (`app/core/limiter.py`)
- IP-based key function

### Deployment Checklist
- [x] PostgreSQL via Supabase *(always-on free tier)*
- [x] Alembic migrations *(auto-run on each startup)*
- [x] CORS locked to domain *(env var `CORS_ORIGINS`, defaults to `*`)*
- [x] Rate limiting on `/api/v1/forecast` *(60/min via slowapi)*
- [x] HTTPS via reverse proxy *(uvicorn `--proxy-headers --forwarded-allow-ips="*"`)*
- [x] Anonymous read-only access on forecast/chat *(get_current_user_optional)*
- [ ] Model storage on filesystem/S3 *(future: when >50 users)*
- [x] Dockerfile *(multi-stage, production-ready)*
