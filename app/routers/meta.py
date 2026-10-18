"""Dashboard statistics, course list and the optional AI assistant."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.schemas import AIAnswer, AIQuestion, CourseCount, DashboardStats
from app.services import ai_service
from app.services import student_service as svc

router = APIRouter(prefix="/api", tags=["Dashboard & AI"])
DB = Annotated[Session, Depends(get_db)]


@router.get("/stats", response_model=DashboardStats, summary="Dashboard statistics from real records")
def stats(db: DB):
    return svc.dashboard_stats(db)


@router.get("/courses", response_model=list[CourseCount], summary="Courses with student counts")
def courses(db: DB):
    return svc.course_counts(db)


@router.get("/ai/status", summary="Is the AI assistant enabled?")
def ai_status():
    s = get_settings()
    return {"enabled": s.enable_ai, "model": s.ollama_model, "examples": ai_service.SUPPORTED_QUESTIONS}


@router.post("/ai/ask", response_model=AIAnswer, summary="Ask a question about the student data (read-only)")
def ask(payload: AIQuestion, db: DB):
    if not get_settings().enable_ai:
        raise HTTPException(status_code=503, detail="The AI assistant is disabled (ENABLE_AI=false).")
    return ai_service.answer_question(db, payload.question)
