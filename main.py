from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.routes import router
from cache.ttl_cache import TTLCache
from config.settings import Settings
from llm.client import LLMClient, OpenAICompatibleClient
from observability import configure_logging
from services.chat_service import ChatService


def create_app(
    settings: Settings | None = None,
    llm_client: LLMClient | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        client = llm_client or OpenAICompatibleClient(resolved_settings)
        app.state.chat_service = ChatService(
            settings=resolved_settings,
            llm_client=client,
            cache=TTLCache(resolved_settings.cache_ttl_seconds),
        )
        yield
        close = getattr(client, "aclose", None)
        if close is not None:
            await close()

    app = FastAPI(
        title="AIPROD LLM Service",
        version="1.0.0",
        lifespan=lifespan,
    )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        del request
        safe_details = [
            {key: value for key, value in error.items() if key not in {"input", "ctx"}}
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Проверьте входные данные",
                    "details": safe_details,
                }
            },
        )

    app.include_router(router)
    return app


app = create_app()

