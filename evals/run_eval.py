import hashlib
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings import Settings  # noqa: E402
from llm.client import LLMUnavailableError  # noqa: E402
from main import create_app  # noqa: E402
from tests.fakes import SequenceLLMClient  # noqa: E402


def main() -> int:
    dataset_path = Path(__file__).with_name("golden_cases.json")
    dataset_bytes = dataset_path.read_bytes()
    dataset = json.loads(dataset_bytes)
    results: list[dict[str, object]] = []

    success_fake = SequenceLLMClient(["Проверенный ответ"])
    with TestClient(create_app(Settings(), success_fake)) as client:
        response = client.post("/chat", json={"message": "Что такое CI?"})
        results.append(
            {
                "case_id": "valid_request",
                "passed": response.status_code == 200
                and set(response.json()) == {"answer", "cached", "model", "duration_ms"},
            }
        )
        repeat = client.post("/chat", json={"message": "Что такое CI?"})
        results.append(
            {
                "case_id": "cache_repeat",
                "passed": repeat.status_code == 200
                and repeat.json()["cached"] is True
                and success_fake.call_count == 1,
            }
        )
        blank = client.post("/chat", json={"message": "   "})
        results.append(
            {"case_id": "blank_message", "passed": blank.status_code == 422}
        )
        oversized = client.post("/chat", json={"message": "x" * 1001})
        results.append(
            {"case_id": "oversized_message", "passed": oversized.status_code == 422}
        )

    failure_fake = SequenceLLMClient([LLMUnavailableError("simulated timeout")])
    with TestClient(create_app(Settings(), failure_fake)) as client:
        fallback = client.post("/chat", json={"message": "Проверка fallback"})
        results.append(
            {
                "case_id": "provider_failure",
                "passed": fallback.status_code == 503
                and fallback.json()["error"]["code"] == "llm_unavailable",
            }
        )

    passed = sum(bool(item["passed"]) for item in results)
    report = {
        "dataset_version": dataset["dataset_version"],
        "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "prompt_sha256": hashlib.sha256(
            Settings().llm_system_prompt.encode("utf-8")
        ).hexdigest(),
        "model_binding": "synthetic-contract-fake",
        "schema_version": "chat-api-v1",
        "evaluator_version": "contract-eval-v1",
        "total": len(results),
        "passed": passed,
        "critical_failures": len(results) - passed,
        "cases": results,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

