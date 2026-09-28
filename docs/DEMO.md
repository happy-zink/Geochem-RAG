# GeoChem-RAG Demo Guide

Status: Wave 3 (QoderCN). This document describes the fixed three-question demo, the architecture diagram, and the recording checklist.

## Fixed demo questions

The demo runs three questions that exercise different capabilities. The same three questions are hard-coded as preset buttons in the Streamlit UI (`src/geochem_rag/app.py`).

### 1. Cross-language: Chinese question about an English paper

**Question:** "这篇英文论文如何解释莫根通埃达克质岩体的成因？请用中文概括。"

**What it tests:** The system retrieves English-language evidence from the Mogetong adakitic pluton paper (Gan et al., 2022, *Frontiers in Earth Science*) and generates an answer in Chinese. This demonstrates cross-language retrieval (Chinese query -> English evidence -> Chinese answer).

**Expected behaviour (online mode):**
- Status: `answered`
- At least one citation pointing to `src_feart_2022_845763`
- The answer summarises the thickened-lower-crust partial melting model
- Query expansion may add terms like "adakitic", "partial melting", "thickened lower crust"

### 2. Geochemistry abbreviation

**Question:** "MORB 是什么缩写？它在岩石成因讨论中通常指示什么源区？"

**What it tests:** The geochemistry abbreviation dictionary in `retrieval.py` expands "MORB" to "mid-ocean ridge basalt" for BM25 retrieval. The system either finds relevant evidence in the loaded corpus or correctly returns `insufficient_evidence` if no paper discusses MORB in detail.

**Expected behaviour (online mode):**
- If the corpus contains MORB discussion: `answered` with citation(s)
- If the corpus does not cover MORB: `insufficient_evidence` with an explanation
- The query expansion trace shows the added synonym terms

**Note:** With only the 4 public sample papers, MORB may not be discussed in depth. The system should honestly report insufficient evidence rather than fabricate an answer from general knowledge.

### 3. Unanswerable: outside the corpus

**Question:** "Summarize the conclusions of a paper about kimberlites in Siberia."

**What it tests:** No loaded paper discusses Siberian kimberlites. The system must return `insufficient_evidence` and must NOT fabricate an answer or invent a citation.

**Expected behaviour (online mode):**
- Status: `insufficient_evidence`
- No citations
- The answer text explains that the loaded corpus does not contain relevant evidence

## Demo recording checklist

When recording a demo GIF or video:

1. **Start the app** with at least the 4 public sample papers imported.
2. **Ask question 1** (cross-language). Expand at least one citation to show:
   - Paper title
   - PDF page number
   - Evidence snippet
   - "Open original" link (for public sources)
3. **Verify the PDF page** by opening the cited page in the actual PDF and confirming the evidence snippet matches the source text.
4. **Ask question 2** (abbreviation). Show the query expansion trace in the UI.
5. **Ask question 3** (unanswerable). Show the `insufficient_evidence` status and the absence of citations.
6. **Show the sidebar**: retrieval mode, top-k, source list with public/private distinction, and the privacy notice.

## Architecture diagram

```
PDF/ (user's local files)
  |
  v
[ingest.py] -- page-by-page text extraction, quality tagging
  |
  v
[store.py] -- JSONL persistence, SHA-256 dedup
  |
  +---> [retrieval.py]
  |       |
  |       +-- DenseIndex (cosine similarity over bge-m3 embeddings)
  |       +-- BM25Index (lexical + geochemistry term expansion)
  |       +-- RRF fusion (k=60)
  |       |
  |       v
  |     Top-5 SearchHits
  |       |
  |       v
  +---> [answering.py]
          |
          +-- build_evidence() resolves chunk_ids to EvidenceItems
          +-- Prompt: system constraint + evidence blocks + question
          +-- Chat provider (DeepSeek / SiliconFlow / offline template)
          +-- Citation validation: every cited chunk_id must be in evidence
          |
          v
        Answer (status, text, citations, evidence)
          |
          v
        [app.py] Streamlit UI
          |
          +-- Answer status banner (answered / insufficient / error)
          +-- Citation cards: title, PDF page, evidence snippet, open-original link
          +-- Public vs private source badges
          +-- Privacy notice: evidence fragments sent to online API
```

## Offline demo mode

When no API key is configured, the app falls back to deterministic stand-in providers:

- `HashingEmbedder` (128-dim bag-of-hashed-tokens) for embeddings
- `TemplateChatProvider` (cites the first evidence id, no real language understanding)

This mode is useful for UI smoke tests and conference demos. Answers are placeholder text and do NOT reflect real retrieval quality. The sidebar clearly shows "Offline demo mode" and a warning that no data is sent externally.

## Demo script (automated)

A non-interactive demo script can be run to verify the three questions produce the expected statuses:

```powershell
# Windows PowerShell
$env:PYTHONPATH = "src"
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe scripts\run_demo.py
```

```bash
# Linux / git-bash
PYTHONPATH=src PYTHONIOENCODING=utf-8 .venv/bin/python scripts/run_demo.py
```

The script prints each question, the answer status, and citation count. It exits 0 if all three questions return the expected status pattern.
