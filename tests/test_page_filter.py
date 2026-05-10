from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from app.services.page_filter import PageRangeError, filter_pdf_pages, parse_page_ranges


def make_pdf(path: Path, page_count: int) -> None:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=72, height=72)
    with path.open("wb") as output:
        writer.write(output)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1", [1]),
        ("1,3,5", [1, 3, 5]),
        ("1-3", [1, 2, 3]),
        ("1,3-5,8", [1, 3, 4, 5, 8]),
    ],
)
def test_parse_page_ranges(text: str, expected: list[int]) -> None:
    assert parse_page_ranges(text, 10) == expected


@pytest.mark.parametrize("text", ["0", "-1", "5-3", "11", "abc", "1,,2", "1-"])
def test_parse_page_ranges_rejects_invalid_input(text: str) -> None:
    with pytest.raises(PageRangeError):
        parse_page_ranges(text, 10)


def test_filter_pdf_pages_preserves_requested_order(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    destination = tmp_path / "filtered.pdf"
    make_pdf(source, 3)

    selected = filter_pdf_pages(source, destination, "3,1-2", 3)

    assert selected == [3, 1, 2]
    assert len(PdfReader(destination).pages) == 3
