"""
Thin wrapper around the OpenAI SDK.

Kept deliberately small: one function, one responsibility (call the model,
return text + usage). All prompt construction and JSON-parsing logic lives
in the orchestrator, not here - this module should stay a pure I/O boundary
so it's trivial to swap providers later if needed.
"""
import time
from dataclasses import dataclass

from openai import OpenAI

from app.config import get_settings

settings = get_settings()
_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


@dataclass
class LLMCallResult:
    text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    model: str


def call_llm(system_prompt: str, user_prompt: str) -> LLMCallResult:
    """
    Makes a single chat completion call and returns the text plus token/latency
    telemetry needed for the System Flow observability page.
    """
    client = get_client()
    model = settings.openai_model

    start = time.perf_counter()
    response = client.chat.completions.create(
        model=model,
        temperature=settings.openai_temperature,
        max_tokens=settings.openai_max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    latency_ms = int((time.perf_counter() - start) * 1000)

    usage = response.usage
    text = response.choices[0].message.content or ""

    return LLMCallResult(
        text=text,
        prompt_tokens=usage.prompt_tokens if usage else 0,
        completion_tokens=usage.completion_tokens if usage else 0,
        total_tokens=usage.total_tokens if usage else 0,
        latency_ms=latency_ms,
        model=model,
    )
