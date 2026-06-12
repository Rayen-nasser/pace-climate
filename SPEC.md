# PaceClimate Feature Specification — Phase 2

## Selected Features

| Feature | Priority | Effort | Target |
|---------|----------|--------|--------|
| Today's Run Plan | P0 | Quick | Web + FCM |
| Weekly Digest | P0 | Quick | Web + FCM |
| Missed Prime Day Alert | P0 | Quick | FCM only |
| Personal Best Celebration | P0 | Quick | FCM only |
| Best Week Ever | P0 | Quick | Web + FCM |
| Shoe Tracker | P1 | Medium | Web + API |
| Structured Workouts | P2 | Large | Flutter-first |
| Race Countdown | P3 | Large | Future |

---

## Phase 1: Quick Wins (API + Web + FCM)

These require no new DB tables. All use existing models and computed data.

---

### 1. Today's Run Plan

**Endpoint:** `GET /api/v1/today-plan`

```python
@router.get("/today-plan")
async def today_plan(
    request: Request,
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
    time_pref: str = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
```

**Response:**
```json
{
  "date": "2026-06-12",
  "run_time": "17:00",
  "run_time_label": "Evening",
  "weather": {
    "temp": 22,
    "wind_max": 8,
    "precip_prob": 5,
    "weather_desc": "Partly cloudy",
    "score": 87,
    "label": "Great"
  },
  "recovery": {
    "status": "ready",
    "reason": "You're recovered and ready to run!"
  },
  "goals": {
    "weekly_distance_remaining_km": 12.4,
    "weekly_runs_remaining": 2,
    "weekly_progress_pct": 71
  },
  "ml_confidence": 0.82,
  "run_count": 25,
  "message": "Run at 17:00 — 22°C, light wind, score 87. You're recovered. 12.4km to weekly goal."
}
```

**FCM Job:** Daily at 06:00 local time
```
Title: "🏃 Today's Run Plan"
Body:  "22°C, light wind, score 87. You're recovered. 12.4km to weekly goal."
Actions: [View Plan, Log Run]
```

**Frontend widget:** Card below forecast, collapsed by default, expands on click.

---

### 2. Weekly Digest

**Endpoint:** `GET /api/v1/weekly-digest`

```python
@router.get("/weekly-digest")
async def weekly_digest(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
```

**Response:**
```json
{
  "week": "2026-W24",
  "week_start": "2026-06-08",
  "week_end": "2026-06-14",
  "runs": 5,
  "distance_km": 42.3,
  "duration_min": 220,
  "avg_pace": "5:12/km",
  "avg_pace_min_km": 5.2,
  "vs_last_week": {
    "distance_pct": 4.2,
    "runs_pct": 0,
    "pace_pct": -1.8
  },
  "last_week_distance_km": 40.6,
  "streak": 3,
  "next_week_forecast": [
    {"date": "2026-06-16", "score": 45, "label": "Okay"},
    {"date": "2026-06-17", "score": 72, "label": "Good"},
    {"date": "2026-06-18", "score": 88, "label": "Great"}
  ],
  "recommendation": "Rain Mon-Wed. Aim for Thu-Sat long runs. You're on track for 180km this month.",
  "monthly_target": {
    "target_km": 180,
    "current_km": 142,
    "progress_pct": 79
  }
}
```

**FCM Job:** Sunday at 09:00 local time
```
Title: "📊 Weekly Digest — 5 runs, 42.3 km"
Body:  "+4.2% vs last week. 3-day streak. Rain Mon-Wed, aim for Thu-Sat."
Actions: [View Details]
```

**Frontend widget:** New tab in sidebar "My Week" — chart + summary + next week forecast.

**Performance:** Query all runs for past 7 and 14 days. Use cached weekly aggregates if available. Add `weekly_stats` cache table if query is slow.

---

### 3. Missed Prime Day Alert

**Scheduled job:** Runs daily at 00:15 local time.

