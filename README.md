# PaceClimate

Smart running weather forecasts with personalized ML scoring, push notifications, and AI coaching.

Choose a time and location, get a 7-day ranked forecast of the best running windows based on weather conditions, your personal running history, and a machine learning model that learns your preferences over time.

## Features

- **7-day forecast** — temperature, wind, precipitation, AQI, UV index, dew point, all ranked by a run suitability score
- **Personalized ML scoring** — blends rule-based weather scoring (30%) with a RandomForest model (70%) trained on 37 features from your own run history + session feedback + environmental data
- **Session feedback** — log perceived effort, pre-run energy, sleep hours, muscle soreness, run type, and tough reasons after each run
- **Push notifications** — schedule daily reminders for your preferred run time, with rich body (recovery status, goal progress, weekly stats)
- **AI coach Q&A** — ask anything about training, recovery, weather, or your stats (powered by Groq / Llama 3.1 8B)
- **Athlete services** — wellness/recovery score, training load tracking, weekly goal setting
- **Auth** — email/password registration + Google Sign-In
- **Mobile-ready API** — all endpoints at `/api/v1/` for Flutter/React Native consumption

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

One-click deploy on SnapDeploy (free, no credit card):

1. Push to GitHub
2. Go to https://snapdeploy.dev
3. New Container -> Deploy from GitHub -> select repo
4. Set environment variables
5. Deploy

Full instructions in [DEPLOY.md](./DEPLOY.md).

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
