## Project
Python 3 FastAPI backend for Canon PIXMA MG5350 printer manager on LAN.

## Constraints
- Target host: Ubuntu 26.04 server, low-end machine: i3 6th gen, 8 GB RAM, HDD.
- Prefer simple, synchronous, debuggable code.
- Avoid heavy background services unless necessary.
- No database in v1.
- No authentication in v1, but bind only to LAN and document security limits.
- Do not expose the service to the internet.
- Do not install random dependencies without explaining why.

## Architecture
- FastAPI REST API.
- CUPS is the source of truth for printer queues/jobs.
- pycups wrapper in app/services/cups_client.py.
- Printer queue name: Canon_MG5350.
- Printer IP: 192.168.100.100.
- Backend host: 192.168.100.99.
- Temporary files under /var/tmp/printer-backend or configurable TMP_DIR.

## Implementation priorities
1. Probe script and CUPS queue setup.
2. Health/status endpoints.
3. Upload PDF/image/text.
4. PDF preview.
5. Basic print submission.
6. Page-range filtering for PDFs.
7. Job list/cancel.
8. Options mapping from lpoptions/PPD.
9. Optional Office conversion later.

## Important trade-offs
- Preview is an approximation, not a guaranteed exact rendering of the final CUPS output.
- Ink reporting may not work reliably via CUPS; treat HTTP scraping as second-pass.
- LibreOffice conversion is optional and must be isolated behind a timeout.
- Do not implement Wake-on-LAN for MG5350.
- Do not use SNMP unless port 161 is actually available.

## Testing
- Unit tests for page ranges, option mapping, translator.
- Mock CUPS for API tests.
- Integration tests requiring real printer should be explicitly marked.
