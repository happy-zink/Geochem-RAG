"""Manual import must work without a metadata registry or network."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter

from geochem_rag.import_pdf import main
from geochem_rag.store import LocalStore


def _write_blank_pdf(path: Path, page_count: int) -> None:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=612, height=792)
    with path.open("wb") as handle:
        writer.write(handle)


def test_manual_private_import_and_reimport(tmp_path: Path, capsys):
    pdf = tmp_path / "new-paper.pdf"
    store_path = tmp_path / "store"
    _write_blank_pdf(pdf, 1)

    assert main(["--pdf", str(pdf), "--store", str(store_path)]) == 0
    first_output = capsys.readouterr().out
    assert '"import_status": "imported"' in first_output
    store = LocalStore(store_path)
    source = store.load_sources()[0]
    assert source.visibility == "private"
    assert source.title == "new-paper"
    assert source.title_is_filename is True
    assert source.authors == []
    assert source.year is None
    assert source.license_url is None

    assert main(["--pdf", str(pdf), "--store", str(store_path)]) == 0
    assert '"import_status": "already_exists"' in capsys.readouterr().out
    assert len(store.load_sources()) == 1

    assert main(["--pdf", str(pdf), "--store", str(store_path), "--title", "Verified title"]) == 0
    assert '"import_status": "metadata_updated"' in capsys.readouterr().out
    assert store.load_sources()[0].title == "Verified title"
    assert store.load_sources()[0].title_is_filename is False

    _write_blank_pdf(pdf, 2)
    assert main(["--pdf", str(pdf), "--store", str(store_path)]) == 0
    assert '"import_status": "replaced"' in capsys.readouterr().out
    assert len(store.load_sources()) == 1
    assert store.load_sources()[0].sha256 != source.sha256
