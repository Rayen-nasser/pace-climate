from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...core.config import DEFAULT_LAT, DEFAULT_LON
from ...core.database import get_db
from ...services.auth import get_current_user_optional
from ...models import User
from ...services.weather import fetch_forecast
from ...services.scoring import score_day
from ...services.run_history import get_run_count
from ...services.chat import answer_question

router = APIRouter(tags=["chat"])


@router.get("/chat")
async def chat(
    q: str = Query(...),
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
    user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Ask the AI coach a question about the forecast, training, or gear."""
    raw_days = await fetch_forecast(lat, lon)
    scored = []
    for day in raw_days:
        result = score_day(day)
        scored.append({**day, **result})
    if user is not None:
        run_count = get_run_count(db, user.id)
        answer = answer_question(q, scored, run_count)
    else:
        answer = answer_question(q, scored, 0) + (
            "\n\nCreate an account for personalized coaching based on your run history."
        )
    return {"answer": answer}
