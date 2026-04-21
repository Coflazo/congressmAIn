from __future__ import annotations

import asyncio
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pdfplumber
from pypdf import PdfReader
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from models import Meeting, MeetingStatus, Segment
from schemas.meeting import AgendaItem, Commitment, MeetingMeta, MeetingSummary, VoteByParty, Votes
from services import openai_client
from services.translate import TARGET_LANGUAGES, _get_cached_translation, _store_translation
from taxonomy import TOPICS

MONTHS = {
    "januari": "01",
    "februari": "02",
    "maart": "03",
    "april": "04",
    "mei": "05",
    "juni": "06",
    "juli": "07",
    "augustus": "08",
    "september": "09",
    "oktober": "10",
    "november": "11",
    "december": "12",
}

TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "housing": ("woning", "huisvesting", "huur", "sluisbuurt", "bestemmingsplan", "bouw"),
    "climate": ("klimaat", "verduurzaming", "isolatie", "warmtepomp", "zonnepanelen", "groen"),
    "infrastructure": ("verkeer", "fietspad", "kruispunt", "busbaan", "openbaar vervoer", "weg"),
    "social-affairs": ("maatschappelijke opvang", "jeugdzorg", "statushouder", "sociale zaken", "kwetsbare groepen"),
    "education": ("school", "onderwijs", "basisschool"),
    "finance": ("budget", "begroting", "investering", "kosten", "euro", "miljoen"),
    "culture": ("cultuur", "erfgoed", "kunst", "monumenten"),
    "digital-affairs": ("ict", "digitale", "data"),
    "healthcare": ("zorg", "gezondheid"),
}

SPEAKER_RE = re.compile(
    r"^(?P<label>(?:De heer|De mevrouw|Mevrouw|Mw\.|Dhr\.|Voorzitter|Wethouder|Burgemeester|De VOORZITTER|VOORZITTER)[^:\n]{0,120}):\s*(?P<content>.*)$",
    re.IGNORECASE,
)
VOTE_HEADER_RE = re.compile(r"(?m)^STEMMING\s+(?P<title>[^:\n]+):\s*$")
AGENDA_RE = re.compile(r"(?m)^AGENDAPUNT\s+(?P<number>\d+):\s*(?P<title>.+)$")

_SUMMARY_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "skills" / "output-schema.json"


@dataclass
class ExtractedPage:
    page_number: int
    text: str


@dataclass
class ParsedSegment:
    order_idx: int
    speaker: str | None
    party: str | None
    role: str | None
    text: str
    page: int | None
    bbox: list[float] | None
    intent: str | None


@dataclass
class VoteBlock:
    title: str
    votes: Votes
    result: str | None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _storage_dir() -> Path:
    path = (Path(__file__).resolve().parents[1] / settings.storage_dir).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _normalize_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _dutch_date_to_iso(text: str) -> str | None:
    match = re.search(r"(\d{1,2})\s+([A-Za-zé]+)\s+(20\d{2})", text, re.IGNORECASE)
    if not match:
        return None
    day, month_name, year = match.groups()
    month = MONTHS.get(month_name.lower())
    if not month:
        return None
    return f"{year}-{month}-{int(day):02d}"


def extract_text(pdf_path: str) -> tuple[list[ExtractedPage], str]:
    path = Path(pdf_path)
    if path.suffix.lower() == ".txt":
        text = path.read_text(encoding="utf-8")
        return [ExtractedPage(page_number=1, text=text)], text

    pages: list[ExtractedPage] = []
    reader = PdfReader(str(path))
    for idx, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(ExtractedPage(page_number=idx, text=text))

    full_text = "\n\n".join(page.text for page in pages if page.text.strip())
    if full_text.strip():
        return pages, _normalize_text(full_text)

    pages = []
    with pdfplumber.open(str(path)) as pdf:
        for idx, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append(ExtractedPage(page_number=idx, text=text))
    return pages, _normalize_text("\n\n".join(page.text for page in pages if page.text.strip()))


