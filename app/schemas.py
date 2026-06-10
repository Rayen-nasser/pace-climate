from pydantic import BaseModel, Field
from typing import Optional


class TokenResponse(BaseModel):
    token: str
    email: str
    username: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str


class RunCreate(BaseModel):
    date: str = Field(..., description="Run date (YYYY-MM-DD)")
    distance_km: float = Field(..., gt=0)
    duration_min: int = Field(..., gt=0)
    rating: int = Field(..., ge=1, le=5)
    notes: Optional[str] = None
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None
    elevation_gain: Optional[float] = None
    tough_reasons: Optional[str] = None
    run_type: Optional[str] = None
    perceived_effort: Optional[int] = Field(None, ge=1, le=10)
    pre_run_energy: Optional[int] = Field(None, ge=1, le=5)
    sleep_hours: Optional[float] = Field(None, ge=0, le=24)
    muscle_soreness: Optional[int] = Field(None, ge=1, le=5)
    lat: float = 34.425
    lon: float = 8.784


class RunResponse(BaseModel):
    id: int
    date: str
    distance_km: float
    duration_min: int
    rating: int
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None
    elevation_gain: Optional[float] = None
    notes: Optional[str] = None
    tough_reasons: Optional[str] = None
    run_type: Optional[str] = None
    perceived_effort: Optional[int] = None
    pre_run_energy: Optional[int] = None
    sleep_hours: Optional[float] = None
    muscle_soreness: Optional[int] = None
    created_at: Optional[str] = None


class RunRateRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    tough_reasons: Optional[str] = None


class RunCreateResponse(BaseModel):
    id: int
    run_count: int
    model_trained: bool = False


class RunRateResponse(BaseModel):
    id: int
    rating: int
    run_count: int
    model_trained: bool = False


class ForecastDay(BaseModel):
    date: str
    temp_max: float
    temp_min: float
    temp_used: float
    precip_sum: float
    precip_prob: int
    wind_max: float
    weather_code: int
    weather_desc: str
    aqi: Optional[int] = None
    uv_index: Optional[float] = None
    dew_point: Optional[float] = None
    score: int
    label: str
    explanation: str


class ForecastResponse(BaseModel):
    location: dict
    time_pref: str
    days: list[ForecastDay]
    run_count: int


class GoalRequest(BaseModel):
    weekly_distance_km: float = 0
    weekly_runs: int = 0


class GoalResponse(BaseModel):
    weekly_distance_km: float
    weekly_runs: int


class WellnessResponse(BaseModel):
    status: str
    reason: str


class StatsResponse(BaseModel):
    run_count: int
    min_runs: int = 20
    ready_for_ml: bool = False
    week_km: float = 0
    week_runs: int = 0
    month_km: float = 0
    month_runs: int = 0
    goal_week_km: float = 0
    goal_week_runs: int = 0


class DeviceRegisterRequest(BaseModel):
    token: str
    platform: str = "web"


class NotificationScheduleRequest(BaseModel):
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    time: str = "17:00"
    title: str
    body: str


class NotificationResponse(BaseModel):
    id: int
    date: str
    time: Optional[str] = None
    title: str
    body: Optional[str] = None


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]


class AveragesResponse(BaseModel):
    distance_km: float = 0
    duration_min: int = 0
    pace: float = 0


class ChatResponse(BaseModel):
    answer: str
