"""Pydantic schemas: request validation and response models for students."""

import re
from datetime import date, datetime, timezone
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

STUDENT_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_-]{2,31}$"
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PHONE = re.compile(r"^\+?[0-9][0-9\s\-().]*$")
MIN_DOB = date(1900, 1, 1)


def _blank_to_none(value: Any) -> Any:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def _strict_iso_date(value: Any) -> Any:
    """Accept only YYYY-MM-DD strings (or date objects), not timestamps or numbers."""
    if value is None or isinstance(value, date):
        return value
    if isinstance(value, str) and _ISO_DATE.match(value.strip()):
        return value.strip()
    raise ValueError("must be a valid date in YYYY-MM-DD format")


class _FieldRules(BaseModel):
    """Per-field rules shared by the create, replace and patch schemas."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("email", "phone", "course", "address", mode="before", check_fields=False)
    @classmethod
    def _empty_to_none(cls, value):
        return _blank_to_none(value)

    @field_validator("date_of_birth", "enrollment_date", mode="before", check_fields=False)
    @classmethod
    def _dates_must_be_iso(cls, value):
        return _strict_iso_date(value)

    @field_validator("email", check_fields=False)
    @classmethod
    def _normalise_email(cls, value):
        return value.lower() if value else value

    @field_validator("phone", check_fields=False)
    @classmethod
    def _validate_phone(cls, value):
        if value is None:
            return value
        digits = re.sub(r"\D", "", value)
        if not _PHONE.match(value) or not 7 <= len(digits) <= 15:
            raise ValueError(
                "phone must contain 7-15 digits and may only include digits, "
                "spaces, '+', '-', '(', ')' and '.'"
            )
        return value

    @field_validator("date_of_birth", check_fields=False)
    @classmethod
    def _validate_dob(cls, value):
        if value is None:
            return value
        if value > datetime.now(timezone.utc).date():
            raise ValueError("date_of_birth cannot be in the future")
        if value < MIN_DOB:
            raise ValueError(f"date_of_birth must be on or after {MIN_DOB.isoformat()}")
        return value


class StudentBase(_FieldRules):
    name: str = Field(..., min_length=1, max_length=120, description="Full name")
    date_of_birth: date = Field(..., description="YYYY-MM-DD, not in the future")
    email: EmailStr | None = Field(None, description="Optional, unique when provided")
    phone: str | None = Field(None, max_length=20, description="Optional contact number")
    course: str | None = Field(None, max_length=100)
    address: str | None = Field(None, max_length=255)
    enrollment_date: date | None = Field(None, description="YYYY-MM-DD")

    @model_validator(mode="after")
    def _cross_field_rules(self):
        if self.email is None and self.phone is None:
            raise ValueError("At least one contact method (email or phone) is required")
        if self.enrollment_date and self.enrollment_date < self.date_of_birth:
            raise ValueError("enrollment_date cannot be earlier than date_of_birth")
        return self


class StudentCreate(StudentBase):
    student_id: str = Field(
        ...,
        pattern=STUDENT_ID_PATTERN,
        description="Unique business identifier, 3-32 chars: letters, digits, '_' or '-'",
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "student_id": "STU1001",
                "name": "Aarav Sharma",
                "date_of_birth": "2005-06-15",
                "email": "aarav@example.com",
                "phone": "9876543210",
                "course": "Computer Science",
                "address": "Bengaluru",
                "enrollment_date": "2025-08-01",
            }
        },
    )


class StudentReplace(StudentBase):
    """Body for PUT: every field is replaced. `student_id` is optional (defaults to the
    one in the URL); supplying a different value renames the student."""

    student_id: str | None = Field(None, pattern=STUDENT_ID_PATTERN)


class StudentPatch(_FieldRules):
    """Body for PATCH: only supplied fields change. Explicit null clears optional fields."""

    student_id: str | None = Field(None, pattern=STUDENT_ID_PATTERN)
    name: str | None = Field(None, min_length=1, max_length=120)
    date_of_birth: date | None = None
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=20)
    course: str | None = Field(None, max_length=100)
    address: str | None = Field(None, max_length=255)
    enrollment_date: date | None = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        json_schema_extra={"example": {"course": "Data Science"}},
    )

    @model_validator(mode="after")
    def _check_payload(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        for field in ("student_id", "name", "date_of_birth"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} is required and cannot be null")
        return self


class StudentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: str
    name: str
    date_of_birth: date
    email: str | None
    phone: str | None
    course: str | None
    address: str | None
    enrollment_date: date | None
    created_at: datetime
    updated_at: datetime


class ErrorResponse(BaseModel):
    detail: str


class FieldError(BaseModel):
    field: str
    message: str
    type: str


class ValidationErrorResponse(BaseModel):
    detail: str = "Validation failed"
    errors: list[FieldError]
