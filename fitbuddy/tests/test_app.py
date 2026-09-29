import json

from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


client = TestClient(app)


def test_home_page():
    response = client.get("/")

    assert response.status_code == 200
    assert "FitBuddy" in response.text
    assert "Generate My Plan" in response.text


def test_health():
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"


def test_generate_workout_api():
    response = client.post(
        "/api/generate-workout",
        json={
            "user_id": "test-user",
            "name": "Alex",
            "age": 25,
            "weight": 70,
            "goal": "muscle gain",
            "intensity": "medium",
            "experience_level": "beginner",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["user"]["user_id"] == "test-user"
    assert len(data["workout_plan"]["days"]) == 7


def test_feedback_update():
    response = client.post(
        "/api/submit-feedback",
        json={
            "user_id": "test-user",
            "feedback": "Add more cardio and include another rest day.",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True

    assert (
        data["updated_plan"]["feedback_applied"]
        == "Add more cardio and include another rest day."
    )