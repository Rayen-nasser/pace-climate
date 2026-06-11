# Deploy PaceClimate to Render (Free 24/7, No Credit Card)

## Prerequisites

1. **GitHub account** — already pushed
2. **Render account** — https://render.com (free, no credit card)

---

## Step 1: Deploy on Render

1. Go to https://dashboard.render.com
2. Click **New +** → **Web Service**
3. Connect your GitHub account and select `Rayen-nasser/pace-climate`
4. Name: `pace-climate`
5. Region: `Frankfurt` (closest to Gafsa, Tunisia)
6. Branch: `master`
7. Runtime: **Docker**
8. Plan: **Free**
9. Advanced → **Add Environment Variables**:

| Variable | Value |
|---|---|
| `GROQ_API_KEY` | `gsk_...` (from .env) |
| `JWT_SECRET_KEY` | `HkN3...` (from .env) |
| `GOOGLE_CLIENT_ID` | `672122558178...` (from .env, optional) |
| `FCM_API_KEY` | `AIzaSy...` (from .env) |
| `FCM_APP_ID` | `1:266848638326...` (from .env) |
| `FCM_SENDER_ID` | `266848638326` |
| `FCM_CREDENTIALS_JSON` | (entire Firebase JSON as a single line) |
| `CORS_ORIGINS` | `https://pace-climate.onrender.com` |

10. Advanced → **Disks** → **Add Disk**:
    - Mount path: `/data`
    - Size: 1 GB
    *(This makes SQLite persistent across restarts)*

11. Click **Deploy Web Service**

---

## Step 2: Verify

Wait for build (2-5 min). Your app is at:

```
https://pace-climate.onrender.com
```

Test:

```
https://pace-climate.onrender.com/docs
https://pace-climate.onrender.com/health
```

> **Note:** Render's free tier sleeps after 15 min of inactivity. First request after idle takes ~30s to wake up.

---

## Updating

```bash
git add .
git commit -m "fix: ..."
git push
```

Render auto-rebuilds and redeploys on push to `master`.

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | Groq API key for AI coach chat |
| `JWT_SECRET_KEY` | Yes | — | Secret key for JWT token signing |
| `CORS_ORIGINS` | Yes | `*` | Comma-separated allowed CORS origins |
| `DATABASE_URL` | No | `sqlite:////data/paceclimate.db` | Database connection string (uses persistent disk) |
| `FCM_API_KEY` | No | — | Firebase Cloud Messaging web API key |
| `FCM_APP_ID` | No | — | Firebase app ID |
| `FCM_SENDER_ID` | No | `266848638326` | Firebase sender ID |
| `FCM_CREDENTIALS_JSON` | No | — | Firebase service account JSON (paste entire JSON) |
| `GOOGLE_CLIENT_ID` | No | — | Google OAuth client ID (optional) |

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `502 Bad Gateway` | Health check path is `/health` — should work out of the box |
| Forecast is empty | Render can reach `api.open-meteo.com` — check env vars |
| Login fails | Register a new user at the live URL, or run `seed_runs.py` locally and push the DB |
| Data lost after restart | Add persistent disk at `/data` (Step 1.10) |
| Cold start too slow | Upgrade to Starter plan ($7/mo, no sleep)
