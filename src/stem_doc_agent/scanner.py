from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


IGNORED_DIRS = {".git", "__pycache__", "node_modules", ".venv", "dist", "build"}


@dataclass
class RepoProfile:
    repo_path: str
    project_type: str
    languages: list[str]
    frameworks: list[str]
    entrypoints: list[str]
    package_files: list[str]
    existing_docs: list[str]
    components: list[str]
    setup_commands: list[str]
    public_interfaces: list[str]
    documentation_risks: list[str]
    file_summaries: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def scan_repository(repo: Path) -> RepoProfile:
    repo = repo.resolve()
    files = _list_files(repo)
    rels = [p.relative_to(repo).as_posix() for p in files]
    package_files = [p for p in rels if Path(p).name in {"package.json", "pyproject.toml", "requirements.txt", "setup.py", "docker-compose.yml"}]
    existing_docs = [p for p in rels if Path(p).name.lower() in {"readme.md", "docs.md"} or p.lower().startswith("docs/")]
    languages = _detect_languages(rels)
    frameworks = _detect_frameworks(repo, rels)
    entrypoints = _detect_entrypoints(repo, rels, frameworks)
    components = _detect_components(rels)
    setup_commands = _detect_setup_commands(repo, rels)
    public_interfaces = _detect_public_interfaces(repo, files)
    project_type = _classify_project(frameworks, rels)
    risks = _documentation_risks(existing_docs, entrypoints, setup_commands, components, frameworks)
    summaries = _summarize_files(repo, files)
    return RepoProfile(
        repo_path=str(repo),
        project_type=project_type,
        languages=languages,
        frameworks=frameworks,
        entrypoints=entrypoints,
        package_files=package_files,
        existing_docs=existing_docs,
        components=components,
        setup_commands=setup_commands,
        public_interfaces=public_interfaces,
        documentation_risks=risks,
        file_summaries=summaries,
    )


def _list_files(repo: Path) -> list[Path]:
    out: list[Path] = []
    for root, dirs, names in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for name in names:
            path = Path(root) / name
            if path.is_file():
                out.append(path)
    return sorted(out)


def _detect_languages(rels: list[str]) -> list[str]:
    mapping = {".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript", ".css": "CSS"}
    langs = sorted({mapping[Path(p).suffix] for p in rels if Path(p).suffix in mapping})
    return langs


def _read(repo: Path, rel: str) -> str:
    try:
        return (repo / rel).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return (repo / rel).read_text(errors="ignore")


def _detect_frameworks(repo: Path, rels: list[str]) -> list[str]:
    frameworks: set[str] = set()
    if "package.json" in rels:
        package = json.loads(_read(repo, "package.json"))
        deps = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
        for name in ["react", "vite", "next", "express"]:
            if name in deps:
                frameworks.add(name.title() if name != "vite" else "Vite")
    text = "\n".join(_read(repo, p) for p in rels if p.endswith(".py"))
    if "FastAPI" in text or "fastapi" in text:
        frameworks.add("FastAPI")
    if "click." in text or "import click" in text:
        frameworks.add("Click")
    if "argparse" in text:
        frameworks.add("argparse")
    return sorted(frameworks)


def _detect_entrypoints(repo: Path, rels: list[str], frameworks: list[str]) -> list[str]:
    entrypoints: set[str] = set()
    if "package.json" in rels:
        package = json.loads(_read(repo, "package.json"))
        for key in ["main", "module"]:
            if package.get(key):
                entrypoints.add(package[key])
        for script in package.get("scripts", {}).values():
            for token in script.split():
                if token.endswith((".js", ".jsx", ".ts", ".tsx")):
                    entrypoints.add(token)
    for rel in rels:
        name = Path(rel).name
        if rel.endswith(".py") and name in {"main.py", "cli.py", "app.py"}:
            entrypoints.add(rel)
        if rel.endswith((".tsx", ".jsx")) and name in {"index.tsx", "index.jsx", "main.tsx", "main.jsx"}:
            entrypoints.add(rel)
    return sorted(e for e in entrypoints if (repo / e).exists())


def _detect_components(rels: list[str]) -> list[str]:
    candidates: set[str] = set()
    for rel in rels:
        parts = Path(rel).parts
        if len(parts) >= 2 and parts[0] in {"src", "app", "lib"}:
            if Path(rel).suffix in {".py", ".js", ".jsx", ".ts", ".tsx"}:
                candidates.add(parts[0] + "/" + parts[1])
        elif Path(rel).suffix in {".py", ".js", ".jsx", ".ts", ".tsx"}:
            candidates.add(rel)
    return sorted(candidates)[:12]


def _detect_setup_commands(repo: Path, rels: list[str]) -> list[str]:
    commands: list[str] = []
    if "requirements.txt" in rels:
        commands.append("pip install -r requirements.txt")
    if "pyproject.toml" in rels:
        commands.append("pip install -e .")
    if "package.json" in rels:
        commands.append("npm install")
        package = json.loads(_read(repo, "package.json"))
        for script in sorted(package.get("scripts", {})):
            commands.append(f"npm run {script}")
    if "docker-compose.yml" in rels:
        commands.append("docker compose up")
    if any(rel.startswith("tests/") for rel in rels):
        commands.append("pytest")
    if "FastAPI" in _detect_frameworks(repo, rels) and "app/main.py" in rels:
        commands.append("uvicorn app.main:app --reload")
    return commands


def _detect_public_interfaces(repo: Path, files: list[Path]) -> list[str]:
    interfaces: set[str] = set()
    for path in files:
        rel = path.relative_to(repo).as_posix()
        if path.suffix == ".py":
            text = _read(repo, rel)
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith(("def ", "class ")) or stripped.startswith(("@app.", "@router.")):
                    interfaces.add(f"{rel}: {stripped[:80]}")
        elif path.suffix in {".tsx", ".jsx", ".ts", ".js"}:
            text = _read(repo, rel)
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("export ") or stripped.startswith("function "):
                    interfaces.add(f"{rel}: {stripped[:80]}")
    return sorted(interfaces)[:30]


def _classify_project(frameworks: list[str], rels: list[str]) -> str:
    if "FastAPI" in frameworks:
        return "FastAPI backend service"
    if "React" in frameworks:
        return "React component library"
    if "Click" in frameworks or "argparse" in frameworks:
        return "Python CLI tool"
    if "package.json" in rels:
        return "JavaScript package"
    if "pyproject.toml" in rels or "requirements.txt" in rels:
        return "Python project"
    return "Unknown repository"


def _documentation_risks(existing_docs: list[str], entrypoints: list[str], setup_commands: list[str], components: list[str], frameworks: list[str]) -> list[str]:
    risks: list[str] = []
    if not existing_docs:
        risks.append("No existing documentation detected.")
    if entrypoints:
        risks.append("Entrypoints need explicit maintainer guidance.")
    if setup_commands:
        risks.append("Setup commands should be documented exactly from package metadata.")
    if components:
        risks.append("Major components should be summarized with file traces.")
    if "FastAPI" in frameworks:
        risks.append("API routes and request models can drift from docs.")
    if "React" in frameworks:
        risks.append("Component props and exports can drift from docs.")
    return risks


def _summarize_files(repo: Path, files: list[Path]) -> dict[str, str]:
    summaries: dict[str, str] = {}
    for path in files:
        rel = path.relative_to(repo).as_posix()
        if path.suffix.lower() not in {".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".toml", ".md", ".txt", ".yml", ".yaml"}:
            continue
        text = _read(repo, rel)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        summaries[rel] = " ".join(lines[:6])[:500]
    return summaries
