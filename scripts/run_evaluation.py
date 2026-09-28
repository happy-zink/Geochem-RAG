"""Run the fixed question set under dense_only and hybrid and write results.

Real API (cached embeddings):

    set -a && . ./.env && set +a
    .venv/Scripts/python.exe scripts/run_evaluation.py --limit 0

Offline harness self-test (no network, deterministic stand-ins; NOT a quality
result):

    .venv/Scripts/python.exe scripts/run_evaluation.py --offline --results eval/results_offline

Outputs (gitignored under eval/results/):
- results_<mode>_<stamp>.jsonl   per-question rows with evidence ids and snippets
- summary_<stamp>.json           metrics manifest, same-condition comparison
- review_sheet.jsonl             human citation/supportability sheet
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from geochem_rag.answering import EvidenceAnswerer  # noqa: E402
from geochem_rag.evaluation import (  # noqa: E402
    load_questions,
    run_mode,
    summarize,
    write_results,
    write_review_sheet,
)
from geochem_rag.offline import HashingEmbedder, TemplateChatProvider  # noqa: E402
from geochem_rag.providers import (  # noqa: E402
    chat_provider_from_env,
    embedding_provider_from_env,
)
from geochem_rag.retrieval import Retriever  # noqa: E402
from geochem_rag.store import LocalStore  # noqa: E402


def _file_sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", default="eval/questions.jsonl")
    parser.add_argument("--store", default="data/processed")
    parser.add_argument("--index-cache", default="data/index/embeddings.json")
    parser.add_argument("--modes", nargs="+", default=["dense_only", "hybrid"])
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--rrf-k", type=int, default=60)
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--limit", type=int, default=0, help="0 = all questions")
    parser.add_argument("--results", default="eval/results")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="use deterministic stand-in providers; no network, not a quality result",
    )
    args = parser.parse_args()

    store = LocalStore(args.store)
    questions = load_questions(args.questions)
    if args.limit:
        questions = questions[: args.limit]

    if args.offline:
        embedder: object = HashingEmbedder()
        chat_provider: object = TemplateChatProvider()
        cache_path = args.index_cache.replace("embeddings.json", "embeddings_offline.json")
        model_manifest = {
            "chat": TemplateChatProvider().model_name,
            "embedding": HashingEmbedder().model_name,
        }
        provider_mode = "offline_standin"
    else:
        embedder = embedding_provider_from_env()
        chat_provider = chat_provider_from_env()
        if not embedder.config.api_key:
            print("SILICONFLOW_API_KEY is not set (or pass --offline)", file=sys.stderr)
            return 2
        if not chat_provider.config.api_key:
            print(f"{chat_provider.config.credential_name} is not set (or pass --offline)", file=sys.stderr)
            return 2
        cache_path = args.index_cache
        model_manifest = {
            "chat": chat_provider.config.chat_model,
            "embedding": embedder.config.embedding_model,
            "chat_base_url": chat_provider.config.base_url,
            "embedding_base_url": embedder.config.base_url,
        }
        provider_mode = f"{type(embedder).__name__}+{type(chat_provider).__name__}"

    retriever = Retriever.from_store(
        store,
        embedder,  # type: ignore[arg-type]
        cache_path=cache_path,
        rrf_k=args.rrf_k,
        candidate_k=args.candidate_k,
    )
    answerer = EvidenceAnswerer(store, chat_provider, top_k=args.top_k)  # type: ignore[arg-type]

    all_results = []
    for mode in args.modes:
        print(f"running mode={mode} over {len(questions)} questions ...", file=sys.stderr)
        all_results.extend(
            run_mode(questions, mode, retriever, answerer, store, top_k=args.top_k)
        )

    manifest = {
        "run_started_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "provider_mode": provider_mode,
        "question_set": args.questions,
        "question_set_sha16": _file_sha(args.questions),
        "question_count": len(questions),
        "corpus": {
            "store": args.store,
            "chunk_count": store.count_chunks(),
            "sources": [
                {"source_id": s.source_id, "sha256": s.sha256, "visibility": s.visibility}
                for s in store.load_sources()
            ],
        },
        "models": model_manifest,
        "retrieval": {"rrf_k": args.rrf_k, "candidate_k": args.candidate_k, "top_k": args.top_k},
        "modes": args.modes,
    }
    paths = write_results(all_results, args.results, manifest=manifest)
    review_path = Path(args.results) / "review_sheet.jsonl"
    write_review_sheet(all_results, review_path)

    summary = {mode: summarize(all_results, mode) for mode in args.modes}
    print(json.dumps({"summary": summary, "paths": paths,
                      "review_sheet": review_path.as_posix()}, ensure_ascii=False, indent=2))
    print("\nNOTE: citation accuracy and answer supportability require human labels in "
          "eval/human_labels.jsonl; they are reported as PENDING until then.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
