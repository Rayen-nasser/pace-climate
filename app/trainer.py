import json
import pickle
from datetime import datetime, timezone

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sqlalchemy.orm import Session
from sqlalchemy import func

from .models import RunLog, MlModel

MIN_RUNS_FOR_TRAINING = 20

TOUGH_REASONS = ["rain", "wind", "heat", "humidity", "tired", "injury", "hills", "stress"]

SESSION_FIELDS = ["run_type_easy", "run_type_tempo", "run_type_interval", "run_type_long_run", "run_type_race", "run_type_recovery",
                  "perceived_effort", "pre_run_energy", "sleep_hours", "muscle_soreness"]

DERIVATIVE_FIELDS = ["days_since_last_run", "recent_7d_distance", "recent_7d_run_count", "heat_index"]


def _get_user_avg(db: Session, user_id: int, field, default):
    val = db.query(func.avg(getattr(RunLog, field))).filter(
        RunLog.user_id == user_id,
        getattr(RunLog, field).isnot(None),
    ).scalar()
    return round(val, 1) if val is not None else default


def _get_user_averages(db: Session, user_id: int):
    logs = db.query(RunLog).filter_by(user_id=user_id).all()
    if not logs:
        return {
            "distance_km": 5.0,
            "duration_min": 30,
            "pace": 6.0,
            "avg_hr": 140,
            "max_hr": 175,
            "elevation_gain": 0,
        }
    dists = [l.distance_km for l in logs if l.distance_km]
    durs = [l.duration_min for l in logs if l.duration_min]
    paces = [l.duration_min / l.distance_km for l in logs if l.distance_km and l.duration_min]
    hrs = [l.avg_hr for l in logs if l.avg_hr]
    max_hrs = [l.max_hr for l in logs if l.max_hr]
    elevs = [l.elevation_gain for l in logs if l.elevation_gain is not None]

    def avg(arr):
        return round(sum(arr) / len(arr), 1) if arr else 0

    ses = [l for l in logs if l.sleep_hours]
    ene = [l for l in logs if l.pre_run_energy]
    sor = [l for l in logs if l.muscle_soreness]
    rpe = [l for l in logs if l.perceived_effort]

    return {
        "distance_km": avg(dists) or 5.0,
        "duration_min": avg(durs) or 30,
        "pace": avg(paces) or 6.0,
        "avg_hr": avg(hrs) or 140,
        "max_hr": avg(max_hrs) or 175,
        "elevation_gain": avg(elevs) or 0,
        "sleep_hours": avg([l.sleep_hours for l in ses]) if ses else 7,
        "pre_run_energy": round(avg([l.pre_run_energy for l in ene])) if ene else 3,
        "muscle_soreness": round(avg([l.muscle_soreness for l in sor])) if sor else 2,
        "perceived_effort": round(avg([l.perceived_effort for l in rpe])) if rpe else 5,
        "days_since_last_run": 2,
        "recent_7d_distance": 15,
        "recent_7d_run_count": 3,
    }


def _resolve_effort(db: Session, user_id: int, planned_distance=None, planned_duration=None):
    avg = _get_user_averages(db, user_id)
    dist = planned_distance if planned_distance is not None else avg["distance_km"]
    dur = planned_duration if planned_duration is not None else (
        avg["duration_min"] if planned_distance is None else round(dist * avg["pace"])
    )
    pace = round(dur / dist, 1) if dist > 0 else avg["pace"]
    return dist, dur, pace


def _parse_tough_reasons(run_log):
    reasons = set()
    if run_log.tough_reasons:
        try:
            reasons = set(json.loads(run_log.tough_reasons))
        except (json.JSONDecodeError, TypeError):
            pass
    return reasons


def _get_run_type_flags(run_type):
    types = ["easy", "tempo", "interval", "long_run", "race", "recovery"]
    return [1 if run_type == t else 0 for t in types]


def _compute_heat_index(ws):
    apparent = ws.get("apparent_max")
    actual = ws.get("temp_max")
    if apparent is not None and actual is not None:
        return round(apparent - actual, 1)
    return 0