```
For each user with device tokens:
  1. yesterday = date.today() - 1 day
  2. Try to fetch yesterday's actual weather (from history or stored snapshot)
  3. Compute score using score_day(weather_data, user_prefs.time_pref)
  4. If score >= 80:
     a. Query run_logs for yesterday (user_id + date)
     b. If no run logged:
        - Skip if user has opted out of this notification type
        - Send push
```

**FCM Payload:**
```
Title: "🌤️ Yesterday was PRIME (87/100)"
Body:  "17°C, light wind — perfect running weather. Take a rest day or missed it?"
Actions: [Log Yesterday, It Was a Rest Day]
```

**Log Yesterday action:** Opens `/` with `?log=yesterday` — form pre-filled with yesterday's date, auto-selects time pref window.

**It Was a Rest Day action:** Silently creates a "rest day" entry (no distance/duration, `run_type=rest`, `rating=null`) — used to prevent repeat alerts for that date.

**Rest Day table (optional):** If no rest-day tracking, store a lightweight `RestDay(user_id, date)` table. Query before sending to deduplicate.

**Edge cases:**
- User just registered yesterday → skip (no baseline)
- Forecast API unavailable for that date → skip gracefully (already handled)
- Multiple devices → send to all, flag `sent` on a per-notification basis
- DST transition → `timezone` handles it

---

### 4. Personal Best Celebration

**Trigger:** After user logs a run, compare new weekly/monthly totals against all-time history.

```python
def check_personal_bests(db, user_id, run_log):
    stats = compute_stats(db, user_id)
    # Fetch all-time bests
    prev_best = db.query(RunLog).filter(
        RunLog.user_id == user_id,
        RunLog.distance_km >= run_log.distance_km  # worst case
    ).order_by(RunLog.distance_km.desc()).first()
    
    new_bests = []
    if stats["week_distance_km"] > stats["all_time_best_week_km"]:
        new_bests.append({"type": "weekly_distance", "value": stats["week_distance_km"], "prev": stats["all_time_best_week_km"]})
    if stats["week_run_count"] > stats["all_time_best_week_count"]:
        new_bests.append(...)
    if run_log.distance_km > stats["longest_run_km"]:
        new_bests.append(...)
    if run_log.duration_min > stats["longest_run_min"]:
        new_bests.append(...)
    return new_bests
```

**Response (included in log-run response):**
```json
{
  "id": 42,
  "run_count": 25,
  "model_trained": false,
  "personal_bests": [
    {
      "type": "weekly_distance",
      "value": 52.3,
      "previous_best": 49.1,
      "unit": "km",
      "label": "🏆 Best Week Ever!"
    }
  ]
}
```

**FCM:** Sent immediately after log, not on a schedule.
```
Title: "🏆 Best Week Ever!"
Body:  "52.3 km this week — beat your previous best by 3.2 km!"
Actions: [Share, View Stats]
```

---

### 5. Best Week Ever (Web Widget)

**Endpoint:** `GET /api/v1/stats/best-week`

```python
@router.get("/stats/best-week")
async def best_week(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
```

**Response:**
```json
{
  "current_week": {
    "distance_km": 52.3,
    "runs": 5,
    "duration_min": 260
  },
  "all_time_best": {
    "distance_km": 49.1,
    "runs": 5,
    "duration_min": 250,
    "date": "2026-05-18"
  },
  "is_best_ever": true,
  "improvement_km": 3.2,
  "improvement_pct": 6.5
}
```

**Frontend:** Hero card on dashboard:
```
┌───────────────────────────────────────┐
│  🏆 BEST WEEK EVER                    │
│                                       │
│  ████████████████████░░ 52.3 km       │
│  Previous best: 49.1 km (+6.5%)      │
│                                       │
│  5 runs · 4h 20min                    │
│  [Share]                              │
└───────────────────────────────────────┘
```

---

## Phase 2: Shoe Tracker

### DB Migration

```python
class Shoe(Base):
    __tablename__ = "shoes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    name = Column(String)
    brand = Column(String, nullable=True)
    max_km = Column(Float, default=600.0)  # expected lifespan
    color = Column(String, nullable=True)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User")
```

Add to `RunLog`:
```python
shoe_id = Column(Integer, ForeignKey("shoes.id"), nullable=True, index=True)
```

