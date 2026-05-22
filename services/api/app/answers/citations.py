def validate_citation_ids(
    *,
    cited_chunk_ids: list[str],
    evidence_chunk_ids: set[str],
) -> bool:
    return bool(cited_chunk_ids) and set(cited_chunk_ids).issubset(evidence_chunk_ids)
