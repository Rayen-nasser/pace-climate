from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from ...core.config import DEFAULT_LAT, DEFAULT_LON
from ...core.limiter import limiter
from ...core.database import get_db
from ...services.auth import get_current_user, get_current_user_optional
from ...models import User
from ...services.weather import fetch_forecast
from ...services.scoring import score_day, TIME_PREFS
from ...services.trainer import predict_score
from ...services.run_history import get_run_count

router = APIRouter(tags=["forecast"])


@router.get("/forecast")
@limiter.limit("60/minute")
async def forecast(
    request: Request,
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
    time_pref: str = "evening",
    planned_distance: float = Query(None),
    planned_duration: int = Query(None),
    user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Get 7-day running forecast. Authenticated users get ML-blended scores."""
    raw_days = await fetch_forecast(lat, lon)
    scored = []
    for day in raw_days:
        result = score_day(day, time_pref)
        if user is not None:
            try:
                ml_score = predict_score(db, user.id, day, planned_distance, planned_duration)
            except Exception:
                ml_score = None
            if ml_score is not None:
                result["score"] = round((result["score"] * 0.3 + ml_score * 0.7))
                s = result["score"]
                result["label"] = "Great" if s >= 80 else "Good" if s >= 60 else "Okay" if s >= 40 else "Skip"
                result["ml_score"] = round(ml_score)
        scored.append({**day, **result})
    scored.sort(key=lambda d: d["score"], reverse=True)

    time_pref_label = TIME_PREFS.get(time_pref, TIME_PREFS["evening"])["label"]
    run_count = get_run_count(db, user.id) if user is not None else 0

    return {
        "location": {"lat": lat, "lon": lon},
        "time_pref": time_pref_label,
        "days": scored,
        "run_count": run_count,
    }
