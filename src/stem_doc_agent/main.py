from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

from stem_doc_agent.basic_agent import run_basic_agent
from stem_doc_agent.kernel.artifacts import ArtifactStore
from evaluation import evaluate_run
from stem_doc_agent.scanner import scan_repository
from stem_doc_agent.stem_agent.loop import StemAgent


ROOT = Path(__file__).resolve().parents[2]


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="stem-doc-agent")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run")
    run_p.add_argument("--repo", required=True)
    run_p.add_argument("--run-id")
    run_p.add_argument("--model", default="gpt-4.1-mini")

    eval_p = sub.add_parser("eval")
    eval_p.add_argument("--run", required=True)

    bench_p = sub.add_parser("benchmark")
    bench_p.add_argument("--model", default="gpt-4.1-mini")

    _configure_logging()
    args = parser.parse_args()
    if args.command == "run":
        print(run(args.repo, args.run_id, args.model))
    elif args.command == "eval":
        print(json.dumps(evaluate_run(Path(args.run)), indent=2))
    elif args.command == "benchmark":
        benchmark(args.model)


def run(repo: str, run_id: str | None = None, model: str = "gpt-4.1-mini") -> Path:
    repo_path = Path(repo).resolve()
    run_id = run_id or f"{repo_path.name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    store = ArtifactStore(ROOT / "artifacts" / "runs" / run_id)
    profile = scan_repository(repo_path)
    store.write_json("repo_profile.json", profile.to_dict())
    store.write_text("baseline_docs.md", run_basic_agent(profile, model))
    StemAgent(repo_path, profile, store, model).run()
    return store.root


def benchmark(model: str) -> None:
    """Run both agents on every fixture, then evaluate all runs.

    Phase 1 — generation: run baseline + stem agent for each fixture and write
    artifacts to artifacts/runs/<fixture-name>-<timestamp>/.  No evaluation
    happens here; this phase only produces the raw documentation artifacts.

    Phase 2 — evaluation: read the finished artifacts with the external
    evaluator and print a comparison table.  The evaluator never re-runs any
    agent; it only reads what Phase 1 wrote.
    """
    fixtures = [ROOT / "fixtures" / name for name in ["python_cli_tool", "fastapi_service", "react_component_lib"]]

    # --- Phase 1: run agents ---
    logging.getLogger(__name__).info("=== Phase 1: running agents on %d fixtures ===", len(fixtures))
    run_dirs = []
    for fixture in fixtures:
        logging.getLogger(__name__).info("Running: %s", fixture.name)
        run_dirs.append((fixture.name, run(str(fixture), model=model)))

    # --- Phase 2: evaluate artifacts ---
    logging.getLogger(__name__).info("=== Phase 2: evaluating finished artifacts ===")
    rows = []
    for name, run_dir in run_dirs:
        report = evaluate_run(run_dir)
        rows.append((name, report["baseline"]["score"], report["evolved"]["score"], report["delta"], run_dir))

    print("\nRepo                  Baseline   Evolved   Delta   Run")
    print("-" * 85)
    for name, baseline, evolved, delta, run_dir in rows:
        print(f"{name:<21} {baseline:>7.2f}   {evolved:>7.2f}   {delta:>+6.2f}   {run_dir}")


if __name__ == "__main__":
    main()