### API Endpoints

```python
# CRUD
POST   /api/v1/shoes                        # Create shoe
GET    /api/v1/shoes                         # List all shoes with mileage
PUT    /api/v1/shoes/{id}                    # Update shoe
DELETE /api/v1/shoes/{id}                    # Deactivate shoe

# Computed
GET    /api/v1/shoes/{id}                    # Shoe detail with mileage breakdown
GET    /api/v1/shoes/stats                   # Summary: total pairs, active, retired
```

### Response Examples

**List shoes:**
```json
{
  "shoes": [
    {
      "id": 1,
      "name": "NB 1080v13",
      "brand": "New Balance",
      "color": "Black",
      "max_km": 600,
      "current_km": 420,
      "remaining_km": 180,
      "wear_pct": 70,
      "is_active": true,
      "last_run_date": "2026-06-10"
    }
  ]
}
```

**Log run with shoe:**
```python
# POST /api/v1/runs?date=...&distance_km=10&shoe_id=1&...
```

### Frontend

- **Shoe list page:** Cards with progress bars, color dots, remaining km
- **Shoe picker:** Dropdown on log form (defaults to last used shoe)
- **Shoe detail:** Timeline of runs grouped by shoe, monthly mileage per shoe

---

## Phase 3: Structured Workouts (Flutter)

### Workout Generator

```python
def generate_workout(user, db):
    """Generate a structured workout based on recovery, ML pace, and goal."""
    recovery = compute_recovery(db, user.id)
    avg_pace = get_ml_pace(db, user.id) or 5.2  # min/km
    goal = db.query(UserGoal).filter_by(user_id=user.id).first()
    
    if recovery["status"] == "rest_day":
        return {"type": "rest", "message": "Rest day recommended"}
    
    if recovery["status"] == "easy_day":
        return {
            "type": "easy_run",
            "segments": [
                {"type": "warmup", "duration_min": 10, "pace": avg_pace + 1.0, "instruction": "Easy jog"},
                {"type": "steady", "duration_min": 20, "pace": avg_pace + 0.3, "instruction": "Conversational pace"},
                {"type": "cooldown", "duration_min": 10, "pace": avg_pace + 1.0, "instruction": "Easy jog"},
            ],
            "total_duration_min": 40,
            "total_distance_km": round(40 / 60 * avg_pace, 1),  # rough
            "intensity": "low",
        }
    
    # Ready — interval workout
    return {
        "type": "intervals",
        "segments": [
            {"type": "warmup", "duration_min": 10, "pace": avg_pace + 1.0},
            {"type": "interval", "duration_min": 3, "pace": avg_pace - 0.5, "reps": 4, "recovery_min": 2},
            {"type": "interval", "duration_min": 5, "pace": avg_pace - 0.3, "reps": 2, "recovery_min": 2},
            {"type": "cooldown", "duration_min": 10, "pace": avg_pace + 1.0},
        ],
        "total_duration_min": 52,
        "intensity": "high",
    }
```

### API Endpoints

```python
GET  /api/v1/workout/today       # Today's generated workout
POST /api/v1/workout/complete    # Mark workout done (logs run + splits)
GET  /api/v1/workout/history     # Past completed workouts
POST /api/v1/workout/custom      # User-authored workout
```

### Flutter Screens

| Screen | Description |
|--------|-------------|
| `WorkoutCard` | Collapsed: duration, type, intensity. Expanded: segment list |
| `WorkoutPlayer` | Live: current segment, time remaining, pace target, voice cues |
| `WorkoutComplete` | Summary: actual vs planned, splits chart, perceived effort input |
| `WorkoutLibrary` | Browse past workouts, repeat favorites, create custom |

### Voice Cues (Flutter TTS)

```
"Warmup complete. Starting interval 1 of 4."
"Halfway there — 2:30 remaining. You're at 4:20/km, target is 4:15."
"Interval complete! 2 minutes recovery jog."
"Final interval. Push hard!"
"Workout complete! Great session. Log your effort below."
```

---

## Phase 4: Race Countdown (Future)

### Models

