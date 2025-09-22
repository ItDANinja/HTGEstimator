"""Input parsing helpers for HTG Estimator."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .models import ProjectInput


def load_project(path: str | Path) -> ProjectInput:
    """Load a project request from JSON or YAML."""

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        data: Any = yaml.safe_load(text)
    elif suffix == ".json":
        data = json.loads(text)
    else:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:  # pragma: no cover - fallback path
            raise ValueError(f"Unsupported file type: {suffix}") from exc
    if not isinstance(data, dict):
        raise ValueError("Estimate request must be a JSON/YAML object at the top level.")
    return ProjectInput.from_dict(data)


def load_project_from_string(data: str, *, fmt: str = "json") -> ProjectInput:
    """Convenience helper for tests or integrations."""

    fmt = fmt.lower()
    if fmt in {"yaml", "yml"}:
        payload: Any = yaml.safe_load(data)
    elif fmt == "json":
        payload = json.loads(data)
    else:  # pragma: no cover - defensive
        raise ValueError(f"Unsupported format: {fmt}")
    if not isinstance(payload, dict):
        raise ValueError("Estimate request must be a JSON/YAML object at the top level.")
    return ProjectInput.from_dict(payload)

