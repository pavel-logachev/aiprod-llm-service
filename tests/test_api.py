import unittest

from fastapi.testclient import TestClient

from config.settings import Settings
from llm.client import LLMUnavailableError
from main import create_app
from tests.fakes import SequenceLLMClient


class APITest(unittest.TestCase):
    def test_success_and_cache_hit(self) -> None:
        fake = SequenceLLMClient(["Краткий ответ"])
        with TestClient(create_app(Settings(), fake)) as client:
            first = client.post("/chat", json={"message": "Объясни CI"})
            second = client.post("/chat", json={"message": "Объясни CI"})

        self.assertEqual(first.status_code, 200)
        self.assertFalse(first.json()["cached"])
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()["cached"])
        self.assertEqual(fake.call_count, 1)

    def test_validation_errors_are_clear_and_do_not_echo_input(self) -> None:
        fake = SequenceLLMClient([])
        with TestClient(create_app(Settings(), fake)) as client:
            blank = client.post("/chat", json={"message": "   "})
            too_long = client.post("/chat", json={"message": "x" * 1001})

        self.assertEqual(blank.status_code, 422)
        self.assertEqual(blank.json()["error"]["code"], "validation_error")
        self.assertNotIn("input", str(blank.json()))
        self.assertEqual(too_long.status_code, 422)
        self.assertNotIn("x" * 1001, str(too_long.json()))

    def test_provider_failure_returns_503_fallback(self) -> None:
        fake = SequenceLLMClient([LLMUnavailableError("timeout")])
        with TestClient(create_app(Settings(), fake)) as client:
            response = client.post("/chat", json={"message": "Привет"})

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "llm_unavailable")
        self.assertIn("попробуйте позже", response.json()["error"]["message"])


if __name__ == "__main__":
    unittest.main()

