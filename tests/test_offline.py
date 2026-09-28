"""Offline stand-in providers must stay deterministic and never fake a real answer."""

from __future__ import annotations

import json

from geochem_rag.offline import HashingEmbedder, TemplateChatProvider


def test_hashing_embedder_is_deterministic_and_normalized():
    embedder = HashingEmbedder()
    first = embedder.embed(["adakite", "埃达克质岩石"])
    second = embedder.embed(["adakite", "埃达克质岩石"])
    assert first == second
    assert len(first) == 2 and len(first[0]) == 128
    assert abs(sum(value * value for value in first[0]) - 1.0) < 1e-9


def test_template_provider_cites_given_evidence_and_flags_placeholder():
    provider = TemplateChatProvider()
    prompt = "EVIDENCE:\n[chk_p0003_c000] (Title; PDF page 3)\ntext\n[chk_p0007_c001] text"
    result = provider.chat(
        [{"role": "system", "content": "s"}, {"role": "user", "content": prompt}],
        json_mode=True,
    )
    parsed = json.loads(result.text)
    assert parsed["status"] == "answered"
    assert parsed["citations"] == ["chk_p0003_c000", "chk_p0007_c001"]
    assert "非真实模型结果" in parsed["answer"]


def test_template_provider_refuses_without_evidence():
    provider = TemplateChatProvider()
    result = provider.chat([{"role": "user", "content": "no evidence here"}], json_mode=True)
    parsed = json.loads(result.text)
    assert parsed["status"] == "insufficient_evidence"
    assert parsed["citations"] == []