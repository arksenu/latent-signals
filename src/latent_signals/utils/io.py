"""I/O helpers for JSONL and numpy files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

import numpy as np
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def ensure_dir(path: Path) -> Path:
    """Create directory (and parents) if it doesn't exist, return the path."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_jsonl(path: Path, items: list[BaseModel]) -> int:
    """Write a list of Pydantic models to a JSONL file. Returns count written."""
    ensure_dir(path.parent)
    with open(path, "w") as f:
        for item in items:
            f.write(item.model_dump_json() + "\n")
    return len(items)


def read_jsonl(path: Path, model_class: type[T]) -> list[T]:
    """Read a JSONL file into a list of Pydantic models."""
    items = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(model_class.model_validate_json(line))
    return items


def write_json(path: Path, data: dict | list) -> None:
    """Write a dict or list to a JSON file."""
    ensure_dir(path.parent)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def read_json(path: Path) -> dict | list:
    """Read a JSON file."""
    with open(path) as f:
        return json.load(f)


def write_numpy(path: Path, array: np.ndarray) -> None:
    """Save a numpy array to disk."""
    ensure_dir(path.parent)
    np.save(path, array)


def read_numpy(path: Path) -> np.ndarray:
    """Load a numpy array from disk."""
    return np.load(path)
