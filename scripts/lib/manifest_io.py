from pathlib import Path

import re
import yaml


def load_manifest(path: Path) -> dict:
    data = yaml.safe_load(path.read_text()) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: manifest root must be a mapping")
    return data


def normalized_pkgdesc(value: str) -> str:
    if value.endswith(")"):
        return re.sub(r"\s+\([^)]+\)$", "", value)
    return value
