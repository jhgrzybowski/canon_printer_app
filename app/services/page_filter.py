from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError


RANGE_RE = re.compile(r"^\d+(?:-\d+)?$")


class PageRangeError(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def parse_page_ranges(page_ranges: str, page_count: int) -> list[int]:
    text = page_ranges.strip()
    if not text:
        raise PageRangeError("Page range is empty")
    if page_count < 1:
        raise PageRangeError("Document has no pages")

    pages: list[int] = []
    for token in text.split(","):
        token = token.strip()
        if not RANGE_RE.fullmatch(token):
            raise PageRangeError(f"Malformed page range: {token or '<empty>'}")
        if "-" in token:
            start_text, end_text = token.split("-", 1)
            start = _parse_page_number(start_text, page_count)
            end = _parse_page_number(end_text, page_count)
            if start > end:
                raise PageRangeError(f"Reversed page range: {token}")
            pages.extend(range(start, end + 1))
        else:
            pages.append(_parse_page_number(token, page_count))

    return pages


def filter_pdf_pages(source: Path, destination: Path, page_ranges: str, page_count: int) -> list[int]:
    pages = parse_page_ranges(page_ranges, page_count)
    try:
        reader = PdfReader(source)
    except PdfReadError as exc:
        raise PageRangeError("Unable to read PDF for page filtering") from exc

    if reader.is_encrypted:
        raise PageRangeError("Password-protected PDFs are not supported")

    writer = PdfWriter()
    try:
        for page_number in pages:
            writer.add_page(reader.pages[page_number - 1])
        with destination.open("wb") as output:
            writer.write(output)
    except Exception as exc:
        destination.unlink(missing_ok=True)
        raise PageRangeError("Unable to create filtered PDF") from exc

    return pages


def _parse_page_number(text: str, page_count: int) -> int:
    try:
        page = int(text)
    except ValueError as exc:
        raise PageRangeError(f"Malformed page number: {text}") from exc
    if page < 1:
        raise PageRangeError(f"Invalid page number: {page}")
    if page > page_count:
        raise PageRangeError(f"Page {page} is outside document bounds")
    return page
