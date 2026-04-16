"""LibreTranslate wrapper — async-first, 120s timeout, 3 retries, SHA256 DB cache."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
from sqlalchemy.exc import IntegrityError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config import settings

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

SUPPORTED_LANGUAGES = ["nl", "en", "tr", "pl", "uk"]
TARGET_LANGUAGES = ["en", "tr", "pl", "uk"]

_log_path = Path(__file__).parent.parent / "logs" / "translate.log"
_log_path.parent.mkdir(exist_ok=True)

_file_handler = logging.FileHandler(_log_path)
_file_handler.setFormatter(logging.Formatter("%(message)s"))

_logger = logging.getLogger("ai020.translate")
_logger.setLevel(logging.DEBUG)
if not _logger.handlers:
    _logger.addHandler(_file_handler)
_logger.propagate = False


def _make_hash(text: str, source: str, target: str) -> str:
    key = f"{source}:{target}:{text}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _log_call(
    *,
    source: str,
    target: str,
    chars: int,
    cached: bool,
    elapsed: float | None = None,
    note: str | None = None,
) -> None:
    record = {
        "source": source,
        "target": target,
        "chars": chars,
        "cached": cached,
        "elapsed_s": round(elapsed, 3) if elapsed is not None else None,
        "note": note,
    }
    _logger.debug(json.dumps(record))


def _get_cached_translation(text: str, source: str, target: str, db: "Session | None") -> str | None:
    if db is None:
        return None

    from models import Translation

    content_hash = _make_hash(text, source, target)
    cached = db.query(Translation).filter_by(
        content_hash=content_hash,
        source_lang=source,
        target_lang=target,
    ).first()
    return cached.translated_text if cached else None


def _store_translation(
    text: str,
    translated_text: str,
    source: str,
    target: str,
    db: "Session | None",
    *,
    meeting_id: int = 0,
    summary_json: dict[str, Any] | None = None,
) -> None:
    if db is None:
        return

    from models import Translation

    content_hash = _make_hash(text, source, target)
    existing = db.query(Translation).filter_by(
        content_hash=content_hash,
        source_lang=source,
        target_lang=target,
    ).first()
    if existing:
        if summary_json is not None and existing.summary_json is None:
            existing.summary_json = summary_json
            if meeting_id:
                existing.meeting_id = meeting_id
            db.commit()
        return

    db.add(
        Translation(
            meeting_id=meeting_id,
            target_lang=target,
            source_lang=source,
            content_hash=content_hash,
            source_text=text,
            translated_text=translated_text,
            summary_json=summary_json,
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()


@retry(
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _call_libretranslate_sync(text: str, source: str, target: str) -> str:
    payload: dict[str, str] = {"q": text, "source": source, "target": target, "format": "text"}
    if settings.libretranslate_api_key:
        payload["api_key"] = settings.libretranslate_api_key

    started = time.perf_counter()
    with httpx.Client(timeout=120.0) as client:
        response = client.post(f"{settings.libretranslate_url}/translate", json=payload)
        response.raise_for_status()
    _log_call(
        source=source,
        target=target,
        chars=len(text),
        cached=False,
        elapsed=time.perf_counter() - started,
    )
    result = response.json()["translatedText"]
    if _looks_mangled(text, result):
        _log_call(
            source=source,
            target=target,
            chars=len(text),
            cached=False,
            note="possible_entity_mangling",
        )
    return result


def _looks_mangled(source_text: str, translated_text: str) -> bool:
    digits_in = any(ch.isdigit() for ch in source_text)
    digits_out = any(ch.isdigit() for ch in translated_text)
    return digits_in and not digits_out


async def translate_async(
    text: str,
    source: str = "nl",
    target: str = "en",
    db: "Session | None" = None,
    *,
    meeting_id: int = 0,
    summary_json: dict[str, Any] | None = None,
) -> str:
    if source == target or not text:
        return text

    return translate(
        text,
        source=source,
        target=target,
        db=db,
        meeting_id=meeting_id,
        summary_json=summary_json,
    )


async def batch_translate_async(
    texts: list[str],
    source: str = "nl",
    target: str = "en",
    db: "Session | None" = None,
    *,
    meeting_id: int = 0,
) -> list[str]:
    return [
        await translate_async(text, source=source, target=target, db=db, meeting_id=meeting_id)
        for text in texts
    ]


async def fan_out_translation(
    texts: list[str],
    source: str = "nl",
    targets: list[str] = TARGET_LANGUAGES,
    db: "Session | None" = None,
    *,
    meeting_id: int = 0,
) -> dict[str, list[str]]:
    semaphore = asyncio.Semaphore(3)

    async def _translate_one(target: str, text: str) -> str:
        async with semaphore:
            return await translate_async(text, source=source, target=target, db=db, meeting_id=meeting_id)

    results: dict[str, list[str]] = {}
    for target in targets:
        results[target] = list(await asyncio.gather(*[_translate_one(target, text) for text in texts]))
    return results


def translate(
    text: str,
    source: str = "nl",
    target: str = "en",
    db: "Session | None" = None,
    *,
    meeting_id: int = 0,
    summary_json: dict[str, Any] | None = None,
) -> str:
    if source == target or not text:
        return text

    cached = _get_cached_translation(text, source, target, db)
    if cached is not None:
        _log_call(source=source, target=target, chars=len(text), cached=True)
        if summary_json is not None:
            _store_translation(text, cached, source, target, db, meeting_id=meeting_id, summary_json=summary_json)
        return cached

    translated = _call_libretranslate_sync(text, source, target)
    _store_translation(
        text,
        translated,
        source,
        target,
        db,
        meeting_id=meeting_id,
        summary_json=summary_json,
    )
    return translated


def batch_translate(
    texts: list[str],
    source: str = "nl",
    target: str = "en",
    db: "Session | None" = None,
    *,
    meeting_id: int = 0,
) -> list[str]:
    results = []
    for text in texts:
        kwargs: dict[str, Any] = {"source": source, "target": target, "db": db}
        if meeting_id:
            kwargs["meeting_id"] = meeting_id
        results.append(translate(text, **kwargs))
    return results


translate_sync = translate


@retry(
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def check_libretranslate() -> bool:
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{settings.libretranslate_url}/languages")
            response.raise_for_status()
        codes = {lang["code"] for lang in response.json()}
        return all(lang in codes for lang in SUPPORTED_LANGUAGES)
    except Exception:
        return False
