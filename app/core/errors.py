"""Consistent JSON error responses. Internal database errors are logged, never exposed."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.services.student_service import (
    DuplicateStudentError,
    StudentConstraintError,
    StudentNotFoundError,
)

logger = logging.getLogger(__name__)


def format_validation_errors(errors) -> list[dict]:
    formatted = []
    for err in errors:
        loc = [str(part) for part in err.get("loc", ()) if part != "body"]
        message = str(err.get("msg", "Invalid value"))
        message = message.removeprefix("Value error, ")
        formatted.append({
            "field": ".".join(loc) or "body",
            "message": message,
            "type": err.get("type", "value_error"),
        })
    return formatted


def _validation_response(errors) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation failed", "errors": format_validation_errors(errors)},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _request_validation(_: Request, exc: RequestValidationError):
        errors = exc.errors()
        if any(e.get("type") == "json_invalid" for e in errors):
            return JSONResponse(status_code=400, content={"detail": "Malformed JSON in request body"})
        return _validation_response(errors)

    @app.exception_handler(ValidationError)
    async def _model_validation(_: Request, exc: ValidationError):
        return _validation_response(exc.errors())

    @app.exception_handler(StudentNotFoundError)
    async def _not_found(_: Request, exc: StudentNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(DuplicateStudentError)
    async def _duplicate(_: Request, exc: DuplicateStudentError):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(StudentConstraintError)
    async def _constraint(_: Request, exc: StudentConstraintError):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(SQLAlchemyError)
    async def _database_error(_: Request, exc: SQLAlchemyError):
        logger.exception("Database error", exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "A database error occurred"})

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception):
        logger.exception("Unhandled error", exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
