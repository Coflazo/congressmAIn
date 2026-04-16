"""Tests for LibreTranslate wrapper — mocked HTTP to avoid real network calls."""

from unittest.mock import MagicMock, patch

import pytest


def test_same_language_returns_input():
    """Translating nl→nl must return input unchanged, no HTTP call."""
    from services.translate import translate

    result = translate("Hallo wereld", source="nl", target="nl")
    assert result == "Hallo wereld"


def test_translate_calls_libretranslate():
    """translate() should POST to /translate and return translatedText."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"translatedText": "Hello world"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from services.translate import translate

        result = translate("Hallo wereld", source="nl", target="en")

    assert result == "Hello world"
    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    assert "/translate" in call_kwargs[0][0]
    assert call_kwargs[1]["json"]["source"] == "nl"
    assert call_kwargs[1]["json"]["target"] == "en"


def test_translate_uses_db_cache(db):
    """translate() with db arg should return cached value without HTTP call."""
    from models import Translation
    from services.translate import _make_hash, translate

    text = "De vergadering is geopend."
    content_hash = _make_hash(text, "nl", "en")

    cached = Translation(
        meeting_id=0,
        target_lang="en",
        source_lang="nl",
        content_hash=content_hash,
        source_text=text,
        translated_text="The meeting has been opened.",
    )
    db.add(cached)
    db.commit()

    with patch("httpx.Client") as mock_client_cls:
        result = translate(text, source="nl", target="en", db=db)
        mock_client_cls.assert_not_called()

    assert result == "The meeting has been opened."


def test_batch_translate_returns_list():
    """batch_translate should return same-length list."""
    import services.translate  # ensure module is loaded before patching
    from services.translate import batch_translate

    with patch("services.translate.translate") as mock_translate:
        mock_translate.side_effect = lambda text, source="nl", target="en", db=None: f"[{text}]"
        results = batch_translate(["Een", "Twee", "Drie"], source="nl", target="en")

    assert len(results) == 3


def test_check_libretranslate_ok():
    """check_libretranslate returns True when all 5 languages present."""
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"code": "nl"}, {"code": "en"}, {"code": "tr"}, {"code": "pl"}, {"code": "uk"}
    ]
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from services.translate import check_libretranslate

        result = check_libretranslate()

    assert result is True


def test_check_libretranslate_missing_lang():
    """check_libretranslate returns False when a language is missing."""
    mock_response = MagicMock()
    mock_response.json.return_value = [{"code": "nl"}, {"code": "en"}]  # missing tr, pl, uk
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from services.translate import check_libretranslate

        result = check_libretranslate()

    assert result is False


def test_check_libretranslate_unreachable():
    """check_libretranslate returns False on connection error."""
    import httpx

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.ConnectError("refused")
        mock_client_cls.return_value = mock_client

        from services.translate import check_libretranslate

        result = check_libretranslate()

    assert result is False
