from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ArtifactStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def write_text(self, name: str, text: str) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def write_json(self, name: str, data: Any) -> Path:
        return self.write_text(name, json.dumps(data, indent=2))

    def read_text(self, name: str) -> str:
        return (self.root / name).read_text(encoding="utf-8")

    def read_json(self, name: str) -> Any:
        return json.loads(self.read_text(name))
