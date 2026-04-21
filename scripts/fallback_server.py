# /// script
# requires-python = ">=3.11"
# dependencies = ["litellm>=1.0.0", "fastapi>=0.115.0", "uvicorn[standard]>=0.30.0"]
# ///
"""
Stateless LLM fallback server — 100% free tier, no credit card required.
Chains 12 providers so something is basically always available.

start with:
    uv run scripts/fallback_server.py
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, AsyncGenerator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from litellm import Router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)
logging.getLogger("LiteLLM Router").setLevel(logging.WARNING)
logging.getLogger("LiteLLM").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Load API keys — try the Desktop first (where the user stores them),
# then fall back to a local api_keys.txt in the project root.
# This way it works both for local dev and if you copy the file elsewhere.
# ---------------------------------------------------------------------------
def load_api_keys() -> None:
    # try these locations in order, use the first one that exists
    candidates = [
        Path("/Users/pc/Desktop/api_keys.txt"),
        Path(__file__).parent.parent / "api_keys.txt",
        Path(__file__).parent / "api_keys.txt",
    ]
    key_file = next((p for p in candidates if p.exists()), None)
    if key_file is None:
        log.warning("api_keys.txt not found in any of: %s", [str(p) for p in candidates])
        log.warning("Keys must be set in the environment instead.")
        return

    loaded: list[str] = []
    with key_file.open() as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if key:
                os.environ[key] = value
                loaded.append(key)
    log.info("Loaded %d key(s) from %s: %s", len(loaded), key_file, ", ".join(loaded))


load_api_keys()


def _key(name: str) -> str | None:
    val = os.environ.get(name)
    if not val:
        log.warning("'%s' not set — that tier will be skipped.", name)
    return val


# ---------------------------------------------------------------------------
# Model list — free tier, ordered by quality for agentic tasks
# ---------------------------------------------------------------------------
model_list: list[dict[str, Any]] = [

    # t0: DeepSeek R1 — best free reasoning, near Claude Opus on coding
    {
        "model_name": "t0-deepseek",
        "litellm_params": {
            "model": "openrouter/deepseek/deepseek-r1:free",
            "api_key": _key("OPENROUTER_API_KEY"),
            "rpm": 20,
            "max_tokens": 8192,
        },
    },

    # t1: Qwen3 235b — MoE model, excellent at structured output
    {
        "model_name": "t1-qwen",
        "litellm_params": {
            "model": "openrouter/qwen/qwen3-235b-a22b:free",
            "api_key": _key("OPENROUTER_API_KEY"),
            "rpm": 20,
            "max_tokens": 8192,
        },
    },

    # t2: SambaNova — 60 RPM, fastest free inference out there
    {
        "model_name": "t2-sambanova",
        "litellm_params": {
            "model": "sambanova/Meta-Llama-3.3-70B-Instruct",
            "api_key": _key("SAMBANOVA_API_KEY"),
            "rpm": 60,
            "max_tokens": 8192,
        },
    },

    # t3: NVIDIA NIM — 40 RPM, solid and reliable
    {
        "model_name": "t3-nvidia",
        "litellm_params": {
            "model": "nvidia_nim/meta/llama-3.1-70b-instruct",
            "api_key": _key("NVIDIA_API_KEY"),
            "rpm": 40,
            "max_tokens": 8192,
        },
    },

    # t4: Cerebras — ultra fast inference, good for classification tasks
    {
        "model_name": "t4-cerebras",
        "litellm_params": {
            "model": "cerebras/llama-3.3-70b",
            "api_key": _key("CEREBRAS_API_KEY"),
            "rpm": 30,
            "max_tokens": 8192,
        },
    },

    # t5: GitHub GPT-4o — 15 RPM, great for summarization
    {
        "model_name": "t5-github",
        "litellm_params": {
            "model": "openai/gpt-4o",
            "api_base": "https://models.inference.ai.azure.com",
            "api_key": _key("GITHUB_API_KEY"),
            "rpm": 15,
            "max_tokens": 8192,
        },
    },
    {
        "model_name": "t5-github-mini",
        "litellm_params": {
            "model": "openai/gpt-4o-mini",
            "api_base": "https://models.inference.ai.azure.com",
            "api_key": _key("GITHUB_API_KEY"),
            "rpm": 15,
            "max_tokens": 8192,
        },
    },

    # t6: Mistral Large — only 1 RPM but high quality when we need it
    {
        "model_name": "t6-mistral",
        "litellm_params": {
            "model": "mistral/mistral-large-latest",
            "api_key": _key("MISTRAL_API_KEY"),
            "rpm": 1,
            "max_tokens": 8192,
        },
    },

    # t7: Groq — fast but the 12k TPM cap makes it bad for long documents
    {
        "model_name": "t7-groq",
        "litellm_params": {
            "model": "groq/llama-3.3-70b-versatile",
            "api_key": _key("GROQ_API_KEY"),
            "rpm": 10,
            "max_tokens": 4096,
        },
    },

    # t8: Gemini Flash — good daily limit, sometimes flaky
    {
        "model_name": "t8-gemini-flash",
        "litellm_params": {
            "model": "gemini/gemini-2.5-flash-lite",
            "api_key": _key("GEMINI_API_KEY"),
            "rpm": 10,
            "max_tokens": 8192,
        },
    },

    # t9: Gemini Pro — best quality Gemini, but only 25 req/day so use sparingly
    {
        "model_name": "t9-gemini-pro",
        "litellm_params": {
            "model": "gemini/gemini-2.5-pro",
            "api_key": _key("GEMINI_API_KEY"),
            "rpm": 2,
            "max_tokens": 8192,
        },
    },

    # t10: Cohere — 5 RPM, reliable final fallback
    {
        "model_name": "t10-cohere",
        "litellm_params": {
            "model": "cohere/command-r-plus-08-2024",
            "api_key": _key("COHERE_API_KEY"),
            "rpm": 5,
            "max_tokens": 4096,
        },
    },

    # t11: OpenRouter Llama — absolute last resort, free but shared limits
    {
        "model_name": "t11-llama-free",
        "litellm_params": {
            "model": "openrouter/meta-llama/llama-3.3-70b-instruct:free",
            "api_key": _key("OPENROUTER_API_KEY"),
            "rpm": 20,
            "max_tokens": 8192,
        },
    },
]

# the fallback chain — if a model fails, try the next ones in order
fallbacks: list[dict[str, list[str]]] = [
    {"t0-deepseek":     ["t1-qwen", "t2-sambanova"]},
    {"t1-qwen":         ["t2-sambanova", "t3-nvidia"]},
    {"t2-sambanova":    ["t3-nvidia", "t4-cerebras"]},
    {"t3-nvidia":       ["t4-cerebras", "t5-github"]},
    {"t4-cerebras":     ["t5-github", "t6-mistral"]},
    {"t5-github":       ["t5-github-mini", "t6-mistral"]},
    {"t5-github-mini":  ["t6-mistral", "t7-groq"]},
    {"t6-mistral":      ["t7-groq", "t8-gemini-flash"]},
    {"t7-groq":         ["t8-gemini-flash", "t9-gemini-pro"]},
    {"t8-gemini-flash": ["t9-gemini-pro", "t10-cohere"]},
    {"t9-gemini-pro":   ["t10-cohere", "t11-llama-free"]},
    {"t10-cohere":      ["t11-llama-free"]},
]

router = Router(
    model_list=model_list,
    fallbacks=fallbacks,
    num_retries=2,
    timeout=60,
    routing_strategy="simple-shuffle",
    set_verbose=False,
)

DEFAULT_MODEL = "t0-deepseek"


# ---------------------------------------------------------------------------
# Context trimmer — keeps system + first 2 + last 6 messages on long sessions
# ---------------------------------------------------------------------------
def trim_context(msgs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(msgs) <= 10:
        return msgs
    system = [m for m in msgs if m.get("role") == "system"]
    non_system = [m for m in msgs if m.get("role") != "system"]
    trimmed = system + non_system[:2] + non_system[-6:]
    log.info("Context trimmed: %d → %d msgs", len(msgs), len(trimmed))
    return trimmed


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="AI020 LLM Fallback Server", version="1.0.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/models")
async def list_models() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {"id": m["model_name"], "object": "model", "owned_by": "fallback-server"}
            for m in model_list
        ],
    }


@app.post("/v1/messages", response_model=None)
async def messages(request: Request) -> StreamingResponse | JSONResponse:
    """Main endpoint — takes messages and returns a completion."""
    try:
        body: dict[str, Any] = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    model: str = body.get("model") or DEFAULT_MODEL
    messages_payload: list[dict[str, Any]] = body.get("messages", [])
    max_tokens: int = body.get("max_tokens", 4096)
    temperature: float = body.get("temperature", 0.7)
    stream: bool = body.get("stream", False)

    if not messages_payload:
        return JSONResponse({"error": "No messages provided"}, status_code=400)

    # remap any unknown model names to the default
    known = {m["model_name"] for m in model_list}
    if model not in known:
        log.warning("Unknown model '%s' → using '%s'", model, DEFAULT_MODEL)
        model = DEFAULT_MODEL

    messages_payload = trim_context(messages_payload)
    log.info("→ model='%s' stream=%s msgs=%d", model, stream, len(messages_payload))

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages_payload,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "drop_params": True,
    }

    if stream:
        return StreamingResponse(_stream(kwargs), media_type="text/event-stream")

    try:
        resp = await router.acompletion(**kwargs)
        content = resp.choices[0].message.content or ""
        log.info("✓ served by '%s'", resp.model)
        return JSONResponse({
            "id": resp.id,
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": content}],
            "model": resp.model,
            "stop_reason": resp.choices[0].finish_reason,
            "usage": resp.usage.model_dump() if resp.usage else None,
        })
    except Exception as exc:
        log.error("All models failed: %s — %r", type(exc).__name__, exc)
        return JSONResponse({"error": str(exc)}, status_code=500)


async def _stream(kwargs: dict[str, Any]) -> AsyncGenerator[bytes, None]:
    try:
        resp = await router.acompletion(**kwargs, stream=True)
        async for chunk in resp:
            yield f"data: {json.dumps(chunk.model_dump())}\n\n".encode()
    except Exception as exc:
        log.error("Stream failed: %s — %r", type(exc).__name__, exc)
        yield f"data: {json.dumps({'error': str(exc)})}\n\n".encode()
    finally:
        yield b"data: [DONE]\n\n"


if __name__ == "__main__":
    log.info("Starting AI020 fallback server on http://0.0.0.0:4000")
    log.info("Models available: %s", [m["model_name"] for m in model_list])
    log.info("Default model: %s", DEFAULT_MODEL)
    uvicorn.run(app, host="0.0.0.0", port=4000, log_level="warning")
