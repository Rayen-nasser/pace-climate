from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...services.auth import get_current_user
from ...models import User
from ...services.trainer import _get_user_averages

router = APIRouter(tags=["averages"])


@router.get("/averages")
async def averages(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get the user's average run stats (distance, duration, pace)."""
    return _get_user_averages(db, user.id)