def _parse_label(label: str) -> tuple[str | None, str | None, str | None]:
    raw = label.strip()
    raw = re.sub(r"\s+", " ", raw)
    if "voorzitter" in raw.lower():
        return "Voorzitter", None, "voorzitter"
    if raw.lower().startswith("wethouder"):
        speaker = raw.split(" ", 1)[1].strip() if " " in raw else "Wethouder"
        return speaker, None, "wethouder"
    if raw.lower().startswith("burgemeester"):
        speaker = raw.split(" ", 1)[1].strip() if " " in raw else "Burgemeester"
        return speaker, None, "burgemeester"

    party_match = re.search(r"\(([^)]+)\)", raw)
    party = party_match.group(1).strip() if party_match else None
    cleaned = re.sub(r"\([^)]+\)", "", raw).strip()
    cleaned = re.sub(r"^(De heer|De mevrouw|Mevrouw|Mw\.|Dhr\.)\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.title()
    return cleaned or None, party, "raadslid"


def _intent_for_text(text: str) -> str:
    lowered = text.lower()
    if "stemming" in lowered or "aangenomen" in lowered or "verworpen" in lowered:
        return "vote"
    if "motie" in lowered or "amendement" in lowered:
        return "motion"
    if "?" in text or "kan de wethouder" in lowered or "wij vragen" in lowered:
        return "question"
    return "statement"


def parse_segments(pages: list[ExtractedPage]) -> list[ParsedSegment]:
    segments: list[ParsedSegment] = []
    current: dict[str, Any] | None = None
    order_idx = 0

    def flush() -> None:
        nonlocal current, order_idx
        if not current:
            return
        text = _normalize_text("\n".join(current["lines"]))
        if text:
            segments.append(
                ParsedSegment(
                    order_idx=order_idx,
                    speaker=current["speaker"],
                    party=current["party"],
                    role=current["role"],
                    text=text,
                    page=current["page"],
                    bbox=current["bbox"],
                    intent=_intent_for_text(text),
                )
            )
            order_idx += 1
        current = None

    for page in pages:
        lines = [line.strip() for line in page.text.splitlines()]
        page_line_count = max(1, len(lines))
        for line_idx, line in enumerate(lines):
            if not line:
                continue
            vote_match = re.match(r"^(STEMMING\b.*)$", line, flags=re.IGNORECASE)
            if vote_match:
                flush()
                top = min(0.95, 0.05 + (line_idx / page_line_count))
                current = {
                    "speaker": "Stemming",
                    "party": None,
                    "role": "stemming",
                    "page": page.page_number,
                    "bbox": [0.08, top, 0.92, min(0.99, top + 0.06)],
                    "lines": [line],
                }
                continue

            speaker_match = SPEAKER_RE.match(line)
            if speaker_match:
                flush()
                speaker, party, role = _parse_label(speaker_match.group("label"))
                top = min(0.95, 0.05 + (line_idx / page_line_count))
                current = {
                    "speaker": speaker,
                    "party": party,
                    "role": role,
                    "page": page.page_number,
                    "bbox": [0.08, top, 0.92, min(0.99, top + 0.08)],
                    "lines": [speaker_match.group("content").strip()],
                }
            elif current:
                current["lines"].append(line)
    flush()
    return segments


def _parse_votes_line(label: str, text: str, votes: Votes) -> None:
    if "geen" in text.lower():
        count = 0
        items: list[str] = []
    else:
        count_match = re.search(r"—\s*(\d+)\s*stem", text)
        count = int(count_match.group(1)) if count_match else None
        items = [part.strip() for part in text.split("—")[0].split(",") if part.strip()]
    if label == "voor":
        votes.for_ = count
        if count and votes.against in (0, None):
            votes.unanimous = votes.unanimous or False
    elif label == "tegen":
        votes.against = count
        if count == 0:
            votes.unanimous = True
    elif label == "onthoudingen":
        votes.abstentions = count

    for item in items:
        match = re.match(r"(.+?)\s*\((\d+)\)$", item)
        if not match:
            continue
        party = match.group(1).strip()
        per_party_vote = "for" if label == "voor" else "against" if label == "tegen" else "abstention"
        votes.by_party.append(VoteByParty(party=party, vote=per_party_vote))


def parse_vote_blocks(text: str) -> list[VoteBlock]:
    matches = list(VOTE_HEADER_RE.finditer(text))
    blocks: list[VoteBlock] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        chunk = text[start:end].strip()
        votes = Votes(by_party=[])
        result: str | None = None
        for line in chunk.splitlines():
            clean = line.strip()
            if not clean:
                continue
            label_match = re.match(r"^(Voor|Tegen|Onthoudingen):\s*(.+)$", clean, flags=re.IGNORECASE)
            if label_match:
                _parse_votes_line(label_match.group(1).lower(), label_match.group(2), votes)
                continue
            if "AANGENOMEN" in clean.upper():
                result = "aangenomen"
                if votes.against in (0, None):
                    votes.unanimous = True
            elif "VERWORPEN" in clean.upper():
                result = "verworpen"
            elif "AANGEHOUDEN" in clean.upper():
                result = "aangehouden"
            elif "INGETROKKEN" in clean.upper():
                result = "ingetrokken"
        blocks.append(VoteBlock(title=match.group("title").strip(), votes=votes, result=result))
    return blocks


def _clean_summary_text(block: str) -> str:
    lines = []
    for line in block.splitlines():
        clean = line.strip()
        if not clean or clean.startswith("STEMMING "):
            continue
        clean = SPEAKER_RE.sub(lambda m: m.group("content").strip(), clean)
        if clean:
            lines.append(clean)
    text = " ".join(lines)
    return re.sub(r"\s+", " ", text).strip()


def _first_sentences(text: str, count: int = 2) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    selected = [sentence.strip() for sentence in sentences if sentence.strip()][:count]
    return " ".join(selected).strip()


def _find_cost(text: str) -> str | None:
    patterns = [
        r"(\d+[.,]?\d*\s*miljoen euro)",
        r"(€\s?\d+[.,]?\d*)",
        r"(\d+[.,]?\d*\s*euro)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _topic_tags(text: str) -> list[str]:
    lowered = text.lower()
    scored = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(lowered.count(keyword) for keyword in keywords)
        if score:
            scored.append((score, topic))
    scored.sort(reverse=True)
    tags = [topic for _, topic in scored[:5]]
    return tags if tags else ["digital-affairs"]


def _resident_impact(title: str, block: str, decision_detail: str) -> str:
    lowered = f"{title} {block}".lower()
    if "park" in lowered or "groen" in lowered:
        return "Bewoners krijgen meer groen, ruimte om te spelen en een prettigere buurt."
    if "huisvesting" in lowered or "woning" in lowered:
        return "Bewoners uit kwetsbare groepen krijgen sneller toegang tot huisvesting."
    if "verduurzaming" in lowered or "isolatie" in lowered:
        return "Huiseigenaren kunnen steun krijgen om hun woning energiezuiniger te maken."
    if "verkeer" in lowered or "fietspad" in lowered or "snelheid" in lowered:
        return "De straat wordt veiliger voor fietsers, voetgangers en omwonenden."
    if "school" in lowered:
        return "Ouders en leerlingen krijgen duidelijkheid over de planning van de school."
    return decision_detail or "De uitkomst van dit punt kan gevolgen hebben voor bewoners en de buurt."


def _parse_commitments(text: str) -> list[Commitment]:
    commitments: list[Commitment] = []
    for match in re.finditer(r"(Ik zeg toe dat[^.]+(?:\.[^.]+)?)", text, flags=re.IGNORECASE):
        description = match.group(1).strip()
        deadline_match = re.search(r"binnen\s+([^.]+)", description, flags=re.IGNORECASE)
        commitments.append(
            Commitment(
                by="College",
                description=description,
                deadline=deadline_match.group(1).strip() if deadline_match else None,
            )
        )
    return commitments


def _parse_parties_present(text: str) -> list[dict[str, Any]]:
    match = re.search(r"Aanwezige fracties:\s*(.+)", text, flags=re.IGNORECASE)
    if not match:
        return []
    parties = []
    for item in match.group(1).split(","):
        item = item.strip()
        party_match = re.match(r"(.+?)\s*\((\d+)\s*zetels?\)", item, flags=re.IGNORECASE)
        if not party_match:
            continue
        parties.append({"name": party_match.group(1).strip(), "seats": int(party_match.group(2))})
    return parties


def parse_meeting_meta(text: str) -> MeetingMeta:
    municipality = None
    municipality_match = re.search(r"Gemeente\s+([A-Za-zÀ-ÿ\-\s]+)", text)
    if municipality_match:
        municipality = municipality_match.group(1).strip()

    date = None
    for pattern in [r"Datum:\s*([^\n]+)", r"Vergaderdatum\s+([^\n]+)"]:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            date = _dutch_date_to_iso(match.group(1))
            if date:
                break

    start_time = None
    for pattern in [r"Aanvang:\s*([\d:.]+)", r"opent de vergadering om\s*([\d:.]+)\s*uur"]:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            start_time = match.group(1).replace(".", ":")[:5]
            break

    end_time = None
    for pattern in [r"sluit deze vergadering om\s*([\d:.]+)", r"sluit de vergadering om\s*([\d:.]+)"]:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            end_time = match.group(1).replace(".", ":")[:5]
            break

    return MeetingMeta(
        municipality=municipality,
        date=date,
        start_time=start_time,
        end_time=end_time,
        parties_present=_parse_parties_present(text),
    )


def _agenda_matches(text: str) -> list[tuple[int | None, str, str]]:
    matches = list(AGENDA_RE.finditer(text))
    if matches:
        items: list[tuple[int | None, str, str]] = []
        for idx, match in enumerate(matches):
            start = match.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            items.append((int(match.group("number")), match.group("title").strip(), text[start:end].strip()))
        return items

    generic_matches = list(re.finditer(r"(?m)^\s*(\d+)\.\s*$", text))
    items = []
    for idx, match in enumerate(generic_matches):
        start = match.end()
        end = generic_matches[idx + 1].start() if idx + 1 < len(generic_matches) else len(text)
        block = text[start:end].strip()
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        title = lines[0]
        if len(title) > 120 or title.lower().startswith("vergaderdatum"):
            continue
        items.append((int(match.group(1)), title, block))
    return items


def build_rule_based_summary(text: str) -> tuple[MeetingSummary, list[str]]:
    meta = parse_meeting_meta(text)
    commitments = _parse_commitments(text)
    topics: list[str] = []
    agenda_items: list[AgendaItem] = []

    for number, title, block in _agenda_matches(text):
        vote_blocks = parse_vote_blocks(block)
        final_vote = next(
            (vote for vote in reversed(vote_blocks) if "motie" not in vote.title.lower() and "amendement" not in vote.title.lower()),
            vote_blocks[-1] if vote_blocks else None,
        )
        narrative = _clean_summary_text(block)
        topic_summary = _first_sentences(narrative, count=2)
        decision_detail = topic_summary
        cost = _find_cost(block)
        tags = _topic_tags(f"{title}\n{block}")
        topics.extend(tags)

        amendments = []
        motions = []
        for vote in vote_blocks:
            record = {
                "submitted_by": None,
                "description": vote.title,
                "decision": vote.result or "geen_stemming",
                "votes_for": vote.votes.for_,
                "votes_against": vote.votes.against,
            }
            if "amendement" in vote.title.lower():
                amendments.append(record)
            elif "motie" in vote.title.lower():
                motions.append(record)

        agenda_items.append(
            AgendaItem(
                number=number,
                title=title.title(),
                topic_summary=topic_summary or title,
                decision=final_vote.result if final_vote and final_vote.result else "geen_stemming",
                decision_detail=decision_detail or title,
                votes=final_vote.votes if final_vote else None,
                amendments=amendments,
                motions=motions,
                resident_impact=_resident_impact(title, block, decision_detail),
                cost=cost,
            )
        )

    if not agenda_items:
        condensed = _first_sentences(_clean_summary_text(text), count=3)
        inferred_topics = _topic_tags(text)
        topics.extend(inferred_topics)
        agenda_items.append(
            AgendaItem(
                number=1,
                title="Samenvatting vergadering",
                topic_summary=condensed,
                decision="geen_stemming",
                decision_detail=condensed,
                resident_impact="De vergadering bevat onderwerpen die gevolgen hebben voor bewoners en het bestuur.",
                cost=_find_cost(text),
            )
        )

    unique_topics = []
    for topic in topics:
        if topic in TOPICS and topic not in unique_topics:
            unique_topics.append(topic)

    summary = MeetingSummary(
        meeting=meta,
        agenda_items=agenda_items,
        commitments=commitments,
    )
    return summary, unique_topics[:5]


def _response_format_schema() -> dict[str, Any]:
    schema = json.loads(_SUMMARY_SCHEMA_PATH.read_text(encoding="utf-8"))
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "meeting_summary",
            "strict": True,
            "schema": schema,
        },
    }


