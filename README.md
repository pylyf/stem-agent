# Stem Documentation Agent

A JetBrains Stem Agent Challenge prototype. A stem agent for documentation maintenance that starts with no repository knowledge, evolves its own skills and tools, freezes into a specialist, and then writes documentation.

## Concept

The agent receives one broad instruction: maintain documentation for this repository. It inspects the codebase through neutral primitive tools, generates its own skills, creates composite and Python tools, designs a documentation plan and workflow, and decides when it is ready to stop evolving. The frozen specialist then executes the documentation plan.

The project separates three independent roles:

- **`basic_agent`** — unspecialized baseline, same prompt surface as stem agent but no evolution loop
- **`stem_agent`** — self-specializing documentation agent (LangGraph state machine)
- **`evaluation`** — external scorer, runs only after both agents finish; never part of the agent loop

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
$env:OPENAI_API_KEY="..."
```

Generated Python tools require Docker Desktop (Linux engine):

```powershell
docker build -t stem-tool-sandbox:latest sandbox
```

## Usage

**Recommended — run on the news-scraper fixture:**

```powershell
stem-doc-agent run --repo fixtures/news-scraper --run-id news-scraper-01
stem-doc-agent eval --run artifacts/runs/news-scraper-01
```

It is the most complex fixture (7 source modules, async pipeline, optional deps, SMTP notifier) and produces the most interesting specialization.

**Run any other fixture:**

```powershell
stem-doc-agent run --repo fixtures/fastapi_service --run-id fastapi-01
stem-doc-agent eval --run artifacts/runs/fastapi-01
```

**Run all fixtures + evaluate (benchmark):**

```powershell
stem-doc-agent benchmark
```

The benchmark runs two phases explicitly: Phase 1 generates all artifacts, Phase 2 evaluates them. No agent re-runs during evaluation.

## Artifacts

Each run writes to `artifacts/runs/<run_id>/`:

```
repo_profile.json          ← deterministic scanner output
baseline_docs.md           ← baseline agent output
iterations/                ← per-iteration state snapshots
frozen_agent/
  stem_state.json          ← full agent state at freeze
  skills.json
  composite_tools.json
  python_tools.json
  doc_plan.json            ← agent's documentation plan (used by evaluator)
  workflow.md
evolved_docs/              ← per-document files
evolved_docs.md            ← concatenated final output
eval/
  rubric_result.json       ← agent's own rubric self-evaluation (when created)
eval_report.json           ← final comparison report
```

## Architecture

```
src/
├── stem_doc_agent/
│   ├── basic_agent/       # unspecialized baseline
│   ├── stem_agent/        # self-specializing agent
│   │   ├── loop.py        # LangGraph state machine
│   │   ├── state.py       # StemState dataclass
│   │   ├── tools.py       # ToolRegistry (primitive + composite + Python tools)
│   │   └── python_sandbox.py  # Docker sandbox for agent-generated Python tools
│   ├── kernel/            # artifact store and JSON helpers
│   ├── scanner.py         # deterministic repository sensing
│   └── llm.py             # OpenAI wrapper
├── evaluation/
│   └── evaluator.py       # external scorer (separate package)
└── stem_doc_agent/
    └── main.py            # CLI (run / eval / benchmark)
```

## Agent Loop (LangGraph)

```
evolve → use_tools → route → [freeze → execute] or [evolve → ...]
```

- **evolve**: model receives tool manifest + iteration history, patches state (skills, tools, doc plan, workflow, ready signal)
- **use_tools**: executes requested tool calls; primitive tools are sandboxed reads, composite tools chain primitives + LLM synthesis, Python tools run in Docker
- **route**: checks freeze conditions (ready flag + documents + skills + created tool + used created tool + composite args satisfied)
- **freeze**: persists full agent state to `frozen_agent/`
- **execute**: runs the doc plan, applying skills to each document; evaluates output using agent's own rubric if it created one

## Evaluation

The evaluator is external. It scores finished `baseline_docs.md` and `evolved_docs.md` independently:

| Metric | Weight |
|--------|--------|
| file_trace_accuracy | 20 |
| entrypoint_coverage | 20 |
| component_coverage | 20 |
| setup_coverage | 15 |
| hallucinated_command_avoidance | 15 |
| docs_structure_completeness | 10 |

Required sections are read from the agent's own `doc_plan.json` when available — the evaluator judges the evolved docs against the agent's stated intentions, not a fixed list.

**Rubric self-evaluation**: if the agent created an `evaluate_docs` Python tool during evolution, it is executed against the final docs. Result is stored in `eval/rubric_result.json` and included in `eval_report.json`.

**LLM judge**: GPT-4.1-mini independently evaluates both docs on accuracy, completeness, maintainer usefulness, and clarity. Runs after the deterministic scorer and never influences it.

## Sample results — `fixtures/news-scraper`

Two representative runs on the news-scraper fixture. The agent is non-deterministic; results vary per run.

### Run 08 — winner: baseline

The agent produced accurate, deep component docs but skipped setup and broader project context, hurting breadth metrics. The LLM judge called it a tie on quality (8.25 / 8.25) but the deterministic scorer penalised the missing setup coverage and hallucinated a shell command.

| | Baseline | Evolved |
|---|---|---|
| file_trace_accuracy | 0.464 | **0.714** |
| entrypoint_coverage | **1.000** | **1.000** |
| component_coverage | **0.750** | 0.500 |
| setup_coverage | **1.000** | 0.333 |
| hallucinated_command_avoidance | **1.000** | 0.500 |
| docs_structure_completeness | **1.000** | **1.000** |
| **score** | **84.29** | 66.79 |

Rubric self-eval (agent): `passes: false` (total 0.60)  
LLM judge: **tie** — *"baseline provides a more comprehensive overview… evolved delivers more accurate component-level detail but lacks setup context"*

### Run 09 — winner: evolved ✓

The agent covered setup, all entrypoints, and referenced real file paths throughout. File trace accuracy hit 1.0. Rubric self-eval also passed.

| | Baseline | Evolved |
|---|---|---|
| file_trace_accuracy | 0.692 | **1.000** |
| entrypoint_coverage | **1.000** | **1.000** |
| component_coverage | 0.583 | **0.750** |
| setup_coverage | **1.000** | **1.000** |
| hallucinated_command_avoidance | **1.000** | 0.667 |
| docs_structure_completeness | 0.500 | **1.000** |
| **score** | 80.51 | **90.00** |

Rubric self-eval (agent): `passes: true` (total 0.925)  
LLM judge: **evolved** — *"more detailed, structured, and practical guidance on setup, configuration, and usage… clearer and more actionable for a new maintainer"*

---

## Fixtures

Four bundled repositories in `fixtures/`:

- `news-scraper` — async scraper with RSS/HN/Google News fetchers, scorer, GPT draft generator, email notifier *(recommended)*
- `python_cli_tool` — Click CLI with subcommands, JSON export, tests
- `fastapi_service` — FastAPI with routers, repositories, billing, background jobs
- `react_component_lib` — React component library with hooks, theme, tests
