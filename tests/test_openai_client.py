"""Tests for the LLM client — mocked so we never actually hit the network."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest


def _make_fallback_response(text: str = '{"answer": "test"}', model: str = "t0-deepseek") -> dict:
    """builds a fake response that looks like what the fallback server returns"""
    return {
        "id": "test-id",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": text}],
        "model": model,
        "stop_reason": "end_turn",
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
    }


def test_chat_completion_calls_fallback_server():
    """chat_completion should POST to the fallback server with the right params."""
    fake_data = _make_fallback_response()

    with patch("services.openai_client._post_to_fallback", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = fake_data
        from services.openai_client import chat_completion

        result = asyncio.run(
            chat_completion(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Hello"}],
            )
        )

    # should have called our internal helper
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    # gpt-4o gets remapped to the configured fallback model
    assert call_kwargs[0][1] == [{"role": "user", "content": "Hello"}]
    assert result.text == '{"answer": "test"}'
    assert result.model == "t0-deepseek"


def test_extract_json_parses_llm_response():
    """extract_json should pull JSON out of an LLMResponse."""
    from services.openai_client import LLMResponse, extract_json

    response = LLMResponse(text='{"key": "value", "number": 42}', model="t0-deepseek")
    result = extract_json(response)

    assert result == {"key": "value", "number": 42}


def test_extract_json_strips_markdown_fences():
    """LLMs often wrap JSON in ```json fences even when told not to — we strip those."""
    from services.openai_client import LLMResponse, extract_json

    response = LLMResponse(
        text='```json\n{"key": "value"}\n```',
        model="t0-deepseek",
    )
    result = extract_json(response)
    assert result == {"key": "value"}


def test_extract_json_invalid_raises():
    """extract_json should raise JSONDecodeError on malformed JSON."""
    from services.openai_client import LLMResponse, extract_json

    response = LLMResponse(text="not valid json {", model="t0-deepseek")
    with pytest.raises(json.JSONDecodeError):
        extract_json(response)


def test_chat_completion_injects_json_schema():
    """when response_format is json_schema, the schema should appear in the system prompt."""
    fake_data = _make_fallback_response('{"result": "ok"}')
    schema = {"type": "object", "properties": {"result": {"type": "string"}}}
    response_format = {
        "type": "json_schema",
        "json_schema": {"name": "test", "strict": True, "schema": schema},
    }

    with patch("services.openai_client._post_to_fallback", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = fake_data
        from services.openai_client import chat_completion

        asyncio.run(
            chat_completion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Summarize."}],
                response_format=response_format,
            )
        )

    # the messages passed to _post_to_fallback should now have a system message with the schema
    actual_messages = mock_post.call_args[0][1]
    system_msgs = [m for m in actual_messages if m.get("role") == "system"]
    assert system_msgs, "should have added a system message with schema"
    assert "json" in system_msgs[0]["content"].lower()


def test_cost_calculation():
    """_calc_cost should compute cost from usage dict — kept from old tests."""
    from services.openai_client import _calc_cost

    # gpt-4o: $2.50/1M input, $10.00/1M output
    cost = _calc_cost("gpt-4o", {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000})
    assert abs(cost - 12.50) < 0.01


def test_cost_calculation_free_tier():
    """free tier models should cost zero."""
    from services.openai_client import _calc_cost

    cost = _calc_cost("t0-deepseek", {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000})
    assert cost == 0.0


def test_cost_calculation_mini():
    """_calc_cost for gpt-4o-mini — $0.15/1M input, $0.60/1M output."""
    from services.openai_client import _calc_cost

    cost = _calc_cost("gpt-4o-mini", {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000})
    assert abs(cost - 0.75) < 0.01
