"""One-shot quiet import of public samples + reimport dedup check.

Uses an isolated temporary store; never clears the user's default store.
"""

from __future__ import annotations

import json
import logging
from tempfile import TemporaryDirectory
from pathlib import Path

logging.disable(logging.WARNING)

from geochem_rag.ingest import ingest_pdf
from geochem_rag.store import LocalStore


def main() -> None:
    meta = json.loads(Path("data/sources.json").read_text(encoding="utf-8"))
    with TemporaryDirectory(prefix="geochem-rag-import-check-") as temp_dir:
        store = LocalStore(temp_dir)
        rows = []
        for m in meta["sources"]:
            pdf = Path(m["local_path"])
            src, chunks, rep = ingest_pdf(
                pdf,
                license_name=m["license"],
                license_url=m["license_url"],
                title=m["title"],
                authors=m["authors"],
                year=m["year"],
                doi_or_url=m["doi_or_url"],
                download_date=m["download_date"],
                visibility=m["visibility"],
                source_id=m["source_id"],
            )
            r1 = store.import_document(src, chunks, rep)
            r2 = store.import_document(src, chunks, rep)
            rows.append(
                {
                    "source_id": r1.source_id,
                    "pages": rep.page_count,
                    "ok": rep.ok_pages,
                    "failed_pages": rep.failed_pages,
                    "quality": rep.quality_counts,
                    "chunks": r1.chunk_count,
                    "first_import": r1.status,
                    "reimport": r2.status,
                    "chunks_after_reimport": store.count_chunks(src.source_id),
                }
            )
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        print("TOTAL_CHUNKS", store.count_chunks())


if __name__ == "__main__":
    main()