def _extract_features(run_log, user_averages=None, prev_log=None, recent_7d_logs=None):
    ws = json.loads(run_log.weather_snapshot) if run_log.weather_snapshot else {}
    dist = run_log.distance_km or 0
    dur = run_log.duration_min or 0
    pace = round(dur / dist, 1) if dist > 0 else 0
    avg_hr = run_log.avg_hr
    max_hr = run_log.max_hr
    elev = run_log.elevation_gain

    if user_averages:
        avg_hr = avg_hr or user_averages.get("avg_hr")
        max_hr = max_hr or user_averages.get("max_hr")
        elev = elev if elev is not None else user_averages.get("elevation_gain")

    reasons = _parse_tough_reasons(run_log)
    reason_flags = [1 if r in reasons else 0 for r in TOUGH_REASONS]

    # Phase A: session feedback
    run_type_flags = _get_run_type_flags(run_log.run_type)
    pee = run_log.perceived_effort or (user_averages.get("perceived_effort") if user_averages else 5)
    ene = run_log.pre_run_energy or (user_averages.get("pre_run_energy") if user_averages else 3)
    sle = run_log.sleep_hours or (user_averages.get("sleep_hours") if user_averages else 7)
    sor = run_log.muscle_soreness or (user_averages.get("muscle_soreness") if user_averages else 2)

    # Phase B: derivative features
    if prev_log:
        from datetime import datetime
        try:
            d1 = datetime.strptime(run_log.date, "%Y-%m-%d")
            d0 = datetime.strptime(prev_log.date, "%Y-%m-%d")
            days_since = (d1 - d0).days
        except (ValueError, TypeError):
            days_since = 2
    else:
        days_since = user_averages.get("days_since_last_run", 2) if user_averages else 2

    if recent_7d_logs:
        recent_7d_dist = sum((l.distance_km or 0) for l in recent_7d_logs)
        recent_7d_cnt = len(recent_7d_logs)
    else:
        recent_7d_dist = user_averages.get("recent_7d_distance", 15) if user_averages else 15
        recent_7d_cnt = user_averages.get("recent_7d_run_count", 3) if user_averages else 3

    heat_idx = _compute_heat_index(ws)

    return [
        ws.get("temp_max", 25),
        ws.get("temp_min", 15),
        ws.get("precip_sum", 0),
        ws.get("precip_prob", 0) or 0,
        ws.get("wind_max", 10),
        ws.get("weather_code", 0),
        dist,
        dur,
        pace,
        avg_hr or 140,
        max_hr or 175,
        elev if elev is not None else 0,
    ] + reason_flags + run_type_flags + [pee, ene, sle, sor] + [days_since, recent_7d_dist, recent_7d_cnt, heat_idx]


FEATURE_NAMES = [
    "temp_max", "temp_min", "precip_sum", "precip_prob", "wind_max", "weather_code",
    "distance_km", "duration_min", "pace", "avg_hr", "max_hr", "elevation_gain",
] + TOUGH_REASONS + SESSION_FIELDS + DERIVATIVE_FIELDS


def train_model(db: Session, user_id: int):
    logs = db.query(RunLog).filter_by(user_id=user_id).order_by(RunLog.date).all()

    if len(logs) < MIN_RUNS_FOR_TRAINING:
        return None

    avg = _get_user_averages(db, user_id)

    def _compute_recent_7d(idx):
        from datetime import datetime, timedelta
        try:
            cur = datetime.strptime(logs[idx].date, "%Y-%m-%d")
            cutoff = cur - timedelta(days=7)
            return [logs[j] for j in range(idx) if logs[j].date and datetime.strptime(logs[j].date, "%Y-%m-%d") >= cutoff]
        except (ValueError, TypeError):
            return []

    X = np.array([_extract_features(logs[i], avg, logs[i-1] if i > 0 else None, _compute_recent_7d(i)) for i in range(len(logs))])
    y = np.array([log.rating for log in logs])

    model = RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42)
    model.fit(X, y)

    blob = pickle.dumps(model)

    ml_entry = db.query(MlModel).filter_by(user_id=user_id).first()
    if ml_entry:
        ml_entry.model_blob = blob
        ml_entry.trained_at = datetime.now(timezone.utc)
        ml_entry.run_count = len(logs)
    else:
        ml_entry = MlModel(
            user_id=user_id,
            model_blob=blob,
            trained_at=datetime.now(timezone.utc),
            run_count=len(logs),
        )
        db.add(ml_entry)

    db.commit()
    return model


def load_model(db: Session, user_id: int):
    ml_entry = db.query(MlModel).filter_by(user_id=user_id).first()
    if ml_entry and ml_entry.model_blob:
        return pickle.loads(ml_entry.model_blob)
    return None


def predict_score(db: Session, user_id: int, day: dict, planned_distance=None, planned_duration=None):
    model = load_model(db, user_id)
    if model is None:
        return None

    dist, dur, pace = _resolve_effort(db, user_id, planned_distance, planned_duration)
    avg = _get_user_averages(db, user_id)

    apparent_max = day.get("apparent_max")
    temp_max = day.get("temp_max", 25)
    heat_idx = round((apparent_max - temp_max), 1) if apparent_max is not None else 0

    features = np.array([[
        day.get("temp_max", 25),
        day.get("temp_min", 15),
        day.get("precip_sum", 0),
        day.get("precip_prob", 0) or 0,
        day.get("wind_max", 10),
        day.get("weather_code", 0),
        dist,
        dur,
        pace,
        avg["avg_hr"],
        avg["max_hr"],
        avg["elevation_gain"],
    ] + [0] * len(TOUGH_REASONS)
    + [0] * 6  # run_type flags — all zero for future
    + [avg.get("perceived_effort", 5), avg.get("pre_run_energy", 3), avg.get("sleep_hours", 7), avg.get("muscle_soreness", 2)]
    + [avg.get("days_since_last_run", 2), avg.get("recent_7d_distance", 15), avg.get("recent_7d_run_count", 3), heat_idx]
    ])

    pred = model.predict(features)[0]
    return max(0, min(100, pred * 20))
