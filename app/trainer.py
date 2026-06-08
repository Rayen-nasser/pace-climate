import json
import pickle
from datetime import datetime, timezone

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sqlalchemy.orm import Session

from .models import RunLog, MlModel
from .database import CURRENT_USER_ID

MIN_RUNS_FOR_TRAINING = 20


def _extract_features(run_log):
    """Convert a run log + weather snapshot into feature vector."""
    ws = json.loads(run_log.weather_snapshot) if run_log.weather_snapshot else {}
    return [
        ws.get("temp_max", 25),
        ws.get("temp_min", 15),
        ws.get("precip_sum", 0),
        ws.get("precip_prob", 0) or 0,
        ws.get("wind_max", 10),
        ws.get("weather_code", 0),
    ]


FEATURE_NAMES = ["temp_max", "temp_min", "precip_sum", "precip_prob", "wind_max", "weather_code"]


def train_model(db: Session, user_id: int = CURRENT_USER_ID):
    logs = db.query(RunLog).filter_by(user_id=user_id).order_by(RunLog.date).all()

    if len(logs) < MIN_RUNS_FOR_TRAINING:
        return None

    X = np.array([_extract_features(log) for log in logs])
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


def load_model(db: Session, user_id: int = CURRENT_USER_ID):
    ml_entry = db.query(MlModel).filter_by(user_id=user_id).first()
    if ml_entry and ml_entry.model_blob:
        return pickle.loads(ml_entry.model_blob)
    return None


def predict_score(db: Session, day: dict, user_id: int = CURRENT_USER_ID):
    model = load_model(db, user_id)
    if model is None:
        return None

    features = np.array([[
        day.get("temp_max", 25),
        day.get("temp_min", 15),
        day.get("precip_sum", 0),
        day.get("precip_prob", 0) or 0,
        day.get("wind_max", 10),
        day.get("weather_code", 0),
    ]])

    pred = model.predict(features)[0]
    return max(0, min(100, pred * 20))
