from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


def main() -> None:
    tool_path = Path(sys.argv[1])
    params_path = Path(sys.argv[2])
    deps_path = Path(sys.argv[3]) if len(sys.argv) > 3 else None

    if deps_path and deps_path.exists():
        deps = json.loads(deps_path.read_text(encoding="utf-8"))
        if deps:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--no-cache-dir", *deps],
                check=True,
                stdout=sys.stderr,
                stderr=sys.stderr,
            )

    spec = importlib.util.spec_from_file_location("generated_tool", tool_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load tool: {tool_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "run"):
        raise RuntimeError("Generated tool must define run(params: dict) -> dict")
    params = json.loads(params_path.read_text(encoding="utf-8"))
    result = module.run(params)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
