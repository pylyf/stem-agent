import json
from pathlib import Path


def write_json(rows: list[dict[str, str]], output_path: str) -> None:
    Path(output_path).write_text(json.dumps(rows, indent=2), encoding="utf-8")
