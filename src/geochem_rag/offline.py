"""Deterministic offline stand-ins for CI and harness self-tests.

These are NOT models. They exist so the retrieval -> answering -> evaluation
pipeline can be exercised without network access:

- ``HashingEmbedder`` hashes tokens (Latin words + CJK bigrams) into a fixed
  vector. It is deterministic and dependency-free but has no semantic ability.
- ``TemplateChatProvider`` cites the first evidence ids it is given and returns a
  clearly-labelled placeholder answer, so the citation-validation and refusal
  code paths can be tested end to end.

Never present their output as a real answer or as a retrieval quality result.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Mapping, Sequence

from .providers import ChatResult
from .retrieval import tokenize

_OFFLINE_NOTICE = "离线占位输出（非真实模型结果，仅用于流程自检）。"

_EVIDENCE_ID_RE = re.compile(r"\[(chk_[A-Za-z0-9_:-]+)\]")


class HashingEmbedder:
    """Deterministic bag-of-hashed-tokens embedding, dimension 128."""

    def __init__(self, dim: int = 128) -> None:
        self.dim = dim
        self.model_name = "offline-hashing-128"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self.dim
            for token in tokenize(text):
                digest = hashlib.md5(token.encode("utf-8")).digest()
                bucket = int.from_bytes(digest[:4], "big") % self.dim
                vector[bucket] += 1.0
            norm = math.sqrt(sum(value * value for value in vector))
            if norm:
                vector = [value / norm for value in vector]
            vectors.append(vector)
        return vectors


class TemplateChatProvider:
    """Cites the first evidence ids it receives; no language understanding."""

    def __init__(self, model_name: str = "offline-template") -> None:
        self.model_name = model_name

    def chat(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> ChatResult:
        user = next(
            (m.get("content", "") for m in reversed(list(messages)) if m.get("role") == "user"),
            "",
        )
        ids = list(dict.fromkeys(_EVIDENCE_ID_RE.findall(user)))[:2]
        if ids:
            payload: dict[str, Any] = {
                "status": "answered",
                "answer": f"{_OFFLINE_NOTICE} 命中证据：{', '.join(ids)}。",
                "citations": ids,
            }
        else:
            payload = {
                "status": "insufficient_evidence",
                "answer": f"{_OFFLINE_NOTICE} 未收到证据。",
                "citations": [],
            }
        return ChatResult(
            text=json.dumps(payload, ensure_ascii=False),
            model=self.model_name,
            usage={},
        )