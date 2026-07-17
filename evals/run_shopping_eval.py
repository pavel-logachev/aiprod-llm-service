import asyncio
import hashlib
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings import Settings  # noqa: E402
from shopping_llm import build_messages, generate_shopping_list  # noqa: E402

DATASET_PATH = ROOT / "evals" / "shopping_golden_cases.json"
EVALUATOR_VERSION = "shopping-eval-v1"
MAX_LATENCY_MS = 45_000


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def count_product_lines(answer: str) -> int:
    return sum(
        bool(re.match(r"^\s*[-*•]\s+\S", line))
        for line in answer.splitlines()
    )


def count_steps(answer: str) -> int:
    return sum(
        bool(re.match(r"^\s*\d+[.)]\s+\S", line))
        for line in answer.splitlines()
    )


def validate_answer(answer: str, criteria: dict[str, object]) -> list[str]:
    failures: list[str] = []
    if not answer.strip():
        failures.append("empty_answer")
    if len(answer) > 4000:
        failures.append("answer_too_long")
    safe_abstention = bool(criteria.get("allow_safe_abstention")) and any(
        phrase in answer.casefold()
        for phrase in ("не могу помочь", "не могу выполнить", "не раскрываю")
    )
    if (
        count_product_lines(answer) < int(criteria["min_product_lines"])
        and not safe_abstention
    ):
        failures.append("too_few_product_lines")

    if bool(criteria.get("requires_steps")):
        steps = count_steps(answer)
        if not int(criteria["min_steps"]) <= steps <= int(criteria["max_steps"]):
            failures.append("step_count_out_of_range")

    normalized = answer.casefold()
    for forbidden in criteria.get("forbidden_terms", []):
        if str(forbidden).casefold() in normalized:
            failures.append(f"forbidden_term:{forbidden}")
    return failures


async def run() -> int:
    dataset_bytes = DATASET_PATH.read_bytes()
    dataset = json.loads(dataset_bytes)
    settings = Settings.from_env()
    sample_prompt = build_messages("sample", "1", "Список продуктов")
    prompt_hash = sha256_bytes(
        json.dumps(sample_prompt, ensure_ascii=False, sort_keys=True).encode("utf-8")
    )
    code_hash = sha256_bytes((ROOT / "shopping_llm.py").read_bytes())

    results: list[dict[str, object]] = []
    critical_failures = 0
    for case in dataset["cases"]:
        started = time.perf_counter()
        try:
            answer = await generate_shopping_list(
                case["dish"],
                case["people"],
                case["format"],
                settings=settings,
            )
            failures = validate_answer(answer, case["criteria"])
        except Exception as exc:
            answer = ""
            failures = [f"safe_failure:{type(exc).__name__}"]
        latency_ms = int((time.perf_counter() - started) * 1000)
        if latency_ms > MAX_LATENCY_MS:
            failures.append("latency_threshold_exceeded")
        if failures and int(case["business_importance"]) >= 5:
            critical_failures += 1
        results.append(
            {
                "case_id": case["case_id"],
                "passed": not failures,
                "failures": failures,
                "latency_ms": latency_ms,
                "output_hash": sha256_bytes(answer.encode("utf-8")) if answer else None,
            }
        )

    passed = sum(bool(result["passed"]) for result in results)
    report = {
        "dataset_version": dataset["dataset_version"],
        "dataset_sha256": sha256_bytes(dataset_bytes),
        "prompt_sha256": prompt_hash,
        "model": settings.llm_model,
        "temperature": settings.llm_temperature,
        "schema_version": dataset["schema_version"],
        "code_sha256": code_hash,
        "evaluator_version": EVALUATOR_VERSION,
        "environment": "local_ollama",
        "cost_usd": 0,
        "passed": passed,
        "total": len(results),
        "critical_failures": critical_failures,
        "results": results,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed == len(results) and critical_failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
