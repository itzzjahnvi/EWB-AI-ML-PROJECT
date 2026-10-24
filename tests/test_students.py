import time

import pytest
from fastapi.testclient import TestClient

from app.database.connection import build_engine, make_session_factory
from app.main import create_app
from app.services import student_service
from tests.conftest import _override_db


# ---------------------------------------------------------------- system / docs
def test_root_and_health(client):
    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["status"] == "running"
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["database"] == "ok"


def test_openapi_documents_all_routes(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    assert set(paths["/students"]) == {"get", "post"}
    assert set(paths["/students/{student_id}"]) == {"get", "put", "patch", "delete"}


# ---------------------------------------------------------------------- create
def test_create_student(client, payload):
    data = payload(student_id="STU1001", name="Aarav Sharma", email="Aarav@Example.com")
    response = client.post("/students", json=data)
    assert response.status_code == 201
    body = response.json()
    assert body["student_id"] == "STU1001"
    assert body["name"] == "Aarav Sharma"
    assert body["email"] == "aarav@example.com"  # normalised to lowercase
    assert body["id"] >= 1 and body["created_at"] and body["updated_at"]
    assert body["created_at"].endswith("Z") or body["created_at"].endswith("+00:00")


def test_create_with_only_phone_or_only_email(client, payload):
    assert client.post("/students", json=payload(email=None)).status_code == 201
    assert client.post("/students", json=payload(phone=None)).status_code == 201


def test_reject_duplicate_student_id(client, create, payload):
    create(student_id="STU2000")
    response = client.post("/students", json=payload(student_id="STU2000"))
    assert response.status_code == 409
    assert "student_id" in response.json()["detail"]


def test_reject_duplicate_email_case_insensitive(client, create, payload):
    create(email="dup@example.com")
    response = client.post("/students", json=payload(email="DUP@example.com"))
    assert response.status_code == 409
    assert "email" in response.json()["detail"]


def test_multiple_students_without_email_allowed(client, payload):
    for _ in range(2):
        assert client.post("/students", json=payload(email=None)).status_code == 201


@pytest.mark.parametrize(
    "overrides, field",
    [
        ({"name": ""}, "name"),
        ({"name": "   "}, "name"),
        ({"email": "not-an-email"}, "email"),
        ({"date_of_birth": "2005-02-30"}, "date_of_birth"),
        ({"date_of_birth": "15/06/2005"}, "date_of_birth"),
        ({"date_of_birth": 1118793600}, "date_of_birth"),
        ({"date_of_birth": "2999-01-01"}, "date_of_birth"),
        ({"date_of_birth": "1800-01-01"}, "date_of_birth"),
        ({"phone": "abc123"}, "phone"),
        ({"phone": "123"}, "phone"),
        ({"student_id": "a b"}, "student_id"),
        ({"student_id": "X"}, "student_id"),
        ({"enrollment_date": "2000-01-01"}, "body"),  # before date of birth
        ({"unknown_field": "x"}, "unknown_field"),
        ({"student_id": ...}, "student_id"),
        ({"name": ...}, "name"),
        ({"date_of_birth": ...}, "date_of_birth"),
    ],
)
def test_reject_invalid_input(client, payload, overrides, field):
    response = client.post("/students", json=payload(**overrides))
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["detail"] == "Validation failed"
    assert field in [e["field"] for e in body["errors"]]


def test_reject_missing_email_and_phone(client, payload):
    response = client.post("/students", json=payload(email=None, phone=None))
    assert response.status_code == 422
    assert "contact method" in response.json()["errors"][0]["message"]


def test_blank_email_and_phone_count_as_missing(client, payload):
    response = client.post("/students", json=payload(email="  ", phone=""))
    assert response.status_code == 422


def test_malformed_json(client):
    response = client.post("/students", content="{bad json", headers={"Content-Type": "application/json"})
    assert response.status_code == 400
    assert "Malformed JSON" in response.json()["detail"]


def test_sql_injection_text_is_stored_literally(client, create):
    created = create(name="Robert'); DROP TABLE students;--")
    assert client.get(f"/students/{created['student_id']}").json()["name"].startswith("Robert'")
    assert len(client.get("/students").json()) == 1


# ------------------------------------------------------------------------ read
def test_list_students_empty(client):
    response = client.get("/students")
    assert response.status_code == 200
    assert response.json() == []


def test_list_all_students(client, create):
    for _ in range(3):
        create()
    assert len(client.get("/students").json()) == 3


def test_get_student_by_student_id(client, create):
    created = create(student_id="STU3001", name="Find Me")
    response = client.get("/students/STU3001")
    assert response.status_code == 200
    assert response.json() == created


def test_get_nonexistent_student(client):
    response = client.get("/students/NOPE999")
    assert response.status_code == 404
    assert "NOPE999" in response.json()["detail"]


@pytest.fixture()
def sample(create):
    create(student_id="STU4001", name="Aarav Sharma", course="Computer Science", date_of_birth="2004-03-10")
    create(student_id="STU4002", name="Aarav Mehta", course="Data Science", date_of_birth="2005-06-15")
    create(student_id="STU4003", name="Diya Patel", course="Computer Science", date_of_birth="2006-01-20")
    create(student_id="STU4004", name="Kabir 100%_Real", course="Electronics", date_of_birth="2003-12-31")


def ids(response):
    assert response.status_code == 200, response.text
    return [s["student_id"] for s in response.json()]


def test_filter_by_name_partial_case_insensitive(client, sample):
    assert ids(client.get("/students", params={"name": "aarav"})) == ["STU4001", "STU4002"]


def test_name_filter_treats_wildcards_literally(client, sample):
    assert ids(client.get("/students", params={"name": "%"})) == ["STU4004"]
    assert ids(client.get("/students", params={"name": "_"})) == ["STU4004"]


def test_filter_by_course(client, sample):
    assert ids(client.get("/students", params={"course": "computer science"})) == ["STU4001", "STU4003"]


def test_filter_by_student_id(client, sample):
    assert ids(client.get("/students", params={"student_id": "stu4003"})) == ["STU4003"]


def test_filter_by_dob(client, sample):
    assert ids(client.get("/students", params={"dob_after": "2005-01-01"})) == ["STU4002", "STU4003"]
    assert ids(client.get("/students", params={"dob_before": "2004-03-10"})) == ["STU4004"]  # strict
    both = client.get("/students", params={"dob_after": "2003-12-31", "dob_before": "2006-01-20"})
    assert ids(both) == ["STU4001", "STU4002"]


def test_combined_filters(client, sample):
    response = client.get("/students", params={"name": "aarav", "course": "Computer Science"})
    assert ids(response) == ["STU4001"]
    response = client.get("/students", params={"course": "Computer Science", "dob_after": "2005-01-01"})
    assert ids(response) == ["STU4003"]


def test_filter_no_match_returns_empty_list(client, sample):
    response = client.get("/students", params={"course": "Astrology"})
    assert response.status_code == 200 and response.json() == []


def test_pagination(client, sample):
    assert ids(client.get("/students", params={"limit": 2})) == ["STU4001", "STU4002"]
    assert ids(client.get("/students", params={"skip": 2, "limit": 2})) == ["STU4003", "STU4004"]
    assert ids(client.get("/students", params={"skip": 10})) == []


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 101}, {"skip": -1}, {"limit": "abc"}, {"dob_after": "yesterday"}],
)
def test_invalid_query_parameters(client, params):
    assert client.get("/students", params=params).status_code == 422


