import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["GROQ_API_KEY"] = "test-groq-key"
os.environ["FCM_API_KEY"] = ""
os.environ["FCM_APP_ID"] = ""
os.environ["DATABASE_URL"] = "sqlite:///test_paceclimate.db"

from app.core.database import Base, engine, SessionLocal, init_db
from app.main import app


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_token(client):
    resp = client.post("/api/v1/auth/register?email=test@test.com&password=test123")
    assert resp.status_code == 200
    return resp.json()["token"]


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}
