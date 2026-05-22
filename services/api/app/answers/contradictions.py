import re
from collections import defaultdict

from pydantic import BaseModel

from app.retrieval.schemas import EvidenceChunk


class Contradiction(BaseModel):
    claim_key: str
    values: list[str]
    chunk_ids: list[str]


CLAIM_PATTERNS = {
    "retention period": re.compile(r"retention period (?:is|remains) (\d+\s+\w+)", re.I),
}


def detect_contradictions(evidence: list[EvidenceChunk]) -> list[Contradiction]:
    observed: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for item in evidence:
        for claim_key, pattern in CLAIM_PATTERNS.items():
            match = pattern.search(item.text)
            if match is None:
                continue
            observed[claim_key][match.group(1).lower()].append(item.chunk_id)

    contradictions: list[Contradiction] = []
    for claim_key, values in observed.items():
        if len(values) <= 1:
            continue
        chunk_ids = [chunk_id for ids in values.values() for chunk_id in ids]
        contradictions.append(
            Contradiction(
                claim_key=claim_key,
                values=list(values.keys()),
                chunk_ids=chunk_ids,
            )
        )
    return contradictions
