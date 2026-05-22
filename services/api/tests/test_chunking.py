from app.ingestion.chunking import SourcePage, chunk_pages


def test_chunk_pages_preserves_page_and_heading_metadata() -> None:
    pages = [
        SourcePage(
            page_number=1,
            text="# Overview\nProofPilot answers with evidence.\nIt refuses unsupported claims.",
        ),
        SourcePage(
            page_number=2,
            text="## Details\nCitations must map to chunks.\nTrace data is stored.",
        ),
    ]

    chunks = chunk_pages(pages, max_chars=80, overlap_chars=20)

    assert [chunk.chunk_order for chunk in chunks] == list(range(len(chunks)))
    assert chunks[0].page_number == 1
    assert chunks[0].section_heading == "Overview"
    assert any(chunk.page_number == 2 and chunk.section_heading == "Details" for chunk in chunks)
    assert all(chunk.token_estimate > 0 for chunk in chunks)
