import unittest

import httpx

from config.settings import Settings
from llm.client import LLMConfigurationError, LLMUnavailableError
from shopping_llm import (
    ACCESS_ERROR_MESSAGE,
    EMPTY_INPUT_MESSAGE,
    EMPTY_RESPONSE_MESSAGE,
    LONG_INPUT_MESSAGE,
    MAX_DISH_LENGTH,
    NETWORK_ERROR_MESSAGE,
    SERVICE_ERROR_MESSAGE,
    UserFacingError,
    build_messages,
    generate_shopping_list,
)
from tests.fakes import SequenceLLMClient


class ShoppingLLMTest(unittest.IsolatedAsyncioTestCase):
    async def test_normal_input_returns_provider_answer(self) -> None:
        client = SequenceLLMClient(["- томаты\n- паста\n- сыр"])

        result = await generate_shopping_list(
            "Паста с томатами",
            "2",
            "Список продуктов",
            client=client,
            settings=Settings(),
        )

        self.assertEqual(result, "- томаты\n- паста\n- сыр")
        self.assertEqual(client.call_count, 1)

    async def test_empty_input_does_not_call_provider(self) -> None:
        client = SequenceLLMClient(["не должен вызываться"])

        with self.assertRaisesRegex(UserFacingError, EMPTY_INPUT_MESSAGE):
            await generate_shopping_list(
                "   ",
                "2",
                "Список продуктов",
                client=client,
                settings=Settings(),
            )

        self.assertEqual(client.call_count, 0)

    async def test_long_input_does_not_call_provider(self) -> None:
        client = SequenceLLMClient(["не должен вызываться"])

        with self.assertRaisesRegex(UserFacingError, LONG_INPUT_MESSAGE):
            await generate_shopping_list(
                "а" * (MAX_DISH_LENGTH + 1),
                "2",
                "Список продуктов",
                client=client,
                settings=Settings(),
            )

        self.assertEqual(client.call_count, 0)

    async def test_configuration_error_has_safe_message(self) -> None:
        client = SequenceLLMClient([LLMConfigurationError("token=secret")])

        with self.assertRaisesRegex(UserFacingError, ACCESS_ERROR_MESSAGE):
            await generate_shopping_list(
                "Суп",
                "1",
                "Список продуктов",
                client=client,
                settings=Settings(),
            )

    async def test_network_error_has_safe_message(self) -> None:
        request = httpx.Request("POST", "http://provider.test/v1/chat/completions")
        client = SequenceLLMClient([httpx.ReadTimeout("secret host", request=request)])

        with self.assertRaisesRegex(UserFacingError, NETWORK_ERROR_MESSAGE):
            await generate_shopping_list(
                "Суп",
                "1",
                "Список продуктов",
                client=client,
                settings=Settings(),
            )

    async def test_unavailable_provider_has_safe_message(self) -> None:
        client = SequenceLLMClient([LLMUnavailableError("HTTP 503 internal")])

        with self.assertRaisesRegex(UserFacingError, SERVICE_ERROR_MESSAGE):
            await generate_shopping_list(
                "Суп",
                "1",
                "Список продуктов",
                client=client,
                settings=Settings(),
            )

    async def test_empty_answer_has_safe_message(self) -> None:
        client = SequenceLLMClient(["   "])

        with self.assertRaisesRegex(UserFacingError, EMPTY_RESPONSE_MESSAGE):
            await generate_shopping_list(
                "Суп",
                "1",
                "Список продуктов",
                client=client,
                settings=Settings(),
            )

    def test_prompt_contains_people_and_selected_format(self) -> None:
        messages = build_messages("Овощное рагу", "6", "Список + шаги")

        self.assertIn("Количество человек: 6", messages[1]["content"])
        self.assertIn("5–8 нумерованных", messages[1]["content"])


if __name__ == "__main__":
    unittest.main()
