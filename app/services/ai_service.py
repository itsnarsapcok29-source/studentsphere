"""Optional local AI assistant (Ollama).

Safety design:
* The model NEVER sees the database or writes SQL.
* A deterministic intent router maps the question to an ALLOWLISTED operation.
* Backend code runs that operation with the ORM and computes all numbers.
* The model only rephrases the retrieved facts. If Ollama is down, the
  deterministic answer is still returned and ``ai_available`` is False.
"""
import json
import re
from datetime import date
from urllib import error, request

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Student
from app.services import student_service as svc

SUPPORTED_QUESTIONS = [
    "How many students are registered?",
    "List students born after 2005",
    "How many students are enrolled in each course?",
    "Show students enrolled this month",
    "Summarize the distribution of students by course",
]
MAX_ROWS = 25


def _brief(s: Student) -> dict:
    return {
        "student_id": s.student_id,
        "name": s.full_name,
        "course": s.course,
        "date_of_birth": s.date_of_birth.isoformat(),
        "enrollment_date": s.enrollment_date.isoformat() if s.enrollment_date else None,
    }


def classify(question: str) -> tuple[str, dict]:
    """Map free text to an allowlisted operation name + parameters."""
    q = question.lower()
    year = re.search(r"\b(19\d{2}|20\d{2})\b", q)
    if "born" in q and year and ("after" in q or "since" in q or "later" in q):
        return "born_after", {"year": int(year.group(1))}
    if "born" in q and year and ("before" in q or "earlier" in q):
        return "born_before", {"year": int(year.group(1))}
    if "this month" in q and ("enrol" in q or "join" in q or "admit" in q):
        return "enrolled_this_month", {}
    if "each course" in q or "per course" in q or "by course" in q or "distribution" in q or "summar" in q:
        return "course_distribution", {}
    if re.search(r"how many|count|total|number of", q):
        return "total_students", {}
    return "unsupported", {}


def run_operation(db: Session, op: str, params: dict) -> tuple[str, list[dict] | dict]:
    """Execute an allowlisted operation; returns (deterministic answer, data)."""
    if op == "total_students":
        n = db.scalar(select(func.count(Student.id))) or 0
        return f"There {'is' if n == 1 else 'are'} {n} registered student{'s' if n != 1 else ''}.", {"total": n}
    if op in ("born_after", "born_before"):
        year = params["year"]
        if op == "born_after":
            cond, word = Student.date_of_birth > date(year, 12, 31), "after"
        else:
            cond, word = Student.date_of_birth < date(year, 1, 1), "before"
        rows = list(db.scalars(select(Student).where(cond).order_by(Student.date_of_birth)))
        data = [_brief(s) for s in rows[:MAX_ROWS]]
        if not rows:
            return f"No students were born {word} {year}.", []
        names = ", ".join(f"{s.full_name} ({s.date_of_birth.year})" for s in rows[:MAX_ROWS])
        extra = f" (showing first {MAX_ROWS})" if len(rows) > MAX_ROWS else ""
        return f"{len(rows)} student(s) born {word} {year}{extra}: {names}.", data
    if op == "enrolled_this_month":
        start, end = svc.month_bounds()
        rows = list(db.scalars(select(Student).where(Student.enrollment_date >= start, Student.enrollment_date < end)))
        if not rows:
            return "No students are enrolled this month.", []
        names = ", ".join(s.full_name for s in rows[:MAX_ROWS])
        return f"{len(rows)} student(s) enrolled this month: {names}.", [_brief(s) for s in rows[:MAX_ROWS]]
    if op == "course_distribution":
        counts = svc.course_counts(db)
        if not counts:
            return "No students have a course assigned yet.", []
        total = sum(c["count"] for c in counts)
        parts = "; ".join(f"{c['course']}: {c['count']} ({c['count'] * 100 // total}%)" for c in counts)
        return f"Students by course ({total} with a course): {parts}.", counts
    return ("I can only answer questions about the student database. Try: " + " | ".join(SUPPORTED_QUESTIONS)), []


def ask_ollama(question: str, facts: str, data) -> str | None:
    """Ask the local model to phrase the verified facts. Returns None if unavailable."""
    s = get_settings()
    prompt = (
        "You are a careful assistant for a student database. Answer the question using ONLY the "
        "verified facts below. Do not add numbers, names or details that are not present. "
        "Reply in 1-3 plain sentences.\n\n"
        f"Question: {question}\nVerified facts: {facts}\nRecords: {json.dumps(data, default=str)[:4000]}\n"
    )
    body = json.dumps({"model": s.ollama_model, "prompt": prompt, "stream": False, "options": {"temperature": 0}}).encode()
    req = request.Request(f"{s.ollama_url.rstrip('/')}/api/generate", data=body, headers={"Content-Type": "application/json"})
    try:
        with request.urlopen(req, timeout=s.ollama_timeout_seconds) as resp:  # noqa: S310 (configured local URL)
            text = json.loads(resp.read().decode()).get("response", "").strip()
            return text or None
    except (error.URLError, TimeoutError, OSError, ValueError):
        return None


def answer_question(db: Session, question: str) -> dict:
    op, params = classify(question)
    facts, data = run_operation(db, op, params)
    if op == "unsupported":
        return {"answer": facts, "operation": op, "data_used": None, "ai_available": True}
    narrated = ask_ollama(question, facts, data)
    if narrated is None:
        return {
            "answer": facts + "\n\n(Local AI model is unavailable, so this is the direct database result.)",
            "operation": op,
            "data_used": data,
            "ai_available": False,
        }
    return {"answer": narrated, "operation": op, "data_used": data, "ai_available": True}
