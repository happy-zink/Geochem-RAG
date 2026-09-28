"""CLI: import one PDF into the local store with page/chunk report.

Usage (PowerShell):
  python -m geochem_rag.import_pdf --pdf "PDF\\new-paper.pdf"

Without --meta, a local PDF is private and unknown metadata stays empty.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .ingest import ingest_pdf
from .store import LocalStore


def _load_meta(meta_path: Path, pdf_path: Path) -> dict:
    data = json.loads(meta_path.read_text(encoding="utf-8"))
    rel = str(pdf_path).replace("\\", "/")
    for row in data.get("sources", []):
        if row.get("local_path") and Path(row["local_path"]).as_posix() == Path(rel).as_posix():
            return row
        if row.get("local_path") and Path(row["local_path"]).name == pdf_path.name:
            return row
    raise SystemExit(f"no metadata entry for {pdf_path} in {meta_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import one local PDF as private by default")
    parser.add_argument("--pdf", required=True, help="path to PDF")
    parser.add_argument("--meta", help="optional source registry JSON for curated metadata")
    parser.add_argument("--title", help="optional title; filename is used when absent")
    parser.add_argument("--author", action="append", default=[], help="author; repeat for multiple authors")
    parser.add_argument("--year", type=int, help="optional publication year")
    parser.add_argument("--doi", help="optional DOI or source URL")
    parser.add_argument("--store", default="data/processed", help="local store directory")
    args = parser.parse_args(argv)

    pdf_path = Path(args.pdf)
    if not pdf_path.is_file():
        parser.error(f"PDF not found: {pdf_path}")
    meta = _load_meta(Path(args.meta), pdf_path) if args.meta else {}
    # A manually added file keeps its source id when its bytes change at the
    # same path, allowing LocalStore to replace old chunks on reimport.
    local_source_id = None
    if not args.meta:
        path_digest = hashlib.sha256(str(pdf_path.resolve()).encode("utf-8")).hexdigest()
        local_source_id = f"src_local_{path_digest[:16]}"
    source, chunks, report = ingest_pdf(
        pdf_path,
        license_name=meta.get("license"),
        license_url=meta.get("license_url"),
        title=args.title or meta.get("title"),
        authors=args.author or meta.get("authors"),
        year=args.year if args.year is not None else meta.get("year"),
        doi_or_url=args.doi or meta.get("doi_or_url"),
        download_date=meta.get("download_date"),
        visibility=meta.get("visibility", "private"),
        source_id=meta.get("source_id") or local_source_id,
    )
    store = LocalStore(args.store)
    result = store.import_document(source, chunks, report)

    print(json.dumps(
        {
            "import_status": result.status,
            "source_id": result.source_id,
            "title": source.title,
            "title_is_filename": source.title_is_filename,
            "visibility": source.visibility,
            "sha256": result.sha256,
            "chunk_count": result.chunk_count,
            "report": report.to_dict(),
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