def _llm_available() -> bool:
    # always try the fallback server if it's configured — it handles availability internally
    return bool(settings.fallback_server_url)


async def maybe_refine_summary_with_openai(text: str, fallback: MeetingSummary) -> MeetingSummary:
    """
    try to improve the rule-based summary using the LLM.
    if the LLM is unavailable or fails, just return the rule-based fallback — no crash.
    """
    if not _llm_available():
        return fallback

    try:
        prompt = (
            "Maak een feitelijke samenvatting van deze Nederlandse raadsvergadering. "
            "Gebruik alleen informatie uit het transcript. "
            "Schrijf in eenvoudig Nederlands op B1-niveau. "
            "Volg het JSON-schema exact. "
            "Elke beslissing moet bevatten wat is besloten, de stemming, en wat dit betekent voor bewoners.\n\n"
            f"Transcript:\n{text[:40000]}"
        )
        completion = await openai_client.chat_completion(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Je bent een zorgvuldige samenvatter van Nederlandse gemeenteraadsvergaderingen."},
                {"role": "user", "content": prompt},
            ],
            response_format=_response_format_schema(),
        )
        data = openai_client.extract_json(completion)
        return MeetingSummary.model_validate(data)
    except Exception:
        # LLM failed — the rule-based summary is good enough to ship
        return fallback


