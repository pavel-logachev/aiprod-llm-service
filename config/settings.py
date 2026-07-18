import os
from dataclasses import dataclass
from urllib.parse import urlparse


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str = "development"
    llm_base_url: str = "http://127.0.0.1:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "qwen2.5-coder:7b"
    llm_system_prompt: str = (
        "Ты полезный технический ассистент. Отвечай кратко и по существу."
    )
    llm_temperature: float = 0.2
    llm_timeout_seconds: float = 20.0
    llm_max_attempts: int = 3
    retry_base_delay_seconds: float = 0.2
    retry_max_delay_seconds: float = 2.0
    cache_ttl_seconds: int = 600
    max_response_chars: int = 4000
    log_raw_content: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        settings = cls(
            app_env=os.getenv("APP_ENV", cls.app_env),
            llm_base_url=os.getenv("LLM_BASE_URL", cls.llm_base_url),
            llm_api_key=os.getenv("LLM_API_KEY", cls.llm_api_key),
            llm_model=os.getenv("LLM_MODEL", cls.llm_model),
            llm_system_prompt=os.getenv("LLM_SYSTEM_PROMPT", cls.llm_system_prompt),
            llm_temperature=float(os.getenv("LLM_TEMPERATURE", str(cls.llm_temperature))),
            llm_timeout_seconds=float(
                os.getenv("LLM_TIMEOUT_SECONDS", str(cls.llm_timeout_seconds))
            ),
            llm_max_attempts=int(os.getenv("LLM_MAX_ATTEMPTS", str(cls.llm_max_attempts))),
            retry_base_delay_seconds=float(
                os.getenv("RETRY_BASE_DELAY_SECONDS", str(cls.retry_base_delay_seconds))
            ),
            retry_max_delay_seconds=float(
                os.getenv("RETRY_MAX_DELAY_SECONDS", str(cls.retry_max_delay_seconds))
            ),
            cache_ttl_seconds=int(
                os.getenv("CACHE_TTL_SECONDS", str(cls.cache_ttl_seconds))
            ),
            max_response_chars=int(
                os.getenv("MAX_RESPONSE_CHARS", str(cls.max_response_chars))
            ),
            log_raw_content=_as_bool(os.getenv("LOG_RAW_CONTENT", "false")),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.app_env not in {"development", "production", "test"}:
            raise ValueError("APP_ENV должен быть development, production или test")
        parsed = urlparse(self.llm_base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("LLM_BASE_URL должен быть абсолютным HTTP(S)-адресом")
        if not 0 <= self.llm_temperature <= 2:
            raise ValueError("LLM_TEMPERATURE должен быть в диапазоне 0..2")
        if not 1 <= self.llm_max_attempts <= 5:
            raise ValueError("LLM_MAX_ATTEMPTS должен быть в диапазоне 1..5")
        if self.llm_timeout_seconds <= 0:
            raise ValueError("LLM_TIMEOUT_SECONDS должен быть положительным")
        if self.cache_ttl_seconds <= 0:
            raise ValueError("CACHE_TTL_SECONDS должен быть положительным")
