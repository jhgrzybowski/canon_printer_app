from fastapi import Depends, FastAPI

from app.services.cups_client import CupsClient, CupsClientError
from app.services.status_translator import translate_error_status, translate_queue_status
from app.settings import QUEUE_NAME


app = FastAPI(title="Canon Printer Manager")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "canon-printer-manager"}


def get_cups_client() -> CupsClient:
    return CupsClient()


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