# ---------------------------------------------------------------------- update
def test_put_replaces_full_record(client, create, payload):
    create(student_id="STU5001")
    new = payload(name="Replaced", email="new@example.com", course="Mathematics")
    new.pop("student_id")
    response = client.put("/students/STU5001", json=new)
    assert response.status_code == 200
    body = response.json()
    assert body["student_id"] == "STU5001"
    assert (body["name"], body["email"], body["course"]) == ("Replaced", "new@example.com", "Mathematics")


def test_put_clears_omitted_optional_fields(client, create):
    create(student_id="STU5002")
    minimal = {"name": "Only Required", "date_of_birth": "2005-01-01", "phone": "9876543210"}
    body = client.put("/students/STU5002", json=minimal).json()
    assert body["email"] is None and body["course"] is None and body["address"] is None


def test_put_can_rename_student_id(client, create, payload):
    create(student_id="STU5003")
    response = client.put("/students/STU5003", json=payload(student_id="STU5999", email="r@example.com"))
    assert response.status_code == 200 and response.json()["student_id"] == "STU5999"
    assert client.get("/students/STU5003").status_code == 404


def test_put_validation_error(client, create, payload):
    create(student_id="STU5004")
    bad = payload(email=None, phone=None)
    assert client.put("/students/STU5004", json=bad).status_code == 422


def test_patch_updates_selected_fields_and_preserves_rest(client, create):
    original = create(student_id="STU6001")
    response = client.patch("/students/STU6001", json={"course": "Data Science"})
    assert response.status_code == 200
    body = response.json()
    assert body["course"] == "Data Science"
    for field in ("name", "email", "phone", "address", "date_of_birth", "enrollment_date", "created_at"):
        assert body[field] == original[field], field