async def translate_summary(summary: MeetingSummary, db: Session, meeting_id: int) -> dict[str, dict[str, Any]]:
    source = summary.model_dump(by_alias=True)
    translations: dict[str, dict[str, Any]] = {}

    async def _translate_texts(texts: list[str], target: str) -> list[str]:
        semaphore = asyncio.Semaphore(3)

        async def _call(text: str) -> str:
            payload: dict[str, str] = {"q": text, "source": "nl", "target": target, "format": "text"}
            async with semaphore:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(f"{settings.libretranslate_url}/translate", json=payload)
                    response.raise_for_status()
                    return response.json()["translatedText"]

        return list(await asyncio.gather(*[_call(text) for text in texts]))

    for target in TARGET_LANGUAGES:
        serialized_source = json.dumps(source, ensure_ascii=False, sort_keys=True)
        cached_summary = _get_cached_translation(serialized_source, "nl", target, db)
        if cached_summary:
            existing = json.loads(cached_summary)
            translations[target] = existing
            _store_translation(
                serialized_source,
                cached_summary,
                "nl",
                target,
                db,
                meeting_id=meeting_id,
                summary_json=existing,
            )
            continue

        translated = json.loads(json.dumps(source))
        paths: list[tuple[str, int | None, str, int | None, str | None]] = []
        texts: list[str] = []

        municipality = translated["meeting"].get("municipality")
        if municipality:
            paths.append(("meeting", None, "municipality", None, None))
            texts.append(municipality)

        for item_index, item in enumerate(translated["agenda_items"]):
            for field in ["title", "topic_summary", "decision_detail", "resident_impact", "cost"]:
                if item.get(field):
                    paths.append(("agenda_items", item_index, field, None, None))
                    texts.append(item[field])
            for amendment_index, amendment in enumerate(item.get("amendments", [])):
                if amendment.get("description"):
                    paths.append(("agenda_items", item_index, "amendments", amendment_index, "description"))
                    texts.append(amendment["description"])
            for motion_index, motion in enumerate(item.get("motions", [])):
                if motion.get("description"):
                    paths.append(("agenda_items", item_index, "motions", motion_index, "description"))
                    texts.append(motion["description"])

        for commitment_index, commitment in enumerate(translated["commitments"]):
            if commitment.get("description"):
                paths.append(("commitments", commitment_index, "description", None, None))
                texts.append(commitment["description"])

        translated_values = await _translate_texts(texts, target) if texts else []
        for path, value in zip(paths, translated_values, strict=False):
            section, item_index, field, nested_index, nested_field = path
            if section == "meeting":
                translated["meeting"][field] = value
            elif section == "commitments":
                translated["commitments"][item_index][field] = value  # type: ignore[index]
            elif nested_index is None:
                translated[section][item_index][field] = value  # type: ignore[index]
            else:
                translated[section][item_index][field][nested_index][nested_field] = value  # type: ignore[index]

        serialized_target = json.dumps(translated, ensure_ascii=False, sort_keys=True)
        _store_translation(
            serialized_source,
            serialized_target,
            "nl",
            target,
            db,
            meeting_id=meeting_id,
            summary_json=translated,
        )
        translations[target] = translated
    return translations


