r"""Load .env into the process and start Streamlit in online mode.

Usage (PowerShell, from repo root):
  .venv\Scripts\python.exe scripts\run_streamlit_online.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
APP = ROOT / "src" / "geochem_rag" / "app.py"


def load_env(path: Path) -> dict[str, str]:
    loaded: dict[str, str] = {}
    if not path.is_file():
        raise SystemExit(f"missing {path} — copy .env.example and fill API keys")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ[key] = value
            loaded[key] = value
    return loaded


def main() -> None:
    loaded = load_env(ENV_PATH)
    required = ["SILICONFLOW_API_KEY", "DEEPSEEK_API_KEY"]
    missing = [k for k in required if not os.environ.get(k, "").strip()]
    if missing:
        raise SystemExit(f"empty keys in .env: {missing}")

    full_store = ROOT / "data" / "private" / "full_corpus"
    default_store = str(full_store) if (full_store / "chunks.jsonl").is_file() else "data/processed"
    os.environ.setdefault("GEOCHEM_STORE", default_store)
    # Ensure providers are the online pair.
    os.environ.setdefault("GEOCHEM_CHAT_PROVIDER", "deepseek")
    os.environ.setdefault("GEOCHEM_EMBEDDING_PROVIDER", "siliconflow")

    print("Loaded env keys:", ", ".join(sorted(loaded)))
    print("GEOCHEM_STORE=", os.environ.get("GEOCHEM_STORE"))
    print("CHAT_PROVIDER=", os.environ.get("GEOCHEM_CHAT_PROVIDER"))
    print("EMBED_PROVIDER=", os.environ.get("GEOCHEM_EMBEDDING_PROVIDER"))

    # Delegate to streamlit with the same interpreter + env.
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT / "src"))
    from streamlit.web import cli as stcli

    sys.argv = [
        "streamlit",
        "run",
        str(APP),
        "--server.headless=true",
        "--server.port=8501",
        "--browser.gatherUsageStats=false",
    ]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
