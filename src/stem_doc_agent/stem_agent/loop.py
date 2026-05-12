from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from evaluation.evaluator import score_docs
from stem_doc_agent.kernel.artifacts import ArtifactStore
from stem_doc_agent.kernel.json_io import parse_json_object
from stem_doc_agent.llm import complete
from stem_doc_agent.scanner import RepoProfile
from stem_doc_agent.stem_agent.state import StemState
from stem_doc_agent.stem_agent.tools import ToolRegistry, compact_results, required_args


logger = logging.getLogger(__name__)


class GraphState(TypedDict):
    """LangGraph node state passed between ``evolve`` and ``use_tools`` nodes.

    ``stem``       : serialised StemState dict
    ``tool_calls`` : tool calls requested by the current evolve step
    ``raw_patch``  : full JSON patch returned by the LLM (used to register tools)
    """

    stem: dict[str, Any]
    tool_calls: list[dict[str, Any]]
    raw_patch: dict[str, Any]


class StemAgent:
    """Self-specialising documentation agent built on a LangGraph evolve→use_tools loop.

    The agent starts with no repository-specific knowledge and iteratively
    builds skills, composite tools, Python (Docker-sandboxed) tools, and a
    documentation plan by observing the repository through primitive tools.
    Once it judges the plan sufficient it freezes its state and executes
    each planned document in a separate LLM call.

    Evolution phase  (``_evolve`` → ``_use_tools`` → ``_route``)
    ---------------------------------------------------------------
    1. ``_evolve``:    Calls the LLM with the current state.  The LLM returns a
                       JSON patch containing observations, new tools/skills, tool
                       call requests, an updated workflow, an updated doc plan,
                       and optionally ``ready=true``.
    2. ``_use_tools``: Registers any new composite/Python tools from the patch,
                       then executes all requested tool calls.  Results are
                       appended to ``state.tool_results``.
    3. ``_route``:     Decides whether to continue evolving or to freeze.  The
                       agent must set ``ready=true`` *and* satisfy structural
                       checks (skills, created tools, doc plan documents, all
                       composite placeholder args satisfied).

    Execution phase  (``_execute_documents``)
    ------------------------------------------
    After freezing, each planned document is written by a separate LLM call
    that receives the document spec, selected skills, and tool outputs gathered
    for that document.
    """

    def __init__(
        self,
        repo: Path,
        profile: RepoProfile,
        store: ArtifactStore,
        model: str,
        recursion_limit: int = 50,
    ):
        self.repo = repo
        self.profile = profile
        self.store = store
        self.model = model
        self.recursion_limit = recursion_limit
        self.tools = ToolRegistry(repo, profile, model, store.root)

    def run(self) -> StemState:
        """Run the full evolution + execution pipeline and return the final state."""
        logger.info("Starting StemAgent on %s", self.repo.name)
        graph = self._build_graph()
        result = graph.invoke(
            {"stem": StemState().to_dict(), "tool_calls": [], "raw_patch": {}},
            config={"recursion_limit": self.recursion_limit},
        )
        state = StemState.from_dict(result["stem"])
        self._freeze(state)
        self._execute_documents(state)
        self._evaluate_docs(state)
        return state

    def _build_graph(self):
        """Construct the two-node LangGraph: evolve → use_tools → (route back or END)."""
        graph = StateGraph(GraphState)
        graph.add_node("evolve", self._evolve)
        graph.add_node("use_tools", self._use_tools)
        graph.set_entry_point("evolve")
        graph.add_edge("evolve", "use_tools")
        graph.add_conditional_edges("use_tools", self._route, {"continue": "evolve", "freeze": END})
        return graph.compile()

    def _evolve(self, graph_state: GraphState) -> GraphState:
        """LangGraph node: ask the LLM for the next evolution step.

        Sends the full current state plus the tool manifest to the LLM and
        receives a JSON patch.  The patch is merged into StemState and
        persisted under ``iterations/<N>/evolve_patch.json``.
        """
        stem = graph_state["stem"]
        current_iter = stem.get("iteration", 0) + 1
        logger.info("── Iteration %d ──────────────────────────────", current_iter)
        prompt = f"""
You are a stem agent for documentation maintenance.

You start with no repository-specific skills, no repository-specific tools, and no documentation plan. You may create skills and composite tools only from evidence you gather.

Available primitive/runtime tools:
{json.dumps(self.tools.manifest(), indent=2)}

Current specialization state:
{json.dumps(stem, indent=2)}

Design your next evolution step. You may:
- request primitive or already registered tool calls
- define new composite tools as sequences of existing tools
- define new Python tools that run in a Docker sandbox with /repo read-only, /artifacts writable, and internet enabled
- define or refine skills
- define or refine a documentation plan
- decide to freeze only when the plan, skills, and tools are sufficient to execute documentation work

Do not use a predetermined number of iterations. Do not write final documentation during evolution. If you create composite tools, assign them to the documents where they should be used. If a composite tool step uses placeholders such as "{{file_path}}", every call to that tool must provide matching args such as {{"file_path": "src/example.py"}}.

Return only JSON with this shape:
{{
  "observations": ["new conclusions"],
  "tool_calls": [{{"name": "tool name", "args": {{}}}}],
  "composite_tools": {{
    "tool_name_you_choose": {{
      "description": "purpose",
      "steps": [{{"tool": "existing tool name", "args": {{}}}}],
      "synthesis": "how to synthesize step outputs"
    }}
  }},
  "python_tools": {{
    "tool_name_you_choose": {{
      "purpose": "why this tool is needed",
      "dependencies": ["optional pip packages"],
      "code": "Python code defining run(params: dict) -> dict. The tool sees repo_root=/repo and artifacts_dir=/artifacts in params."
    }}
  }},
  "skills": {{"skill_name_you_choose": "skill procedure"}},
  "workflow": ["workflow steps you choose"],
  "doc_plan": {{
    "documents": [
      {{
        "path": "relative markdown path you choose",
        "purpose": "why this document exists",
        "skills": ["skill names to apply"],
        "tools": [{{"name": "tool name", "args": {{}}}}]
      }}
    ]
  }},
  "rubric": {{
    "criteria": {{"criterion_name": weight_0_to_100}},
    "threshold": 0.7
  }},
  "ready": false,
  "stop_reason": ""
}}

Rubric and self-evaluation guidance:
- You may define a rubric with criteria relevant to this specific repository (e.g. entrypoint_coverage, setup_accuracy, component_coverage, hallucination_avoidance).
- If you define a rubric, also create a Python tool named exactly "evaluate_docs". It receives params: {{docs: dict[str,str], profile: dict, rubric: dict}} and must return {{criteria: {{name: score_0_to_1}}, total: float, passes: bool}}.
- "evaluate_docs" should check repository-grounded facts: do file references exist, are entrypoints mentioned, are setup commands present.
- After execution the tool will be run automatically on your produced documentation. This gives you a measurable self-check.
- You do NOT need to run "evaluate_docs" yourself during evolution. It runs post-execution.
- IMPORTANT: When writing evaluate_docs, use only one level of iteration at a time. For example:
  all_text = ' '.join(docs.values()).lower()
  entrypoint_coverage = sum(1 for ep in entrypoints if ep in all_text) / max(len(entrypoints), 1)
  component_coverage  = sum(1 for c  in components if c  in all_text) / max(len(components),  1)
  Never nest any() inside all() or vice versa — this causes TypeError.

"""
        patch = parse_json_object(
            complete(prompt, model=self.model, system="Return strict JSON for a LangGraph stem-agent state update.")
        )
        next_state = StemState.from_dict(stem)
        next_state.update(_normalize_patch(patch))

        # Log what the LLM decided to do this iteration
        new_skills = list(patch.get("skills", {}).keys())
        new_composite = list(patch.get("composite_tools", {}).keys())
        new_python = list(patch.get("python_tools", {}).keys())
        calls = [c.get("name") for c in patch.get("tool_calls", [])]
        if new_skills:
            logger.info("  New skills: %s", ", ".join(new_skills))
        if new_composite:
            logger.info("  New composite tools: %s", ", ".join(new_composite))
        if new_python:
            logger.info("  New python tools: %s", ", ".join(new_python))
        if calls:
            logger.info("  Tool calls requested: %s", ", ".join(calls))
        if patch.get("ready"):
            logger.info("  Agent signals ready — %s", patch.get("stop_reason", ""))

        self.store.write_json(f"iterations/{next_state.iteration:02d}/evolve_patch.json", patch)
        return {"stem": next_state.to_dict(), "tool_calls": patch.get("tool_calls", []), "raw_patch": patch}

    def _use_tools(self, graph_state: GraphState) -> GraphState:
        """LangGraph node: register agent-created tools and execute tool calls.

        Processing order:
        1. Register composite tools from the patch (must precede tool calls that use them).
        2. Register Python tools from the patch.
        3. Execute all requested tool calls in order.

        All results are appended to ``state.tool_results`` and persisted under
        ``iterations/<N>/tool_results.json``.
        """
        stem = StemState.from_dict(graph_state["stem"])
        patch = graph_state["raw_patch"]
        results = []

        for name, spec in patch.get("composite_tools", {}).items():
            results.append(self.tools.register_composite(name, spec))

        for name, spec in patch.get("python_tools", {}).items():
            results.append(self.tools.register_python_tool(name, spec))

        for call in graph_state.get("tool_calls", []):
            tool_name = call.get("name", "")
            logger.info("  Running tool: %s", tool_name)
            results.append(self.tools.run(tool_name, call.get("args", {})))

        stem.tool_results.extend(compact_results(results))
        self.store.write_json(f"iterations/{stem.iteration:02d}/tool_results.json", compact_results(results))
        self.store.write_json(f"iterations/{stem.iteration:02d}/state.json", stem.to_dict())
        return {"stem": stem.to_dict(), "tool_calls": [], "raw_patch": {}}

    def _route(self, graph_state: GraphState) -> Literal["continue", "freeze"]:
        """Decide whether to continue evolving or freeze.

        Freezing requires ALL of the following:
        - The LLM set ``ready=true``.
        - The doc plan contains at least one document.
        - At least one skill has been defined.
        - At least one composite or Python tool has been created.
        - At least one created tool is referenced in the doc plan.
        - All composite tools used in the doc plan have their required
          placeholder args satisfied.

        Any unmet condition causes another evolution iteration.
        """
        stem = graph_state["stem"]
        documents = stem.get("doc_plan", {}).get("documents", [])
        used_tools = {
            call.get("name")
            for document in documents
            for call in document.get("tools", [])
            if isinstance(call, dict)
        }
        created_tools = set(self.tools.composite_specs) | set(self.tools.python_tool_specs)
        uses_created_tool = bool(created_tools & used_tools)
        has_required_args = self._doc_plan_satisfies_composite_args(documents)

        if stem.get("ready") and documents and stem.get("skills") and created_tools and uses_created_tool and has_required_args:
            logger.info("Freeze conditions met — entering execution phase")
            return "freeze"

        # Log which condition(s) are blocking the freeze
        missing = []
        if not stem.get("ready"):
            missing.append("ready=false")
        if not documents:
            missing.append("no documents in doc_plan")
        if not stem.get("skills"):
            missing.append("no skills")
        if not created_tools:
            missing.append("no created tools")
        if not uses_created_tool:
            missing.append("doc plan does not use any created tool")
        if not has_required_args:
            missing.append("composite tool args unsatisfied")
        logger.info("  Continuing evolution (%s)", "; ".join(missing) if missing else "not ready")
        return "continue"

    def _doc_plan_satisfies_composite_args(self, documents: list[dict[str, Any]]) -> bool:
        """Return True if every composite tool call in the doc plan supplies all required placeholder args."""
        for document in documents:
            for call in document.get("tools", []):
                name = call.get("name")
                if name not in self.tools.composite_specs:
                    continue
                missing = required_args(self.tools.composite_specs[name]) - set(call.get("args", {}))
                if missing:
                    return False
        return True

    def _freeze(self, state: StemState) -> None:
        """Persist the final agent state, skills, tools, and workflow to disk."""
        logger.info("Freezing agent state after %d iteration(s)", state.iteration)
        self.store.write_json("frozen_agent/stem_state.json", state.to_dict())
        self.store.write_json("frozen_agent/skills.json", state.skills)
        self.store.write_json("frozen_agent/composite_tools.json", self.tools.composite_specs)
        self.store.write_json("frozen_agent/python_tools.json", self.tools.python_tool_specs)
        self.store.write_json("frozen_agent/doc_plan.json", state.doc_plan)
        self.store.write_text(
            "frozen_agent/workflow.md",
            "\n".join(f"- {step}" for step in state.workflow) + "\n",
        )

    def _execute_documents(self, state: StemState) -> None:
        """Render every planned document and write results to disk.

        For each document in the doc plan:
        1. Re-execute the document's assigned tool calls to gather fresh context.
        2. Collect the document's assigned skills.
        3. Call ``_write_document`` to produce the final Markdown via LLM.
        4. Write the document to ``evolved_docs/<path>``.

        All documents are also bundled into a single ``evolved_docs.md`` file.
        """
        docs: dict[str, str] = {}
        for document in state.doc_plan.get("documents", []):
            path = str(document.get("path", "document.md")).strip("/") or "document.md"
            logger.info("Writing document: %s", path)
            context_results = [
                self.tools.run(call.get("name", ""), call.get("args", {})).__dict__
                for call in document.get("tools", [])
            ]
            selected_skills = {
                name: state.skills.get(name, "")
                for name in document.get("skills", [])
                if name in state.skills
            }
            if selected_skills:
                logger.info("  Applying skills: %s", ", ".join(selected_skills))
            docs[path] = self._write_document(document, selected_skills, context_results)
            self.store.write_text(f"evolved_docs/{path}", docs[path].strip() + "\n")

        bundle = "\n\n".join(f"# {path}\n\n{body.strip()}" for path, body in docs.items())
        state.docs = docs
        self.store.write_json("frozen_agent/stem_state.json", state.to_dict())
        self.store.write_text("evolved_docs.md", bundle.strip() + "\n")
        logger.info("Execution complete — wrote %d document(s)", len(docs))

    def _evaluate_docs(self, state: StemState) -> None:
        """Run rubric self-evaluation on the produced documents.

        Two paths:

        1. **Agent-created tool** — if the agent registered a Python tool named
           ``evaluate_docs``, call it with ``docs``, ``profile``, and ``rubric``.
           The tool is expected to return
           ``{"criteria": {name: 0–1}, "total": float, "passes": bool}``.

        2. **Deterministic fallback** — if no ``evaluate_docs`` tool exists but
           the agent did define a ``rubric``, run the built-in :func:`score_docs`
           evaluator against the agent's own rubric criteria.  This guarantees a
           rubric result even when the agent skipped creating the Python tool.

        If neither a rubric nor an eval tool exists the step is skipped.
        Results are persisted to ``eval/rubric_result.json``.
        """
        all_text = "\n\n".join(state.docs.values())
        profile_dict = self.profile.to_dict()

        if "evaluate_docs" in self.tools.python_tool_specs:
            logger.info("Running agent evaluate_docs tool...")
            result = self.tools.run("evaluate_docs", {
                "docs": state.docs,
                "profile": profile_dict,
                "rubric": state.rubric,
            })
            if isinstance(result.output, dict) and "error" not in result.output:
                self._save_rubric_result(state, result.output)
                return
            logger.warning("evaluate_docs tool failed: %s — falling back to deterministic eval", result.output)

        if state.rubric:
            logger.info("Running deterministic rubric self-evaluation (fallback)...")
            required = [k for k in state.rubric.get("criteria", {})]
            scored = score_docs(all_text, profile_dict, required)
            threshold = float(state.rubric.get("threshold", 0.7))
            rubric_result = {
                "source": "deterministic_fallback",
                "criteria": scored["metrics"],
                "total": round(scored["score"] / 100, 4),
                "passes": (scored["score"] / 100) >= threshold,
                "threshold": threshold,
            }
            self._save_rubric_result(state, rubric_result)
            return

        logger.info("No rubric defined — skipping self-evaluation")

    def _save_rubric_result(self, state: StemState, result: dict) -> None:
        """Persist a rubric result dict and log a summary line."""
        state.rubric_result = result
        self.store.write_json("eval/rubric_result.json", result)
        self.store.write_json("frozen_agent/stem_state.json", state.to_dict())
        total = result.get("total", 0)
        passes = result.get("passes", False)
        source = result.get("source", "agent_tool")
        logger.info(
            "Rubric result [%s]: total=%.2f  passes=%s",
            source, float(total) if isinstance(total, (int, float)) else 0, passes,
        )

    def _write_document(
        self,
        document: dict[str, Any],
        skills: dict[str, str],
        context_results: list[dict[str, Any]],
    ) -> str:
        """Ask the LLM to render a single planned document.

        The LLM receives the document spec, the prose skill procedures selected
        for this document, the tool outputs gathered for it, and the repo
        profile for grounding.  It must return only Markdown.
        """
        prompt = f"""
You are executing a frozen documentation specialist.

Write exactly one planned document using the skills and tool outputs selected for this document.

Planned document:
{json.dumps(document, indent=2)}

Applied skills:
{json.dumps(skills, indent=2)}

Tool outputs gathered for this document:
{json.dumps(context_results, indent=2)}

Repository profile for grounding:
{json.dumps(self.profile.to_dict(), indent=2)}

Rules:
- Use the applied skills as procedures, not as decorative text.
- Ground claims in repository evidence.
- Do not invent files, commands, APIs, components, or frameworks.
- Return only Markdown for this document.
"""
        return complete(
            prompt,
            model=self.model,
            system="Execute one document from a frozen agent-created documentation plan.",
        ).strip()


def _normalize_patch(patch: dict[str, Any]) -> dict[str, Any]:
    """Extract and type-check known fields from a raw LLM patch dict."""
    return {
        "observations": patch.get("observations", []),
        "skills": patch.get("skills", {}),
        "composite_tools": patch.get("composite_tools", {}),
        "python_tools": patch.get("python_tools", {}),
        "workflow": patch.get("workflow", []),
        "doc_plan": patch.get("doc_plan", {}),
        "rubric": patch.get("rubric", {}),
        "ready": bool(patch.get("ready", False)),
        "stop_reason": patch.get("stop_reason", ""),
    }
