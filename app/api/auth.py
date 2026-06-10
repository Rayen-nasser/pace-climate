from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import register_with_password, login_with_password, login_with_google, get_current_user
from ..models import User

router = APIRouter(tags=["auth"])


@router.post("/auth/register")
async def register(email: str = Query(...), password: str = Query(...), db: Session = Depends(get_db)):
    """Register a new user with email and password."""
    return register_with_password(db, email, password)


@router.post("/auth/login")
async def login(email: str = Query(...), password: str = Query(...), db: Session = Depends(get_db)):
    """Login with email and password, returns JWT token."""
    return login_with_password(db, email, password)


@router.post("/auth/google")
async def google_login(credential: str = Query(...), db: Session = Depends(get_db)):
    """Login or register with Google credential token."""
    return login_with_google(db, credential)


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    """Get current authenticated user's info."""
    return {"id": user.id, "email": user.email, "username": user.username}
