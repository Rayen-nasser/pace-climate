# PaceClimate

[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen?style=for-the-badge)](https://pace-climate.onrender.com/)

Smart running weather forecasts with personalized ML scoring, push notifications, and AI coaching. **No account required for basic forecast access.**

Choose a time and location, get a 7-day ranked forecast of the best running windows based on weather conditions. Create an account to unlock personalized ML scoring, run logging, push notifications, and AI coaching powered by your own training history.

## Features

- **7-day forecast** — temperature, wind, precipitation, AQI, UV index, dew point, all ranked by a run suitability score (anonymous: rule-based only)
- **Personalized ML scoring** — blends rule-based weather scoring (30%) with a RandomForest model (70%) trained on 37 features from your own run history
- **Session feedback** — log perceived effort, pre-run energy, sleep hours, muscle soreness, run type, and tough reasons
- **Push notifications** — schedule daily reminders with rich body (recovery status, goal progress, weekly stats)
- **AI coach Q&A** — ask about training, recovery, weather, or stats (powered by Groq / Llama 3.1 8B)
- **Athlete services** — wellness/recovery score, training load tracking, weekly goal setting
- **Auth** — email/password + Google Sign-In
- **Anonymous access** — browse 7-day forecast without signing up (ML features require an account)

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy |
| Frontend | HTML, Tailwind CSS (CDN), Vanilla JS |
| Weather | Open-Meteo (free, no API key) |
| ML | scikit-learn RandomForestRegressor (37 features) |
| Auth | bcrypt + JWT + Google Sign-In (GSI) |
| Push | Firebase Cloud Messaging (FCM) |
| AI | Groq API / Llama 3.1 8B |
| DB | SQLite (default) / PostgreSQL (optional) |

## Quick Start

```bash
# Clone
git clone git@github.com:Rayen-nasser/pace-climate.git
cd pace-climate

# Install
pip install -r requirements.txt

# Create .env with required vars (see DEPLOY.md for reference)
# Set at minimum: GROQ_API_KEY, JWT_SECRET_KEY

# Run
fastapi dev app/main.py
```

Open http://localhost:8000

## Deploy

One-click deploy on Render (free tier, no credit card — see [DEPLOY.md](./DEPLOY.md) for full instructions):

```bash
git push
```

Render auto-rebuilds and redeploys on push to `master`.

## Seed Data

Generate 25 realistic runs with real historical weather to bootstrap the ML model:

```bash
python seed_runs.py <email> <password>
```

## Tests

```bash
pip install pytest httpx
pytest tests/test_api.py -v
```

## Docs

- API docs (Swagger): `/docs`
- API reference: [ARCHITECTURE.md](./ARCHITECTURE.md)
- Roadmap: [ROADMAP.md](./ROADMAP.md)

## License

MIT