```python
class Race(Base):
    __tablename__ = "races"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    date = Column(String)     # YYYY-MM-DD
    distance_km = Column(Float)   # 5.0, 10.0, 21.1, 42.2
    target_time_min = Column(Integer, nullable=True)  # goal
    status = Column(String, default="upcoming")  # upcoming, completed, cancelled
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

### Training Plan Generator

Based on Pfitzinger / Jack Daniels / Hal Higdon principles:
- **16 weeks** for marathon, **12 weeks** for half, **8 weeks** for 10k
- Progressive long runs
- Taper in final 2 weeks
- Auto-adjusts if user misses runs or is overtrained (via recovery score)

### Checkpoints

`/api/v1/races/{id}/checkpoints` — milestone status:
```
- 12w out: "Start base building. 5 runs/week, 80% easy."
- 8w out:  "Long run hits 18km this weekend."
- 4w out:  "Peak week. Long run 28km."
- 2w out:  "Taper begins. Reduce volume 30%."
- Race week: "Carb load. Rest. You're ready."
```

---

## Notification Architecture

### New Models

```python
class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    today_plan = Column(Integer, default=1)      # 06:00 daily
    weekly_digest = Column(Integer, default=1)    # Sunday 09:00
    missed_prime = Column(Integer, default=1)      # 00:15 daily
    best_week = Column(Integer, default=1)         # on detection
```

### Job Scheduler

Replace the single `notification_checker_loop` with a cron-like scheduler:

```python
NOTIFICATION_JOBS = [
    {"id": "today_plan",    "cron": "06:00", "daily": True},
    {"id": "weekly_digest", "cron": "09:00", "weekday": 6},  # Sunday
    {"id": "missed_prime",  "cron": "00:15", "daily": True},
]
```

Each job checks `NotificationPreference` before sending.

### Deduplication

Each notification type gets a unique key:
```python
key = f"{job_id}:{user_id}:{date}"
# Skip if already sent today
```

---

## Frontend Widget Summary (Web)

| Route | Widget | Phase |
|-------|--------|-------|
| Dashboard | Today's Run Plan card | P0 |
| Dashboard | Best Week Ever hero | P0 |
| Sidebar tab | "My Week" — weekly digest | P0 |
| Log Run form | Shoe picker dropdown | P1 |
| /shoes | Shoe list + add/edit | P1 |

### My Week Tab Mockup

```
┌─── My Week ────────────────────────────┐
│ 📊 W24 · Jun 8 — Jun 14                │
│                                         │
│  ████████████████ 42.3 km               │
│  ████████████████░░░░ +4.2% vs W23     │
│                                         │
│  5 runs · 3:40h · 5:12/km avg          │
│                                         │
│  Next week outlook:                     │
│   Mon ☁️ 20°  58/100                     │
│   Tue 🌧️ 16°  45/100                     │
│   Wed 🌧️ 15°  42/100                     │
│   Thu ☀️ 24°  84/100 ⭐ Best day          │
│   Fri ☀️ 26°  82/100                     │
│   Sat ⛅ 22°  74/100                     │
│   Sun ⛅ 21°  70/100                     │
│                                         │
│  🎯 Monthly: 142/180 km (79%)           │
└─────────────────────────────────────────┘
```

---

## Implementation Order

| Step | What | Deliverable |
|------|------|-------------|
| 1 | `GET /api/v1/today-plan` | Endpoint + frontend card |
| 2 | `GET /api/v1/weekly-digest` | Endpoint + My Week tab |
| 3 | Missed Prime job in notification loop | FCM alert |
| 4 | Personal Best + Best Week | Endpoint + FCM + hero card |
| 5 | Shoe Tracker (models + CRUD + picker) | Full feature |
| 6 | Notification preferences | Settings UI + opt-in/out |
| 7 | Structured Workouts (Flutter) | Flutter app v1 |
| 8 | Race Countdown | Future |

---

## Migration Path

No breaking changes to existing API. All new endpoints added at `/api/v1/`. Existing `POST /api/v1/runs` gains optional `shoe_id` field. Notification loop gains new job types without removing old scheduled notification system.
