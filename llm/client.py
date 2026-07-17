import asyncio
import json
import random
from collections.abc import Awaitable, Callable
from typing import Protocol

import httpx

from config.settings import Settings


class LLMError(RuntimeError):
    """Base error for the provider boundary."""


class LLMConfigurationError(LLMError):
    """Permanent provider/authentication/configuration error."""


class LLMUnavailableError(LLMError):
    """Retry budget was exhausted or the response stayed invalid."""


class LLMClient(Protocol):
    async def complete(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
    ) -> str: ...


class OpenAICompatibleClient:
    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        jitter: Callable[[float], float] | None = None,
    ) -> None:
        self._settings = settings
        self._sleep = sleep
        self._jitter = jitter or (lambda upper: random.uniform(0.0, upper))
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=settings.llm_base_url.rstrip("/") + "/",
            timeout=httpx.Timeout(settings.llm_timeout_seconds),
            headers={
                "Authorization": f"Bearer {settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            follow_redirects=False,
            trust_env=False,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def complete(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
    ) -> str:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        last_error: Exception | None = None

        for attempt in range(1, self._settings.llm_max_attempts + 1):
            try:
                response = await self._client.post("chat/completions", json=payload)
                if response.status_code in {408, 429} or response.status_code >= 500:
                    last_error = LLMUnavailableError(
                        f"временная ошибка провайдера: HTTP {response.status_code}"
                    )
                    if attempt < self._settings.llm_max_attempts:
                        await self._sleep(self._retry_delay(attempt, response))
                        continue
                    break
                if response.status_code >= 400:
                    raise LLMConfigurationError(
                        f"провайдер отклонил запрос: HTTP {response.status_code}"
                    )
                return self._extract_content(response)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                if attempt < self._settings.llm_max_attempts:
                    await self._sleep(self._retry_delay(attempt))
                    continue
                break
            except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as exc:
                last_error = exc
                if attempt < self._settings.llm_max_attempts:
                    await self._sleep(self._retry_delay(attempt))
                    continue
                break

        reason = type(last_error).__name__ if last_error else "unknown"
        raise LLMUnavailableError(
            f"LLM недоступна после {self._settings.llm_max_attempts} попыток ({reason})"
        ) from last_error

    def _retry_delay(self, attempt: int, response: httpx.Response | None = None) -> float:
        retry_after: float | None = None
        if response is not None:
            raw_retry_after = response.headers.get("retry-after")
            if raw_retry_after:
                try:
                    retry_after = float(raw_retry_after)
                except ValueError:
                    retry_after = None

        exponential = min(
            self._settings.retry_base_delay_seconds * (2 ** (attempt - 1)),
            self._settings.retry_max_delay_seconds,
        )
        base_delay = retry_after if retry_after is not None else exponential
        bounded = min(max(base_delay, 0.0), self._settings.retry_max_delay_seconds)
        return bounded + self._jitter(bounded * 0.1)

    @staticmethod
    def _extract_content(response: httpx.Response) -> str:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("провайдер вернул пустой ответ")
        return content

