from pydantic import BaseModel, Field

from app.answers.contradictions import Contradiction


def empty_contradictions() -> list[Contradiction]:
    return []


class Citation(BaseModel):
    chunk_id: str | None = None
    citation_label: str | None = None
    source_kind: str = "document"
    source_filename: str | None = None
    page_number: int | None
    section_heading: str | None
    evidence_text: str
    title: str | None = None
    uri: str | None = None


class AnswerResponse(BaseModel):
    query_run_id: str
    answer_text: str
    citations: list[Citation]
    evidence_chunk_ids: list[str]
    confidence_label: str
    refusal_reason: str | None
    generation_model_used: str | None = None
    live_grounding_used: bool = False
    mode: str
    route: str
    freshness_label: str
    search_suggestions_html: str | None = None
    contradictions: list[Contradiction] = Field(default_factory=empty_contradictions)
    cache_status: str = "miss"


class GeminiCitedAnswer(BaseModel):
    answer_text: str = Field(default="")
    citation_chunk_ids: list[str] = Field(default_factory=list)
