from app.answers.schemas import AnswerResponse


def can_cache_response(answer: AnswerResponse) -> bool:
    if answer.refusal_reason is not None:
        return False
    if answer.route == "route_freshness_required":
        return False
    if answer.live_grounding_used:
        return False
    return bool(answer.answer_text and answer.evidence_chunk_ids)
