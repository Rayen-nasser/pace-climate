import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models import RunLog


def log_run(db: Session, user_id: int, date_str: str, distance_km: float, duration_min: int, rating: int, notes: str = None, weather_snapshot: dict = None, avg_hr: int = None, max_hr: int = None, elevation_gain: float = None, tough_reasons: str = None, run_type: str = None, perceived_effort: int = None, pre_run_energy: int = None, sleep_hours: float = None, muscle_soreness: int = None):
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
        tough_reasons=tough_reasons,
        run_type=run_type,
        perceived_effort=perceived_effort,
        pre_run_energy=pre_run_energy,
        sleep_hours=sleep_hours,
        muscle_soreness=muscle_soreness,
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


def update_run_rating(db: Session, user_id: int, run_id: int, rating: int, tough_reasons: str = None):
    log = db.query(RunLog).filter_by(id=run_id, user_id=user_id).first()
    if not log:
        return None
    log.rating = rating
    if tough_reasons is not None:
        log.tough_reasons = tough_reasons
    db.commit()
    db.refresh(log)
    return log


def get_training_load(db: Session, user_id: int):
    from datetime import datetime, timedelta
    today = datetime.now()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    logs = db.query(RunLog).filter_by(user_id=user_id).order_by(RunLog.date.desc()).all()
    week_dist = sum(l.distance_km or 0 for l in logs if l.date and _parse_date(l.date) >= week_ago) if logs else 0
    week_cnt = sum(1 for l in logs if l.date and _parse_date(l.date) >= week_ago) if logs else 0
    month_dist = sum(l.distance_km or 0 for l in logs if l.date and _parse_date(l.date) >= month_ago) if logs else 0
    month_cnt = sum(1 for l in logs if l.date and _parse_date(l.date) >= month_ago) if logs else 0
    return week_dist, week_cnt, month_dist, month_cnt


def _parse_date(s):
    from datetime import datetime
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except (ValueError, TypeError):
        return datetime.min


def compute_recovery(db: Session, user_id: int):
    from datetime import datetime, timedelta
    logs = db.query(RunLog).filter_by(user_id=user_id).order_by(RunLog.date.desc()).limit(3).all()
    if not logs:
        return {"status": "ready", "reason": "No recent runs — you're fresh!"}

    last = logs[0]
    recent_7d = [l for l in logs if l.date and _parse_date(l.date) >= datetime.now() - timedelta(days=7)]
    week_km = sum(l.distance_km or 0 for l in recent_7d)

    reasons = []
    score = 0

    # sleep
    if last.sleep_hours is not None:
        if last.sleep_hours < 6:
            reasons.append("low sleep")
            score += 2
        elif last.sleep_hours < 7:
            reasons.append("slightly tired")
            score += 1

    # soreness
    if last.muscle_soreness is not None and last.muscle_soreness >= 4:
        reasons.append("high soreness")
        score += 2
    elif last.muscle_soreness is not None and last.muscle_soreness >= 3:
        reasons.append("some soreness")
        score += 1

    # rpe
    if last.perceived_effort is not None and last.perceived_effort >= 8:
        reasons.append("hard effort")
        score += 2
    elif last.perceived_effort is not None and last.perceived_effort >= 6:
        reasons.append("moderate effort")
        score += 1

    # weekly volume
    if week_km > 50:
        reasons.append("heavy week")
        score += 2
    elif week_km > 30:
        reasons.append("moderate week")
        score += 1

    if score >= 4:
        status = "rest_day"
        reason = f"High load: {', '.join(reasons)}. Take a rest day."
    elif score >= 2:
        status = "easy_day"
        reason = f"Easy day: {', '.join(reasons)}. Light run or rest."
    else:
        status = "ready"
        reason = "You're well recovered. Go for it!"

    return {"status": status, "reason": reason, "week_km": round(week_km, 1)}


def get_recent_runs(db: Session, user_id: int, limit=5):
    return (
        db.query(RunLog)
        .filter_by(user_id=user_id)
        .order_by(RunLog.date.desc())
        .limit(limit)
        .all()
    )
