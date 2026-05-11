# Known Limitations and Future Steps

This document tracks intentional v1 limitations and possible future improvements.

---

## Current limitations

## 1. Backend only

The current project is backend-only.

Not included in v1:

- React frontend
- authentication
- user accounts
- persistent job history
- multi-user permissions
- admin UI
- cloud sync

The backend is intended to expose a clean REST API for a future LAN frontend.

---

## 2. No authentication

The service has no authentication in v1.

Implication:

- Anyone on the reachable network can potentially upload files, submit print jobs, inspect jobs, or cancel jobs.

Current recommendation:

```text
Bind only to LAN.
Do not expose to the internet.
```

Future options:

* simple LAN token,
* basic auth,
* reverse proxy auth,
* IP allowlist,
* local-only mode with frontend served on same host.

---

## 3. CUPS is the source of truth

The backend intentionally delegates real print state to CUPS.

Implication:

* The backend does not maintain a persistent job database.
* Completed historical jobs may disappear depending on CUPS configuration.
* Job status accuracy depends on CUPS and printer reporting.

Future option:

* SQLite job history for UX,
* reprint support,
* last-used settings,
* audit log.

---

## 4. Preview is approximate

PDF/image preview is generated before CUPS/Gutenprint final processing.

Preview may differ from physical print because of:

* driver margins,
* scaling,
* printable area,
* media type,
* color handling,
* duplex layout,
* Gutenprint-specific transformations.

Current wording:

```text
Preview is for user convenience and is not guaranteed to match final printer-driver output exactly.
```

Future options:

* expose printable area,
* warn when document page size differs from selected paper,
* generate preview with selected paper size overlay,
* add margin visualization,
* add better fit-to-page simulation.

---

## 5. Office documents are not included yet

Current upload scope:

* PDF
* PNG
* JPEG
* plain text

Not yet supported:

* DOCX
* ODT
* XLSX
* PPTX

Reason:

* Office conversion requires LibreOffice.
* LibreOffice can be slow on low-end servers.
* Conversion adds more failure modes.

Future option:

* add optional `libreoffice --headless --convert-to pdf`,
* wrap conversion in timeout,
* document dependency separately,
* keep disabled unless system package is installed.

---

## 6. Ink reporting may be incomplete

CUPS marker attributes may not expose complete ink levels for this printer/driver combination.

Potential attributes:

* `marker-names`
* `marker-levels`
* `marker-colors`
* `marker-types`

Limitations:

* older printer firmware may not expose everything,
* LPD transport may expose less status than richer protocols,
* Gutenprint/CUPS marker support may vary.

Future options:

* scrape Canon HTTP status page on port 80,
* parse ink/status information from printer web UI,
* expose best-effort cartridge state,
* clearly mark unknown values as unknown.

---

## 7. Printer is not handled as IPP Everywhere

The Canon PIXMA MG5350 is handled through:

```text
Gutenprint + LPD
```

Verified setup:

```text
lpd://192.168.100.100/PASSTHRU
gutenprint.5.3://bjc-PIXMA-MG5350/expert
```

Driverless IPP failed in this environment.

Implication:

* API option mapping must be based on actual CUPS/PPD options.
* Do not assume IPP Everywhere keys such as `print-color-mode` or `media` will work directly.
* Gutenprint-specific options such as `ColorModel`, `Resolution`, `Duplex`, `PageSize`, `MediaType`, `StpiShrinkOutput`, and `StpOrientation` may be relevant.

Future option:

* make queue capability detection more generic,
* support multiple printer profiles,
* support IPP Everywhere printers separately.

---

## 8. Option mapping is conservative

Current print API uses frontend-style options, then maps them to detected CUPS/Gutenprint capabilities.

Unsupported options are dropped and reported.

Known behavior:

* `collate` is ignored quietly when `copies=1`.
* `collate` may warn for multiple copies if no compatible CUPS option is detected.
* `media_type` maps only when safe detected values exist.
* `fit_to_page` maps only when a detected scaling option exists.
* orientation may use `StpOrientation` or standard `orientation-requested`.

