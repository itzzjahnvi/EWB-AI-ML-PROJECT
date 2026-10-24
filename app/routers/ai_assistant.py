"""Optional bonus: natural-language questions answered from the SQLite data."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.ollama_service import OllamaClient
from app.core.config import Settings, get_settings
from app.database.connection import get_db
from app.schemas.ai import AskRequest, AskResponse
from app.schemas.student import ErrorResponse, ValidationErrorResponse
from app.services import ai_service

router = APIRouter(prefix="/ai", tags=["AI Assistant (Bonus)"])


def get_ollama_client(settings: Annotated[Settings, Depends(get_settings)]) -> OllamaClient:
    return OllamaClient(settings.ollama_base_url, settings.ollama_model,
                        settings.ollama_timeout_seconds)


@router.post(
    "/ask", response_model=AskResponse, summary="Ask a question about the students",
    description=(
        "Counts are computed directly from SQLite. Listing questions are answered by a "
        "local Ollama model that only sees the retrieved records. The model never writes "
        "or runs SQL. Returns 503 when AI is disabled (`AI_ENABLED=false`)."
    ),
    responses={503: {"model": ErrorResponse, "description": "AI assistant disabled"},
               422: {"model": ValidationErrorResponse}},
)
def ask(
    payload: AskRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    client: Annotated[OllamaClient, Depends(get_ollama_client)],
):
    if not settings.ai_enabled:
        raise HTTPException(
            status_code=503,
            detail="The AI assistant is disabled. Set AI_ENABLED=true to enable it.",
        )
    if len(payload.question) > settings.ai_max_question_length:
        raise HTTPException(status_code=422, detail="Question is too long")
    return ai_service.answer_question(db, payload.question, settings, client)
