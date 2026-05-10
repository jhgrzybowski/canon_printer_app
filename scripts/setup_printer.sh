#!/usr/bin/env bash
set -euo pipefail

QUEUE_NAME="${QUEUE_NAME:-Canon_MG5350}"
PRINTER_IP="${PRINTER_IP:-192.168.100.100}"
DEVICE_URI="${DEVICE_URI:-ipp://${PRINTER_IP}/ipp/print}"
MODEL="${MODEL:-everywhere}"

require_command() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    echo "Required command not found: $name" >&2
    exit 1
  fi
}

queue_exists() {
  lpstat -p "$QUEUE_NAME" >/dev/null 2>&1
}

current_device_uri() {
  lpstat -v "$QUEUE_NAME" 2>/dev/null | sed -n "s/^device for ${QUEUE_NAME}: //p"
}

confirm() {
  local prompt="$1"
  local answer
  read -r -p "${prompt} [y/N] " answer
  case "$answer" in
    y|Y|yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

print_status() {
  echo
  echo "CUPS status:"
  lpstat -p "$QUEUE_NAME" || true
  lpstat -v "$QUEUE_NAME" || true
  lpoptions -p "$QUEUE_NAME" -l || true
}

require_command lpadmin
require_command lpstat
require_command lpoptions
require_command cupsaccept
require_command cupsenable

echo "Queue name: $QUEUE_NAME"
echo "Printer IP: $PRINTER_IP"
echo "Device URI: $DEVICE_URI"
echo "Model for new queue: $MODEL"

if queue_exists; then
  existing_uri="$(current_device_uri)"
  if [[ "$existing_uri" == "$DEVICE_URI" ]]; then
    echo "Queue already exists with expected device URI. No changes needed."
    print_status
    exit 0
  fi

  echo "Queue already exists with a different device URI."
  echo "Existing URI: ${existing_uri:-unknown}"
  echo "Expected URI: $DEVICE_URI"
  if ! confirm "Update this queue to use the expected URI?"; then
    echo "No changes made."
    print_status
    exit 0
  fi

  lpadmin -p "$QUEUE_NAME" -E -v "$DEVICE_URI"
else
  lpadmin -p "$QUEUE_NAME" -E -v "$DEVICE_URI" -m "$MODEL"
fi

cupsaccept "$QUEUE_NAME"
cupsenable "$QUEUE_NAME"

echo "Queue configured."
print_status
