# Canon Printer Manager

Lightweight Python/FastAPI backend foundation for managing a Canon PIXMA MG5350
printer on a LAN. Current endpoints cover health, CUPS queue status, upload,
and preview. Printing endpoints are not implemented yet.

## Setup and diagnostics

Expected LAN addresses:

- Printer queue: `Canon_MG5350`
- Printer IP: `192.168.100.100`
- Backend host: `192.168.100.99`

This service has no authentication in v1. Bind it only to the LAN interface and
do not expose it to the internet.

### System prerequisites

On Ubuntu, install CUPS and the system Python bindings for CUPS:

```bash
sudo apt update
sudo apt install -y cups cups-client python3-cups poppler-utils
```

Do not install `pycups` from pip for this project. It requires native
compilation and duplicates the Ubuntu-packaged CUPS bindings this backend uses
to talk to the system CUPS daemon.

`poppler-utils` is required by PDF preview generation. Preview rendering is an
approximation for convenience and is not guaranteed to match final CUPS or
printer-driver output exactly.

### Python environment

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python -c "import cups; print('cups ok')"
```

The current dependencies are intentionally small:

- Runtime pip dependencies: `fastapi` and `uvicorn`.
- Development/test pip dependencies: `pytest` and `httpx`.
- CUPS Python bindings: `python3-cups` from apt, exposed to the venv through
  `--system-site-packages`.

### Run the API

```bash
uvicorn app.main:app --host 192.168.100.99 --port 8000
```

Available endpoints:

- `GET /health` returns service liveness.
- `GET /status` returns normalized CUPS status for `Canon_MG5350`.
- `POST /files` accepts a PDF, PNG, JPEG, or text upload.
- `GET /files/{file_id}/preview` returns preview page metadata and URLs.
- `GET /files/{file_id}/preview/{page}` returns a preview PNG.
- `POST /print` submits an uploaded file to CUPS after safety checks.
- `GET /jobs` lists CUPS jobs.
- `GET /jobs/{job_id}` returns one CUPS job.
- `DELETE /jobs/{job_id}` cancels a CUPS job where possible.

Upload responses include `file_id`, sanitized `original_filename`,
`detected_mime`, `size_bytes`, `page_count` when known, and
`preview_available`.

Temporary uploads and previews are stored under `TMP_DIR`, which defaults to
`/var/tmp/printer-backend`. Set `MAX_UPLOAD_MB` to change the upload size
limit; the default is `50`.

### Print submission

`POST /print` accepts an uploaded `file_id` and conservative print options:

```json
{
  "file_id": "uploaded-file-id",
  "options": {
    "copies": 1,
    "pages": "1",
    "paper_size": "A4",
    "orientation": "portrait",
    "color_mode": "monochrome",
    "duplex": "none",
    "quality": "normal",
    "collate": false,
    "media_type": "Plain",
    "fit_to_page": true
  }
}
```

The response includes `job_id`, queue name, submitted title,
`applied_options`, `unsupported_options`, and `warnings`. Unsupported or
undetected CUPS options are dropped instead of failing the request.

Page ranges support values like `1`, `1,3,5`, `1-3`, and `1,3-5,8`. For PDFs,
the backend creates a temporary filtered PDF and preserves the requested page
order. For image files, page ranges are only valid when selecting page `1`.

Before submitting, the backend blocks printing if CUPS is unavailable, the
`Canon_MG5350` queue is missing, the queue is stopped, the queue is rejecting
jobs, or CUPS reports an offline reason. Infrastructure failures return `503`;
queue state conflicts return `409`.

Current option mapping uses detected queue capabilities from:

```bash
lpoptions -p Canon_MG5350 -l
```

At minimum, the backend attempts to map `copies`, `duplex`, `orientation`,
`paper_size`, `color_mode`, and `quality`. Color, quality, and media mappings
may vary by driver/PPD, so review response warnings before relying on them.

First real print should be simplex, monochrome, and one page:

```bash
curl -4 -X POST http://ubuntu26-remote.local:8000/files \
  -F "file=@test.pdf;type=application/pdf"

curl -4 -X POST http://ubuntu26-remote.local:8000/print \
  -H "content-type: application/json" \
  -d '{
    "file_id": "replace-with-uploaded-file-id",
    "options": {
      "copies": 1,
      "pages": "1",
      "color_mode": "monochrome",
      "duplex": "none"
    }
  }'
```

Inspect jobs with:

```bash
lpstat -o
lpstat -p Canon_MG5350 -l
cancel <job_id>
```

### Run diagnostics

The probe script checks local CUPS tooling, the expected queue, printer network
reachability, common printer TCP ports, and available `lpstat`/`lpoptions`
diagnostics. It prints human-readable output and ends with a single-line JSON
summary.

```bash
python3 scripts/probe.py
```

### Configure the printer queue

The setup script is idempotent and defaults to:

- `QUEUE_NAME=Canon_MG5350`
- `PRINTER_IP=192.168.100.100`
- `DEVICE_URI=ipp://192.168.100.100/ipp/print`
- `MODEL=everywhere` for new queue creation

Run it only when you are ready to change local CUPS configuration:

```bash
sudo scripts/setup_printer.sh
```

Override defaults with environment variables when needed:

```bash
sudo QUEUE_NAME=Canon_MG5350 PRINTER_IP=192.168.100.100 \
  DEVICE_URI=ipp://192.168.100.100/ipp/print scripts/setup_printer.sh
```

If the queue already exists with the expected URI, the script makes no changes.
If it exists with another URI, it prompts before updating only the URI. It does
not delete queues, purge jobs, reset CUPS, or change an existing queue driver.

### Run tests

The tests mock CUPS access and do not require a real printer:

```bash
pytest
```
