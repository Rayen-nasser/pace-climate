import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Header
from jose import JWTError, jwt
from passlib.context import CryptContext
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from sqlalchemy.orm import Session

from .database import get_db
from .models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def register_with_password(db: Session, email: str, password: str):
    email = email.strip().lower()
    existing = db.query(User).filter_by(email=email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    name = email.split("@")[0]
    user = User(email=email, username=name, password_hash=pwd_context.hash(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id), "email": user.email})
    return {"token": token, "email": user.email, "username": user.username}


def login_with_password(db: Session, email: str, password: str):
    email = email.strip().lower()
    user = db.query(User).filter_by(email=email).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not pwd_context.verify(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": str(user.id), "email": user.email})
    return {"token": token, "email": user.email, "username": user.username}


GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")


def login_with_google(db: Session, credential: str):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google auth not configured")
    try:
        info = google_id_token.verify_oauth2_token(
            credential, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Google token")

    email = info.get("email")
    name = info.get("name", email.split("@")[0] if email else "Runner")
    if not email:
        raise HTTPException(status_code=400, detail="Email not provided by Google")

    user = db.query(User).filter_by(email=email).first()
    if not user:
        user = User(email=email, username=name)
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return {"token": token, "email": user.email, "username": user.username}


async def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid auth header")
    token = parts[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter_by(id=int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user
