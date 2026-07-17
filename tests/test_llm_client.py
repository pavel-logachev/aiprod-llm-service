import unittest

import httpx

from config.settings import Settings
from llm.client import (
    LLMConfigurationError,
    LLMUnavailableError,
    OpenAICompatibleClient,
)


class OpenAICompatibleClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_retries_transient_errors_then_succeeds(self) -> None:
        calls = [0]
        sleeps: list[float] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            calls[0] += 1
            if calls[0] < 3:
                return httpx.Response(503, request=request)
            return httpx.Response(
                200,
                request=request,
                json={"choices": [{"message": {"content": "  готово  "}}]},
            )

        async def fake_sleep(delay: float) -> None:
            sleeps.append(delay)

        settings = Settings(llm_max_attempts=3)
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test/v1/",
        ) as http_client:
            client = OpenAICompatibleClient(
                settings,
                client=http_client,
                sleep=fake_sleep,
                jitter=lambda upper: 0.0,
            )
            result = await client.complete(
                messages=[{"role": "user", "content": "test"}],
                model="model",
                temperature=0.2,
            )

        self.assertEqual(result, "  готово  ")
        self.assertEqual(calls[0], 3)
        self.assertEqual(sleeps, [0.2, 0.4])

    async def test_does_not_retry_permanent_client_error(self) -> None:
        calls = [0]

        async def handler(request: httpx.Request) -> httpx.Response:
            calls[0] += 1
            return httpx.Response(401, request=request)

        settings = Settings(llm_max_attempts=3)
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test/v1/",
        ) as http_client:
            client = OpenAICompatibleClient(settings, client=http_client)
            with self.assertRaises(LLMConfigurationError):
                await client.complete(
                    messages=[{"role": "user", "content": "test"}],
                    model="model",
                    temperature=0.2,
                )

        self.assertEqual(calls[0], 1)

    async def test_invalid_responses_exhaust_retry_budget(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, request=request, content=b"not-json")

        async def fake_sleep(delay: float) -> None:
            del delay

        settings = Settings(llm_max_attempts=2)
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test/v1/",
        ) as http_client:
            client = OpenAICompatibleClient(
                settings,
                client=http_client,
                sleep=fake_sleep,
                jitter=lambda upper: 0.0,
            )
            with self.assertRaises(LLMUnavailableError):
                await client.complete(
                    messages=[{"role": "user", "content": "test"}],
                    model="model",
                    temperature=0.2,
                )


if __name__ == "__main__":
    unittest.main()

