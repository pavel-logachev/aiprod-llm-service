from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from api.models import ChatRequest, ChatResponse
from services.chat_service import ChatService, ServiceUnavailableError

router = APIRouter()


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "aiprod-llm-service"}


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={503: {"description": "LLM provider is unavailable"}},
)
async def chat(
    payload: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse | JSONResponse:
    try:
        result = await service.chat(
            message=payload.message,
            model=payload.model,
            temperature=payload.temperature,
        )
    except ServiceUnavailableError as exc:
        return JSONResponse(
            status_code=503,
            content={"error": {"code": "llm_unavailable", "message": str(exc)}},
        )

    return ChatResponse(
        answer=result.answer,
        cached=result.cached,
        model=result.model,
        duration_ms=result.duration_ms,
    )
