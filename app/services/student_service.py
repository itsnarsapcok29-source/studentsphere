"""Business logic for student operations. Routers stay thin; all queries live here."""
import math
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import DuplicateStudentError, StudentNotFoundError
from app.models import Student
from app.schemas import StudentCreate, StudentUpdate

SORTABLE = {
    "student_id": Student.student_id,
    "full_name": Student.full_name,
    "email": Student.email,
    "course": Student.course,
    "enrollment_date": Student.enrollment_date,
    "date_of_birth": Student.date_of_birth,
    "created_at": Student.created_at,
}


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def get_student(db: Session, student_id: str) -> Student:
    student = db.scalar(select(Student).where(Student.student_id == student_id))
    if student is None:
        raise StudentNotFoundError(student_id)
    return student


def _assert_unique(db: Session, student_id: str | None, email: str | None, exclude_pk: int | None = None) -> None:
    """Raise DuplicateStudentError if ID or e-mail already belongs to another student."""
    checks = (("student_id", Student.student_id, student_id), ("email", func.lower(Student.email), email and email.lower()))
    for field, column, value in checks:
        if value is None:
            continue
        stmt = select(Student.id).where(column == value)
        if exclude_pk is not None:
            stmt = stmt.where(Student.id != exclude_pk)
        if db.scalar(stmt) is not None:
            raise DuplicateStudentError(field, getattr(value, "strip", lambda: value)() if field == "student_id" else value)


def _commit(db: Session, student_id: str, email: str) -> None:
    """Commit; translate DB-level uniqueness races into a 409."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        msg = str(exc.orig).lower()
        if "email" in msg:
            raise DuplicateStudentError("email", email) from exc
        raise DuplicateStudentError("student_id", student_id) from exc


def create_student(db: Session, data: StudentCreate) -> Student:
    _assert_unique(db, data.student_id, str(data.email))
    student = Student(**data.model_dump(mode="python"))
    student.email = str(data.email)
    db.add(student)
    _commit(db, data.student_id, str(data.email))
    db.refresh(student)
    return student


def replace_student(db: Session, student_id: str, data: StudentCreate) -> Student:
    student = get_student(db, student_id)
    _assert_unique(db, data.student_id, str(data.email), exclude_pk=student.id)
    for key, value in data.model_dump(mode="python").items():
        setattr(student, key, value)
    student.email = str(data.email)
    _commit(db, data.student_id, str(data.email))
    db.refresh(student)
    return student


def patch_student(db: Session, student_id: str, data: StudentUpdate) -> Student:
    student = get_student(db, student_id)
    changes = data.model_dump(exclude_unset=True, mode="python")
    _assert_unique(db, changes.get("student_id"), changes.get("email") and str(changes["email"]), exclude_pk=student.id)
    for key, value in changes.items():
        setattr(student, key, str(value) if key == "email" else value)
    _commit(db, student.student_id, student.email)
    db.refresh(student)
    return student


def delete_student(db: Session, student_id: str) -> None:
    db.delete(get_student(db, student_id))
    db.commit()


def list_students(
    db: Session,
    *,
    search: str | None = None,
    course: str | None = None,
    enrolled_from: date | None = None,
    enrolled_to: date | None = None,
    born_after: date | None = None,
    born_before: date | None = None,
    sort_by: str = "created_at",
    order: str = "desc",
    page: int = 1,
    page_size: int = 10,
) -> dict:
    """Search, filter, sort and paginate students (ORM, parameterised)."""
    stmt = select(Student)
    if search and search.strip():
        pattern = f"%{_escape_like(search.strip())}%"
        stmt = stmt.where(
            or_(
                Student.full_name.ilike(pattern, escape="\\"),
                Student.student_id.ilike(pattern, escape="\\"),
                Student.email.ilike(pattern, escape="\\"),
                Student.phone.ilike(pattern, escape="\\"),
            )
        )
    if course:
        stmt = stmt.where(func.lower(Student.course) == course.strip().lower())
    if enrolled_from:
        stmt = stmt.where(Student.enrollment_date >= enrolled_from)
    if enrolled_to:
        stmt = stmt.where(Student.enrollment_date <= enrolled_to)
    if born_after:
        stmt = stmt.where(Student.date_of_birth > born_after)
    if born_before:
        stmt = stmt.where(Student.date_of_birth < born_before)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    column = SORTABLE.get(sort_by, Student.created_at)
    ordering = column.asc() if order == "asc" else column.desc()
    stmt = stmt.order_by(ordering, Student.id.desc()).offset((page - 1) * page_size).limit(page_size)
    items = list(db.scalars(stmt))
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)),
    }


def course_counts(db: Session) -> list[dict]:
    rows = db.execute(
        select(Student.course, func.count(Student.id))
        .where(Student.course.is_not(None))
        .group_by(Student.course)
        .order_by(func.count(Student.id).desc(), Student.course)
    ).all()
    return [{"course": c, "count": n} for c, n in rows]


def month_bounds(today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    start = today.replace(day=1)
    end = date(start.year + (start.month == 12), (start.month % 12) + 1, 1)
    return start, end


def count_enrolled_this_month(db: Session) -> int:
    start, end = month_bounds()
    return db.scalar(
        select(func.count(Student.id)).where(Student.enrollment_date >= start, Student.enrollment_date < end)
    ) or 0


def dashboard_stats(db: Session) -> dict:
    courses = course_counts(db)
    recent = list(db.scalars(select(Student).order_by(Student.created_at.desc(), Student.id.desc()).limit(5)))
    return {
        "total_students": db.scalar(select(func.count(Student.id))) or 0,
        "enrolled_this_month": count_enrolled_this_month(db),
        "course_count": len(courses),
        "recent_students": recent,
        "courses": courses,
    }
