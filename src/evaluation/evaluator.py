from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# Matches only explicitly labeled shell code blocks — NOT python/js/etc.
# The language tag is required (no `?`) so ```python blocks are excluded.
_COMMAND_BLOCK_RE = re.compile(
    r"```(?:bash|powershell|sh|shell)\s+(.*?)```", re.DOTALL
)
# Matches inline backtick commands: `pip install ...`
_INLINE_CMD_RE = re.compile(
    r"`((?:npm|pip|python|pytest|uvicorn|docker)\b[^`\n]*)`"
)
# Extracts individual command lines from a code block
_CMD_LINE_RE = re.compile(
    r"^\s*((?:npm|pip|python|pytest|uvicorn|docker)\b[^\n]*)", re.MULTILINE
)
# Matches backtick-quoted file references like `src/foo.py`
_FILE_REF_RE = re.compile(r"`([^`\s]+\.[A-Za-z0-9]{1,6})`")

# Weights used when computing the aggregate score (must sum to 100)
RUBRIC_WEIGHTS: dict[str, int] = {
    "file_trace_accuracy": 20,
    "entrypoint_coverage": 20,
    "component_coverage": 20,
    "setup_coverage": 15,
    "hallucinated_command_avoidance": 15,
    "docs_structure_completeness": 10,
}

# Fallback section names used when no doc_plan.json is present in the run dir
_DEFAULT_SECTIONS = ["Setup", "Components", "Architecture", "Usage", "Maintainer"]


