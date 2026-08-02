"""
Telemetry layer for the orchestration brain.

Responsibilities:
1. Compute cost (USD) for a given model + token usage, from data/pricing.json.
2. Optionally wrap LLM calls with LangSmith tracing via the `traceable`
   decorator, IF the user has configured LANGCHAIN_API_KEY /
   LANGCHAIN_TRACING_V2 in .env. This is deliberately NOT a hard dependency:
   the app works fully without it, it just won't have trace links.

We do not use the LangChain framework itself (no chains/agents) - only the
standalone LangSmith SDK's `traceable` decorator, which works with plain
function calls. This keeps us aligned with the "no multi-agent framework"
constraint while still getting real, inspectable traces when configured.
"""
import json
import os
from pathlib import Path
from typing import Callable, Optional

from app.config import get_settings
from app.models.schemas import LLMCallTelemetry
from app.services.openai_client import LLMCallResult

settings = get_settings()
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_pricing_cache: Optional[dict] = None

# --- Optional LangSmith wiring -------------------------------------------------
_langsmith_traceable = None
if settings.langsmith_enabled:
    try:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
        os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint

        from langsmith import traceable as _traceable_import

        _langsmith_traceable = _traceable_import
    except ImportError:
        # langsmith package not installed / import failed -> degrade gracefully
        _langsmith_traceable = None


def _load_pricing() -> dict:
    global _pricing_cache
    if _pricing_cache is None:
        with open(DATA_DIR / "pricing.json", "r", encoding="utf-8") as f:
            _pricing_cache = json.load(f)
    return _pricing_cache


def compute_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = _load_pricing()
    rates = pricing.get(model, pricing["_default"])
    cost = (prompt_tokens / 1000) * rates["input_per_1k"] + (completion_tokens / 1000) * rates["output_per_1k"]
    return round(cost, 6)


def wrap_traceable(name: str, fn: Callable) -> Callable:
    """
    Wraps `fn` with LangSmith's traceable decorator if LangSmith is
    configured; otherwise returns `fn` unchanged. Call sites don't need to
    know which branch was taken.
    """
    if _langsmith_traceable is not None:
        return _langsmith_traceable(name=name, run_type="llm")(fn)
    return fn


def build_telemetry(
    step: str,
    result: LLMCallResult,
    trace_url: Optional[str] = None,
) -> LLMCallTelemetry:
    cost = compute_cost_usd(result.model, result.prompt_tokens, result.completion_tokens)
    return LLMCallTelemetry(
        step=step,  # type: ignore[arg-type]
        model=result.model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        total_tokens=result.total_tokens,
        latency_ms=result.latency_ms,
        cost_usd=cost,
        langsmith_trace_url=trace_url,
        langsmith_enabled=settings.langsmith_enabled,
    )


def langsmith_project_url() -> Optional[str]:
    """Best-effort link to the LangSmith project dashboard, for the demo UI."""
    if not settings.langsmith_enabled:
        return None
    return f"https://smith.langchain.com/o/-/projects/p/{settings.langchain_project}"
