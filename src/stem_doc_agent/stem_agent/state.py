from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class StemState:
    """Mutable accumulator for a single StemAgent run.

    The state is threaded through the LangGraph loop as a plain dict (via
    ``to_dict`` / ``from_dict``) so LangGraph can serialise it between nodes.
    Each ``update`` call advances the iteration counter and merges the LLM's
    patch into the running state.

    Fields
    ------
    iteration       : how many evolve→use_tools cycles have completed
    observations    : append-only log of LLM-reported discoveries
    skills          : named procedures the LLM has defined (name → prose)
    composite_tools : composite tool specs registered this run (name → spec)
    python_tools    : python tool specs registered this run (name → spec)
    tool_results    : flattened list of every tool output seen so far
    workflow        : ordered list of planned workflow steps (latest version wins)
    doc_plan        : planned output documents with skills/tools assigned
    rubric          : agent-generated scoring criteria with weights (name → weight)
    docs            : final rendered document bodies (path → markdown)
    rubric_result   : output of the self-eval Python tool run after execution
    stop_reason     : human-readable reason the agent set ready=True
    ready           : True once the LLM declares the plan sufficient to freeze
    """

    iteration: int = 0
    observations: list[str] = field(default_factory=list)
    skills: dict[str, str] = field(default_factory=dict)
    composite_tools: dict[str, Any] = field(default_factory=dict)
    python_tools: dict[str, Any] = field(default_factory=dict)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    workflow: list[str] = field(default_factory=list)
    doc_plan: dict[str, Any] = field(default_factory=dict)
    rubric: dict[str, Any] = field(default_factory=dict)
    docs: dict[str, str] = field(default_factory=dict)
    rubric_result: dict[str, Any] = field(default_factory=dict)
    stop_reason: str = ""
    ready: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict for LangGraph state passing."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StemState":
        """Deserialise from a LangGraph state dict, ignoring unknown keys."""
        state = cls()
        for key, value in data.items():
            if hasattr(state, key):
                setattr(state, key, value)
        return state

    def update(self, patch: dict[str, Any]) -> None:
        """Merge an LLM-generated patch into the state and advance the iteration.

        Lists (observations, tool_results) are appended; dicts (skills,
        composite_tools, python_tools, docs) are merged with update().
        workflow and doc_plan are replaced wholesale when present in the patch,
        because the LLM always emits a complete revised version.
        """
        self.iteration += 1
        self.observations.extend(patch.get("observations", []))
        self.skills.update(patch.get("skills", {}))
        self.composite_tools.update(patch.get("composite_tools", {}))
        self.python_tools.update(patch.get("python_tools", {}))
        self.tool_results.extend(patch.get("tool_results", []))
        # workflow, doc_plan, and rubric are always emitted in full by the LLM
        if patch.get("workflow"):
            self.workflow = patch["workflow"]
        if patch.get("doc_plan"):
            self.doc_plan = patch["doc_plan"]
        if patch.get("rubric"):
            self.rubric = patch["rubric"]
        self.docs.update(patch.get("docs", {}))
        self.stop_reason = patch.get("stop_reason", "")
        self.ready = bool(patch.get("ready", False))
