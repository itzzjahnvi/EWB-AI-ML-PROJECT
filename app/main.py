"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import __version__
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.database.connection import get_db, init_db
from app.routers import ai_assistant, students

logging.basicConfig(level=logging.INFO)

DESCRIPTION = """
REST API for managing student records (Create, Read, Update, Delete) backed by SQLite.

* **Students** - full CRUD with filtering and pagination.
* **AI Assistant (bonus)** - optional natural-language questions answered from the
  database using a *local* Ollama model. Disabled by default.
"""


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()  # creates missing tables only; existing data is never touched
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=DESCRIPTION,
        lifespan=lifespan,
        openapi_tags=[
            {"name": "Students", "description": "CRUD operations on student records"},
            {"name": "AI Assistant (Bonus)", "description": "Optional local-LLM assistant"},
            {"name": "System", "description": "Service status"},
        ],
    )
    register_exception_handlers(app)
    app.include_router(students.router)
    app.include_router(ai_assistant.router)

    @app.get("/", tags=["System"], summary="Service information")
    def root():
        return {"application": settings.app_name, "version": __version__,
                "status": "running", "docs": "/docs"}

    @app.get("/health", tags=["System"], summary="Health check (verifies database access)",
             responses={503: {"description": "Database unavailable"}})
    def health(db: Annotated[Session, Depends(get_db)]):
        try:
            db.execute(text("SELECT 1"))
        except Exception:
            logging.getLogger(__name__).exception("Health check failed")
            return JSONResponse(status_code=503,
                                content={"status": "unhealthy", "database": "unavailable"})
        return {"status": "healthy", "database": "ok", "ai_enabled": settings.ai_enabled}

    return app


app = create_app()
