from __future__ import annotations

from typing import Any

from app.settings import QUEUE_NAME


class CupsClientError(RuntimeError):
    """Raised when CUPS cannot be reached or queried."""


class CupsClient:
    """Small lazy wrapper around the CUPS Python bindings."""

    def __init__(self, queue_name: str = QUEUE_NAME) -> None:
        self.queue_name = queue_name

    def get_queue(self) -> dict[str, Any]:
        try:
            import cups  # type: ignore[import-not-found]
        except ImportError as exc:
            raise CupsClientError("CUPS Python bindings are not installed") from exc

        try:
            connection = cups.Connection()
            printers = connection.getPrinters()
        except Exception as exc:
            raise CupsClientError(f"CUPS query failed: {exc}") from exc

        if self.queue_name not in printers:
            return {"name": self.queue_name, "exists": False, "attributes": {}}

        return {
            "name": self.queue_name,
            "exists": True,
            "attributes": dict(printers[self.queue_name]),
        }
