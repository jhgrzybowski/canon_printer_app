from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.main import app, get_cups_client, get_file_storage
from app.services.cups_client import CupsClientError
from app.services.file_storage import TempFileStorage


@pytest.fixture
def storage(tmp_path: Path) -> TempFileStorage:
    return TempFileStorage(tmp_path, max_upload_mb=1)


@pytest.fixture
def client(storage: TempFileStorage) -> TestClient:
    app.dependency_overrides.clear()
    app.dependency_overrides[get_file_storage] = lambda: storage
    app.dependency_overrides[get_cups_client] = lambda: FakeCupsClient()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class FakeCupsClient:
    queue_name = "Canon_MG5350"

    def __init__(self, queue: dict[str, Any] | None = None) -> None:
        self.queue = queue or ready_queue()
        self.submissions: list[dict[str, Any]] = []

    def get_queue(self) -> dict[str, Any]:
        return self.queue

    def get_option_capabilities(self) -> dict[str, set[str]]:
        return {
            "PageSize": {"A4"},
            "ColorModel": {"Gray", "RGB"},
            "Duplex": {"None", "DuplexNoTumble", "DuplexTumble"},
            "Quality": {"Normal", "High"},
        }

    def print_file(self, path: Path, title: str, options: dict[str, str]) -> int:
        self.submissions.append({"path": path, "title": title, "options": options})
        return 123

    def list_jobs(self) -> list[dict[str, Any]]:
        return [{"job_id": 123, "state": "processing", "reasons": []}]

    def get_job(self, job_id: int) -> dict[str, Any] | None:
        if job_id == 123:
            return {"job_id": 123, "state": "processing", "reasons": []}
        return None

    def cancel_job(self, job_id: int) -> bool:
        return job_id == 123


class FailingCupsClient(FakeCupsClient):
    def get_queue(self) -> dict[str, Any]:
        raise CupsClientError("CUPS unavailable")


def ready_queue() -> dict[str, Any]:
    return {
        "name": "Canon_MG5350",
        "exists": True,
        "attributes": {
            "printer-state": 3,
            "printer-is-accepting-jobs": True,
            "printer-state-reasons": ["none"],
        },
    }


def missing_queue() -> dict[str, Any]:
    return {"name": "Canon_MG5350", "exists": False, "attributes": {}}


def stopped_queue() -> dict[str, Any]:
    queue = ready_queue()
    queue["attributes"]["printer-state"] = 5
    return queue


def make_pdf(page_count: int = 2) -> bytes:
    buffer = BytesIO()
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=72, height=72)
    writer.write(buffer)
    return buffer.getvalue()


def make_png() -> bytes:
    from PIL import Image

    buffer = BytesIO()
    image = Image.new("RGB", (4, 4), color="white")
    image.save(buffer, "PNG")
    return buffer.getvalue()


def upload_pdf(client: TestClient, page_count: int = 2) -> str:
    response = client.post(
        "/files",
        files={"file": ("print.pdf", make_pdf(page_count), "application/pdf")},
    )
    assert response.status_code == 200
    return response.json()["file_id"]


def upload_png(client: TestClient) -> str:
    response = client.post(
        "/files",
        files={"file": ("image.png", make_png(), "image/png")},
    )
    assert response.status_code == 200
    return response.json()["file_id"]


def test_print_pdf_with_mocked_cups(client: TestClient) -> None:
    file_id = upload_pdf(client, 3)

    response = client.post(
        "/print",
        json={
            "file_id": file_id,
            "options": {
                "copies": 2,
                "pages": "1,3",
                "paper_size": "A4",
                "color_mode": "monochrome",
                "duplex": "none",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == 123
    assert body["queue"] == "Canon_MG5350"
    assert body["applied_options"]["copies"] == "2"
    assert body["applied_options"]["PageSize"] == "A4"
    assert body["unsupported_options"] == []
    assert any("page order" in warning for warning in body["warnings"])


def test_print_missing_file_id(client: TestClient) -> None:
    response = client.post("/print", json={"file_id": "missing", "options": {}})

    assert response.status_code == 404


def test_print_invalid_page_range(client: TestClient) -> None:
    file_id = upload_pdf(client, 3)

    response = client.post("/print", json={"file_id": file_id, "options": {"pages": "3-1"}})

    assert response.status_code == 400
    assert "Reversed page range" in response.json()["detail"]


def test_print_rejects_image_page_range_other_than_one(client: TestClient) -> None:
    file_id = upload_png(client)

    response = client.post("/print", json={"file_id": file_id, "options": {"pages": "2"}})

    assert response.status_code == 400
    assert "outside document bounds" in response.json()["detail"]


def test_print_reports_cups_unavailable(storage: TempFileStorage) -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[get_file_storage] = lambda: storage
    app.dependency_overrides[get_cups_client] = lambda: FailingCupsClient()
    with TestClient(app) as client:
        file_id = upload_pdf(client)
        response = client.post("/print", json={"file_id": file_id, "options": {}})

    app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.json()["detail"] == "CUPS unavailable"


def test_print_reports_queue_missing(storage: TempFileStorage) -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[get_file_storage] = lambda: storage
    app.dependency_overrides[get_cups_client] = lambda: FakeCupsClient(missing_queue())
    with TestClient(app) as client:
        file_id = upload_pdf(client)
        response = client.post("/print", json={"file_id": file_id, "options": {}})

    app.dependency_overrides.clear()
    assert response.status_code == 503
    assert "missing" in response.json()["detail"]


def test_print_reports_queue_stopped(storage: TempFileStorage) -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[get_file_storage] = lambda: storage
    app.dependency_overrides[get_cups_client] = lambda: FakeCupsClient(stopped_queue())
    with TestClient(app) as client:
        file_id = upload_pdf(client)
        response = client.post("/print", json={"file_id": file_id, "options": {}})

    app.dependency_overrides.clear()
    assert response.status_code == 409


def test_job_endpoints_use_cups_client(client: TestClient) -> None:
    list_response = client.get("/jobs")
    get_response = client.get("/jobs/123")
    cancel_response = client.delete("/jobs/123")
    missing_cancel_response = client.delete("/jobs/999")

    assert list_response.status_code == 200
    assert list_response.json()["jobs"][0]["job_id"] == 123
    assert get_response.status_code == 200
    assert get_response.json()["state"] == "processing"
    assert cancel_response.status_code == 200
    assert cancel_response.json() == {"job_id": 123, "cancelled": True}
    assert missing_cancel_response.status_code == 200
    assert missing_cancel_response.json() == {"job_id": 999, "cancelled": False}


def test_options_endpoint_returns_detected_capabilities(client: TestClient) -> None:
    response = client.get("/options")

    assert response.status_code == 200
    assert response.json()["queue"] == "Canon_MG5350"
    assert response.json()["options"]["PageSize"] == ["A4"]
