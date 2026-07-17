def build_messages(system_prompt: str, message: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
    ]