def test_patch_updates_updated_at(client, create):
    original = create(student_id="STU6002")
    time.sleep(0.02)
    body = client.patch("/students/STU6002", json={"address": "Mysuru"}).json()
    assert body["updated_at"] > original["updated_at"]
    assert body["created_at"] == original["created_at"]


def test_patch_can_clear_optional_field_when_contact_remains(client, create):
    create(student_id="STU6003")
    response = client.patch("/students/STU6003", json={"email": None})
    assert response.status_code == 200 and response.json()["email"] is None


def test_patch_cannot_remove_last_contact_method(client, create):
    create(student_id="STU6004", email=None)
    assert client.patch("/students/STU6004", json={"phone": None}).status_code == 422
    assert client.get("/students/STU6004").json()["phone"] == "9876543210"  # unchanged


@pytest.mark.parametrize(
    "body", [{}, {"name": None}, {"student_id": None}, {"date_of_birth": None},
             {"email": "bad"}, {"nonsense": 1}, {"enrollment_date": "1990-01-01"}],
)
def test_patch_invalid_payloads(client, create, body):
    create(student_id="STU6005")
    assert client.patch("/students/STU6005", json=body).status_code == 422


def test_patch_duplicate_student_id_and_email(client, create):
    create(student_id="STU6101", email="one@example.com")
    create(student_id="STU6102", email="two@example.com")
    dup_id = client.patch("/students/STU6102", json={"student_id": "STU6101"})
    assert dup_id.status_code == 409
    dup_email = client.patch("/students/STU6102", json={"email": "ONE@example.com"})
    assert dup_email.status_code == 409
    assert client.get("/students/STU6102").json()["email"] == "two@example.com"


def test_patch_to_own_values_is_not_a_conflict(client, create):
    create(student_id="STU6103", email="same@example.com")
    response = client.patch("/students/STU6103", json={"student_id": "STU6103", "email": "same@example.com"})
    assert response.status_code == 200


def test_put_duplicate_email(client, create, payload):
    create(student_id="STU6201", email="a@example.com")
    create(student_id="STU6202", email="b@example.com")
    body = payload(email="a@example.com")
    body.pop("student_id")
    assert client.put("/students/STU6202", json=body).status_code == 409


def test_update_nonexistent_student(client, payload):
    assert client.patch("/students/GHOST1", json={"course": "X"}).status_code == 404
    assert client.put("/students/GHOST1", json=payload()).status_code == 404


# ---------------------------------------------------------------------- delete
def test_delete_student(client, create):
    create(student_id="STU7001")
    response = client.delete("/students/STU7001")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get("/students/STU7001").status_code == 404
    assert client.get("/students").json() == []


def test_delete_nonexistent_student(client):
    response = client.delete("/students/GHOST2")
    assert response.status_code == 404
    assert "GHOST2" in response.json()["detail"]


def test_delete_twice_second_is_404(client, create):
    create(student_id="STU7002")
    assert client.delete("/students/STU7002").status_code == 204
    assert client.delete("/students/STU7002").status_code == 404


# ----------------------------------------------------------------- persistence
def test_records_visible_from_a_new_database_session(client, create, session_factory):
    create(student_id="STU8001", name="Persistent Student")
    with session_factory() as new_session:
        student = student_service.get_student(new_session, "STU8001")
        assert student.name == "Persistent Student"
        assert student.created_at.tzinfo is not None


def test_records_survive_application_restart(client, create, db_url):
    create(student_id="STU8002", name="Survivor")
    # Simulate a restart: brand-new engine, session factory and FastAPI app on the same file.
    new_engine = build_engine(db_url)
    try:
        restarted = create_app()
        _override_db(restarted, make_session_factory(new_engine))
        response = TestClient(restarted).get("/students/STU8002")
        assert response.status_code == 200 and response.json()["name"] == "Survivor"
    finally:
        new_engine.dispose()


def test_database_enforces_contact_rule_independently_of_api(session_factory):
    from sqlalchemy.exc import IntegrityError

    from app.database.models import Student
    from datetime import date

    with session_factory() as db:
        db.add(Student(student_id="RAW001", name="No Contact", date_of_birth=date(2000, 1, 1)))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_tests_do_not_use_the_developer_database(engine):
    assert "students_test" in str(engine.url) or "test_students" in str(engine.url)
    assert "data/students.db" not in str(engine.url)
