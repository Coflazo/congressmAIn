"""
LLM client — calls our local fallback server instead of OpenAI directly.
the fallback server chains 12 free providers so something is always available.
start it with: make fallback-server
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from config import settings

# keeping a cost table even though free tier costs $0 — useful if we switch providers later
_COST_PER_1M: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.150, "output": 0.600},
    # all the free tier models — zero cost
    "t0-deepseek": {"input": 0.0, "output": 0.0},
    "t1-qwen": {"input": 0.0, "output": 0.0},
    "t2-sambanova": {"input": 0.0, "output": 0.0},
    "t3-nvidia": {"input": 0.0, "output": 0.0},
    "t4-cerebras": {"input": 0.0, "output": 0.0},
    "t5-github": {"input": 0.0, "output": 0.0},
    "t5-github-mini": {"input": 0.0, "output": 0.0},
    "t6-mistral": {"input": 0.0, "output": 0.0},
    "t7-groq": {"input": 0.0, "output": 0.0},
    "t8-gemini-flash": {"input": 0.0, "output": 0.0},
    "t9-gemini-pro": {"input": 0.0, "output": 0.0},
    "t10-cohere": {"input": 0.0, "output": 0.0},
    "t11-llama-free": {"input": 0.0, "output": 0.0},
}

# log file — renamed from openai.log to llm.log since we're not using openai anymore
_log_path = Path(__file__).parent.parent / "logs" / "llm.log"
_log_path.parent.mkdir(exist_ok=True)

_file_handler = logging.FileHandler(_log_path)
_file_handler.setFormatter(logging.Formatter("%(message)s"))

_logger = logging.getLogger("ai020.llm")
_logger.setLevel(logging.DEBUG)
_logger.addHandler(_file_handler)
_logger.propagate = False


@dataclass
class LLMResponse:
    """what we get back from the fallback server"""
    text: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)


def _calc_cost(model: str, usage: dict[str, int]) -> float:
    """calculate cost in USD — mostly $0 for free tier but kept for tracking"""
    rates = _COST_PER_1M.get(model, {"input": 0.0, "output": 0.0})
    return (
        usage.get("prompt_tokens", 0) * rates["input"] / 1_000_000
        + usage.get("completion_tokens", 0) * rates["output"] / 1_000_000
    )


def _inject_json_schema(messages: list[dict[str, Any]], schema: dict[str, Any]) -> list[dict[str, Any]]:
    """
    since the fallback server doesn't support structured outputs natively,
    we inject the JSON schema into the system prompt instead — works well enough
    """
    instruction = (
        "Respond ONLY with valid JSON. No markdown code fences. No explanation outside the JSON. "
        f"Your response must match this schema exactly:\n{json.dumps(schema, indent=2)}"
    )
    result = [dict(m) for m in messages]
    # find existing system message and prepend the instruction to it
    for msg in result:
        if msg.get("role") == "system":
            msg["content"] = instruction + "\n\n" + msg["content"]
            return result
    # no system message found — add one at the start
    result.insert(0, {"role": "system", "content": instruction})
    return result


async def _post_to_fallback(
    model: str,
    messages: list[dict[str, Any]],
    max_tokens: int = 4096,
    temperature: float = 0.0,
) -> dict[str, Any]:
    """
    the actual HTTP call to our fallback server.
    kept as a separate function so tests can mock it easily
    """
    url = f"{settings.fallback_server_url}/v1/messages"
    async with httpx.AsyncClient(timeout=65.0) as client:
        resp = await client.post(
            url,
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
        )
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]


async def chat_completion(
    *,
    model: str,
    messages: list[dict[str, Any]],
    response_format: dict[str, Any] | None = None,
    temperature: float = 0.0,
    max_tokens: int = 4096,
) -> LLMResponse:
    """
    main function — sends messages to the fallback server, gets a response back.
    if response_format is a json_schema, the schema gets injected into the system prompt
    so the model knows what shape to output.
    retries twice on connection errors before giving up.
    """
    # map old gpt-* model names to the fallback default
    actual_model = settings.fallback_model if model.startswith("gpt-") else model

    # inject JSON schema as system prompt instruction when structured output is requested
    if response_format and response_format.get("type") == "json_schema":
        schema = response_format.get("json_schema", {}).get("schema", {})
        messages = _inject_json_schema(messages, schema)

    t0 = time.perf_counter()
    last_exc: Exception | None = None

    # retry up to 3 times with exponential backoff
    for attempt in range(3):
        try:
            data = await _post_to_fallback(actual_model, messages, max_tokens=max_tokens, temperature=temperature)
            break
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            last_exc = exc
            if attempt < 2:
                import asyncio
                await asyncio.sleep(2 ** attempt)
            continue
    else:
        raise ConnectionError(f"Fallback server unreachable after 3 attempts: {last_exc}")

    # extract text from the Anthropic-style response format the server returns
    content = ""
    raw_content = data.get("content")
    if isinstance(raw_content, list) and raw_content:
        content = raw_content[0].get("text", "")
    elif isinstance(raw_content, str):
        content = raw_content

    returned_model = data.get("model", actual_model)
    usage_raw = data.get("usage") or {}
    usage: dict[str, int] = {
        "prompt_tokens": int(usage_raw.get("prompt_tokens", 0)) if isinstance(usage_raw, dict) else 0,
        "completion_tokens": int(usage_raw.get("completion_tokens", 0)) if isinstance(usage_raw, dict) else 0,
    }

    elapsed = time.perf_counter() - t0
    _logger.debug(json.dumps({
        "model": returned_model,
        "elapsed_s": round(elapsed, 3),
        "usage": usage,
        "cost_usd": round(_calc_cost(returned_model, usage), 6),
        "request_messages_count": len(messages),
    }))

    return LLMResponse(text=content, model=returned_model, usage=usage)


def extract_json(response: LLMResponse | Any) -> Any:
    """
    parse JSON out of the LLM response.
    LLMs sometimes wrap their output in ```json fences even when told not to,
    so we strip those before parsing.
    also handles the old mock response format from tests (choices[0].message.content)
    """
    if isinstance(response, LLMResponse):
        text = response.text
    else:
        # backward compat — old OpenAI-style mock objects used in some tests
        text = response.choices[0].message.content or ""

    clean = text.strip()

    # strip markdown code fences if present — ```json ... ``` or ``` ... ```
    if clean.startswith("```"):
        lines = clean.splitlines()
        # drop first line (```json or ```) and last line (```)
        inner_lines = lines[1:]
        if inner_lines and inner_lines[-1].strip() == "```":
            inner_lines = inner_lines[:-1]
        clean = "\n".join(inner_lines).strip()

    return json.loads(clean)
