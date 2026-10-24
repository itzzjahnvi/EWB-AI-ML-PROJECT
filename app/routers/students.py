"""Student CRUD endpoints."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.student import (
    ErrorResponse,
    StudentCreate,
    StudentPatch,
    StudentRead,
    StudentReplace,
    ValidationErrorResponse,
)
from app.services import student_service as service
from app.services.student_service import StudentFilters

router = APIRouter(prefix="/students", tags=["Students"])

DbSession = Annotated[Session, Depends(get_db)]
StudentIdPath = Annotated[
    str, Path(min_length=1, max_length=64, description="Unique business student ID, e.g. STU1001")
]

_404 = {404: {"model": ErrorResponse, "description": "Student not found"}}
_409 = {409: {"model": ErrorResponse, "description": "Duplicate student_id or email"}}
_422 = {422: {"model": ValidationErrorResponse, "description": "Validation error"}}


@router.post(
    "", response_model=StudentRead, status_code=status.HTTP_201_CREATED,
    summary="Create a student", responses={**_409, **_422},
)
def create_student(payload: StudentCreate, db: DbSession):
    return service.create_student(db, payload)


@router.get("", response_model=list[StudentRead], summary="List and filter students",
            responses=_422)
def list_students(
    db: DbSession,
    name: Annotated[str | None, Query(min_length=1, max_length=120,
                    description="Case-insensitive partial match on name")] = None,
    course: Annotated[str | None, Query(min_length=1, max_length=100,
                      description="Case-insensitive exact match on course")] = None,
    student_id: Annotated[str | None, Query(min_length=1, max_length=64,
                          description="Case-insensitive exact match on student ID")] = None,
    dob_after: Annotated[date | None, Query(description="Born strictly after this date (YYYY-MM-DD)")] = None,
    dob_before: Annotated[date | None, Query(description="Born strictly before this date (YYYY-MM-DD)")] = None,
    skip: Annotated[int, Query(ge=0, le=1_000_000, description="Records to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Max records to return (1-100)")] = 50,
):
    filters = StudentFilters(name=name, course=course, student_id=student_id,
                             dob_after=dob_after, dob_before=dob_before)
    return service.list_students(db, filters, skip=skip, limit=limit)


@router.get("/{student_id}", response_model=StudentRead, summary="Retrieve one student",
            responses=_404)
def get_student(student_id: StudentIdPath, db: DbSession):
    return service.get_student(db, student_id)


@router.put("/{student_id}", response_model=StudentRead, summary="Replace a student (full update)",
            responses={**_404, **_409, **_422})
def replace_student(student_id: StudentIdPath, payload: StudentReplace, db: DbSession):
    return service.replace_student(db, student_id, payload)


@router.patch("/{student_id}", response_model=StudentRead,
              summary="Partially update a student", responses={**_404, **_409, **_422})
def patch_student(student_id: StudentIdPath, payload: StudentPatch, db: DbSession):
    return service.patch_student(db, student_id, payload)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete a student", responses=_404)
def delete_student(student_id: StudentIdPath, db: DbSession):
    service.delete_student(db, student_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
