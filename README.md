# Canon Printer Manager

Lightweight Python/FastAPI backend foundation for managing a Canon PIXMA MG5350
printer on a LAN. Current endpoints cover health, CUPS queue status, upload,
preview, conservative print submission, and CUPS job lifecycle operations.

## Setup and diagnostics

Expected LAN addresses:

- Printer queue: `Canon_MG5350`
- Printer IP: `192.168.100.100`
- Backend host: `192.168.100.99` or `ubuntu26-remote` hostname

This service has no authentication in v1. Bind it only to the LAN interface and
do not expose it to the internet.

### System prerequisites

On Ubuntu, install CUPS, the system Python bindings for CUPS, and Gutenprint:

```bash
sudo apt update
sudo apt install -y cups cups-client python3-cups poppler-utils printer-driver-gutenprint
```

Do not install `pycups` from pip for this project. It requires native
compilation and duplicates the Ubuntu-packaged CUPS bindings this backend uses
to talk to the system CUPS daemon.

`poppler-utils` is required by PDF preview generation. Preview rendering is an
approximation for convenience and is not guaranteed to match final CUPS or
printer-driver output exactly.

The Canon PIXMA MG5350 does not work as an IPP Everywhere / driverless printer
in this setup. Port `631` is reachable, but the printer does not provide the
IPP attributes/document formats CUPS needs for `MODEL=everywhere`.

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
uvicorn app.main:app --host ubuntu26-remote --port 8000
```

Available endpoints:

- `GET /health` returns service liveness.
- `GET /status` returns normalized CUPS status for `Canon_MG5350`.
- `POST /files` accepts a PDF, PNG, JPEG, or text upload.
- `GET /files/{file_id}/preview` returns preview page metadata and URLs.
- `GET /files/{file_id}/preview/{page}` returns a preview PNG.
- `POST /print` submits an uploaded file to CUPS after safety checks.
- `GET /options` returns detected CUPS option capabilities for the queue.
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

### Verified MG5350 setup

The currently verified real-printer setup is:

- Queue: `Canon_MG5350`
- Device URI: `lpd://192.168.100.100/PASSTHRU`
- Driver/model: `gutenprint.5.3://bjc-PIXMA-MG5350/expert`

The first successful API print used one page, monochrome, simplex, A4, normal
quality, with this effective CUPS option set:

```json
{
  "copies": "1",
  "Duplex": "None",
  "orientation-requested": "3",
  "PageSize": "A4",
  "ColorModel": "Gray",
  "Resolution": "600dpi"
}
```

`GET /options` reports the detected CUPS/Gutenprint capabilities in a
frontend-friendly shape. Use `GET /options?debug=true` to include raw option
names and values from `lpoptions`.

Known option mapping notes:

- `collate` is ignored without a noisy unsupported warning when `copies=1`.
- `collate` is reported unsupported for multiple copies unless CUPS exposes a
  collate option.
- `media_type` maps safe aliases such as `plain`, `photo`, `glossy`, and
  `matte` only when corresponding Gutenprint media values are detected.
- `fit_to_page` maps only when a detected CUPS/Gutenprint scaling option exists;
  it is otherwise reported unsupported rather than faked.
- `orientation` prefers detected Gutenprint `StpOrientation`; otherwise it falls
  back to standard `orientation-requested` values. Landscape should still be
  verified with a real test page before relying on it.

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

Manual integration checks:

```bash
lpstat -v Canon_MG5350
lpoptions -p Canon_MG5350 -l
lpstat -W all -o Canon_MG5350
sudo journalctl -u cups --no-pager -n 100
```

Dry-run API smoke test:

```bash
PRINTER_BACKEND=http://ubuntu26-remote.local:8000 scripts/smoke_print_api.sh --dry-run
```

Real one-page smoke print:

```bash
PRINTER_BACKEND=http://ubuntu26-remote.local:8000 scripts/smoke_print_api.sh --print
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

The verified working setup is:

- `QUEUE_NAME=Canon_MG5350`
- `PRINTER_IP=192.168.100.100`
- `DEVICE_URI=lpd://192.168.100.100/PASSTHRU`
- `MODEL=gutenprint.5.3://bjc-PIXMA-MG5350/expert`

The setup script auto-detects Gutenprint models in this order:

1. `gutenprint.5.3://bjc-PIXMA-MG5350/expert`
2. `gutenprint.5.3://bjc-PIXMA-MG5300/expert`
3. `gutenprint.5.3://bjc-MG5300-series/expert`

It does not default to `everywhere`, IPP, or socket/9100. Known LPD fallback
URIs, if `PASSTHRU` ever stops working, are `lpd://192.168.100.100/lp` and
`lpd://192.168.100.100/print`.

Run it only when you are ready to change local CUPS configuration:

```bash
sudo scripts/setup_printer.sh
```

If an existing queue does not match the verified URI/model signal, the script
does not overwrite it unless `--force` or `FORCE=1` is used:

```bash
sudo scripts/setup_printer.sh --force
```

To submit a tiny text test job after setup:

```bash
sudo scripts/setup_printer.sh --test
```

Override defaults with environment variables when needed:

```bash
sudo QUEUE_NAME=Canon_MG5350 PRINTER_IP=192.168.100.100 \
  DEVICE_URI=lpd://192.168.100.100/PASSTHRU \
  MODEL=gutenprint.5.3://bjc-PIXMA-MG5350/expert \
  scripts/setup_printer.sh
```

The script prints final diagnostics with queue state, device URI, and the first
80 `lpoptions` lines.

### LPD diagnostics

Run the non-destructive LPD debug script from the server:

```bash
scripts/debug_printer_lpd.sh
```

It checks the current user/groups, CUPS service state, required commands,
Gutenprint model discovery, printer reachability, TCP ports `80`, `515`, `631`,
and `9100`, queue status, queue options, and recent CUPS logs.

It does not print unless explicitly requested:

```bash
scripts/debug_printer_lpd.sh --test-print
```

Useful troubleshooting commands:

```bash
lpstat -p Canon_MG5350 -l
lpstat -v Canon_MG5350
lpstat -W all -o Canon_MG5350
lpoptions -p Canon_MG5350 -l
sudo journalctl -u cups --no-pager -n 100
```

### Run tests

The tests mock CUPS access and do not require a real printer:

```bash
pytest
```
