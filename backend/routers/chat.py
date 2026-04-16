"""Chat (RAG) endpoint — TF-IDF retrieval over meeting segments."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Meeting, Segment
from schemas.meeting import ChatRequest, ChatResponse, CitationItem
from services import openai_client
from services.translate import translate_async

router = APIRouter()

# Structured output schema for chat response
_CHAT_RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "chat_response",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "answer": {"type": "string"},
                "citations": {
                    "type": "array",
                    "items": {"type": "integer"},
                },
            },
            "required": ["answer", "citations"],
            "additionalProperties": False,
        },
    },
}

_SYSTEM_PROMPT = """Je bent een assistent die vragen beantwoordt over gemeenteraadsvergaderingen.
Gebruik ALLEEN de aangeboden tekstfragmenten als bron. Verzin geen informatie.
Citeer altijd de segment_id's die je hebt gebruikt in het veld 'citations'.
Als het antwoord niet in de fragmenten staat, zeg dan eerlijk dat je het niet weet.
Antwoord altijd in het Nederlands."""


def _retrieve_segments(meeting_id: int, question_nl: str, db: Session, top_k: int = 8) -> list[Segment]:
    """TF-IDF retrieval over meeting segments."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np

    segments = db.query(Segment).filter(Segment.meeting_id == meeting_id).all()
    if not segments:
        return []

    corpus = [s.text for s in segments]
    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
    tfidf_matrix = vectorizer.fit_transform(corpus)
    query_vec = vectorizer.transform([question_nl])
    scores = cosine_similarity(query_vec, tfidf_matrix).flatten()
    top_indices = np.argsort(scores)[::-1][:top_k]
    return [segments[i] for i in top_indices if scores[i] > 0]


@router.post("/{meeting_id}/chat", response_model=ChatResponse)
async def chat(meeting_id: int, request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    question = request.question
    user_lang = request.language

    # Translate question to Dutch if needed
    if user_lang != "nl":
        question_nl = await translate_async(question, source=user_lang, target="nl", db=db, meeting_id=meeting.id)
    else:
        question_nl = question

    # Retrieve top-k segments
    top_segments = _retrieve_segments(meeting_id, question_nl, db)
    if not top_segments:
        raise HTTPException(status_code=422, detail="No searchable content for this meeting yet")

    # Build context
    context_parts = []
    for seg in top_segments:
        header = f"[segment_id={seg.id}]"
        if seg.speaker:
            header += f" {seg.speaker}"
            if seg.party:
                header += f" ({seg.party})"
        context_parts.append(f"{header}:\n{seg.text}")
    context = "\n\n---\n\n".join(context_parts)

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Fragmenten:\n\n{context}\n\nVraag: {question_nl}",
        },
    ]

    completion = openai_client.chat_completion(
        model="gpt-4o",
        messages=messages,
        response_format=_CHAT_RESPONSE_SCHEMA,
    )
    raw = openai_client.extract_json(completion)
    answer_nl: str = raw["answer"]
    citation_ids: list[int] = raw.get("citations", [])

    # Translate answer back if needed
    if user_lang != "nl":
        answer = await translate_async(answer_nl, source="nl", target=user_lang, db=db, meeting_id=meeting.id)
    else:
        answer = answer_nl

    # Build citation objects
    seg_map = {s.id: s for s in top_segments}
    citations = [
        CitationItem(
            segment_id=sid,
            speaker=seg_map[sid].speaker if sid in seg_map else None,
            text_excerpt=(seg_map[sid].text[:200] + "…") if sid in seg_map else "",
        )
        for sid in citation_ids
        if sid in seg_map
    ]

    return ChatResponse(answer=answer, citations=citations, answer_language=user_lang)
