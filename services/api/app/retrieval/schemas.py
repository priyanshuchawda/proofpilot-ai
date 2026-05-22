from pydantic import BaseModel


class EvidenceChunk(BaseModel):
    chunk_id: str
    workspace_id: str
    document_id: str
    document_version_id: str
    source_filename: str
    mime_type: str
    page_number: int | None
    section_heading: str | None
    chunk_order: int
    text: str
    score: float
    source: str


class RetrievalResult(BaseModel):
    query_run_id: str
    evidence: list[EvidenceChunk]
