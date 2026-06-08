# PaceClimate Architecture

## Tech Stack
- **Backend**: Python + FastAPI
- **Frontend**: HTML + Tailwind CSS (served via Jinja2)
- **Weather Data**: Open-Meteo (free, no API key)
- **Database**: SQLite + SQLAlchemy (PostgreSQL before deploy)
- **ML**: scikit-learn (Random Forest)

## Project Structure
```
PaceClimate/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI routes + server
│   ├── weather.py        # Open-Meteo API client
│   ├── scoring.py        # Rule-based + ML scoring
│   ├── database.py       # SQLAlchemy engine + session
│   ├── models.py         # DB schema (users, run_logs)
│   ├── history.py        # Log + query runs
│   ├── trainer.py        # Per-user ML model training
│   ├── chat.py           # Simple Q&A engine
│   └── templates/
│       └── index.html    # Dashboard
├── data/                 # DB + model files (gitignored)
├── ARCHITECTURE.md
├── requirements.txt
└── .gitignore
```

## Multi-User Architecture
All tables have `user_id`. Currently hardcoded to `CURRENT_USER_ID = 1`.
When auth is added later, swap for real user ID — zero refactoring needed.

### Schema
```
users: id, username, password_hash, created_at
user_preferences: user_id, lat, lon, time_pref, temp_min, temp_max
run_logs: id, user_id, date, distance_km, duration_min, rating (1-5), weather_snapshot (JSON), notes, created_at
ml_models: user_id (PK), model_blob (pickle), trained_at
```

## Key Design Notes

### Before Deploy Checklist
- [ ] Auth system (JWT + OAuth2PasswordBearer)
- [ ] PostgreSQL instead of SQLite
- [ ] Alembic migrations ready
- [ ] Env vars for all config (`python-dotenv`)
- [ ] CORS locked to your domain
- [ ] Rate limiting on `/api/forecast` (60/min Open-Meteo limit)
- [ ] HTTPS via reverse proxy (nginx/Caddy)
- [ ] Model storage on filesystem/S3 (not DB blob)
- [ ] Unit tests for scoring + API
- [ ] Dockerfile for deployment

### Auth Migration Path
1. Add `app/auth.py` with register/login endpoints
2. Use `passlib` + `bcrypt` for passwords
3. Use FastAPI `Depends(get_current_user)` everywhere
4. Replace `CURRENT_USER_ID = 1` with `user.id`

### PostgreSQL Migration
- Already using SQLAlchemy → change only the connection string
- `sqlite:///data/paceclimate.db` → `postgresql://user:pass@host/db`
- Use `alembic` for migrations
- Use `asyncpg` driver for async

### ML Model Storage
- Currently: pickle blob in SQLite → fine for dev
- Production: save `.pkl` to filesystem or S3, store path in DB
- Consider `joblib` instead of pickle

### Performance
- Cache forecast responses (1-hour TTL)
- Async model training via FastAPI `BackgroundTasks`
- SQLAlchemy connection pooling (auto for PostgreSQL)

### Multi-User Frontend
- Current: single Jinja2 template → fine for 1 user
- For multi-user: split to FastAPI backend + SPA frontend