Future improvements:

* stronger `/options` contract for frontend,
* option grouping by feature,
* exact mapping table from detected PPD,
* UI hints for unsupported features,
* per-queue mapping profiles.

---

## 9. Duplex needs real-world validation

The printer supports duplex, and the backend maps duplex through detected CUPS/Gutenprint options.

Still worth validating manually:

* `duplex: "none"`
* `duplex: "long-edge"`
* `duplex: "short-edge"`

Future test cases:

* portrait long-edge,
* landscape long-edge,
* portrait short-edge,
* landscape short-edge,
* multi-page PDF duplex behavior.

---

## 10. Landscape orientation needs validation

Portrait printing has been validated in the basic print path.

Landscape should be tested with:

* landscape PDF,
* portrait PDF printed as landscape,
* page-range filtered landscape PDF,
* image file landscape print.

Future improvement:

* add generated landscape smoke-test PDF,
* document physical result expectations.

---

## 11. Fit-to-page behavior may vary

`fit_to_page` is only safe when the queue exposes a compatible scaling/shrink option.

In Gutenprint, relevant options may include:

```text
StpiShrinkOutput
```

Limitations:

* not every document size maps predictably,
* image scaling and PDF scaling may differ,
* CUPS/Gutenprint may handle margins differently.

Future improvements:

* expose fit/scaling support clearly in `/options`,
* add generated non-A4 test PDF,
* compare output with and without fit-to-page.

---

## 12. No SNMP support

SNMP was not available in the observed printer probing.

Current status:

```text
SNMP is not used.
```

Future options:

* only add SNMP if port 161 is available and useful,
* use `pysnmp` optionally,
* keep it disabled by default.

---

## 13. No Wake-on-LAN

Wake-on-LAN is not implemented.

Reason:

* Canon MG5350 Wi-Fi wake behavior is not reliable/documented enough for this setup.
* Printer may be off, sleeping, or disconnected from Wi-Fi.

Current behavior:

* report offline/unreachable clearly,
* ask user to power on printer.

Future option:

* only revisit if a reliable wake method is found.

---

## 14. Temporary storage is local and simple

Uploads and previews are stored under `TMP_DIR`.

Current limitations:

* no long-term persistence,
* no user separation,
* no quota system beyond upload size limit,
* cleanup policy may be simple.

Future improvements:

* TTL cleanup background task,
* max total storage size,
* per-file expiry,
* manual cleanup endpoint for admin use,
* SQLite metadata if needed.

---

## 15. No multi-printer support yet

The backend is currently centered around one configured queue.

Future improvements:

* list all CUPS printers,
* support multiple queues,
* per-printer `/options`,
* per-printer status,
* default queue selection,
* printer profiles.

---

## Future roadmap

## Near-term

Recommended next steps:

1. Validate duplex:

   * long-edge
   * short-edge

2. Validate landscape:

   * generated landscape PDF
   * image print

3. Validate color:

   * color PDF
   * color image

4. Validate media type mapping:

   * plain
   * photo/glossy if available

5. Improve `/options` for frontend:

   * stable response shape,
   * clear unsupported indicators,
   * raw debug mode remains optional.

6. Add cleanup policy:

   * delete old uploads/previews after TTL.

---

## Medium-term

Potential improvements:

* React frontend.
* Drag-and-drop upload.
* Preview pane.
* Print options sidebar.
* Status banner.
* Job list with cancel button.
* LAN-only token authentication.
* Better error UX.
* Persistent local settings.

---

## Longer-term

Possible future directions:

* SQLite job history.
* Reprint previous job.
* Save favorite print presets.
* WebSocket or Server-Sent Events for live job/status updates.
* Canon HTTP status scraping for ink/errors.
* Multi-printer support.
* Optional Office document conversion.
* Nginx reverse proxy or systemd service deployment.
* Better frontend accessibility.
