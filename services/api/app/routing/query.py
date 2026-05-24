from enum import StrEnum

from pydantic import BaseModel


class QueryMode(StrEnum):
    FAST = "fast"
    VERIFIED = "verified"


class QueryRouteDecision(BaseModel):
    route: str
    freshness_label: str


FRESHNESS_TERMS = (
    "current",
    "latest",
    "today",
    "recent",
    "recently",
    "version",
    "pricing",
    "price",
    "release",
    "status",
)


def requires_freshness(query: str) -> bool:
    normalized = query.lower()
    return any(term in normalized for term in FRESHNESS_TERMS)


def determine_query_route(
    *,
    query: str,
    mode: QueryMode,
    evidence_count: int,
    grounding_enabled: bool = False,
) -> QueryRouteDecision:
    if requires_freshness(query):
        return QueryRouteDecision(
            route="route_freshness_required",
            freshness_label=(
                "freshness_required_grounding_enabled"
                if grounding_enabled
                else "freshness_required_grounding_disabled"
            ),
        )
    if evidence_count == 0:
        return QueryRouteDecision(route="route_no_evidence", freshness_label="not_required")
    if mode == QueryMode.FAST:
        return QueryRouteDecision(route="route_document_fast", freshness_label="not_required")
    return QueryRouteDecision(route="route_document_verified", freshness_label="not_required")
