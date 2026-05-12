from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


IMAGE_NAME = "stem-tool-sandbox:latest"


@dataclass
class SandboxResult:
    """Return value from a sandboxed Python tool execution.

    Attributes
    ----------
    ok     : True when the container exited 0 and stdout was valid JSON.
    output : Parsed JSON output on success; error dict on failure.
    stderr : First 4 KB of container stderr (useful for debugging).
    """

    ok: bool
    output: Any
    stderr: str = ""


class DockerPythonSandbox:
    """Executes agent-generated Python tools inside an isolated Docker container.

    Each tool is written to a per-tool directory under ``tools_dir`` as
    ``tool.py`` (the code), ``params.json`` (runtime args), and
    ``dependencies.json`` (optional pip packages).  The container receives:

    - ``/repo``      — the repository root, mounted read-only
    - ``/artifacts`` — a per-run writable output directory
    - ``/tool``      — the tool directory, mounted read-only

    ``run_tool.py`` inside the image installs dependencies then calls the
    ``run(params)`` function defined in ``tool.py`` and prints the result as
    JSON to stdout.  A non-zero exit code or invalid JSON stdout is treated as
    failure.
    """

    def __init__(self, repo: Path, run_dir: Path, timeout_seconds: int = 60):
        self.repo = repo.resolve()
        self.run_dir = run_dir.resolve()
        self.timeout_seconds = timeout_seconds
        self.tools_dir = self.run_dir / "generated_python_tools"
        self.runs_dir = self.run_dir / "python_tool_runs"
        self.tools_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def ensure_image(self) -> None:
        """Build the sandbox Docker image if not already present.

        Looks for the Dockerfile in ``<repo_root>/sandbox/``.
        Raises ``RuntimeError`` when Docker is unavailable or the build fails.
        """
        root = Path(__file__).resolve().parents[3]
        dockerfile_dir = root / "sandbox"
        try:
            subprocess.run(
                ["docker", "build", "-t", IMAGE_NAME, str(dockerfile_dir)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("Docker CLI is not installed or not on PATH.") from exc
        except subprocess.CalledProcessError as exc:
            details = (exc.stderr or exc.stdout or "").strip()
            raise RuntimeError(f"Docker sandbox image build failed: {details}") from exc

    def save_tool(self, name: str, spec: dict[str, Any]) -> Path:
        """Persist a tool spec to disk so the container can mount it.

        Creates ``<tools_dir>/<safe_name>/`` with ``tool.py``,
        ``dependencies.json``, and ``spec.json``.  Returns the tool directory.
        """
        safe_name = _safe_name(name)
        tool_dir = self.tools_dir / safe_name
        tool_dir.mkdir(parents=True, exist_ok=True)
        (tool_dir / "tool.py").write_text(str(spec.get("code", "")), encoding="utf-8")
        (tool_dir / "dependencies.json").write_text(json.dumps(spec.get("dependencies", []), indent=2), encoding="utf-8")
        (tool_dir / "spec.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
        return tool_dir

    def run_tool(self, name: str, spec: dict[str, Any], params: dict[str, Any]) -> SandboxResult:
        """Run a named Python tool in the Docker sandbox.

        Builds the image on first use (cached by Docker layer cache), writes
        the tool to disk, then executes the container.  Returns a
        ``SandboxResult`` — callers should check ``.ok`` before using ``.output``.
        """
        try:
            self.ensure_image()
        except RuntimeError as exc:
            return SandboxResult(False, {"error": "docker_unavailable", "details": str(exc)})
        tool_dir = self.save_tool(name, spec)
        run_dir = self.runs_dir / _safe_name(name)
        run_dir.mkdir(parents=True, exist_ok=True)
        # Inject standard paths the tool code can rely on
        params = {**params, "repo_root": "/repo", "artifacts_dir": "/artifacts"}
        (tool_dir / "params.json").write_text(json.dumps(params, indent=2), encoding="utf-8")
        cmd = [
            "docker", "run", "--rm",
            "--cpus", "1",
            "--memory", "1g",
            "--pids-limit", "256",
            "--cap-drop", "ALL",
            "-v", f"{self.repo}:/repo:ro",
            "-v", f"{run_dir}:/artifacts:rw",
            "-v", f"{tool_dir}:/tool:ro",
            IMAGE_NAME,
            "/tool/tool.py",
            "/tool/params.json",
            "/tool/dependencies.json",
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            return SandboxResult(False, {"error": "timeout"}, (exc.stderr or "")[:4000])
        if proc.returncode != 0:
            return SandboxResult(False, {"error": "sandbox_failed", "returncode": proc.returncode}, proc.stderr[:4000])
        try:
            return SandboxResult(True, json.loads(proc.stdout), proc.stderr[:4000])
        except json.JSONDecodeError:
            return SandboxResult(False, {"error": "invalid_json_stdout", "stdout": proc.stdout[:4000]}, proc.stderr[:4000])


def _safe_name(name: str) -> str:
    """Sanitise a tool name for use as a filesystem directory name."""
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in name)[:80] or "tool"
