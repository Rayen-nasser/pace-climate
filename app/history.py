import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .models import RunLog


def log_run(db: Session, user_id: int, date_str: str, distance_km: float, duration_min: int, rating: int, notes: str = None, weather_snapshot: dict = None, avg_hr: int = None, max_hr: int = None, elevation_gain: float = None):
    log = RunLog(
        user_id=user_id,
        date=date_str,
        distance_km=distance_km,
        duration_min=duration_min,
        rating=rating,
        avg_hr=avg_hr,
        max_hr=max_hr,
        elevation_gain=elevation_gain,
        notes=notes,
        weather_snapshot=json.dumps(weather_snapshot) if weather_snapshot else None,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_history(db: Session, user_id: int, limit=50):
    return (
        db.query(RunLog)
        .filter_by(user_id=user_id)
        .order_by(RunLog.date.desc())
        .limit(limit)
        .all()
    )


def get_run_count(db: Session, user_id: int):
    return db.query(RunLog).filter_by(user_id=user_id).count()


def get_recent_runs(db: Session, user_id: int, limit=5):
    return (
        db.query(RunLog)
        .filter_by(user_id=user_id)
        .order_by(RunLog.date.desc())
        .limit(limit)
        .all()
    )
