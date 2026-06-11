import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
FCM_API_KEY = os.environ.get("FCM_API_KEY", "")
FCM_APP_ID = os.environ.get("FCM_APP_ID", "")
FCM_SENDER_ID = os.environ.get("FCM_SENDER_ID", "266848638326")
FCM_CREDENTIALS_PATH = os.environ.get("FCM_CREDENTIALS_PATH", "")
FCM_CREDENTIALS_JSON = os.environ.get("FCM_CREDENTIALS_JSON", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:////data/paceclimate.db")
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")

DEFAULT_LAT = 34.425
DEFAULT_LON = 8.784
DEFAULT_CITY = "Gafsa, Tunisia"
