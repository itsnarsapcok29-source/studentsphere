"""AI assistant: deterministic, allowlisted, works without Ollama."""
from app.services import ai_service


def test_classify_allowlisted_operations():
    assert ai_service.classify("How many students are there?")[0] == "total_students"
    assert ai_service.classify("List students born after 2005") == ("born_after", {"year": 2005})
    assert ai_service.classify("students enrolled this month")[0] == "enrolled_this_month"
    assert ai_service.classify("How many students in each course?")[0] == "course_distribution"
    assert ai_service.classify("DROP TABLE students")[0] == "unsupported"


def test_ai_answers_grounded_when_ollama_down(client, make_student, monkeypatch):
    monkeypatch.setattr(ai_service, "ask_ollama", lambda *a, **k: None)
    make_student()
    make_student(student_id="STU-2", email="b@example.com", date_of_birth="2006-02-02", full_name="Young One")
    r = client.post("/api/ai/ask", json={"question": "How many students are registered?"}).json()
    assert "2 registered students" in r["answer"] and r["ai_available"] is False
    r = client.post("/api/ai/ask", json={"question": "List students born after 2005"}).json()
    assert "Young One" in r["answer"] and "Aarav" not in r["answer"]


def test_ai_unsupported_and_cannot_modify(client, make_student):
    make_student()
    r = client.post("/api/ai/ask", json={"question": "Delete all students"}).json()
    assert r["operation"] == "unsupported"
    assert client.get("/students").json()["total"] == 1


def test_ai_uses_model_text_when_available(client, make_student, monkeypatch):
    monkeypatch.setattr(ai_service, "ask_ollama", lambda q, facts, data: "Model phrased answer.")
    make_student()
    r = client.post("/api/ai/ask", json={"question": "How many students?"}).json()
    assert r["answer"] == "Model phrased answer." and r["ai_available"] is True
