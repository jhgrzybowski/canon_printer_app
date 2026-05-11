from __future__ import annotations

import re


PPD_OPEN_UI_RE = re.compile(r"^\*(?:JCL)?OpenUI\s+\*(?P<option>[^/:\s]+)")
PPD_CLOSE_UI_RE = re.compile(r"^\*(?:JCL)?CloseUI:\s+\*(?P<option>[^/:\s]+)")
PPD_CHOICE_RE = re.compile(r"^\*(?P<option>[A-Za-z0-9_.-]+)\s+(?P<choice>[^/:\s]+)")


def parse_lpoptions(output: str) -> dict[str, set[str]]:
    capabilities: dict[str, set[str]] = {}
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        option_part, choices_part = line.split(":", 1)
        option_name = option_part.split("/", 1)[0].strip()
        if not option_name:
            continue
        choices = {
            choice.lstrip("*").strip()
            for choice in choices_part.split()
            if choice.lstrip("*").strip()
        }
        capabilities[option_name] = choices
    return capabilities


def parse_ppd_options(output: str) -> dict[str, set[str]]:
    capabilities: dict[str, set[str]] = {}
    open_options: set[str] = set()

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        open_match = PPD_OPEN_UI_RE.match(line)
        if open_match:
            option_name = open_match.group("option")
            open_options.add(option_name)
            capabilities.setdefault(option_name, set())
            continue

        close_match = PPD_CLOSE_UI_RE.match(line)
        if close_match:
            open_options.discard(close_match.group("option"))
            continue

        choice_match = PPD_CHOICE_RE.match(line)
        if not choice_match:
            continue

        option_name = choice_match.group("option")
        if option_name not in open_options:
            continue

        choice = choice_match.group("choice").lstrip("*").strip()
        if choice:
            capabilities.setdefault(option_name, set()).add(choice)

    return {name: choices for name, choices in capabilities.items() if choices}
