from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.services.cups_client import CupsClient, CupsClientError
from app.services.file_storage import StoredFile, StorageError, TempFileStorage
from app.services.preview import PreviewError, PreviewService
from app.services.status_translator import translate_error_status, translate_queue_status
from app.settings import QUEUE_NAME


app = FastAPI(title="Canon Printer Manager")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "canon-printer-manager"}


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
