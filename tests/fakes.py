from collections.abc import Iterable


class SequenceLLMClient:
    def __init__(self, outcomes: Iterable[str | Exception]) -> None:
        self._outcomes = list(outcomes)
        self.call_count = 0

    async def complete(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
    ) -> str:
        del messages, model, temperature
        self.call_count += 1
        if not self._outcomes:
            raise AssertionError("Для fake LLM не задан следующий ответ")
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

