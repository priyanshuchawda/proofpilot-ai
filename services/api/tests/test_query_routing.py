from app.routing.query import QueryMode, determine_query_route, requires_freshness


def test_requires_freshness_detects_current_information_questions() -> None:
    assert requires_freshness("What is the latest Gemini pricing today?")
    assert requires_freshness("Which version was released recently?")


def test_query_route_selects_no_evidence_when_retrieval_is_empty() -> None:
    assert (
        determine_query_route(
            query="What does the document say?",
            mode=QueryMode.VERIFIED,
            evidence_count=0,
        ).route
        == "route_no_evidence"
    )


def test_query_route_selects_fast_or_verified_document_routes() -> None:
    assert (
        determine_query_route(
            query="Summarize the policy.",
            mode=QueryMode.FAST,
            evidence_count=2,
        ).route
        == "route_document_fast"
    )
    assert (
        determine_query_route(
            query="Summarize the policy.",
            mode=QueryMode.VERIFIED,
            evidence_count=2,
        ).route
        == "route_document_verified"
    )


def test_query_route_marks_freshness_required_without_grounding() -> None:
    decision = determine_query_route(
        query="What is the latest release?",
        mode=QueryMode.VERIFIED,
        evidence_count=2,
    )

    assert decision.route == "route_freshness_required"
    assert decision.freshness_label == "freshness_required_grounding_disabled"


def test_query_route_uses_enabled_grounding_for_freshness_without_document_evidence() -> None:
    decision = determine_query_route(
        query="What is the latest release today?",
        mode=QueryMode.VERIFIED,
        evidence_count=0,
        grounding_enabled=True,
    )

    assert decision.route == "route_freshness_required"
    assert decision.freshness_label == "freshness_required_grounding_enabled"


def test_query_route_explains_disabled_grounding_for_freshness_without_document_evidence() -> None:
    decision = determine_query_route(
        query="What is the latest release today?",
        mode=QueryMode.VERIFIED,
        evidence_count=0,
        grounding_enabled=False,
    )

    assert decision.route == "route_freshness_required"
    assert decision.freshness_label == "freshness_required_grounding_disabled"
