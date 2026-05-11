from __future__ import annotations

import os


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


QUEUE_NAME = os.getenv("QUEUE_NAME", "Canon_MG5350")
PRINTER_IP = os.getenv("PRINTER_IP", "192.168.100.100")
BACKEND_HOST = os.getenv("BACKEND_HOST", "192.168.100.99")
BACKEND_PORT = _env_int("BACKEND_PORT", 8000)
TMP_DIR = os.getenv("TMP_DIR", "/var/tmp/printer-backend")
MAX_UPLOAD_MB = _env_int("MAX_UPLOAD_MB", 50)
PREVIEW_DPI = _env_int("PREVIEW_DPI", 110)
