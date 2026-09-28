"""Build or refresh the embedding cache used by dense retrieval.

Reads chunks from the local store and stores vectors in data/index/. Requires a
valid key only on the first run (or when chunk text changes). No key is logged.

    set -a && . ./.env && set +a
    .venv/Scripts/python.exe scripts/build_index.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from geochem_rag.providers import ProviderConfig, SiliconFlowClient  # noqa: E402
from geochem_rag.retrieval import Retriever  # noqa: E402
from geochem_rag.store import LocalStore  # noqa: E402


def main() -> int:
    config = ProviderConfig.from_env()
    if not config.api_key:
        print("SILICONFLOW_API_KEY is not set", file=sys.stderr)
        return 2
    client = SiliconFlowClient(config, embedding_batch_size=16)
    store = LocalStore("data/processed")
    chunk_count = store.count_chunks()
    if not chunk_count:
        print("No chunks in store", file=sys.stderr)
        return 2
    retriever = Retriever.from_store(
        store, client, cache_path="data/index/embeddings.json"
    )
    print(f"indexed chunks={chunk_count} dim={retriever.dense_index.dim} "
          f"model={config.embedding_model}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())