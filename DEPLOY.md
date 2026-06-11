# Deploy PaceClimate to SnapDeploy (Free 24/7, No Credit Card)

## Prerequisites

1. **GitHub account** — push this repo
2. **SnapDeploy account** — https://snapdeploy.dev (free, no credit card)

---

## Step 1: Push to GitHub

```bash
git init
git add .
git commit -m "Ready for SnapDeploy deployment"
git remote add origin git@github.com:Rayen-nasser/pace-climate.git
git push -u origin main
```

---

## Step 2: Deploy on SnapDeploy

1. Go to https://snapdeploy.dev and sign up (no credit card)
2. Click **New Container**
3. Choose **Deploy from GitHub** and authorize
4. Select your `paceclimate` repo, branch `main`
5. Name: `paceclimate` (URL becomes `paceclimate.snapdeploy.app`)
6. Port: `8000` (auto-detected for FastAPI)
7. Under **Environment Variables**, add:

| Variable | Value |
|---|---|
| `GROQ_API_KEY` | `gsk_...` (from .env) |
| `JWT_SECRET_KEY` | `HkN3...` (from .env) |
| `GOOGLE_CLIENT_ID` | `672122558178...` (from .env, optional) |
| `FCM_API_KEY` | `AIzaSy...` (from .env) |
| `FCM_APP_ID` | `1:266848638326...` (from .env) |
| `FCM_SENDER_ID` | `266848638326` |
| `FCM_CREDENTIALS_JSON` | (entire Firebase JSON as a single line) |
| `CORS_ORIGINS` | `https://paceclimate.snapdeploy.app` |

8. (Optional) **Add-ons** → **PostgreSQL** — SnapDeploy injects `DATABASE_URL` automatically. If you skip this, the app uses SQLite (data persists while container is running, but lost on restart).
9. Click **Deploy**

---

## Step 3: Verify

Wait for build (60–90 seconds). Your app is at:

```
https://paceclimate.snapdeploy.app
```

Test:

```
https://paceclimate.snapdeploy.app/docs
https://paceclimate.snapdeploy.app/health
```

---

## Updating

```bash
git add .
git commit -m "fix: ..."
git push
```

SnapDeploy auto-rebuilds and redeploys. 10 deploys/day on the free tier.

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | Groq API key for AI coach chat |
| `JWT_SECRET_KEY` | Yes | — | Secret key for JWT token signing |
| `CORS_ORIGINS` | Yes | `*` | Comma-separated allowed CORS origins |
| `DATABASE_URL` | No | `sqlite:///data/paceclimate.db` | Database connection string |
| `FCM_API_KEY` | No | — | Firebase Cloud Messaging web API key |
| `FCM_APP_ID` | No | — | Firebase app ID |
| `FCM_SENDER_ID` | No | `266848638326` | Firebase sender ID |
| `FCM_CREDENTIALS_JSON` | No | — | Firebase service account JSON (paste entire JSON) |
| `FCM_CREDENTIALS_PATH` | No | — | Path to Firebase credentials JSON file |
| `GOOGLE_CLIENT_ID` | No | — | Google OAuth client ID (optional) |

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `502 Bad Gateway` | Health check path is `/health` — should work out of the box |
| Forecast is empty | SnapDeploy can reach `api.open-meteo.com` — no fix needed |
| Login fails | Register a new user at the live URL, or run `seed_runs.py` locally and push the DB |
| Container restarts, data lost | Add SnapDeploy PostgreSQL add-on (free tier includes it) |
