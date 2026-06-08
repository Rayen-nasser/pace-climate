import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .models import RunLog
from .database import CURRENT_USER_ID


def log_run(db: Session, date_str: str, distance_km: float, duration_min: int, rating: int, notes: str = None, weather_snapshot: dict = None):
    log = RunLog(
        user_id=CURRENT_USER_ID,
        date=date_str,
        distance_km=distance_km,
        duration_min=duration_min,
        rating=rating,
        notes=notes,
        weather_snapshot=json.dumps(weather_snapshot) if weather_snapshot else None,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_history(db: Session, limit=50):
    return (
        db.query(RunLog)
        .filter_by(user_id=CURRENT_USER_ID)
        .order_by(RunLog.date.desc())
        .limit(limit)
        .all()
    )


def get_run_count(db: Session):
    return db.query(RunLog).filter_by(user_id=CURRENT_USER_ID).count()


def get_recent_runs(db: Session, limit=5):
    return (
        db.query(RunLog)
        .filter_by(user_id=CURRENT_USER_ID)
        .order_by(RunLog.date.desc())
        .limit(limit)
        .all()
    )
