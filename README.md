# Local Printer API

Lightweight Python/FastAPI backend for managing any printer through a local CUPS queue.

The app exposes a REST API for:

- checking backend and printer status,
- uploading files,
- generating previews,
- submitting conservative print jobs,
- inspecting CUPS jobs,
- cancelling CUPS jobs,
- discovering printer options for a future frontend.

The backend is designed as a thin orchestration layer over Linux CUPS. CUPS remains the source of truth for printer queues, printer capabilities, and print jobs.

This project currently focuses on the backend only. Frontend, authentication, persistent job history, and multi-user management are outside v1 scope.

---

## Features

Current backend capabilities:

- FastAPI REST API.
- CUPS queue status endpoint.
- File upload support:
  - PDF
  - PNG
  - JPEG
  - plain text
- Temporary file storage with metadata sidecars.
- PDF page-count detection.
- PDF and image preview generation.
- Preview page serving as PNG.
- PDF page-range filtering before print submission.
- Print submission through CUPS.
- CUPS job listing, details, and cancellation.
- Frontend-friendly `/options` endpoint based on detected CUPS/PPD capabilities.
- Diagnostic and setup scripts.

---

## Basic installation

### 1. Install system packages

On Ubuntu/Debian-like systems:

```bash
sudo apt update
sudo apt install -y \
  cups \
  cups-client \
  python3-cups \
  poppler-utils \
  printer-driver-gutenprint
```

Package purpose:

* `cups`, `cups-client` — local print server and CLI tools.
* `python3-cups` — Python bindings for CUPS.
* `poppler-utils` — required for PDF preview rendering.
* `printer-driver-gutenprint` — useful driver package for many older printers.

Do not install `pycups` from pip for this project. Use the system package `python3-cups`.

---

### 2. Create Python environment

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python -c "import cups; print('cups ok')"
```

The `--system-site-packages` flag is important because the `cups` Python module comes from the OS package `python3-cups`.

---

### 3. Configure a CUPS queue

This app requires a working CUPS printer queue.

A typical setup script is provided:

```bash
sudo scripts/setup_printer.sh
```

If you need to overwrite an existing queue configuration:

```bash
sudo scripts/setup_printer.sh --force
```

Optional tiny test print:

```bash
sudo scripts/setup_printer.sh --test
```

If you are not using the Canon MG5350 environment documented in this repository, adapt the queue name, device URI, and driver/model first.

---

## Run the API

From the repository root:

```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then test:

```bash
curl -i http://localhost:8000/health
```

From another machine on the LAN:

```bash
export PRINTER_BACKEND="http://<server-host-or-ip>:8000"
curl -i "$PRINTER_BACKEND/health"
```

---

## Basic API usage

### Health check

```bash
curl -s "$PRINTER_BACKEND/health" | jq
```

### Printer status

```bash
curl -s "$PRINTER_BACKEND/status" | jq
```

### Printer options

```bash
curl -s "$PRINTER_BACKEND/options" | jq
```

With raw CUPS/PPD debug information:

```bash
curl -s "$PRINTER_BACKEND/options?debug=true" | jq
```

### Upload a file

```bash
curl -s -X POST "$PRINTER_BACKEND/files" \
  -F "file=@test.pdf;type=application/pdf" | jq
```

Save the returned `file_id`:

```bash
export FILE_ID="replace-with-uploaded-file-id"
```

### Generate/read preview

```bash
curl -s "$PRINTER_BACKEND/files/$FILE_ID/preview" | jq
```

Download page 1 preview:

```bash
curl -o preview-page-1.png "$PRINTER_BACKEND/files/$FILE_ID/preview/1"
```

### Print one page safely

```bash
curl -s -X POST "$PRINTER_BACKEND/print" \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "'"$FILE_ID"'",
    "options": {
      "copies": 1,
      "pages": "1",
      "paper_size": "A4",
      "orientation": "portrait",
      "color_mode": "monochrome",
      "duplex": "none",
      "quality": "normal",
      "collate": false,
      "media_type": "plain",
      "fit_to_page": true
    }
  }' | jq
```

### Jobs

```bash
curl -s "$PRINTER_BACKEND/jobs" | jq
curl -s "$PRINTER_BACKEND/jobs/2" | jq
curl -s -X DELETE "$PRINTER_BACKEND/jobs/2" | jq
```

---

## Testing

Run syntax checks:

```bash
python -m py_compile $(find app scripts tests -name '*.py')
```

Run tests:

```bash
python -m pytest -q
```

Verbose mode:

```bash
python -m pytest -v
```

Check shell scripts:

```bash
bash -n scripts/*.sh
```

Recommended full validation:

```bash
python -m py_compile $(find app scripts tests -name '*.py')
python -m pytest -q
bash -n scripts/*.sh
```

Normal tests mock CUPS and should not require a physical printer.

---

## Diagnostic scripts

General probe:

```bash
python3 scripts/probe.py
```

LPD/CUPS diagnostic script:

```bash
scripts/debug_printer_lpd.sh
```

API smoke test without printing:

```bash
PRINTER_BACKEND=http://localhost:8000 scripts/smoke_print_api.sh --dry-run
```

Real one-page smoke print:

```bash
PRINTER_BACKEND=http://localhost:8000 scripts/smoke_print_api.sh --print
```

---

## Documentation map

For more detail, see:

* `openapi.yaml` — full API reference.
* `ENVIRONMENT.md` — documented verified Canon MG5350 environment.
* `TROUBLESHOOTING.md` — CUPS, driver, LPD, backend, and diagnostic notes.
* `LIMITATIONS_AND_FUTURE.md` — known limitations and planned improvements.
