"""Pydantic request/response schemas with validation."""
import re
from datetime import date, datetime
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-_]{1,19}$")
_PHONE_RE = re.compile(r"^\+?[0-9][0-9\s\-()]{5,17}[0-9]$")


def _blank_to_none(value):
    if isinstance(value, str) and not value.strip():
        return None
    return value.strip() if isinstance(value, str) else value


class _StudentFields(BaseModel):
    """Validators shared by create and update schemas."""

    @field_validator("student_id", "full_name", check_fields=False)
    @classmethod
    def _strip_required(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("phone", "course", "address", "enrollment_date", mode="before", check_fields=False)
    @classmethod
    def _optional_blank(cls, v):
        return _blank_to_none(v)

    @field_validator("student_id", check_fields=False)
    @classmethod
    def _check_student_id(cls, v):
        if v is not None and not _ID_RE.match(v):
            raise ValueError("Student ID must be 2-20 characters: letters, digits, '-' or '_'.")
        return v

    @field_validator("full_name", check_fields=False)
    @classmethod
    def _check_name(cls, v):
        if v is not None and len(v) < 2:
            raise ValueError("Full name must be at least 2 characters.")
        return v

    @field_validator("phone", check_fields=False)
    @classmethod
    def _check_phone(cls, v):
        if v is not None and not _PHONE_RE.match(v):
            raise ValueError("Enter a valid phone number (7-20 digits; may start with +).")
        return v

    @field_validator("date_of_birth", check_fields=False)
    @classmethod
    def _check_dob(cls, v):
        if v is None:
            return v
        if v >= date.today():
            raise ValueError("Date of birth must be in the past.")
        if v.year < 1900:
            raise ValueError("Date of birth must be after 1900.")
        return v

    @field_validator("enrollment_date", check_fields=False)
    @classmethod
    def _check_enrollment(cls, v):
        if v is not None and v.year < 1990:
            raise ValueError("Enrollment date must be 1990 or later.")
        return v


class StudentBase(_StudentFields):
    student_id: Annotated[str, Field(min_length=2, max_length=20, examples=["STU-1001"])]
    full_name: Annotated[str, Field(min_length=2, max_length=100, examples=["Aarav Sharma"])]
    date_of_birth: date = Field(examples=["2004-05-17"])
    email: EmailStr = Field(max_length=254, examples=["aarav@example.com"])
    phone: Annotated[str | None, Field(max_length=20, examples=["+91 98765 43210"])] = None
    course: Annotated[str | None, Field(max_length=100, examples=["Computer Science"])] = None
    address: Annotated[str | None, Field(max_length=500)] = None
    enrollment_date: date | None = Field(default=None, examples=["2024-08-01"])


class StudentCreate(StudentBase):
    """Body for POST /students and PUT /students/{id} (full replacement)."""


class StudentUpdate(_StudentFields):
    """Body for PATCH /students/{id}: every field optional."""

    student_id: Annotated[str | None, Field(min_length=2, max_length=20)] = None
    full_name: Annotated[str | None, Field(min_length=2, max_length=100)] = None
    date_of_birth: date | None = None
    email: EmailStr | None = Field(default=None, max_length=254)
    phone: Annotated[str | None, Field(max_length=20)] = None
    course: Annotated[str | None, Field(max_length=100)] = None
    address: Annotated[str | None, Field(max_length=500)] = None
    enrollment_date: date | None = None

    @model_validator(mode="after")
    def _required_not_null(self):
        for name in ("student_id", "full_name", "date_of_birth", "email"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null or empty.")
        return self


class StudentRead(StudentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class StudentList(BaseModel):
    items: list[StudentRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class CourseCount(BaseModel):
    course: str
    count: int


class DashboardStats(BaseModel):
    total_students: int
    enrolled_this_month: int
    course_count: int
    recent_students: list[StudentRead]
    courses: list[CourseCount]


class ErrorResponse(BaseModel):
    detail: str
    errors: list[dict] | None = None


class AIQuestion(BaseModel):
    question: Annotated[str, Field(min_length=3, max_length=300)]


class AIAnswer(BaseModel):
    answer: str
    operation: str
    data_used: list[dict] | dict | None = None
    ai_available: bool
    grounded_only: bool = True
