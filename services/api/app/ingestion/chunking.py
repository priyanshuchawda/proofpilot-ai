from pydantic import BaseModel, Field


class SourcePage(BaseModel):
    page_number: int | None
    text: str


class TextChunk(BaseModel):
    chunk_order: int
    text: str
    page_number: int | None
    section_heading: str | None
    token_estimate: int = Field(ge=1)


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def heading_from_line(line: str) -> str | None:
    stripped = line.strip()
    if not stripped.startswith("#"):
        return None
    heading = stripped.lstrip("#").strip()
    return heading or None


def chunk_pages(
    pages: list[SourcePage],
    *,
    max_chars: int = 1200,
    overlap_chars: int = 160,
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    active_heading: str | None = None

    for page in pages:
        page_text = page.text.strip()
        if not page_text:
            continue

        lines = page_text.splitlines()
        for line in lines:
            active_heading = heading_from_line(line) or active_heading

        start = 0
        while start < len(page_text):
            end = min(len(page_text), start + max_chars)
            text = page_text[start:end].strip()
            if text:
                chunks.append(
                    TextChunk(
                        chunk_order=len(chunks),
                        text=text,
                        page_number=page.page_number,
                        section_heading=active_heading,
                        token_estimate=estimate_tokens(text),
                    )
                )
            if end == len(page_text):
                break
            start = max(0, end - overlap_chars)

    return chunks