def evaluate_run(run_dir: Path) -> dict[str, Any]:
    """Score baseline and evolved docs for a completed run.

    Reads ``repo_profile.json``, ``baseline_docs.md``, and ``evolved_docs.md``
    from *run_dir*, scores each with :func:`score_docs`, computes the delta,
    and writes ``eval_report.json`` back to *run_dir*.

    Returns the report dict.
    """
    profile = json.loads((run_dir / "repo_profile.json").read_text(encoding="utf-8"))
    baseline = (run_dir / "baseline_docs.md").read_text(encoding="utf-8")
    evolved = (run_dir / "evolved_docs.md").read_text(encoding="utf-8")
    required = _required_sections(run_dir)

    report: dict[str, Any] = {
        "baseline": score_docs(baseline, profile, required),
        "evolved": score_docs(evolved, profile, required),
    }
    report["delta"] = round(report["evolved"]["score"] - report["baseline"]["score"], 2)
    report["winner"] = "evolved" if report["delta"] >= 0 else "baseline"
    report["accepted"] = report["delta"] >= 0

    # Include rubric self-eval result when available
    rubric_path = run_dir / "eval" / "rubric_result.json"
    if rubric_path.exists():
        report["rubric_self_eval"] = json.loads(rubric_path.read_text(encoding="utf-8"))

    # Optional LLM judge — runs only when OpenAI key is available
    report["llm_judge"] = llm_judge(baseline, evolved, profile)

    (run_dir / "eval_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def score_docs(text: str, profile: dict[str, Any], required_sections: list[str]) -> dict[str, Any]:
    """Compute a weighted score for a single documentation artifact.

    All six metric functions return a value in [0.0, 1.0].  The final score
    is a weighted average scaled to [0, 100].
    """
    metrics = {
        "file_trace_accuracy": _file_trace_accuracy(text, profile),
        "entrypoint_coverage": _coverage(text, profile.get("entrypoints", [])),
        "component_coverage": _coverage(text, profile.get("components", [])),
        "setup_coverage": _coverage(text, profile.get("setup_commands", [])),
        "hallucinated_command_avoidance": _command_avoidance(text, profile.get("setup_commands", [])),
        "docs_structure_completeness": _section_coverage(text, required_sections),
    }
    total_weight = sum(RUBRIC_WEIGHTS.values())
    score = sum(metrics[name] * RUBRIC_WEIGHTS[name] for name in metrics) / total_weight
    return {
        "metrics": {k: round(v, 4) for k, v in metrics.items()},
        "score": round(score * 100, 2),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _required_sections(run_dir: Path) -> list[str]:
    """Return required section names: from doc_plan.json if present, else defaults.

    Using doc_plan.json means the evaluator judges the evolved docs against the
    *agent's own stated intentions*, not a fixed external list.
    """
    doc_plan_path = run_dir / "frozen_agent" / "doc_plan.json"
    if doc_plan_path.exists():
        try:
            plan = json.loads(doc_plan_path.read_text(encoding="utf-8"))
            sections = [doc.get("path", "").split("/")[-1].replace(".md", "").title()
                        for doc in plan.get("documents", [])
                        if doc.get("path")]
            if sections:
                return sections
        except (json.JSONDecodeError, KeyError):
            pass
    return _DEFAULT_SECTIONS


def _file_trace_accuracy(text: str, profile: dict[str, Any]) -> float:
    """Fraction of backtick file references that point to real repo files.

    A reference is accepted if the path (without any trailing `: label`) exists
    in file_summaries, package_files, or entrypoints.
    """
    raw_refs = _FILE_REF_RE.findall(text)
    # Strip trailing `: some label` that the scanner sometimes appends
    refs = [r.split(":")[0].strip() for r in raw_refs]
    if not refs:
        return 0.0
    known = (
        set(profile.get("file_summaries", {}))
        | set(profile.get("package_files", []))
        | set(profile.get("entrypoints", []))
    )
    return sum(1 for r in refs if r in known) / len(refs)


def _coverage(text: str, expected: list[str]) -> float:
    """Fraction of expected items (entrypoints / components / commands) mentioned in text."""
    if not expected:
        return 1.0
    return sum(1 for item in expected if item in text) / len(expected)


def _command_avoidance(text: str, allowed: list[str]) -> float:
    """Fraction of shell commands in the docs that are sanctioned by the repo profile.

    Extracts commands from both inline backticks and fenced code blocks, then
    checks each against the ``setup_commands`` list from the profile.  A high
    score means the docs don't invent commands that aren't in the package
    metadata.
    """
    commands: list[str] = []
    # Inline: `pip install -r requirements.txt`
    commands.extend(m.strip() for m in _INLINE_CMD_RE.findall(text))
    # Fenced blocks
    for block in _COMMAND_BLOCK_RE.findall(text):
        commands.extend(m.strip() for m in _CMD_LINE_RE.findall(block))
    if not commands:
        return 1.0
    allowed_set = set(allowed)
    # A command is "allowed" if it matches or is a prefix of an allowed command
    def _is_allowed(cmd: str) -> bool:
        if cmd in allowed_set:
            return True
        return any(cmd in a or a in cmd for a in allowed_set)
    return sum(1 for c in commands if _is_allowed(c)) / len(commands)


def _section_coverage(text: str, sections: list[str]) -> float:
    """Fraction of required section names (as headings or keywords) present in text."""
    if not sections:
        return 1.0
    normalized = text.lower()
    return sum(1 for s in sections if s.lower() in normalized) / len(sections)


# ---------------------------------------------------------------------------
# LLM judge
# ---------------------------------------------------------------------------

_JUDGE_SYSTEM = """\
You are an impartial technical documentation evaluator.
You will receive two documentation artifacts for the same repository — a baseline \
and an evolved version — and a brief repository profile.
Evaluate both fairly and return ONLY a JSON object, no prose outside the JSON.
"""

_JUDGE_PROMPT = """\
Repository profile (summary):
- project_type: {project_type}
- languages: {languages}
- frameworks: {frameworks}
- entrypoints: {entrypoints}
- components: {components}

--- BASELINE DOCUMENTATION ---
{baseline}

--- EVOLVED DOCUMENTATION ---
{evolved}

Evaluate both documents on these criteria (score each 0–10):
- accuracy: claims are grounded in the repository profile, no hallucinations
- completeness: covers entrypoints, setup, components, and key interfaces
- maintainer_usefulness: a new maintainer could orient themselves using this doc
- clarity: well-structured, scannable, unambiguous

Return exactly this JSON shape:
{{
  "baseline": {{"accuracy": 0, "completeness": 0, "maintainer_usefulness": 0, "clarity": 0, "total": 0}},
  "evolved":  {{"accuracy": 0, "completeness": 0, "maintainer_usefulness": 0, "clarity": 0, "total": 0}},
  "winner": "baseline" | "evolved" | "tie",
  "reasoning": "one or two sentences"
}}
The "total" field is the unweighted average of the four criteria scores.
"""


def llm_judge(baseline: str, evolved: str, profile: dict[str, Any]) -> dict[str, Any]:
    """Ask the LLM to compare baseline and evolved docs and return a structured verdict.

    Returns a result dict on success, or ``{"error": "..."}`` when the API is
    unavailable so the rest of the evaluation is not interrupted.
    """
    try:
        from stem_doc_agent.llm import complete, load_dotenv
        load_dotenv()
    except ImportError:
        return {"error": "stem_doc_agent not importable from evaluation package"}

    # Truncate to avoid very large prompts — 6 000 chars each is enough for judgment
    prompt = _JUDGE_PROMPT.format(
        project_type=profile.get("project_type", "unknown"),
        languages=", ".join(profile.get("languages", [])),
        frameworks=", ".join(profile.get("frameworks", [])),
        entrypoints=", ".join(profile.get("entrypoints", [])),
        components=", ".join(profile.get("components", [])[:10]),
        baseline=baseline[:6000],
        evolved=evolved[:6000],
    )

    try:
        raw = complete(prompt, model="gpt-4.1-mini", system=_JUDGE_SYSTEM)
        # Strip markdown fences if the model wraps JSON in ```json ... ```
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()
        result = json.loads(raw)
        logger.info(
            "LLM judge: winner=%s  baseline=%.1f  evolved=%.1f  — %s",
            result.get("winner"),
            result.get("baseline", {}).get("total", 0),
            result.get("evolved", {}).get("total", 0),
            result.get("reasoning", ""),
        )
        return result
    except Exception as exc:
        logger.warning("LLM judge failed: %s", exc)
        return {"error": str(exc)}
