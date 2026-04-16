"""Pydantic v2 schemas matching skills/output-schema.json."""

from pydantic import BaseModel, Field


# ── Output-schema.json structures ──────────────────────────────────────────────


class PartyPresent(BaseModel):
    name: str
    seats: int | None = None


class VoteByParty(BaseModel):
    party: str
    vote: str  # "for" | "against" | "abstention"


class Votes(BaseModel):
    for_: int | None = Field(None, alias="for")
    against: int | None = None
    abstentions: int | None = None
    unanimous: bool | None = None
    by_party: list[VoteByParty] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class Amendment(BaseModel):
    submitted_by: str | None = None
    description: str
    decision: str  # "aangenomen" | "verworpen"
    votes_for: int | None = None
    votes_against: int | None = None


class Motion(BaseModel):
    submitted_by: str | None = None
    description: str
    decision: str  # "aangenomen" | "verworpen"
    votes_for: int | None = None
    votes_against: int | None = None


class AgendaItem(BaseModel):
    number: int | None = None
    title: str
    topic_summary: str | None = None
    decision: str | None = None  # enum from schema
    decision_detail: str | None = None
    votes: Votes | None = None
    amendments: list[Amendment] = Field(default_factory=list)
    motions: list[Motion] = Field(default_factory=list)
    resident_impact: str | None = None
    cost: str | None = None


class Commitment(BaseModel):
    by: str | None = None
    description: str
    deadline: str | None = None


class MeetingMeta(BaseModel):
    municipality: str | None = None
    date: str | None = None  # YYYY-MM-DD
    start_time: str | None = None
    end_time: str | None = None
    parties_present: list[PartyPresent] = Field(default_factory=list)


class MeetingSummary(BaseModel):
    """Full structured output — matches skills/output-schema.json."""

    meeting: MeetingMeta
    agenda_items: list[AgendaItem] = Field(default_factory=list)
    commitments: list[Commitment] = Field(default_factory=list)


# ── API request/response models ────────────────────────────────────────────────


class MeetingListItem(BaseModel):
    id: int
    title: str
    municipality: str | None
    date: str | None
    status: str
    topics: list[str] | None
    agenda_item_count: int

    model_config = {"from_attributes": True}


class MeetingDetail(BaseModel):
    id: int
    title: str
    municipality: str | None
    date: str | None
    start_time: str | None
    end_time: str | None
    status: str
    topics: list[str] | None
    summary_nl: dict | None
    pdf_path: str | None

    model_config = {"from_attributes": True}


class SegmentOut(BaseModel):
    id: int
    order_idx: int
    speaker: str | None
    party: str | None
    role: str | None
    text: str
    page: int | None
    bbox: list[float] | None
    intent: str | None

    model_config = {"from_attributes": True}


class SpeakerSummary(BaseModel):
    id: str
    speaker: str
    party: str | None = None
    role: str | None = None
    segment_count: int


class ChatRequest(BaseModel):
    question: str
    language: str = "nl"


class CitationItem(BaseModel):
    segment_id: int
    speaker: str | None
    text_excerpt: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[CitationItem]
    answer_language: str


class SubscriberCreate(BaseModel):
    email: str
    language: str = "nl"
    topics: list[str] = Field(default_factory=list)
    frequency: str = "immediate"


class SubscriberOut(BaseModel):
    id: int
    email: str
    language: str
    topics: list[str] | None
    frequency: str
    is_active: bool

    model_config = {"from_attributes": True}


class DigestDeliveryOut(BaseModel):
    id: int
    recipient_email: str
    language: str
    message_id: str
    status: str
    output_path: str | None = None

    model_config = {"from_attributes": True}
