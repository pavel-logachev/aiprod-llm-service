import logging
import unittest
from io import StringIO

from cache.ttl_cache import TTLCache
from config.settings import Settings
from llm.client import LLMUnavailableError
from observability import JsonFormatter
from services.chat_service import ChatService, ServiceUnavailableError
from tests.fakes import SequenceLLMClient


class ChatServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_raw_content_is_not_logged_by_default(self) -> None:
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonFormatter())
        logger = logging.getLogger("aiprod.test.privacy")
        logger.handlers = [handler]
        logger.propagate = False
        logger.setLevel(logging.INFO)
        service = ChatService(
            settings=Settings(),
            llm_client=SequenceLLMClient(["секретный ответ"]),
            cache=TTLCache(600),
            logger=logger,
        )

        await service.chat(message="секретный запрос")

        logs = stream.getvalue()
        self.assertNotIn("секретный запрос", logs)
        self.assertNotIn("секретный ответ", logs)
        self.assertIn('"raw_content_logged":false', logs)

    async def test_identical_second_request_uses_cache(self) -> None:
        fake = SequenceLLMClient(["  Первый   ответ  "])
        service = ChatService(
            settings=Settings(),
            llm_client=fake,
            cache=TTLCache(600),
        )

        first = await service.chat(message="Привет")
        second = await service.chat(message="Привет")

        self.assertEqual(first.answer, "Первый ответ")
        self.assertFalse(first.cached)
        self.assertTrue(second.cached)
        self.assertEqual(fake.call_count, 1)

    async def test_provider_failure_returns_safe_fallback(self) -> None:
        fake = SequenceLLMClient([LLMUnavailableError("network")])
        service = ChatService(
            settings=Settings(),
            llm_client=fake,
            cache=TTLCache(600),
        )

        with self.assertRaisesRegex(ServiceUnavailableError, "временно недоступен"):
            await service.chat(message="Привет")


if __name__ == "__main__":
    unittest.main()
