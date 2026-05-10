#!/usr/bin/env bash
set -u

QUEUE_NAME="${QUEUE_NAME:-Canon_MG5350}"
PRINTER_IP="${PRINTER_IP:-192.168.100.100}"
RUN_TEST=0

PREFERRED_MODEL="gutenprint.5.3://bjc-PIXMA-MG5350/expert"
FALLBACK_MODEL_1="gutenprint.5.3://bjc-PIXMA-MG5300/expert"
FALLBACK_MODEL_2="gutenprint.5.3://bjc-MG5300-series/expert"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --test-print)
      RUN_TEST=1
      ;;
    -h|--help)
      echo "Usage: $0 [--test-print]"
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
  shift
done

critical=0

section() {
  echo
  echo "== $1 =="
}

run() {
  echo "\$ $*"
  "$@"
  local status=$?
  echo "exit: $status"
  return "$status"
}

check_command() {
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    echo "$name: $(command -v "$name")"
  else
    echo "$name: missing"
  fi
}

check_tcp() {
  local port="$1"
  if timeout 3 bash -c ":</dev/tcp/${PRINTER_IP}/${port}" >/dev/null 2>&1; then
    echo "tcp/${port}: open"
  else
    echo "tcp/${port}: closed/unreachable"
  fi
}

section "User"
run id || true

section "CUPS Service"
if command -v systemctl >/dev/null 2>&1; then
  run systemctl is-active cups || true
else
  run lpstat -r || critical=1
fi
run lpstat -r || critical=1

section "Required Commands"
for command_name in lpadmin lpstat lpoptions lpinfo lp; do
  check_command "$command_name"
done

section "Gutenprint Model Discovery"
if command -v lpinfo >/dev/null 2>&1; then
  models="$(lpinfo -m 2>/dev/null || true)"
  for model in "$PREFERRED_MODEL" "$FALLBACK_MODEL_1" "$FALLBACK_MODEL_2"; do
    if grep -Fq "$model" <<<"$models"; then
      echo "found: $model"
    else
      echo "missing: $model"
    fi
  done
else
  echo "lpinfo missing; cannot inspect models"
fi

section "Printer Network"
run ping -c 1 -W 2 "$PRINTER_IP" || true
for port in 80 515 631 9100; do
  check_tcp "$port"
done

section "Queue Status"
run lpstat -p "$QUEUE_NAME" -l || critical=1
run lpstat -v "$QUEUE_NAME" || critical=1
run lpstat -W all -o "$QUEUE_NAME" || true

section "First 80 Queue Options"
lpoptions -p "$QUEUE_NAME" -l 2>&1 | head -80
echo "exit: ${PIPESTATUS[0]}"

section "Recent CUPS Logs"
if command -v journalctl >/dev/null 2>&1; then
  run journalctl -u cups --no-pager -n 80 || true
else
  echo "journalctl missing"
fi

if [[ "$RUN_TEST" == "1" ]]; then
  section "Test Print"
  test_file="/tmp/canon-lpd-debug-test.txt"
  cat > "$test_file" <<EOF
Canon MG5350 CUPS/Gutenprint test
Queue: $QUEUE_NAME
Transport: LPD PASSTHRU
EOF
  run lp -d "$QUEUE_NAME" "$test_file" || critical=1
fi

exit "$critical"