def _copy_pdf(pdf_path: str, meeting_id: int) -> str:
    source = Path(pdf_path)
    suffix = source.suffix.lower() or ".pdf"
    destination = _storage_dir() / f"meeting-{meeting_id}{suffix}"
    shutil.copy2(source, destination)
    return str(destination)


def _store_segments(meeting: Meeting, parsed_segments: list[ParsedSegment], db: Session) -> None:
    db.query(Segment).filter(Segment.meeting_id == meeting.id).delete()
    for segment in parsed_segments:
        db.add(
            Segment(
                meeting_id=meeting.id,
                order_idx=segment.order_idx,
                speaker=segment.speaker,
                party=segment.party,
                role=segment.role,
                text=segment.text,
                page=segment.page,
                bbox=segment.bbox,
                intent=segment.intent,
            )
        )
    db.commit()


async def _ingest_with_session(
    *,
    pdf_path: str,
    source_email: str | None,
    subject: str | None,
    meeting_id: int | None,
    db: Session,
) -> Meeting:
    created_new = False
    if meeting_id is None:
        meeting = Meeting(
            title=subject or Path(pdf_path).stem.replace("-", " ").title(),
            source_email=source_email,
            status=MeetingStatus.processing,
            processing_started_at=datetime.now(timezone.utc),
        )
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
        created_new = True
    else:
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if meeting is None:
            raise ValueError(f"Meeting {meeting_id} not found")
        meeting.status = MeetingStatus.processing
        meeting.processing_started_at = datetime.now(timezone.utc)
        meeting.error_message = None
        db.commit()

    try:
        meeting.pdf_path = _copy_pdf(pdf_path, meeting.id)
        pages, raw_text = extract_text(pdf_path)
        meeting.raw_text = raw_text
        parsed_segments = parse_segments(pages)
        summary, topics = build_rule_based_summary(raw_text)
        summary = await maybe_refine_summary_with_openai(raw_text, summary)

        meeting.title = subject or meeting.title or (summary.agenda_items[0].title if summary.agenda_items else meeting.title)
        meeting.municipality = summary.meeting.municipality
        meeting.date = summary.meeting.date
        meeting.start_time = summary.meeting.start_time
        meeting.end_time = summary.meeting.end_time
        meeting.summary_nl = summary.model_dump(by_alias=True)
        meeting.topics = topics
        meeting.status = MeetingStatus.ready
        meeting.processing_finished_at = datetime.now(timezone.utc)
        db.commit()

        _store_segments(meeting, parsed_segments, db)
        await translate_summary(summary, db, meeting.id)
        db.refresh(meeting)
        return meeting
    except Exception as exc:
        meeting.status = MeetingStatus.failed
        meeting.error_message = str(exc)
        meeting.processing_finished_at = datetime.now(timezone.utc)
        db.commit()
        if created_new:
            db.refresh(meeting)
        raise


async def ingest_pdf(
    *,
    pdf_path: str,
    source_email: str | None = None,
    subject: str | None = None,
    meeting_id: int | None = None,
    deliver: bool = True,
) -> Meeting:
    db = SessionLocal()
    try:
        meeting = await _ingest_with_session(
            pdf_path=pdf_path,
            source_email=source_email,
            subject=subject,
            meeting_id=meeting_id,
            db=db,
        )
        if deliver:
            from services.digests import deliver_meeting_digest

            await deliver_meeting_digest(meeting.id, db)
            db.refresh(meeting)
        return meeting
    finally:
        db.close()


def ingest_pdf_sync(
    *,
    pdf_path: str,
    source_email: str | None = None,
    subject: str | None = None,
    meeting_id: int | None = None,
    deliver: bool = True,
) -> Meeting:
    return asyncio.run(
        ingest_pdf(
            pdf_path=pdf_path,
            source_email=source_email,
            subject=subject,
            meeting_id=meeting_id,
            deliver=deliver,
        )
    )
