import pytest
from rest_framework.test import APIClient


@pytest.fixture
def client() -> APIClient:
    return APIClient()


def authenticate(client: APIClient, username: str = "student") -> None:
    response = client.post(
        "/api/v1/auth/register",
        {"username": username, "password": "safe-pass-230"},
        format="json",
    )
    assert response.status_code == 201
    client.credentials(HTTP_AUTHORIZATION=f"Token {response.json()['token']}")


@pytest.mark.django_db
def test_public_question_does_not_leak_solution(client: APIClient) -> None:
    response = client.get("/api/v1/questions/mb230-q0001")
    assert response.status_code == 200
    payload = response.json()
    assert payload["pdf_order"] == 1
    assert "source_answer" not in payload
    assert "explanation_raw" not in payload
    assert "community_discussion_raw" not in payload
    assert "community_comments" not in payload


@pytest.mark.django_db
def test_questions_are_returned_and_filtered_in_pdf_order(client: APIClient) -> None:
    response = client.get(
        "/api/v1/exams/mb-230/questions",
        {"limit": 5, "question_type": "yes_no"},
        HTTP_ORIGIN="http://localhost:4200",
    )
    assert response.status_code == 200
    payload = response.json()
    assert [item["pdf_order"] for item in payload["data"]] == [1, 2, 3, 4, 5]
    assert payload["next_after_order"] == 5
    assert response["Access-Control-Allow-Origin"] == "http://localhost:4200"


@pytest.mark.django_db(transaction=True)
def test_sequential_practice_reveals_feedback_after_answer(client: APIClient) -> None:
    authenticate(client)
    created = client.post(
        "/api/v1/practice-sessions",
        {"exam_slug": "mb-230", "from_order": 1, "to_order": 2},
        format="json",
    )
    assert created.status_code == 201
    session_id = created.json()["id"]

    first = client.get(f"/api/v1/practice-sessions/{session_id}/next")
    assert first.status_code == 200
    assert first.json()["id"] == "mb230-q0001"

    request_payload = {
        "question_id": "mb230-q0001",
        "response": {"choice_keys": ["B"]},
    }
    answered = client.post(
        f"/api/v1/practice-sessions/{session_id}/answers",
        request_payload,
        format="json",
        HTTP_IDEMPOTENCY_KEY="test-q1",
    )
    assert answered.status_code == 200
    feedback = answered.json()
    assert feedback["is_correct"] is True
    assert feedback["source_answer"]["option_keys"] == ["B"]
    assert feedback["explanation_raw"]
    assert feedback["community_discussion_raw"]

    retried = client.post(
        f"/api/v1/practice-sessions/{session_id}/answers",
        request_payload,
        format="json",
        HTTP_IDEMPOTENCY_KEY="test-q1",
    )
    assert retried.status_code == 200
    assert retried.json()["question_id"] == "mb230-q0001"

    second = client.get(f"/api/v1/practice-sessions/{session_id}/next")
    assert second.status_code == 200
    assert second.json()["id"] == "mb230-q0002"


@pytest.mark.django_db
def test_account_preferences_and_session_resume_are_private(client: APIClient) -> None:
    authenticate(client, "joaquin")
    preferences = client.patch(
        "/api/v1/me/preferences",
        {"theme": "dark", "default_session_size": 463},
        format="json",
    )
    assert preferences.status_code == 200
    assert preferences.json()["theme"] == "dark"

    created = client.post(
        "/api/v1/practice-sessions",
        {"exam_slug": "mb-230", "from_order": 1, "to_order": 463},
        format="json",
    )
    assert created.status_code == 201
    assert created.json()["total_items"] == 463

    sessions = client.get("/api/v1/practice-sessions")
    assert sessions.status_code == 200
    assert sessions.json()[0]["id"] == created.json()["id"]

    other = APIClient()
    authenticate(other, "other-student")
    hidden = other.get(f"/api/v1/practice-sessions/{created.json()['id']}")
    assert hidden.status_code == 404


@pytest.mark.django_db
def test_practice_requires_login(client: APIClient) -> None:
    response = client.post(
        "/api/v1/practice-sessions",
        {"exam_slug": "mb-230", "from_order": 1, "to_order": 10},
        format="json",
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_visual_question_has_public_question_asset(client: APIClient) -> None:
    response = client.get("/api/v1/questions/mb230-q0010")
    assert response.status_code == 200
    assert response.json()["question_media"]


@pytest.mark.django_db
def test_openapi_and_ready_health(client: APIClient) -> None:
    ready = client.get("/health/ready")
    schema = client.get("/api/schema/")
    assert ready.status_code == 200
    assert ready.json()["question_count"] == 463
    assert schema.status_code == 200
