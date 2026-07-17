import hashlib
import logging
import time
import uuid
from dataclasses import dataclass

from cache.ttl_cache import TTLCache, build_cache_key
from config.settings import Settings
from llm.client import LLMClient, LLMConfigurationError, LLMUnavailableError
from llm.prompts import build_messages
from observability import log_event


class ServiceUnavailableError(RuntimeError):
    """Safe user-facing fallback error."""


@dataclass(frozen=True)
class ChatResult:
    answer: str
    cached: bool
    model: str
    duration_ms: int


class ChatService:
    def __init__(
        self,
        *,
        settings: Settings,
        llm_client: LLMClient,
        cache: TTLCache,
        logger: logging.Logger | None = None,
    ) -> None:
        self._settings = settings
        self._llm_client = llm_client
        self._cache = cache
        self._logger = logger or logging.getLogger("aiprod.chat")

    async def chat(
        self,
        *,
        message: str,
        model: str | None = None,
        temperature: float | None = None,
    ) -> ChatResult:
        started = time.perf_counter()
        request_id = uuid.uuid4().hex
        selected_model = model or self._settings.llm_model
        selected_temperature = (
            self._settings.llm_temperature if temperature is None else temperature
        )
        cache_key = build_cache_key(
            message=message,
            model=selected_model,
            temperature=selected_temperature,
            system_prompt=self._settings.llm_system_prompt,
        )
        message_hash = hashlib.sha256(message.encode("utf-8")).hexdigest()[:12]

        log_event(
            self._logger,
            "request_received",
            request_id=request_id,
            message_length=len(message),
            message_hash=message_hash,
            model=selected_model,
        )

        cached_answer = await self._cache.get(cache_key)
        if cached_answer is not None:
            duration_ms = int((time.perf_counter() - started) * 1000)
            log_event(
                self._logger,
                "cache_hit",
                request_id=request_id,
                cache_key=cache_key[:12],
                duration_ms=duration_ms,
            )
            return ChatResult(cached_answer, True, selected_model, duration_ms)

        log_event(
            self._logger,
            "cache_miss",
            request_id=request_id,
            cache_key=cache_key[:12],
        )
        messages = build_messages(self._settings.llm_system_prompt, message)
        prompt_event: dict[str, object] = {
            "request_id": request_id,
            "prompt_hash": hashlib.sha256(
                str(messages).encode("utf-8")
            ).hexdigest()[:12],
            "raw_content_logged": self._settings.log_raw_content,
        }
        if self._settings.log_raw_content:
            prompt_event["prompt"] = messages
        log_event(
            self._logger,
            "prompt_built",
            **prompt_event,
        )

        try:
            answer = await self._llm_client.complete(
                messages=messages,
                model=selected_model,
                temperature=selected_temperature,
            )
        except (LLMUnavailableError, LLMConfigurationError) as exc:
            log_event(
                self._logger,
                "llm_fallback",
                level=logging.WARNING,
                request_id=request_id,
                error_type=type(exc).__name__,
            )
            raise ServiceUnavailableError(
                "Сервис временно недоступен, попробуйте позже"
            ) from exc

        cleaned = " ".join(answer.split()).strip()
        if not cleaned:
            raise ServiceUnavailableError("Модель вернула пустой ответ, попробуйте позже")
        cleaned = cleaned[: self._settings.max_response_chars]
        await self._cache.set(cache_key, cleaned)

        duration_ms = int((time.perf_counter() - started) * 1000)
        response_event: dict[str, object] = {
            "request_id": request_id,
            "response_length": len(cleaned),
            "response_hash": hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:12],
            "duration_ms": duration_ms,
        }
        if self._settings.log_raw_content:
            response_event["response"] = cleaned
        log_event(
            self._logger,
            "request_completed",
            **response_event,
        )
        return ChatResult(cleaned, False, selected_model, duration_ms)
