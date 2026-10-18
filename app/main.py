"""StudentSphere application entry point."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import __version__
from app.config import get_settings
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db, init_db
from app.exceptions import register_exception_handlers
from app.routers import meta, students

APP_DIR = Path(__file__).resolve().parent
settings = get_settings()
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()  # create tables automatically on start-up
    yield


app = FastAPI(
    title="StudentSphere API",
    description="Student Database Management System - FastAPI + SQLite. EWB Edu Tech internship project by Narendra Vishnoi.",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)
register_exception_handlers(app)
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")
app.include_router(students.router)
app.include_router(meta.router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard(request: Request):
    return templates.TemplateResponse(
        request, "index.html", {"app_name": settings.app_name, "ai_enabled": settings.enable_ai, "version": __version__}
    )


@app.get("/health", tags=["System"], summary="Health check")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected", "version": __version__}
