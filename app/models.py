from sqlalchemy import Column, Integer, Float, String, Text, DateTime, ForeignKey, PickleType
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    preferences = relationship("UserPreference", uselist=False, back_populates="user")
    run_logs = relationship("RunLog", back_populates="user")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    lat = Column(Float, default=34.425)
    lon = Column(Float, default=8.784)
    time_pref = Column(String, default="evening")
    temp_min = Column(Integer, nullable=True)
    temp_max = Column(Integer, nullable=True)

    user = relationship("User", back_populates="preferences")


class RunLog(Base):
    __tablename__ = "run_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    date = Column(String)
    distance_km = Column(Float)
    duration_min = Column(Integer)
    rating = Column(Integer)
    weather_snapshot = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="run_logs")


class MlModel(Base):
    __tablename__ = "ml_models"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    model_blob = Column(PickleType, nullable=True)
    trained_at = Column(DateTime, nullable=True)
    run_count = Column(Integer, default=0)
