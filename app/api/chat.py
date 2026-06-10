from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..config import DEFAULT_LAT, DEFAULT_LON
from ..database import get_db
from ..auth import get_current_user
from ..models import User
from ..weather import fetch_forecast
from ..scoring import score_day
from ..history import get_run_count
from ..chat import answer_question

router = APIRouter(tags=["chat"])


@router.get("/chat")
async def chat(
    q: str = Query(...),
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ask the AI coach a question about the forecast, training, or gear."""
    raw_days = await fetch_forecast(lat, lon)
    scored = []
    for day in raw_days:
        result = score_day(day)
        scored.append({**day, **result})
    run_count = get_run_count(db, user.id)
    answer = answer_question(q, scored, run_count)
    return {"answer": answer}
