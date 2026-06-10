from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...services.auth import get_current_user
from ...models import User
from ...services.run_history import log_run, get_history, get_run_count, update_run_rating
from ...services.trainer import train_model
from ...services.weather import fetch_historical_weather

router = APIRouter(tags=["runs"])


@router.post("/runs")
async def create_run(
    date: str = Query(...),
    distance_km: float = Query(...),
    duration_min: int = Query(...),
    rating: int = Query(...),
    notes: str = Query(None),
    avg_hr: int = Query(None),
    max_hr: int = Query(None),
    elevation_gain: float = Query(None),
    tough_reasons: str = Query(None),
    run_type: str = Query(None),
    perceived_effort: int = Query(None),
    pre_run_energy: int = Query(None),
    sleep_hours: float = Query(None),
    muscle_soreness: int = Query(None),
    lat: float = Query(34.425),
    lon: float = Query(8.784),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Log a new run with weather data, session feedback, and tough reasons."""
    weather = await fetch_historical_weather(lat, lon, date)
    log = log_run(db, user.id, date, distance_km, duration_min, rating, notes, weather,
                  avg_hr, max_hr, elevation_gain, tough_reasons, run_type,
                  perceived_effort, pre_run_energy, sleep_hours, muscle_soreness)
    count = get_run_count(db, user.id)
    trained = False
    if count >= 20 and count % 5 == 0:
        train_model(db, user.id)
        trained = True
    return {"id": log.id, "run_count": count, "model_trained": trained}


@router.get("/runs")
async def get_runs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all logged runs for the current user."""
    runs = get_history(db, user.id)
    return {
        "runs": [
            {
                "id": r.id, "date": r.date, "distance_km": r.distance_km,
                "duration_min": r.duration_min, "rating": r.rating,
                "avg_hr": r.avg_hr, "max_hr": r.max_hr,
                "elevation_gain": r.elevation_gain, "notes": r.notes,
                "tough_reasons": r.tough_reasons, "run_type": r.run_type,
                "perceived_effort": r.perceived_effort,
                "pre_run_energy": r.pre_run_energy,
                "sleep_hours": r.sleep_hours,
                "muscle_soreness": r.muscle_soreness,
                "created_at": str(r.created_at),
            }
            for r in runs
        ],
        "count": len(runs),
    }


@router.patch("/runs/{run_id}/rate")
async def rate_run(
    run_id: int,
    rating: int = Query(...),
    tough_reasons: str = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a run's rating and optional tough reasons. Retrains ML if eligible."""
    log = update_run_rating(db, user.id, run_id, rating, tough_reasons)
    if not log:
        return JSONResponse(status_code=404, content={"detail": "Run not found"})
    count = get_run_count(db, user.id)
    trained = False
    if count >= 20 and count % 5 == 0:
        train_model(db, user.id)
        trained = True
    return {"id": log.id, "rating": log.rating, "run_count": count, "model_trained": trained}
