"""Business logic and database access for students.

All database access (including the optional AI assistant) goes through this module.
Queries use the SQLAlchemy ORM only, so user input is always bound as parameters.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.models import Student, utcnow
from app.schemas.student import StudentCreate, StudentPatch, StudentReplace

_FIELDS = (
    "student_id", "name", "date_of_birth", "email",
    "phone", "course", "address", "enrollment_date",
)


class StudentNotFoundError(Exception):
    def __init__(self, student_id: str):
        self.student_id = student_id
        super().__init__(f"Student with student_id '{student_id}' not found")


class DuplicateStudentError(Exception):
    def __init__(self, field: str):
        self.field = field
        label = "student_id" if field == "student_id" else "email address"
        super().__init__(f"A student with this {label} already exists")


class StudentConstraintError(Exception):
    """A database constraint was violated that we could not map to a friendlier error."""


@dataclass
class StudentFilters:
    name: str | None = None          # case-insensitive "contains"
    course: str | None = None        # case-insensitive exact match
    student_id: str | None = None    # case-insensitive exact match
    dob_after: date | None = None    # strictly after
    dob_before: date | None = None   # strictly before


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _apply_filters(stmt, filters: StudentFilters):
    if filters.name:
        stmt = stmt.where(Student.name.ilike(f"%{_escape_like(filters.name)}%", escape="\\"))
    if filters.course:
        stmt = stmt.where(func.lower(Student.course) == filters.course.lower())
    if filters.student_id:
        stmt = stmt.where(func.lower(Student.student_id) == filters.student_id.lower())
    if filters.dob_after:
        stmt = stmt.where(Student.date_of_birth > filters.dob_after)
    if filters.dob_before:
        stmt = stmt.where(Student.date_of_birth < filters.dob_before)
    return stmt


def _translate_integrity_error(exc: IntegrityError) -> Exception:
    message = str(exc.orig).lower()
    if "students.student_id" in message:
        return DuplicateStudentError("student_id")
    if "students.email" in message:
        return DuplicateStudentError("email")
    return StudentConstraintError("The request conflicts with a database constraint")


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:  # e.g. a concurrent insert beat our pre-check
        db.rollback()
        raise _translate_integrity_error(exc) from None
    except Exception:
        db.rollback()
        raise


def _ensure_unique(db: Session, *, student_id: str | None, email: str | None,
                   exclude_pk: int | None = None) -> None:
    if student_id:
        stmt = select(Student.id).where(Student.student_id == student_id)
        if exclude_pk is not None:
            stmt = stmt.where(Student.id != exclude_pk)
        if db.scalar(stmt.limit(1)) is not None:
            raise DuplicateStudentError("student_id")
    if email:
        stmt = select(Student.id).where(func.lower(Student.email) == email.lower())
        if exclude_pk is not None:
            stmt = stmt.where(Student.id != exclude_pk)
        if db.scalar(stmt.limit(1)) is not None:
            raise DuplicateStudentError("email")


def get_student(db: Session, student_id: str) -> Student:
    student = db.scalar(select(Student).where(Student.student_id == student_id))
    if student is None:
        raise StudentNotFoundError(student_id)
    return student


def create_student(db: Session, data: StudentCreate) -> Student:
    _ensure_unique(db, student_id=data.student_id, email=data.email)
    student = Student(**data.model_dump())
    db.add(student)
    _commit(db)
    db.refresh(student)
    return student


def list_students(db: Session, filters: StudentFilters | None = None,
                  skip: int = 0, limit: int = 50) -> list[Student]:
    stmt = _apply_filters(select(Student), filters or StudentFilters())
    stmt = stmt.order_by(Student.id).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def count_students(db: Session, filters: StudentFilters | None = None) -> int:
    stmt = _apply_filters(select(func.count(Student.id)), filters or StudentFilters())
    return db.scalar(stmt) or 0


def list_distinct_courses(db: Session) -> list[str]:
    stmt = select(Student.course).where(Student.course.is_not(None)).distinct()
    return sorted(c for c in db.scalars(stmt) if c)


def _save_changes(db: Session, student: Student, values: dict) -> Student:
    _ensure_unique(db, student_id=values["student_id"], email=values["email"],
                   exclude_pk=student.id)
    for field, value in values.items():
        setattr(student, field, value)
    student.updated_at = utcnow()
    _commit(db)
    db.refresh(student)
    return student


def replace_student(db: Session, student_id: str, data: StudentReplace) -> Student:
    student = get_student(db, student_id)
    values = data.model_dump()
    values["student_id"] = data.student_id or student.student_id
    return _save_changes(db, student, values)


def patch_student(db: Session, student_id: str, data: StudentPatch) -> Student:
    student = get_student(db, student_id)
    merged = {f: getattr(student, f) for f in _FIELDS}
    merged.update(data.model_dump(exclude_unset=True))
    # Re-validate the *merged* record so all business rules (contact method, dates,
    # formats) hold after the patch. Raises pydantic.ValidationError -> HTTP 422.
    validated = StudentCreate.model_validate(merged)
    return _save_changes(db, student, validated.model_dump())


def delete_student(db: Session, student_id: str) -> None:
    student = get_student(db, student_id)
    db.delete(student)
    _commit(db)
