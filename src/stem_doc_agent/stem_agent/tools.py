from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from stem_doc_agent.llm import complete
from stem_doc_agent.scanner import RepoProfile
from stem_doc_agent.stem_agent.python_sandbox import DockerPythonSandbox


logger = logging.getLogger(__name__)

PLACEHOLDER_RE = re.compile(r"^\{([A-Za-z_][A-Za-z0-9_]*)\}$")


@dataclass
class ToolResult:
    """Uniform return type for every tool call.

    ``name`` is the tool that produced the result; ``output`` is the raw
    return value (dict, list, or string depending on the tool).
    """

    name: str
    output: Any


class ToolRegistry:
    """Runtime registry that holds primitive tools and all agent-created tools.

    Primitive tools (repo_profile, list_files, read_file, search_text,
    registered_tools) are built-in and always available.  The agent grows the
    registry by calling ``register_composite`` and ``register_python_tool``
    during the evolution phase.

    The ``manifest()`` method returns a full schema of all currently available
    tools — including argument names — so the LLM knows exactly what to call.
    """

    # Argument schemas for the built-in primitive tools, shown in the manifest
    # so the LLM does not have to guess parameter names.
    _PRIMITIVE_SCHEMAS: dict[str, dict[str, Any]] = {
        "repo_profile": {"args": {}},
        "list_files": {"args": {}},
        "read_file": {"args": {"path": "string — repo-relative file path"}},
        "search_text": {"args": {"query": "string — substring to search across all files"}},
        "registered_tools": {"args": {}},
    }

    def __init__(self, repo: Path, profile: RepoProfile, model: str, run_dir: Path | None = None):
        self.repo = repo.resolve()
        self.profile = profile
        self.model = model
        self.sandbox = DockerPythonSandbox(self.repo, run_dir or (Path.cwd() / "artifacts" / "sandbox"))
        self._tools: dict[str, Callable[[dict[str, Any]], ToolResult]] = {
            "repo_profile": lambda args: ToolResult("repo_profile", self.profile.to_dict()),
            "list_files": self._list_files,
            "read_file": self._read_file,
            "search_text": self._search_text,
            "registered_tools": lambda args: ToolResult("registered_tools", self.manifest()),
        }
        self.composite_specs: dict[str, dict[str, Any]] = {}
        self.python_tool_specs: dict[str, dict[str, Any]] = {}

    def manifest(self) -> list[dict[str, Any]]:
        """Return a schema list of all currently registered tools.

        Each entry includes the tool name, kind (primitive/composite/python),
        and an ``args`` dict mapping argument names to short descriptions.
        Composite tools expose the placeholder names extracted from their step
        definitions; python tools show a generic ``params`` dict entry.
        """
        primitive = set(self._PRIMITIVE_SCHEMAS)
        result = []
        for name in sorted(self._tools):
            if name in primitive:
                entry: dict[str, Any] = {"name": name, "kind": "primitive", **self._PRIMITIVE_SCHEMAS[name]}
            elif name in self.python_tool_specs:
                spec = self.python_tool_specs[name]
                entry = {
                    "name": name,
                    "kind": "python",
                    "args": {"params": "dict — passed as params to run(params)"},
                    "purpose": spec.get("purpose", ""),
                }
            else:
                spec = self.composite_specs[name]
                entry = {
                    "name": name,
                    "kind": "composite",
                    # Dynamically derived from {placeholder} patterns in step args
                    "args": {p: "string" for p in required_args(spec)},
                    "description": spec.get("description", ""),
                }
            result.append(entry)
        return result

    def register_composite(self, name: str, spec: dict[str, Any]) -> ToolResult:
        """Register a new composite tool defined by the agent.

        A composite tool is a sequence of existing tool calls optionally
        followed by an LLM synthesis step.  Registration fails if the name
        is already taken, if steps is empty, or if any step references an
        unknown tool.
        """
        if not name or name in self._tools:
            return ToolResult("register_composite", {"error": f"Invalid or duplicate tool name: {name}"})
        steps = spec.get("steps", [])
        if not isinstance(steps, list) or not steps:
            return ToolResult("register_composite", {"error": f"Composite tool {name} has no steps."})
        unknown = [step.get("tool") for step in steps if step.get("tool") not in self._tools]
        if unknown:
            return ToolResult("register_composite", {"error": f"Unknown tools in {name}: {unknown}"})
        self.composite_specs[name] = spec
        self._tools[name] = lambda args, tool_name=name: self._run_composite(tool_name, args)
        logger.info("Registered composite tool: %s (%d steps)", name, len(steps))
        return ToolResult("register_composite", {"registered": name, "spec": spec})

    def register_python_tool(self, name: str, spec: dict[str, Any]) -> ToolResult:
        """Register a new Docker-sandboxed Python tool defined by the agent.

        The spec must contain a ``code`` field with a ``def run(params)``
        function.  The tool is persisted to disk but not executed at
        registration time — it runs when the agent calls it by name.
        """
        if not name or name in self._tools:
            return ToolResult("register_python_tool", {"error": f"Invalid or duplicate tool name: {name}"})
        if "code" not in spec or "def run(" not in str(spec["code"]):
            return ToolResult("register_python_tool", {"error": "Python tool must include code with def run(params)."})
        self.python_tool_specs[name] = spec
        self._tools[name] = lambda args, tool_name=name: self._run_python_tool(tool_name, args)
        logger.info(
            "Registered python tool: %s — %s",
            name,
            spec.get("purpose", "(no purpose given)"),
        )
        return ToolResult("register_python_tool", {
            "registered": name,
            "purpose": spec.get("purpose", ""),
            "dependencies": spec.get("dependencies", []),
        })

    def run(self, name: str, args: dict[str, Any] | None = None) -> ToolResult:
        """Dispatch a tool call by name, returning a ToolResult.

        Unknown tool names and runtime exceptions are caught and returned as
        error ToolResults so the agent can observe failures in tool_results.
        """
        try:
            if name not in self._tools:
                raise ValueError(f"Unknown tool: {name}")
            logger.debug("Running tool: %s  args=%s", name, args)
            return self._tools[name](args or {})
        except Exception as exc:
            logger.warning("Tool %s failed: %s", name, exc)
            return ToolResult(name, {"error": str(exc), "args": args or {}})

    # ------------------------------------------------------------------
    # Primitive tool implementations
    # ------------------------------------------------------------------

    def _list_files(self, args: dict[str, Any]) -> ToolResult:
        """Return a sorted list of all files known to the repo profile."""
        return ToolResult("list_files", sorted(self.profile.file_summaries))

    def _read_file(self, args: dict[str, Any]) -> ToolResult:
        """Read one or more repo-relative files, capped at 12 000 characters each.

        Accepts either a single path string or a list of paths.  When a list is
        given each file is read separately and the results are returned as a
        dict mapping path → content so callers can distinguish the sources.
        """
        path_arg = args["path"]
        if isinstance(path_arg, list):
            results = {}
            for p in path_arg:
                results[str(p)] = self._read_single_file(str(p))
            return ToolResult("read_file", results)
        return ToolResult("read_file", self._read_single_file(str(path_arg)))

    def _read_single_file(self, rel: str) -> str:
        """Read one repo-relative file and return its text, capped at 12 000 chars."""
        path = (self.repo / rel).resolve()
        if path != self.repo and self.repo not in path.parents:
            raise ValueError(f"Refusing to read outside repository: {rel}")
        if not path.is_file():
            raise FileNotFoundError(f"File does not exist in repository: {rel}")
        return path.read_text(encoding="utf-8", errors="ignore")[:12000]

    def _search_text(self, args: dict[str, Any]) -> ToolResult:
        """Full-text search across all tracked repo files, returning up to 80 matches."""
        query = str(args["query"]).lower()
        matches: list[dict[str, str]] = []
        for rel in self.profile.file_summaries:
            text = (self.repo / rel).read_text(encoding="utf-8", errors="ignore")
            if query in text.lower():
                matches.append({"path": rel, "summary": self.profile.file_summaries.get(rel, "")})
        return ToolResult("search_text", matches[:80])

    # ------------------------------------------------------------------
    # Agent-created tool runners
    # ------------------------------------------------------------------

    def _run_composite(self, name: str, args: dict[str, Any]) -> ToolResult:
        """Execute a composite tool: run each step in order, then synthesise.

        Placeholder values like ``{file_path}`` in step args are resolved
        against the call-time ``args`` dict.  If the spec defines a
        ``synthesis`` instruction the step outputs are fed back to the LLM;
        otherwise the raw list of step outputs is returned.
        """
        spec = self.composite_specs[name]
        step_outputs = []
        for step in spec["steps"]:
            step_args = _resolve_args(dict(step.get("args", {})), args)
            step_args.update(args.get(step.get("arg_key", ""), {}) if step.get("arg_key") else {})
            step_outputs.append(self.run(step["tool"], step_args).__dict__)
        synthesis = spec.get("synthesis", "")
        if not synthesis:
            return ToolResult(name, step_outputs)
        prompt = f"""
Synthesize the output of an agent-created composite repository tool.

Tool name: {name}
Tool purpose: {spec.get("description", "")}
Synthesis instruction: {synthesis}
Step outputs:
{json.dumps(step_outputs, indent=2)}

Return concise JSON or Markdown, whichever fits the synthesis instruction.
"""
        return ToolResult(name, complete(prompt, model=self.model).strip())

    def _run_python_tool(self, name: str, args: dict[str, Any]) -> ToolResult:
        """Execute a Python tool in the Docker sandbox and return its output."""
        logger.info("Executing python tool in sandbox: %s", name)
        result = self.sandbox.run_tool(name, self.python_tool_specs[name], args)
        if not result.ok:
            logger.warning("Python tool %s failed: %s", name, result.output)
        output = result.output if result.ok else {"error": result.output, "stderr": result.stderr}
        return ToolResult(name, output)


