"""Custom exceptions and global exception handlers."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("studentsphere")


class StudentNotFoundError(Exception):
    def __init__(self, student_id: str):
        self.student_id = student_id
        super().__init__(f"Student '{student_id}' was not found.")


class DuplicateStudentError(Exception):
    def __init__(self, field: str, value: str):
        self.field = field
        self.value = value
        label = "Student ID" if field == "student_id" else "Email address"
        super().__init__(f"{label} '{value}' is already registered.")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StudentNotFoundError)
    async def _not_found(_: Request, exc: StudentNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(DuplicateStudentError)
    async def _conflict(_: Request, exc: DuplicateStudentError):
        return JSONResponse(
            status_code=409,
            content={"detail": str(exc), "errors": [{"field": exc.field, "message": str(exc)}]},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        errors = []
        for err in exc.errors():
            loc = [str(p) for p in err["loc"] if p not in ("body", "query", "path")]
            msg = str(err["msg"]).removeprefix("Value error, ")
            errors.append({"field": ".".join(loc) or "request", "message": msg})
        return JSONResponse(
            status_code=422, content={"detail": "Validation failed.", "errors": errors}
        )

    @app.exception_handler(SQLAlchemyError)
    async def _db_error(_: Request, exc: SQLAlchemyError):
        logger.exception("Database error: %s", exc)
        return JSONResponse(status_code=500, content={"detail": "A database error occurred. Please try again."})

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception):
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(status_code=500, content={"detail": "An unexpected server error occurred."})
