from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse

from app.models.print_options import PrintRequest
from app.services.cups_client import CupsClient, CupsClientError
from app.services.file_storage import StoredFile, StorageError, TempFileStorage
from app.services.options_summary import build_options_summary
from app.services.preview import PreviewError, PreviewService
from app.services.print_service import PrintRequestError, submit_print_job
from app.services.status_translator import translate_error_status, translate_queue_status
from app.settings import QUEUE_NAME


OPENAPI_YAML_PATH = Path(__file__).resolve().parent.parent / "openapi.yaml"


app = FastAPI(title="Local Printer API", docs_url=None)


@app.get("/openapi.yaml", include_in_schema=False)
def openapi_yaml() -> FileResponse:
    if not OPENAPI_YAML_PATH.exists():
        raise HTTPException(status_code=404, detail="openapi.yaml not found")
    return FileResponse(OPENAPI_YAML_PATH, media_type="application/yaml")


@app.get("/docs", include_in_schema=False)
def swagger_docs() -> HTMLResponse:
    return get_swagger_ui_html(
        openapi_url="/openapi.yaml",
        title="Local Printer API Docs",
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "local-printer-api"}


def get_cups_client() -> CupsClient:
    return CupsClient()


def get_file_storage() -> TempFileStorage:
    return TempFileStorage()


@app.get("/status")
def status(client: CupsClient = Depends(get_cups_client)) -> dict[str, object]:
    try:
        payload = translate_queue_status(client.get_queue())
        payload["cups"] = {"available": True, "error": None}
        return payload
    except CupsClientError as exc:
        payload = translate_error_status(QUEUE_NAME, str(exc))
        payload["cups"] = {"available": False, "error": str(exc)}
        return payload


@app.post("/print")
def print_file(
    request: PrintRequest,
    client: CupsClient = Depends(get_cups_client),
    storage: TempFileStorage = Depends(get_file_storage),
) -> dict[str, object]:
    record = storage.get_record(request.file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        return submit_print_job(client, storage, record, request.options)
    except PrintRequestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@app.get("/jobs")
def list_jobs(client: CupsClient = Depends(get_cups_client)) -> dict[str, object]:
    try:
        return {"jobs": client.list_jobs()}
    except CupsClientError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/options")
def get_options(
    debug: bool = False,
    client: CupsClient = Depends(get_cups_client),
) -> dict[str, object]:
    try:
        capabilities = client.get_option_capabilities()
    except CupsClientError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return build_options_summary(client.queue_name, capabilities, include_debug=debug)


@app.get("/jobs/{job_id}")
def get_job(job_id: int, client: CupsClient = Depends(get_cups_client)) -> dict[str, object]:
    try:
        job = client.get_job(job_id)
    except CupsClientError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.delete("/jobs/{job_id}")
def cancel_job(job_id: int, client: CupsClient = Depends(get_cups_client)) -> dict[str, object]:
    try:
        cancelled = client.cancel_job(job_id)
    except CupsClientError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {"job_id": job_id, "cancelled": cancelled}


@app.post("/files")
async def upload_file(
    file: UploadFile = File(...),
    storage: TempFileStorage = Depends(get_file_storage),
) -> dict[str, object]:
    try:
        record = await storage.save_upload(file)
    except StorageError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return file_response(record)


@app.get("/files/{file_id}/preview")
def list_previews(
    file_id: str,
    storage: TempFileStorage = Depends(get_file_storage),
) -> dict[str, object]:
    record = storage.get_record(file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")

    preview_service = PreviewService(storage)
    try:
        paths = preview_service.ensure_previews(record)
    except PreviewError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return {
        "file_id": record.file_id,
        "page_count": record.page_count,
        "pages": [
            {
                "page": index,
                "url": f"/files/{record.file_id}/preview/{index}",
                "size_bytes": path.stat().st_size,
            }
            for index, path in enumerate(paths, start=1)
        ],
    }


@app.get("/files/{file_id}/preview/{page}")
def get_preview_page(
    file_id: str,
    page: str,
    storage: TempFileStorage = Depends(get_file_storage),
) -> FileResponse:
    record = storage.get_record(file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")

    preview_service = PreviewService(storage)
    try:
        page_number = parse_page_number(page)
        path = preview_service.preview_path(record, page_number)
    except PreviewError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return FileResponse(path, media_type="image/png")


def file_response(record: StoredFile) -> dict[str, object]:
    return {
        "file_id": record.file_id,
        "original_filename": record.original_filename,
        "detected_mime": record.detected_mime,
        "size_bytes": record.size_bytes,
        "page_count": record.page_count,
        "preview_available": record.preview_available,
    }


def parse_page_number(page: str) -> int:
    try:
        page_number = int(page)
    except ValueError as exc:
        raise PreviewError("Invalid page number", 400) from exc
    if page_number < 1:
        raise PreviewError("Invalid page number", 400)
    return page_number
