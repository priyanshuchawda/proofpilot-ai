def validate_citation_ids(
    *,
    cited_chunk_ids: list[str],
    evidence_chunk_ids: set[str],
) -> bool:
    return bool(cited_chunk_ids) and set(cited_chunk_ids).issubset(evidence_chunk_ids)


def validate_cited_paragraphs(*, answer_text: str, cited_chunk_ids: list[str]) -> bool:
    if not answer_text.strip() or not cited_chunk_ids:
        return False
    paragraphs = [paragraph.strip() for paragraph in answer_text.split("\n\n") if paragraph.strip()]
    if not paragraphs:
        return False
    citation_markers = [f"[{chunk_id}]" for chunk_id in cited_chunk_ids]
    return all(any(marker in paragraph for marker in citation_markers) for paragraph in paragraphs)
