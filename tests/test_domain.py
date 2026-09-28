"""Offline tests for the Wave 0 data contracts."""

from __future__ import annotations

import pytest

from geochem_rag.domain import (
    Answer,
    AnswerStatus,
    Citation,
    EvidenceChunk,
    PageQuality,
    SearchHit,
    Source,
    Visibility,
    make_chunk_id,
    make_source_id,
)

SHA = "a" * 64
SHA_B = "b" * 64


def test_make_ids_are_stable():
    assert make_source_id(SHA) == make_source_id(SHA)
    assert make_source_id(SHA) != make_source_id(SHA_B)
    assert make_chunk_id(SHA, 1, 0) == make_chunk_id(SHA, 1, 0)
    assert make_chunk_id(SHA, 1, 0) != make_chunk_id(SHA, 1, 1)
    assert make_chunk_id(SHA, 1, 0) != make_chunk_id(SHA, 2, 0)


def test_pdf_page_must_start_at_one():
    with pytest.raises(ValueError, match="pdf_page"):
        EvidenceChunk(
            chunk_id="chk_x",
            source_id="src_x",
            pdf_page=0,
            text="hello",
            section=None,
            quality="ok",
            chunk_index=0,
            sha256=SHA,
        )


def test_chunk_rejects_empty_text():
    with pytest.raises(ValueError, match="text"):
        EvidenceChunk(
            chunk_id="chk_x",
            source_id="src_x",
            pdf_page=1,
            text="   ",
            section=None,
            quality="ok",
            chunk_index=0,
            sha256=SHA,
        )


def test_chunk_quality_values():
    for quality in PageQuality:
        chunk = EvidenceChunk(
            chunk_id="chk_x",
            source_id="src_x",
            pdf_page=3,
            text="geochemistry",
            section="methods",
            quality=quality.value,
            chunk_index=0,
            sha256=SHA,
        )
        assert chunk.quality == quality.value
        assert chunk.pdf_page == 3


def test_source_requires_public_license_url():
    with pytest.raises(ValueError, match="license_url"):
        Source(
            source_id="src_x",
            title="T",
            authors=["A"],
            year=2020,
            doi_or_url="https://example.org/x",
            license="CC BY 4.0",
            license_url="not-a-url",
            sha256=SHA,
            visibility=Visibility.PUBLIC.value,
            download_date="2026-09-28",
        )


def test_source_roundtrip():
    source = Source(
        source_id="src_x",
        title="T",
        authors=["A B", "C D"],
        year=2021,
        doi_or_url="https://doi.org/10.1/x",
        license="CC BY 4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        sha256=SHA,
        visibility="public",
        download_date="2026-09-28",
        local_path="data/public/x.pdf",
    )
    assert Source.from_dict(source.to_dict()) == source


def test_private_source_keeps_unknown_metadata_empty():
    source = Source(
        source_id="src_local_0123456789abcdef",
        title="Filename used as title",
        authors=[],
        year=None,
        doi_or_url=None,
        license=None,
        license_url=None,
        sha256=SHA,
        visibility="private",
        download_date=None,
        local_path="PDF/filename.pdf",
    )
    assert Source.from_dict(source.to_dict()) == source
    assert source.authors == []
    assert source.year is None
    assert source.doi_or_url is None


def test_chunk_roundtrip_preserves_page():
    chunk = EvidenceChunk(
        chunk_id="chk_x_p0002_c000",
        source_id="src_x",
        pdf_page=2,
        text="MORB basalt",
        section="abstract",
        quality="ok",
        chunk_index=0,
        sha256=SHA,
        char_start=10,
        char_end=21,
    )
    restored = EvidenceChunk.from_dict(chunk.to_dict())
    assert restored == chunk
    assert restored.pdf_page == 2


def test_search_hit_contract():
    hit = SearchHit(
        chunk_id="chk_x",
        score=0.42,
        rank=1,
        retrievers=["dense", "bm25"],
        source_id="src_x",
        pdf_page=1,
        dense_score=0.5,
        bm25_score=1.2,
    )
    assert SearchHit.from_dict(hit.to_dict()) == hit
    with pytest.raises(ValueError, match="rank"):
        SearchHit(chunk_id="chk_x", score=1.0, rank=0, retrievers=["dense"])


def test_answer_requires_citations_when_answered():
    citation = Citation(chunk_id="chk_1", source_id="src_x", title="T", pdf_page=4)
    ok = Answer(
        status=AnswerStatus.ANSWERED.value,
        text="Because of slab melting.",
        citations=[citation],
        evidence=["chk_1"],
    )
    assert ok.status == "answered"
    assert ok.citations[0].pdf_page == 4

    with pytest.raises(ValueError, match="citation"):
        Answer(status="answered", text="x", citations=[], evidence=["chk_1"])

    with pytest.raises(ValueError, match="insufficient_evidence"):
        Answer(
            status="insufficient_evidence",
            text="cannot answer",
            citations=[citation],
            evidence=["chk_1"],
        )


def test_answer_rejects_fabricated_citation_ids():
    with pytest.raises(ValueError, match="evidence"):
        Answer(
            status="answered",
            text="x",
            citations=[
                Citation(chunk_id="chk_fake", source_id="src_x", title="T", pdf_page=1)
            ],
            evidence=["chk_real"],
        )
