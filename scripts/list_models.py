"""List currently available SiliconFlow model ids for chat/embedding/rerank.

Requires SILICONFLOW_API_KEY. Never prints the key.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from geochem_rag.providers import ProviderConfig, ProviderError, list_available_models


def main() -> int:
    config = ProviderConfig.from_env()
    if not config.api_key:
        print("SILICONFLOW_API_KEY is not set", file=sys.stderr)
        return 2
    for sub_type in ("chat", "embedding", "reranker"):
        try:
            ids = list_available_models(config, sub_type=sub_type)
        except ProviderError as exc:
            print(f"{sub_type}: ERROR {exc.kind}", file=sys.stderr)
            continue
        print(f"== {sub_type} ({len(ids)}) ==")
        for model_id in ids:
            print(model_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())