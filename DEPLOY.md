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
| `GROQ_API_KEY` | `<your-groq-api-key>` |
| `JWT_SECRET_KEY` | `<your-jwt-secret>` |
| `GOOGLE_CLIENT_ID` | `<your-google-client-id>` (optional) |
| `FCM_API_KEY` | `<your-fcm-api-key>` (optional) |
| `FCM_APP_ID` | `<your-fcm-app-id>` (optional) |
| `FCM_SENDER_ID` | `<your-fcm-sender-id>` (optional) |
| `FCM_CREDENTIALS_JSON` | (entire Firebase service account JSON as a single line, optional) |
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
|---|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | Groq API key for AI coach chat |
| `JWT_SECRET_KEY` | Yes | — | Secret key for JWT token signing (generate with `openssl rand -hex 32`) |
| `CORS_ORIGINS` | Yes | `*` | Comma-separated allowed CORS origins |
| `DATABASE_URL` | No | `sqlite:////data/paceclimate.db` | Database connection string (uses persistent disk) |
| `TIMEZONE` | No | `Africa/Tunis` | Timezone for notification scheduling |
| `FCM_API_KEY` | No | — | Firebase Cloud Messaging web API key |
| `FCM_APP_ID` | No | — | Firebase app ID |
| `FCM_SENDER_ID` | No | — | Firebase sender ID |
| `FCM_CREDENTIALS_JSON` | No | — | Firebase service account JSON (paste entire JSON as single line) |
| `GOOGLE_CLIENT_ID` | No | — | Google OAuth client ID (optional) |

For local development, add a `.env` file or set DATABASE_URL to a local path:

```bash
DATABASE_URL=sqlite:///./paceclimate.db uvicorn app.main:app --reload
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `502 Bad Gateway` | Health check path is `/health` — should work out of the box |
| Forecast is empty | Render can reach `api.open-meteo.com` — check env vars |
| Login fails | Register a new user at the live URL, or run `seed_runs.py` locally and push the DB |
| Data lost after restart | Add persistent disk at `/data` (Step 1.10) |
| Cold start too slow | Upgrade to Starter plan ($7/mo, no sleep)