def compact_results(results: list[ToolResult]) -> list[dict[str, Any]]:
    """Convert a list of ToolResults to plain dicts for JSON serialisation."""
    return [result.__dict__ for result in results]


def required_args(spec: dict[str, Any]) -> set[str]:
    """Return the set of placeholder names (e.g. ``file_path``) in a composite tool spec.

    Placeholders are step arg values that match ``{identifier}`` exactly.
    These must be supplied as call-time args when the tool is invoked.
    """
    found: set[str] = set()
    for step in spec.get("steps", []):
        found |= _find_placeholders(step.get("args", {}))
    return found


def _resolve_args(value: Any, runtime_args: dict[str, Any]) -> Any:
    """Recursively replace ``{placeholder}`` strings with values from runtime_args."""
    if isinstance(value, dict):
        return {key: _resolve_args(item, runtime_args) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_args(item, runtime_args) for item in value]
    if isinstance(value, str):
        match = PLACEHOLDER_RE.match(value)
        if match:
            key = match.group(1)
            if key not in runtime_args:
                raise ValueError(f"Missing composite tool argument: {key}")
            return runtime_args[key]
    return value


def _find_placeholders(value: Any) -> set[str]:
    """Recursively collect placeholder names from a step args structure."""
    if isinstance(value, dict):
        return set().union(*(_find_placeholders(item) for item in value.values())) if value else set()
    if isinstance(value, list):
        return set().union(*(_find_placeholders(item) for item in value)) if value else set()
    if isinstance(value, str):
        match = PLACEHOLDER_RE.match(value)
        return {match.group(1)} if match else set()
    return set()
