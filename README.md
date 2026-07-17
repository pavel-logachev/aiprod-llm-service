# Пользовательский сценарий LLM-сервиса

Выполнил: Павел Логачев

Минимальный FastAPI-сервис для задания «Практика: собрать пользовательский сценарий сервиса». Сервис принимает запрос пользователя, валидирует его, формирует prompt, обращается к OpenAI-совместимому LLM API, очищает ответ и кеширует результат.

## Реализованный pipeline

1. `POST /chat` принимает JSON с полем `message`, необязательными `model` и `temperature`.
2. Pydantic отклоняет пустой текст, строки длиннее 1000 символов, лишние поля и некорректные параметры модели.
3. `ChatService` формирует системный и пользовательский prompt.
4. `OpenAICompatibleClient` выполняет запрос с явным таймаутом и максимум тремя попытками.
5. Повторяются только временные ошибки: timeout, network error, HTTP 408, 429 и 5xx. Ошибки 4xx не повторяются.
6. После исчерпания попыток API возвращает контролируемый HTTP 503 с fallback-сообщением.
7. Валидный ответ очищается и сохраняется в TTL-кеш на 10 минут.
8. Ключ кеша учитывает текст, модель, температуру и системный prompt.
9. Логи пишутся в JSON и содержат correlation id, cache hit/miss, длительность и хеши содержимого.

По умолчанию сырой prompt и ответ не пишутся в лог, чтобы не сохранять пользовательские данные. Для учебной отладки можно включить `LOG_RAW_CONTENT=true`, но ключи и заголовки авторизации не логируются никогда.

## Структура

```text
api/            HTTP-модели и эндпоинты
cache/          потокобезопасный TTL-кеш
config/         настройки из переменных окружения
llm/            prompt builder и OpenAI-совместимый клиент
services/       бизнес-логика пользовательского pipeline
tests/          unit и API-тесты
evals/          версия golden contract dataset и evaluator
main.py         точка входа FastAPI
```

## Установка и запуск

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn main:app --host 127.0.0.1 --port 8000
```

По умолчанию используется локальный Ollama:

```powershell
ollama serve
ollama pull qwen2.5-coder:7b
```

Для другого OpenAI-совместимого провайдера задайте `LLM_BASE_URL`, `LLM_API_KEY` и `LLM_MODEL`. Файл `.env` не коммитится.

## Примеры запросов

Успешный запрос:

```powershell
$body = @{ message = 'Кратко объясни разницу между CI и CD' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat -ContentType 'application/json' -Body $body
```

Пример ответа:

```json
{
  "answer": "CI автоматически проверяет изменения, а CD автоматизирует доставку релиза.",
  "cached": false,
  "model": "qwen2.5-coder:7b",
  "duration_ms": 1240
}
```

Повторите тот же запрос: `cached` должен стать `true`, а в логах появится `cache_hit`.

Ошибка валидации:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat -ContentType 'application/json' -Body '{"message":""}'
```

При недоступности LLM сервис не падает и возвращает:

```json
{
  "error": {
    "code": "llm_unavailable",
    "message": "Сервис временно недоступен, попробуйте позже"
  }
}
```

## Проверка

```powershell
python -m unittest discover -s tests -v
python evals/run_eval.py
ruff check .
python -m compileall -q .
```

Ручной чек-лист и фактические результаты находятся в [test_report.md](test_report.md).

## Docker

```powershell
docker build -t aiprod-llm-service:local .
docker run --rm -p 8000:8000 `
  -e LLM_BASE_URL=http://host.docker.internal:11434/v1 `
  -e LLM_API_KEY=ollama `
  -e LLM_MODEL=qwen2.5-coder:7b `
  aiprod-llm-service:local
```

Swagger UI: <http://127.0.0.1:8000/docs>

## Демонстрация сценариев

Скриншоты получены из Swagger UI запущенного Docker-контейнера:

- [успешный ответ, HTTP 200](evidence/01-success.png);
- [повторный запрос из кеша, `cached=true`](evidence/02-cache-hit.png);
- [ошибка валидации, HTTP 422](evidence/03-validation-error.png);
- [fallback при недоступной модели, HTTP 503](evidence/04-provider-fallback.png).
