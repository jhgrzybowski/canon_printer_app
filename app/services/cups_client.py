from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from app.settings import QUEUE_NAME
from app.services.lpoptions_parser import parse_lpoptions


class CupsClientError(RuntimeError):
    """Raised when CUPS cannot be reached or queried."""


class CupsClient:
    """Small lazy wrapper around the CUPS Python bindings."""

    def __init__(self, queue_name: str = QUEUE_NAME) -> None:
        self.queue_name = queue_name

    def _connection(self) -> Any:
        try:
            import cups  # type: ignore[import-not-found]
        except ImportError as exc:
            raise CupsClientError("CUPS Python bindings are not installed") from exc

        try:
            return cups.Connection()
        except Exception as exc:
            raise CupsClientError(f"CUPS connection failed: {exc}") from exc

    def get_queue(self) -> dict[str, Any]:
        try:
            connection = self._connection()
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

    def get_option_capabilities(self) -> dict[str, set[str]]:
        try:
            completed = subprocess.run(
                ["lpoptions", "-p", self.queue_name, "-l"],
                check=False,
                capture_output=True,
                text=True,
                timeout=8,
            )
        except (OSError, subprocess.TimeoutExpired):
            return {}

        if completed.returncode != 0:
            return {}
        return parse_lpoptions(completed.stdout)

    def print_file(self, path: Path, title: str, options: dict[str, str]) -> int:
        try:
            connection = self._connection()
            return int(connection.printFile(self.queue_name, str(path), title, options))
        except Exception as exc:
            raise CupsClientError(f"CUPS print submission failed: {exc}") from exc

    def list_jobs(self) -> list[dict[str, Any]]:
        try:
            connection = self._connection()
            jobs = connection.getJobs(which_jobs="all")
        except Exception as exc:
            raise CupsClientError(f"CUPS job query failed: {exc}") from exc
        return [normalize_job(job_id, attrs) for job_id, attrs in jobs.items()]

    def get_job(self, job_id: int) -> dict[str, Any] | None:
        try:
            connection = self._connection()
            attrs = connection.getJobAttributes(job_id)
        except Exception as exc:
            message = str(exc).lower()
            if "not found" in message or "no such" in message or "unknown" in message:
                return None
            raise CupsClientError(f"CUPS job query failed: {exc}") from exc
        return normalize_job(job_id, attrs)

    def cancel_job(self, job_id: int) -> bool:
        if self.get_job(job_id) is None:
            return False
        try:
            connection = self._connection()
            connection.cancelJob(job_id)
        except Exception as exc:
            message = str(exc).lower()
            if "not found" in message or "no such" in message or "unknown" in message:
                return False
            raise CupsClientError(f"CUPS job cancellation failed: {exc}") from exc
        return True


JOB_STATE_LABELS = {
    3: "pending",
    4: "pending-held",
    5: "processing",
    6: "processing-stopped",
    7: "canceled",
    8: "aborted",
    9: "completed",
}


def normalize_job(job_id: int, attrs: dict[str, Any]) -> dict[str, Any]:
    state_code = _as_int(attrs.get("job-state"))
    return {
        "job_id": int(job_id),
        "name": attrs.get("job-name") or attrs.get("document-name-supplied") or "",
        "user": attrs.get("job-originating-user-name") or "",
        "state": JOB_STATE_LABELS.get(state_code, "unknown"),
        "state_code": state_code,
        "reasons": _as_list(attrs.get("job-state-reasons")),
        "printer_uri": attrs.get("job-printer-uri"),
        "created_at": attrs.get("time-at-creation"),
        "completed_at": attrs.get("time-at-completed"),
    }


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list | tuple | set):
        return [str(item) for item in value]
    return [str(value)]
