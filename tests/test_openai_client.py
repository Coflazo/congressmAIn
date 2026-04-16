"""Tests for OpenAI wrapper — mock-based, no real API calls."""

from unittest.mock import MagicMock, patch

import pytest


def _make_completion(content: str = '{"answer": "test"}', model: str = "gpt-4o") -> MagicMock:
    completion = MagicMock()
    completion.choices = [MagicMock()]
    completion.choices[0].message.content = content
    completion.choices[0].finish_reason = "stop"
    completion.usage = MagicMock()
    completion.usage.model_dump.return_value = {"prompt_tokens": 100, "completion_tokens": 50}
    return completion


def test_chat_completion_calls_openai():
    """chat_completion should call OpenAI client with correct params."""
    mock_completion = _make_completion()

    with patch("services.openai_client._client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_completion
        from services.openai_client import chat_completion

        result = chat_completion(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}],
        )

    assert result is mock_completion
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == "gpt-4o"


def test_extract_json_parses_content():
    """extract_json should parse JSON from completion content."""
    from services.openai_client import extract_json

    completion = _make_completion('{"key": "value", "number": 42}')
    result = extract_json(completion)

    assert result == {"key": "value", "number": 42}


def test_extract_json_invalid_raises():
    """extract_json raises ValueError on malformed JSON."""
    import json

    from services.openai_client import extract_json

    completion = _make_completion("not valid json {")
    with pytest.raises(json.JSONDecodeError):
        extract_json(completion)


def test_chat_completion_includes_response_format():
    """response_format passed through to OpenAI client when provided."""
    mock_completion = _make_completion()
    schema = {"type": "json_schema", "json_schema": {"name": "test", "strict": True, "schema": {}}}

    with patch("services.openai_client._client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_completion
        from services.openai_client import chat_completion

        chat_completion(model="gpt-4o-mini", messages=[], response_format=schema)

    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["response_format"] == schema


def test_cost_calculation():
    """_calc_cost should compute cost from usage dict."""
    from services.openai_client import _calc_cost

    # gpt-4o: $2.50/1M input, $10.00/1M output
    cost = _calc_cost("gpt-4o", {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000})
    assert abs(cost - 12.50) < 0.01


def test_cost_calculation_mini():
    """_calc_cost for gpt-4o-mini."""
    from services.openai_client import _calc_cost

    cost = _calc_cost("gpt-4o-mini", {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000})
    assert abs(cost - 0.75) < 0.01
