# Canon Printer Manager

Lightweight Python/FastAPI backend foundation for managing a Canon PIXMA MG5350
printer on a LAN. The first milestone only includes project structure, CUPS
diagnostics, and an idempotent printer setup helper.

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
sudo apt install -y cups cups-client python3-cups
```

Do not install `pycups` from pip for this project. It requires native
compilation and duplicates the Ubuntu-packaged CUPS bindings this backend uses
to talk to the system CUPS daemon.

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
