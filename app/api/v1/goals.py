from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...services.auth import get_current_user
from ...models import User, UserGoal

router = APIRouter(tags=["goals"])


@router.put("/goals")
async def set_goals(
    weekly_distance_km: float = Query(0),
    weekly_runs: int = Query(0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set weekly running goals (distance and/or frequency)."""
    goal = db.query(UserGoal).filter_by(user_id=user.id).first()
    if goal:
        goal.weekly_distance_km = weekly_distance_km
        goal.weekly_runs = weekly_runs
    else:
        goal = UserGoal(user_id=user.id, weekly_distance_km=weekly_distance_km, weekly_runs=weekly_runs)
        db.add(goal)
    db.commit()
    return {"weekly_distance_km": weekly_distance_km, "weekly_runs": weekly_runs}


@router.get("/goals")
async def get_goals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user's weekly goals."""
    goal = db.query(UserGoal).filter_by(user_id=user.id).first()
    if goal:
        return {"weekly_distance_km": goal.weekly_distance_km, "weekly_runs": goal.weekly_runs}
    return {"weekly_distance_km": 0, "weekly_runs": 0}
