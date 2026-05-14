from __future__ import annotations

import os


DEFAULT_CORS_ALLOWED_ORIGINS = (
    "http://192.168.100.99:5173",
    "http://ubuntu26-remote.local:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://192.168.100.99:5174",
    "http://ubuntu26-remote.local:5174",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://192.168.100.99:5175",
    "http://ubuntu26-remote.local:5175",
    "http://localhost:5175",
    "http://127.0.0.1:5175",
)


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _env_csv(name: str, default: tuple[str, ...]) -> list[str]:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


QUEUE_NAME = os.getenv("QUEUE_NAME", "Canon_MG5350")
PRINTER_IP = os.getenv("PRINTER_IP", "192.168.100.100")
BACKEND_HOST = os.getenv("BACKEND_HOST", "192.168.100.99")
BACKEND_PORT = _env_int("BACKEND_PORT", 8000)
TMP_DIR = os.getenv("TMP_DIR", "/var/tmp/printer-backend")
MAX_UPLOAD_MB = _env_int("MAX_UPLOAD_MB", 50)
PREVIEW_DPI = _env_int("PREVIEW_DPI", 110)
CORS_ALLOWED_ORIGINS = _env_csv("CORS_ALLOWED_ORIGINS", DEFAULT_CORS_ALLOWED_ORIGINS)
