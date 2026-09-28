"""Streamlit front-end for GeoChem-RAG.

Displays evidence-grounded answers with verifiable citations (paper title,
PDF page number, short evidence snippet). Public and private sources are
visually distinguished. A clear notice explains that retrieved evidence
fragments are sent to the configured online API for answer generation.

Two runtime modes:

- **Online** (default): uses real SiliconFlow embeddings and the configured
  chat provider. Requires ``SILICONFLOW_API_KEY`` (and ``DEEPSEEK_API_KEY``
  when ``GEOCHEM_CHAT_PROVIDER=deepseek``).
- **Offline demo**: deterministic stand-in providers (``HashingEmbedder`` +
  ``TemplateChatProvider``). No network, no API key. Useful for UI smoke
  tests and conference demos where the corpus is public.

Run from the repo root::

    streamlit run src/geochem_rag/app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# Ensure ``geochem_rag`` is importable when running ``streamlit run app.py``
# from the repo root (src/ is not installed site-wide in dev environments).
_HERE = Path(__file__).resolve()
_SRC = _HERE.parents[1]  # src/
_REPO = _SRC.parent  # repo root
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st  # noqa: E402

from geochem_rag.answering import (  # noqa: E402
    EvidenceAnswerer,
    EvidenceItem,
    build_evidence,
    format_citation,
)
from geochem_rag.domain import AnswerStatus, Citation, Source  # noqa: E402
from geochem_rag.offline import (  # noqa: E402
    HashingEmbedder,
    TemplateChatProvider,
)
from geochem_rag.providers import (  # noqa: E402
    ChatProvider,
    EmbeddingProvider,
    ProviderConfig,
    ProviderError,
    chat_provider_from_env,
    embedding_provider_from_env,
)
from geochem_rag.retrieval import Retriever, expand_query  # noqa: E402
from geochem_rag.store import LocalStore  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PAGE_TITLE = "GeoChem-RAG"
_PAGE_ICON = None  # Streamlit picks a default icon
_DEMO_QUESTIONS = [
    (
        "Cross-language: Chinese question about an English paper",
        "这篇英文论文如何解释莫根通埃达克质岩体的成因？请用中文概括。",
    ),
    (
        "Geochemistry abbreviation",
        "MORB 是什么缩写？它在岩石成因讨论中通常指示什么源区？",
    ),
    (
        "Unanswerable: outside the corpus",
        "Summarize the conclusions of a paper about kimberlites in Siberia.",
    ),
]

# ---------------------------------------------------------------------------
# Session-state initialisation
# ---------------------------------------------------------------------------


def _init_session() -> None:
    """One-time setup of store, providers, retriever and answerer."""
    if "initialised" in st.session_state:
        return

    st.session_state.setdefault("offline_mode", False)
    st.session_state.setdefault("last_answer", None)
    st.session_state.setdefault("last_hits", [])
    st.session_state.setdefault("last_error", None)

    store_root = os.environ.get("GEOCHEM_STORE", "data/processed")
    store = LocalStore(store_root)
    st.session_state.store = store

    chunk_count = store.count_chunks()
    st.session_state.chunk_count = chunk_count

    if chunk_count == 0:
        st.session_state.initialised = True
        st.session_state.ready = False
        return

    # Try online providers first; fall back to offline when keys are missing.
    embedder: EmbeddingProvider | HashingEmbedder
    chat: ChatProvider | TemplateChatProvider
    offline = False

    try:
        embedder = embedding_provider_from_env()
        if not embedder.config.api_key:  # type: ignore[attr-defined]
            raise ProviderError("not_configured", "SILICONFLOW_API_KEY not set")
        chat = chat_provider_from_env()
        if not chat.config.api_key:  # type: ignore[attr-defined]
            raise ProviderError("not_configured", "chat provider key not set")
    except (ProviderError, ValueError, KeyError):
        embedder = HashingEmbedder()
        chat = TemplateChatProvider()
        offline = True

    st.session_state.offline_mode = offline
    st.session_state.embedder = embedder
    st.session_state.chat = chat

    cache_path = os.environ.get(
        "GEOCHEM_EMBEDDING_CACHE",
        "data/index/embeddings.json"
        if not offline
        else "data/index/embeddings_offline.json",
    )
    try:
        retriever = Retriever.from_store(
            store, embedder, cache_path=cache_path  # type: ignore[arg-type]
        )
    except Exception as exc:  # noqa: BLE001
        st.session_state.last_error = f"Retriever init failed: {exc}"
        st.session_state.initialised = True
        st.session_state.ready = False
        return

    answerer = EvidenceAnswerer(store, chat, top_k=5)  # type: ignore[arg-type]
    st.session_state.retriever = retriever
    st.session_state.answerer = answerer
    st.session_state.initialised = True
    st.session_state.ready = True


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------


def _render_sidebar() -> dict[str, Any]:
    """Sidebar: configuration, source list, privacy notice."""
    with st.sidebar:
        st.header("Configuration")

        mode_label = "Offline demo (stand-in providers)" if st.session_state.offline_mode else "Online (real API)"
        st.caption(f"Mode: **{mode_label}**")

        if not st.session_state.offline_mode:
            chat_cfg = getattr(st.session_state.chat, "config", None)
            embed_cfg = getattr(st.session_state.embedder, "config", None)
            if chat_cfg:
                st.caption(f"Chat model: `{chat_cfg.chat_model}`")
                st.caption(f"Chat endpoint: `{chat_cfg.base_url}`")
            if embed_cfg:
                st.caption(f"Embedding model: `{embed_cfg.embedding_model}`")
        else:
            st.caption("Chat: `TemplateChatProvider` (offline)")
            st.caption("Embedding: `HashingEmbedder` (offline)")

        retrieval_mode = st.selectbox(
            "Retrieval mode",
            ["hybrid", "dense_only", "bm25_only"],
            index=0,
        )
        top_k = st.slider("Top-k evidence", min_value=1, max_value=10, value=5)

        st.divider()
        st.header("Sources")
        chunk_count = st.session_state.chunk_count
        st.caption(f"Evidence chunks loaded: **{chunk_count}**")

        if chunk_count > 0:
            sources = st.session_state.store.load_sources()
            public_sources = [s for s in sources if s.visibility == "public"]
            private_sources = [s for s in sources if s.visibility == "private"]

            if public_sources:
                st.caption(f"Public ({len(public_sources)}):")
                for src in public_sources:
                    label = src.title
                    if len(label) > 60:
                        label = label[:57] + "..."
                    st.text(f"  {label} ({src.year or '?'})")

            if private_sources:
                st.caption(f"Private ({len(private_sources)}):")
                for src in private_sources:
                    label = src.title
                    if len(label) > 60:
                        label = label[:57] + "..."
                    if src.title_is_filename:
                        label = f"[filename] {label}"
                    st.text(f"  {label}")

        st.divider()
        st.header("Privacy & data flow")
        st.info(
            "**Where your data goes:**\n\n"
            "- Local PDFs and extracted evidence stay on this machine.\n"
            "- `PDF/` and `data/private/` are excluded from Git.\n"
            "- When you ask a question, the **retrieved evidence fragments** "
            "and your question are sent to the configured online API "
            "(SiliconFlow / DeepSeek) to generate an answer.\n"
            "- Private corpus text is transmitted only as the specific "
            "evidence chunks matched by retrieval, never the full document.\n"
            "- No API key is shown or logged in this interface."
        )
        if st.session_state.offline_mode:
            st.warning(
                "Currently running in **offline demo mode**. No data is "
                "sent to any external API. Answers are placeholder text."
            )

    return {"retrieval_mode": retrieval_mode, "top_k": top_k}


# ---------------------------------------------------------------------------
# Answer display
# ---------------------------------------------------------------------------


def _status_banner(status: str):
    """Return the appropriate Streamlit alert type for an answer status."""
    if status == AnswerStatus.ANSWERED.value:
        return st.success
    if status == AnswerStatus.INSUFFICIENT_EVIDENCE.value:
        return st.warning
    return st.error


def _status_label(status: str) -> str:
    labels = {
        "answered": "Answered",
        "insufficient_evidence": "Insufficient evidence",
        "error": "API / generation error",
    }
    return labels.get(status, status)


def _source_for_chunk(store: LocalStore, chunk_id: str) -> Source | None:
    """Look up the Source that owns a given chunk."""
    chunk = store.find_chunk(chunk_id)
    if chunk is None:
        return None
    return store.get_source(chunk.source_id)


def _render_citation(
    citation: Citation,
    store: LocalStore,
    evidence_items: list[EvidenceItem],
    index: int,
) -> None:
    """Render one expandable citation card."""
    source = store.get_source(citation.source_id)
    visibility = source.visibility if source else "unknown"
    vis_badge = "public" if visibility == "public" else "private"

    # Find the matching evidence item for the snippet.
    snippet_text = ""
    for item in evidence_items:
        if item.chunk_id == citation.chunk_id:
            snippet_text = item.snippet()
            break

    header = f"**[{index + 1}]** {citation.title} -- PDF page {citation.pdf_page}  \n"
    header += f"`{vis_badge}` | chunk `{citation.chunk_id}`"

    with st.expander(header, expanded=False):
        if snippet_text:
            st.markdown("**Evidence snippet:**")
            st.markdown(f"> {snippet_text}")

        if source is not None:
            st.markdown(f"**Source ID:** `{source.source_id}`")
            if source.doi_or_url and visibility == "public":
                st.markdown(f"**Open original:** [{source.doi_or_url}]({source.doi_or_url})")
            if source.title_is_filename:
                st.caption("Title is a filename placeholder (private source).")


def _render_answer(answer, store: LocalStore, evidence_items: list[EvidenceItem]) -> None:
    """Render the full answer block with citations."""
    banner = _status_banner(answer.status)
    banner.markdown(f"**{_status_label(answer.status)}**")

    if answer.status == AnswerStatus.ANSWERED.value:
        st.markdown(answer.text)
        st.divider()
        st.markdown("**Citations:**")
        for idx, citation in enumerate(answer.citations):
            _render_citation(citation, store, evidence_items, idx)

    elif answer.status == AnswerStatus.INSUFFICIENT_EVIDENCE.value:
        st.markdown(answer.text)
        if answer.evidence:
            st.caption(
                f"{len(answer.evidence)} evidence block(s) were retrieved but "
                "did not support a verified answer."
            )

    else:  # error
        st.markdown(answer.text)
        error_detail = answer.meta.get("error")
        if error_detail:
            st.caption(f"Error kind: `{error_detail.get('kind', '?')}`")


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(
        page_title=_PAGE_TITLE,
        page_icon=_PAGE_ICON,
        layout="wide",
    )
    st.title(_PAGE_TITLE)
    st.markdown(
        "Evidence-grounded literature Q&A for rock geochemistry. "
        "Every answer cites the exact paper title, PDF page, and a short "
        "evidence snippet. Claims without verifiable citations are refused."
    )

    _init_session()

    if not st.session_state.get("ready", False):
        chunk_count = st.session_state.chunk_count
        if chunk_count == 0:
            st.error(
                "**No evidence chunks found.** Import at least one PDF first:\n\n"
                "```\n"
                "python -m geochem_rag.import_pdf --pdf path/to/paper.pdf\n"
                "```\n\n"
                "Then restart this app."
            )
        else:
            error = st.session_state.get("last_error", "Unknown initialisation error.")
            st.error(f"**Initialisation failed:** {error}")
        st.stop()

    config = _render_sidebar()

    # --- Question input ------------------------------------------------
    st.divider()
    question = st.text_input(
        "Ask a question about the loaded geochemistry literature:",
        placeholder="e.g. What does MORB stand for?",
    )

    # Preset demo questions
    cols = st.columns(len(_DEMO_QUESTIONS))
    for col, (label, text) in zip(cols, _DEMO_QUESTIONS):
        with col:
            if st.button(label, use_container_width=True):
                question = text

    if not question:
        st.info("Type a question or choose a demo question above.")
        st.stop()

    # --- Run retrieval + answering ------------------------------------
    with st.spinner("Retrieving evidence and generating answer..."):
        retriever: Retriever = st.session_state.retriever
        answerer: EvidenceAnswerer = st.session_state.answerer
        store: LocalStore = st.session_state.store

        mode = config["retrieval_mode"]
        top_k = config["top_k"]

        trace = retriever.retrieve_with_trace(question, mode=mode, top_k=top_k)
        answer = answerer.answer(question, trace.hits)

    # Build evidence items for display.
    evidence_items = build_evidence(trace.hits, store, top_k=top_k)

    # --- Display results ----------------------------------------------
    st.divider()
    st.subheader("Question")
    st.markdown(question)

    # Show query expansion info if hybrid/bm25 was used.
    if trace.expanded_terms:
        st.caption(
            f"Query expansion added: {', '.join(trace.expanded_terms)} "
            f"(matched: {', '.join(trace.matched_terms) or 'none'})"
        )

    st.subheader("Answer")
    _render_answer(answer, store, evidence_items)

    # --- All retrieved evidence (transparency) -------------------------
    if evidence_items:
        st.divider()
        st.subheader(f"Retrieved evidence ({len(evidence_items)} blocks)")
        for idx, item in enumerate(evidence_items):
            source = store.get_source(item.source_id)
            vis = source.visibility if source else "?"
            vis_tag = "public" if vis == "public" else "private"
            st.markdown(
                f"**[{idx + 1}]** `{vis_tag}` | "
                f"{item.title} | PDF page {item.pdf_page} | "
                f"chunk `{item.chunk_id}`"
            )
            st.code(item.snippet(limit=400), language=None)


if __name__ == "__main__":
    main()
