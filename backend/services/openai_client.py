"""OpenAI wrapper — 60s timeout, 2 retries, JSON logging, cost tracking."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from openai import APIError, APITimeoutError, OpenAI, RateLimitError
from openai.types.chat import ChatCompletion
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config import settings

# ── Cost table (USD per 1M tokens, as of 2025) ─────────────────────────────────
_COST_PER_1M: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.150, "output": 0.600},
}

# ── Logging ────────────────────────────────────────────────────────────────────
_log_path = Path(__file__).parent.parent / "logs" / "openai.log"
_log_path.parent.mkdir(exist_ok=True)

_file_handler = logging.FileHandler(_log_path)
_file_handler.setFormatter(logging.Formatter("%(message)s"))

_logger = logging.getLogger("ai020.openai")
_logger.setLevel(logging.DEBUG)
_logger.addHandler(_file_handler)
_logger.propagate = False

# ── Client ─────────────────────────────────────────────────────────────────────
_client = OpenAI(
    api_key=settings.openai_api_key,
    timeout=60.0,
    max_retries=0,  # we handle retries via tenacity
)


def _calc_cost(model: str, usage: dict[str, int]) -> float:
    rates = _COST_PER_1M.get(model, {"input": 0.0, "output": 0.0})
    return (
        usage.get("prompt_tokens", 0) * rates["input"] / 1_000_000
        + usage.get("completion_tokens", 0) * rates["output"] / 1_000_000
    )


def _log(
    model: str,
    messages: list[dict[str, Any]],
    response: ChatCompletion,
    elapsed: float,
) -> None:
    usage = response.usage.model_dump() if response.usage else {}
    record = {
        "model": model,
        "elapsed_s": round(elapsed, 3),
        "usage": usage,
        "cost_usd": round(_calc_cost(model, usage), 6),
        "request_messages_count": len(messages),
        "finish_reason": response.choices[0].finish_reason if response.choices else None,
    }
    _logger.debug(json.dumps(record))


@retry(
    retry=retry_if_exception_type((APITimeoutError, RateLimitError, APIError)),
    stop=stop_after_attempt(3),  # 1 original + 2 retries
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def chat_completion(
    *,
    model: str,
    messages: list[dict[str, Any]],
    response_format: dict[str, Any] | None = None,
    temperature: float = 0.0,
) -> ChatCompletion:
    """Single chat completion with retry, logging, and cost tracking."""
    t0 = time.perf_counter()
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format:
        kwargs["response_format"] = response_format

    response = _client.chat.completions.create(**kwargs)
    _log(model, messages, response, time.perf_counter() - t0)
    return response


def extract_json(response: ChatCompletion) -> Any:
    """Parse the JSON content from a structured-output response."""
    content = response.choices[0].message.content or ""
    return json.loads(content)
