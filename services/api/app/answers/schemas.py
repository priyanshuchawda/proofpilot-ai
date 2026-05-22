from pydantic import BaseModel, Field


class Citation(BaseModel):
    chunk_id: str
    source_filename: str
    page_number: int | None
    section_heading: str | None
    evidence_text: str


class AnswerResponse(BaseModel):
    query_run_id: str
    answer_text: str
    citations: list[Citation]
    evidence_chunk_ids: list[str]
    confidence_label: str
    refusal_reason: str | None
    live_grounding_used: bool = False
    mode: str
    cache_status: str = "miss"


class GeminiCitedAnswer(BaseModel):
    answer_text: str = Field(default="")
    citation_chunk_ids: list[str] = Field(default_factory=list)
