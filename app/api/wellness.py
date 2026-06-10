from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_user
from ..models import User, UserGoal
from ..history import get_run_count, get_training_load, compute_recovery

router = APIRouter(tags=["wellness"])


@router.get("/wellness")
async def wellness(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get recovery recommendation based on recent runs, sleep, soreness, and effort."""
    return compute_recovery(db, user.id)


@router.get("/stats")
async def stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get training stats including weekly/monthly volume and goal progress."""
    count = get_run_count(db, user.id)
    week_km, week_cnt, month_km, month_cnt = get_training_load(db, user.id)
    goal = db.query(UserGoal).filter_by(user_id=user.id).first()
    return {
        "run_count": count, "min_runs": 20, "ready_for_ml": count >= 20,
        "week_km": round(week_km, 1), "week_runs": week_cnt,
        "month_km": round(month_km, 1), "month_runs": month_cnt,
        "goal_week_km": goal.weekly_distance_km if goal else 0,
        "goal_week_runs": goal.weekly_runs if goal else 0,
    }
