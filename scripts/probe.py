#!/usr/bin/env python3
"""Probe local CUPS state and Canon MG5350 network reachability."""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
from dataclasses import dataclass
from typing import Any


QUEUE_NAME = "Canon_MG5350"
PRINTER_IP = "192.168.100.100"
TCP_PORTS = (80, 515, 631, 9100)
COMMAND_TIMEOUT_SECONDS = 8
CONNECT_TIMEOUT_SECONDS = 3


@dataclass
class CommandResult:
    available: bool
    command: list[str]
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.available and self.returncode == 0

    def to_summary(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "command": self.command,
            "ok": self.ok,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "error": self.error,
        }


def run_command(command: list[str], timeout: int = COMMAND_TIMEOUT_SECONDS) -> CommandResult:
    if shutil.which(command[0]) is None:
        return CommandResult(available=False, command=command, error="command not found")

    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            available=True,
            command=command,
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
            error=f"timed out after {timeout}s",
        )
    except OSError as exc:
        return CommandResult(available=True, command=command, error=str(exc))

    return CommandResult(
        available=True,
        command=command,
        returncode=completed.returncode,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
    )


def print_command_result(label: str, result: CommandResult) -> None:
    print(f"\n== {label} ==")
    print(f"$ {' '.join(result.command)}")
    if not result.available:
        print(f"UNAVAILABLE: {result.error}")
        return
    if result.error:
        print(f"ERROR: {result.error}")
    print(f"exit: {result.returncode}")
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("stderr:")
        print(result.stderr)


def check_ping(host: str) -> dict[str, Any]:
    result = run_command(["ping", "-c", "1", "-W", "2", host], timeout=5)
    return result.to_summary() | {"reachable": result.ok}


def check_tcp(host: str, port: int) -> dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=CONNECT_TIMEOUT_SECONDS):
            return {"port": port, "open": True, "error": None}
    except OSError as exc:
        return {"port": port, "open": False, "error": str(exc)}


def check_pycups(queue_name: str) -> dict[str, Any]:
    try:
        import cups  # type: ignore[import-not-found]
    except ImportError as exc:
        return {"available": False, "connected": False, "queue_exists": False, "error": str(exc)}

    try:
        connection = cups.Connection()
        printers = connection.getPrinters()
    except RuntimeError as exc:
        return {"available": True, "connected": False, "queue_exists": False, "error": str(exc)}

    return {
        "available": True,
        "connected": True,
        "queue_exists": queue_name in printers,
        "printer_names": sorted(printers),
        "error": None,
    }


def main() -> int:
    print("Canon MG5350 printer diagnostics")
    print(f"Queue: {QUEUE_NAME}")
    print(f"Printer IP: {PRINTER_IP}")

    lpstat_r = run_command(["lpstat", "-r"])
    lpstat_queue = run_command(["lpstat", "-p", QUEUE_NAME])
    lpstat_all = run_command(["lpstat", "-t"])
    lpstat_uri = run_command(["lpstat", "-v", QUEUE_NAME])
    lpoptions = run_command(["lpoptions", "-p", QUEUE_NAME, "-l"])

    command_results = {
        "lpstat_running": lpstat_r,
        "lpstat_queue": lpstat_queue,
        "lpstat_all": lpstat_all,
        "lpstat_uri": lpstat_uri,
        "lpoptions": lpoptions,
    }

    print_command_result("CUPS running", lpstat_r)
    print_command_result("Queue exists", lpstat_queue)
    print_command_result("lpstat diagnostics", lpstat_all)
    print_command_result("Queue URI", lpstat_uri)
    print_command_result("Queue options", lpoptions)

    print("\n== pycups ==")
    pycups_summary = check_pycups(QUEUE_NAME)
    print(json.dumps(pycups_summary, indent=2, sort_keys=True))

    print("\n== Ping ==")
    ping_summary = check_ping(PRINTER_IP)
    print(json.dumps(ping_summary, indent=2, sort_keys=True))

    print("\n== TCP ports ==")
    tcp_summary = [check_tcp(PRINTER_IP, port) for port in TCP_PORTS]
    for port_result in tcp_summary:
        status = "open" if port_result["open"] else "closed/unreachable"
        print(f"{PRINTER_IP}:{port_result['port']} {status}")
        if port_result["error"]:
            print(f"  {port_result['error']}")

    summary = {
        "queue_name": QUEUE_NAME,
        "printer_ip": PRINTER_IP,
        "cups": {
            "lpstat_available": lpstat_r.available,
            "lpoptions_available": lpoptions.available,
            "running": lpstat_r.ok,
            "queue_exists": lpstat_queue.ok,
        },
        "commands": {name: result.to_summary() for name, result in command_results.items()},
        "pycups": pycups_summary,
        "network": {
            "ping": ping_summary,
            "tcp_ports": tcp_summary,
        },
    }

    print("\n== JSON summary ==")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
