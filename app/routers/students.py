"""CRUD endpoints for /students."""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ErrorResponse, StudentCreate, StudentList, StudentRead, StudentUpdate
from app.services import student_service as svc

router = APIRouter(prefix="/students", tags=["Students"])
DB = Annotated[Session, Depends(get_db)]

_errors = {
    404: {"model": ErrorResponse, "description": "Student not found"},
    409: {"model": ErrorResponse, "description": "Duplicate student ID or email"},
    422: {"model": ErrorResponse, "description": "Validation error"},
}


@router.post("", response_model=StudentRead, status_code=status.HTTP_201_CREATED,
             responses={409: _errors[409], 422: _errors[422]}, summary="Create a student")
def create_student(payload: StudentCreate, db: DB):
    return svc.create_student(db, payload)


@router.get("", response_model=StudentList, summary="List, search, filter and paginate students")
def list_students(
    db: DB,
    search: Annotated[str | None, Query(max_length=100, description="Matches name, ID, email or phone")] = None,
    course: Annotated[str | None, Query(max_length=100)] = None,
    enrolled_from: date | None = None,
    enrolled_to: date | None = None,
    born_after: date | None = None,
    born_before: date | None = None,
    sort_by: Annotated[str, Query(pattern="^(student_id|full_name|email|course|enrollment_date|date_of_birth|created_at)$")] = "created_at",
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
):
    return svc.list_students(
        db, search=search, course=course, enrolled_from=enrolled_from, enrolled_to=enrolled_to,
        born_after=born_after, born_before=born_before, sort_by=sort_by, order=order,
        page=page, page_size=page_size,
    )


@router.get("/{student_id}", response_model=StudentRead, responses={404: _errors[404]}, summary="Get one student")
def get_student(student_id: str, db: DB):
    return svc.get_student(db, student_id)


@router.put("/{student_id}", response_model=StudentRead, responses=_errors, summary="Replace a student's details")
def replace_student(student_id: str, payload: StudentCreate, db: DB):
    return svc.replace_student(db, student_id, payload)


@router.patch("/{student_id}", response_model=StudentRead, responses=_errors, summary="Partially update a student")
def patch_student(student_id: str, payload: StudentUpdate, db: DB):
    return svc.patch_student(db, student_id, payload)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT,
               responses={404: _errors[404]}, summary="Delete a student")
def delete_student(student_id: str, db: DB):
    svc.delete_student(db, student_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
