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

    return {
        "distance_km": avg(dists) or 5.0,
        "duration_min": avg(durs) or 30,
        "pace": avg(paces) or 6.0,
        "avg_hr": avg(hrs) or 140,
        "max_hr": avg(max_hrs) or 175,
        "elevation_gain": avg(elevs) or 0,
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


def _extract_features(run_log, user_averages=None):
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
    ] + reason_flags


FEATURE_NAMES = [
    "temp_max", "temp_min", "precip_sum", "precip_prob", "wind_max", "weather_code",
    "distance_km", "duration_min", "pace", "avg_hr", "max_hr", "elevation_gain",
] + TOUGH_REASONS


def train_model(db: Session, user_id: int):
    logs = db.query(RunLog).filter_by(user_id=user_id).order_by(RunLog.date).all()

    if len(logs) < MIN_RUNS_FOR_TRAINING:
        return None

    avg = _get_user_averages(db, user_id)
    X = np.array([_extract_features(log, avg) for log in logs])
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
    ] + [0] * len(TOUGH_REASONS)])

    pred = model.predict(features)[0]
    return max(0, min(100, pred * 20))
