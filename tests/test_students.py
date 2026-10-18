"""CRUD, validation, search/filter and persistence tests."""
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.database import Base


def test_create_student(client, payload):
    r = client.post("/students", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body["student_id"] == "STU-1001"
    assert body["id"] and body["created_at"] and body["updated_at"]


def test_optional_fields_are_optional(client):
    r = client.post("/students", json={"student_id": "STU-2", "full_name": "Min Only",
                                       "date_of_birth": "2003-01-01", "email": "min@example.com"})
    assert r.status_code == 201
    assert r.json()["phone"] is None and r.json()["course"] is None


def test_blank_optional_strings_become_null(client, payload):
    r = client.post("/students", json={**payload, "phone": "", "course": "  ", "enrollment_date": ""})
    assert r.status_code == 201
    assert r.json()["phone"] is None and r.json()["course"] is None and r.json()["enrollment_date"] is None


def test_list_students(client, make_student):
    make_student()
    make_student(student_id="STU-1002", email="b@example.com")
    r = client.get("/students")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2 and len(data["items"]) == 2 and data["page"] == 1


def test_get_student(client, make_student):
    make_student()
    r = client.get("/students/STU-1001")
    assert r.status_code == 200 and r.json()["full_name"] == "Aarav Sample"


def test_put_replaces_student(client, make_student, payload):
    make_student()
    r = client.put("/students/STU-1001", json={**payload, "full_name": "Aarav Updated", "course": "Mathematics"})
    assert r.status_code == 200
    assert r.json()["full_name"] == "Aarav Updated" and r.json()["course"] == "Mathematics"


def test_patch_updates_only_given_fields(client, make_student):
    make_student()
    r = client.patch("/students/STU-1001", json={"phone": "9876543210"})
    assert r.status_code == 200
    assert r.json()["phone"] == "9876543210" and r.json()["full_name"] == "Aarav Sample"


def test_patch_can_clear_optional_field(client, make_student):
    make_student()
    r = client.patch("/students/STU-1001", json={"address": None})
    assert r.status_code == 200 and r.json()["address"] is None


def test_patch_required_field_cannot_be_null(client, make_student):
    make_student()
    assert client.patch("/students/STU-1001", json={"full_name": None}).status_code == 422


def test_delete_student(client, make_student):
    make_student()
    assert client.delete("/students/STU-1001").status_code == 204
    assert client.get("/students/STU-1001").status_code == 404


def test_missing_student_returns_404(client, payload):
    assert client.get("/students/NOPE").status_code == 404
    assert client.put("/students/NOPE", json=payload).status_code == 404
    assert client.patch("/students/NOPE", json={"phone": "1234567"}).status_code == 404
    assert client.delete("/students/NOPE").status_code == 404


def test_invalid_input_rejected(client, payload):
    bad = [
        {**payload, "email": "not-an-email"},
        {**payload, "full_name": ""},
        {**payload, "date_of_birth": "2999-01-01"},
        {**payload, "date_of_birth": "not-a-date"},
        {**payload, "phone": "abc"},
        {**payload, "student_id": "bad id!"},
        {**payload, "full_name": "x" * 101},
    ]
    for body in bad:
        r = client.post("/students", json=body)
        assert r.status_code == 422, body
        assert r.json()["errors"]


def test_missing_required_field_rejected(client, payload):
    del payload["email"]
    r = client.post("/students", json=payload)
    assert r.status_code == 422
    assert any(e["field"] == "email" for e in r.json()["errors"])


def test_duplicate_student_id_conflict(client, make_student, payload):
    make_student()
    r = client.post("/students", json={**payload, "email": "other@example.com"})
    assert r.status_code == 409
    assert "STU-1001" in r.json()["detail"]


def test_duplicate_email_conflict_case_insensitive(client, make_student, payload):
    make_student()
    r = client.post("/students", json={**payload, "student_id": "STU-9", "email": "AARAV.SAMPLE@example.com"})
    assert r.status_code == 409


def test_update_to_existing_email_conflicts_but_own_email_ok(client, make_student, payload):
    make_student()
    make_student(student_id="STU-1002", email="b@example.com")
    assert client.patch("/students/STU-1002", json={"email": payload["email"]}).status_code == 409
    assert client.put("/students/STU-1001", json=payload).status_code == 200  # unchanged email is fine


def test_search_by_name_id_email_phone(client, make_student):
    make_student()
    make_student(student_id="STU-1002", full_name="Diya Example", email="diya@example.com",
                 phone="+91 11111 22222", course="Physics")
    def names(q):
        return [s["full_name"] for s in client.get("/students", params={"search": q}).json()["items"]]
    assert names("aarav") == ["Aarav Sample"]
    assert names("STU-1002") == ["Diya Example"]
    assert names("diya@") == ["Diya Example"]
    assert names("11111") == ["Diya Example"]
    assert names("zzz") == []


def test_search_treats_wildcards_literally(client, make_student):
    make_student()
    assert client.get("/students", params={"search": "%"}).json()["total"] == 0


def test_filter_by_course_and_dates(client, make_student):
    make_student()
    make_student(student_id="STU-1002", email="b@example.com", course="Physics",
                 enrollment_date="2023-01-10", date_of_birth="2006-03-03")
    assert client.get("/students", params={"course": "physics"}).json()["total"] == 1
    assert client.get("/students", params={"enrolled_from": "2024-01-01"}).json()["total"] == 1
    assert client.get("/students", params={"born_after": "2005-12-31"}).json()["items"][0]["student_id"] == "STU-1002"


def test_pagination_and_sorting(client, make_student):
    for i in range(1, 8):
        make_student(student_id=f"STU-{i:03d}", email=f"s{i}@example.com", full_name=f"Student {i}")
    page2 = client.get("/students", params={"page": 2, "page_size": 3, "sort_by": "student_id", "order": "asc"}).json()
    assert page2["total"] == 7 and page2["total_pages"] == 3
    assert [s["student_id"] for s in page2["items"]] == ["STU-004", "STU-005", "STU-006"]
    assert client.get("/students", params={"page": 0}).status_code == 422
    assert client.get("/students", params={"sort_by": "password"}).status_code == 422


def test_dashboard_stats_from_real_data(client, make_student):
    today = date.today().isoformat()
    assert client.get("/api/stats").json()["total_students"] == 0
    make_student(enrollment_date=today)
    make_student(student_id="STU-2", email="b@example.com", course="Physics", enrollment_date="2020-01-01")
    stats = client.get("/api/stats").json()
    assert stats["total_students"] == 2 and stats["enrolled_this_month"] == 1 and stats["course_count"] == 2
    assert len(stats["recent_students"]) == 2


def test_data_persists_across_connections(db_path, session_factory, client, make_student):
    make_student()
    fresh_engine = create_engine(f"sqlite:///{db_path}")  # simulates an app restart
    with sessionmaker(bind=fresh_engine)() as db:
        rows = db.query(models.Student).all()
        assert len(rows) == 1 and rows[0].email == "aarav.sample@example.com"
    fresh_engine.dispose()


def test_health_and_docs_and_dashboard(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    r = client.get("/")
    assert r.status_code == 200 and "StudentSphere" in r.text
