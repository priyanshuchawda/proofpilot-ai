import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gemini import GeminiGenerateRequest, GeminiProvider
from app.answers.citations import validate_citation_ids
from app.answers.context import build_evidence_context
from app.answers.contradictions import Contradiction
from app.answers.schemas import AnswerResponse, Citation, GeminiCitedAnswer
from app.db.models import CitedEvidence, GeneratedAnswer
from app.retrieval.schemas import EvidenceChunk, RetrievalResult

FRESHNESS_GROUNDING_DISABLED_REFUSAL = (
    "Freshness is required, but live grounding is disabled for this free-tier-safe configuration."
)


class AnswerService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        gemini_provider: GeminiProvider,
        generation_model: str,
        grounding_model: str | None = None,
    ) -> None:
        self._session = session
        self._gemini_provider = gemini_provider
        self._generation_model = generation_model
        self._grounding_model = grounding_model or generation_model

    async def generate_answer(
        self,
        *,
        retrieval: RetrievalResult,
        query: str,
        mode: str,
        route: str,
        freshness_label: str,
        contradictions: list[Contradiction],
    ) -> AnswerResponse:
        if not retrieval.evidence:
            return await self._persist_refusal(
                query_run_id=retrieval.query_run_id,
                mode=mode,
                route=route,
                freshness_label=freshness_label,
                contradictions=contradictions,
                confidence_label="none",
                refusal_reason="No reliable evidence was found for this question.",
            )
        if (
            route == "route_freshness_required"
            and freshness_label == "freshness_required_grounding_disabled"
        ):
            return await self._persist_refusal(
                query_run_id=retrieval.query_run_id,
                mode=mode,
                route=route,
                freshness_label=freshness_label,
                contradictions=contradictions,
                confidence_label="low",
                refusal_reason=FRESHNESS_GROUNDING_DISABLED_REFUSAL,
            )

        prompt = self._build_prompt(query=query, evidence=retrieval.evidence)
        response = await self._gemini_provider.generate_text(
            GeminiGenerateRequest(
                prompt=prompt,
                model=(
                    self._grounding_model
                    if route == "route_freshness_required"
                    else self._generation_model
                ),
                response_json_schema=GeminiCitedAnswer.model_json_schema(),
                enable_google_search=route == "route_freshness_required",
            )
        )
        cited_answer = _parse_cited_answer(response.text)
        evidence_ids = {item.chunk_id for item in retrieval.evidence}
        if not validate_citation_ids(
            cited_chunk_ids=cited_answer.citation_chunk_ids,
            evidence_chunk_ids=evidence_ids,
        ):
            return await self._persist_refusal(
                query_run_id=retrieval.query_run_id,
                mode=mode,
                route=route,
                freshness_label=freshness_label,
                contradictions=contradictions,
                confidence_label="low",
                refusal_reason="Generated citations did not map to retrieved evidence.",
            )

        citations = _citations_from_evidence(
            cited_chunk_ids=cited_answer.citation_chunk_ids,
            evidence=retrieval.evidence,
        )
        self._session.add(
            GeneratedAnswer(
                query_run_id=retrieval.query_run_id,
                answer_text=cited_answer.answer_text,
                confidence_label="medium",
                refusal_reason=None,
                live_grounding_used=route == "route_freshness_required",
            )
        )
        for citation in citations:
            self._session.add(
                CitedEvidence(
                    query_run_id=retrieval.query_run_id,
                    chunk_id=citation.chunk_id,
                    citation_label=citation.chunk_id,
                    evidence_text=citation.evidence_text,
                    source_kind="document",
                )
            )
        await self._session.commit()
        return AnswerResponse(
            query_run_id=retrieval.query_run_id,
            answer_text=cited_answer.answer_text,
            citations=citations,
            evidence_chunk_ids=[citation.chunk_id for citation in citations],
            confidence_label="medium",
            refusal_reason=None,
            mode=mode,
            route=route,
            freshness_label=freshness_label,
            live_grounding_used=route == "route_freshness_required",
            contradictions=contradictions,
        )

    def _build_prompt(self, *, query: str, evidence: list[EvidenceChunk]) -> str:
        context = build_evidence_context(evidence)
        return "\n\n".join(
            [
                "Answer the user question using only the supplied evidence.",
                "Return strict JSON with keys answer_text and citation_chunk_ids.",
                "Every factual sentence must cite at least one retrieved chunk ID.",
                "If the evidence is insufficient, return an empty answer_text and no citations.",
                context,
                f"Question: {query}",
            ]
        )

    async def _persist_refusal(
        self,
        *,
        query_run_id: str,
        mode: str,
        route: str,
        freshness_label: str,
        contradictions: list[Contradiction],
        confidence_label: str,
        refusal_reason: str,
    ) -> AnswerResponse:
        self._session.add(
            GeneratedAnswer(
                query_run_id=query_run_id,
                answer_text="",
                confidence_label=confidence_label,
                refusal_reason=refusal_reason,
                live_grounding_used=False,
            )
        )
        await self._session.commit()
        return AnswerResponse(
            query_run_id=query_run_id,
            answer_text="",
            citations=[],
            evidence_chunk_ids=[],
            confidence_label=confidence_label,
            refusal_reason=refusal_reason,
            mode=mode,
            route=route,
            freshness_label=freshness_label,
            contradictions=contradictions,
        )


def _parse_cited_answer(raw_text: str) -> GeminiCitedAnswer:
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        return GeminiCitedAnswer(answer_text="", citation_chunk_ids=[])
    return GeminiCitedAnswer.model_validate(payload)


def _citations_from_evidence(
    *,
    cited_chunk_ids: list[str],
    evidence: list[EvidenceChunk],
) -> list[Citation]:
    evidence_by_id = {item.chunk_id: item for item in evidence}
    citations: list[Citation] = []
    for chunk_id in cited_chunk_ids:
        item = evidence_by_id[chunk_id]
        citations.append(
            Citation(
                chunk_id=item.chunk_id,
                source_filename=item.source_filename,
                page_number=item.page_number,
                section_heading=item.section_heading,
                evidence_text=item.text,
            )
        )
    return citations
