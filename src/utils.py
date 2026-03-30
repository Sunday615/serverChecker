from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

import yaml


ENV_LINE_RE = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def now_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def now_display() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def slugify(value: str) -> str:
    value = str(value).strip()
    value = re.sub(r"[^a-zA-Z0-9._-]+", "_", value)
    return value.strip("_")


def safe_string(value: object, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _parse_env_value(raw_value: str) -> str:
    value = raw_value.strip()
    if not value:
        return ""

    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        inner_value = value[1:-1]
        if value[0] == '"':
            return bytes(inner_value, "utf-8").decode("unicode_escape")
        return inner_value

    if " #" in value:
        return value.split(" #", 1)[0].rstrip()

    return value


def load_env_file(path: Path, override: bool = False) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        match = ENV_LINE_RE.match(line)
        if not match:
            continue

        key, raw_value = match.groups()
        if override or key not in os.environ:
            os.environ[key] = _parse_env_value(raw_value)
