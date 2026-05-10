from __future__ import annotations


SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "text/plain",
}


def detect_mime(sample: bytes) -> str:
    magic_mime = _detect_with_python_magic(sample)
    if magic_mime in SUPPORTED_MIME_TYPES:
        return magic_mime

    fallback_mime = _detect_from_content(sample)
    if fallback_mime in SUPPORTED_MIME_TYPES:
        return fallback_mime

    return magic_mime or fallback_mime or "application/octet-stream"


def _detect_with_python_magic(sample: bytes) -> str | None:
    try:
        import magic  # type: ignore[import-not-found]
    except ImportError:
        return None

    try:
        detected = magic.from_buffer(sample, mime=True)
    except Exception:
        return None

    if not isinstance(detected, str):
        return None
    return detected.split(";", 1)[0].strip().lower()


def _detect_from_content(sample: bytes) -> str:
    if sample.startswith(b"%PDF-"):
        return "application/pdf"
    if sample.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if sample.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if _looks_like_text(sample):
        return "text/plain"
    return "application/octet-stream"


def _looks_like_text(sample: bytes) -> bool:
    if not sample:
        return False
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True
