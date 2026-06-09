from sqlalchemy import Column, Integer, Float, String, Text, DateTime, ForeignKey, PickleType
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String)
    password_hash = Column(String, nullable=True)
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
    avg_hr = Column(Integer, nullable=True)
    max_hr = Column(Integer, nullable=True)
    elevation_gain = Column(Float, nullable=True)
    weather_snapshot = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    tough_reasons = Column(Text, nullable=True)
    run_type = Column(String, nullable=True)
    perceived_effort = Column(Integer, nullable=True)
    pre_run_energy = Column(Integer, nullable=True)
    sleep_hours = Column(Float, nullable=True)
    muscle_soreness = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="run_logs")


class MlModel(Base):
    __tablename__ = "ml_models"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    model_blob = Column(PickleType, nullable=True)
    trained_at = Column(DateTime, nullable=True)
    run_count = Column(Integer, default=0)


class UserGoal(Base):
    __tablename__ = "user_goals"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    weekly_distance_km = Column(Float, default=0)
    weekly_runs = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User")


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    token = Column(String, unique=True)
    platform = Column(String, default="web")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ScheduledNotification(Base):
    __tablename__ = "scheduled_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    date = Column(String, index=True)
    title = Column(String)
    body = Column(String)
    sent = Column(Integer, default=0)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
