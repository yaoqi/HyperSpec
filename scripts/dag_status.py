#!/usr/bin/env python3
"""Evaluate the HyperSpec workflow DAG from filesystem evidence.

The script is dependency-free. It intentionally treats .hyperspec-state.yaml as
a cache: state fields help identify the active change, but node status is
computed from files whenever possible.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


CHECKPOINT_ORDER = [
    "profiler-done",
    "brainstorm-started",
    "brainstorm-done",
    "requirements-confirmed",
    "openspec-generated",
    "plan-generated",
    "plan-generated-and-confirmed",
    "task-N-complete",
    "verified",
    "reviewed",
    "apply-done",
    "consistency-verified",
    "archived",
    "done",
]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def nonempty_file(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def parse_state(root: Path) -> dict[str, Any]:
    path = root / ".hyperspec-state.yaml"
    state: dict[str, Any] = {"exists": path.exists(), "path": str(path)}
    if not path.exists():
        return state

    for raw_line in read_text(path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key in {"active_change", "phase", "checkpoint"}:
            state[key] = None if value in {"", "null", "~"} else value
    return state


def active_change_dirs(root: Path) -> list[Path]:
    changes = root / "openspec" / "changes"
    if not changes.is_dir():
        return []
    return sorted(
        path
        for path in changes.iterdir()
        if path.is_dir() and path.name != "archive"
    )


def archived_change_dirs(root: Path, change: str | None) -> list[Path]:
    archive = root / "openspec" / "changes" / "archive"
    if not archive.is_dir():
        return []
    dirs = [path for path in archive.iterdir() if path.is_dir()]
    if change:
        dirs = [path for path in dirs if path.name == change or path.name.endswith(f"-{change}")]
    return sorted(dirs)


def infer_change(root: Path, state: dict[str, Any], explicit_change: str | None = None) -> str | None:
    if explicit_change:
        return explicit_change
    state_change = state.get("active_change")
    if isinstance(state_change, str) and state_change:
        return state_change
    dirs = active_change_dirs(root)
    if len(dirs) == 1:
        return dirs[0].name
    return None


def find_change_dir(root: Path, change: str | None) -> Path | None:
    dirs = active_change_dirs(root)
    if change:
        for path in dirs:
            if path.name == change:
                return path
    if len(dirs) == 1:
        return dirs[0]
    return None


def specs_nonempty(change_dir: Path | None) -> bool:
    if not change_dir:
        return False
    specs = change_dir / "specs"
    if not specs.is_dir():
        return False
    return any(nonempty_file(path) for path in specs.rglob("*.md"))


def openspec_artifacts_done(change_dir: Path | None) -> bool:
    if not change_dir:
        return False
    required = ("proposal.md", "design.md", "tasks.md")
    return all(nonempty_file(change_dir / name) for name in required) and specs_nonempty(change_dir)


def plan_files(root: Path, change: str | None) -> list[Path]:
    plans = root / "superpowers" / "plans"
    if not plans.is_dir():
        return []
    files = sorted(path for path in plans.glob("*.md") if path.is_file())
    if not change:
        return files
    marker = f"<!-- hyperspec change: {change} -->"
    matched = [path for path in files if marker in read_text(path)]
    if matched:
        return matched
    return [path for path in files if change in path.name]


CHECKBOX_RE = re.compile(r"^\s*-\s+\[( |x|X)\]", re.MULTILINE)
UNCHECKED_RE = re.compile(r"^\s*-\s+\[ \]", re.MULTILINE)


def plan_status(paths: list[Path]) -> dict[str, Any]:
    if not paths:
        return {"exists": False, "hasCheckbox": False, "allChecked": False, "paths": []}
    texts = [read_text(path) for path in paths]
    checkbox_count = sum(len(CHECKBOX_RE.findall(text)) for text in texts)
    unchecked_count = sum(len(UNCHECKED_RE.findall(text)) for text in texts)
    return {
        "exists": True,
        "hasCheckbox": checkbox_count > 0,
        "allChecked": checkbox_count > 0 and unchecked_count == 0,
        "checkboxCount": checkbox_count,
        "uncheckedCount": unchecked_count,
        "paths": [str(path) for path in paths],
    }


def checkpoint_at_least(state: dict[str, Any], checkpoint: str) -> bool:
    current = state.get("checkpoint")
    if not isinstance(current, str):
        return False
    if current.startswith("task-") and checkpoint == "task-N-complete":
        return True
    try:
        return CHECKPOINT_ORDER.index(current) >= CHECKPOINT_ORDER.index(checkpoint)
    except ValueError:
        return False


def status_label(done: bool, deps_done: bool, optional_blocked: bool = False) -> str:
    if done:
        return "done"
    if deps_done and not optional_blocked:
        return "ready"
    return "blocked"


def build_nodes(root: Path, dag: dict[str, Any], state: dict[str, Any], change: str | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    change_dir = find_change_dir(root, change)
    archives = archived_change_dirs(root, change)
    archive_dir = archives[-1] if archives else None
    plan = plan_status(plan_files(root, change))
    brainstorm_path = root / ".hyperspec-brainstorm.md"
    archived_brainstorm = archive_dir / "brainstorm.md" if archive_dir else None

    facts = {
        "activeChangeDirs": [str(path) for path in active_change_dirs(root)],
        "changeDir": str(change_dir) if change_dir else None,
        "archiveDir": str(archive_dir) if archive_dir else None,
        "plan": plan,
    }

    archive_done = bool(archive_dir)
    downstream_evidence = bool(
        nonempty_file(brainstorm_path)
        or change_dir
        or plan["exists"]
        or archive_dir
    )
    done_by_id = {
        "project-profile": bool(
            (state.get("exists") and "project_profile:" in read_text(root / ".hyperspec-state.yaml"))
            or downstream_evidence
        ),
        "brainstorm": nonempty_file(brainstorm_path) or bool(archived_brainstorm and nonempty_file(archived_brainstorm)),
        "openspec-artifacts": openspec_artifacts_done(change_dir) or bool(archive_dir),
        "implementation-plan": bool((plan["exists"] and plan["hasCheckbox"]) or archive_dir),
        "implementation": bool(plan["allChecked"] or archive_dir),
        "verification": bool(checkpoint_at_least(state, "verified") or archive_dir),
        "review": bool(checkpoint_at_least(state, "reviewed") or archive_dir),
        "consistency": bool((change_dir and nonempty_file(change_dir / ".close-verification-done")) or checkpoint_at_least(state, "consistency-verified") or archive_dir),
        "archive": archive_done,
        "cleanup": archive_done and (not (root / ".hyperspec-state.yaml").exists()) and (not brainstorm_path.exists()),
    }

    nodes: list[dict[str, Any]] = []
    for raw_node in dag.get("nodes", []):
        node_id = raw_node["id"]
        deps = raw_node.get("deps", [])
        missing = [dep for dep in deps if not done_by_id.get(dep, False)]
        deps_done = not missing
        status = status_label(done_by_id.get(node_id, False), deps_done)
        node = {
            "id": node_id,
            "phase": raw_node.get("phase"),
            "checkpoint": raw_node.get("checkpoint"),
            "status": status,
            "missingDeps": missing,
            "optional": bool(raw_node.get("optional", False)),
            "outputs": raw_node.get("outputs", []),
            "description": raw_node.get("description", ""),
        }
        nodes.append(node)
    return nodes, facts


def load_dag(path: Path) -> dict[str, Any]:
    try:
        dag = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid DAG JSON {path}: {exc}") from exc
    validate_dag(dag, path)
    return dag


def validate_dag(dag: dict[str, Any], path: Path) -> None:
    if not isinstance(dag.get("nodes"), list) or not dag["nodes"]:
        raise SystemExit(f"Invalid DAG JSON {path}: nodes must be a non-empty list")
    required = set(dag.get("schema", {}).get("nodeRequiredFields", [])) or {
        "id",
        "phase",
        "checkpoint",
        "deps",
        "outputs",
        "description",
    }
    seen: set[str] = set()
    for index, node in enumerate(dag["nodes"]):
        if not isinstance(node, dict):
            raise SystemExit(f"Invalid DAG JSON {path}: node #{index} must be an object")
        missing = sorted(required - set(node))
        if missing:
            raise SystemExit(f"Invalid DAG JSON {path}: node #{index} missing {', '.join(missing)}")
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            raise SystemExit(f"Invalid DAG JSON {path}: node #{index} has invalid id")
        if node_id in seen:
            raise SystemExit(f"Invalid DAG JSON {path}: duplicate node id {node_id}")
        seen.add(node_id)
    for node in dag["nodes"]:
        for dep in node.get("deps", []) + node.get("optionalDeps", []):
            if dep not in seen:
                raise SystemExit(f"Invalid DAG JSON {path}: node {node['id']} references unknown dependency {dep}")


def mermaid(nodes: list[dict[str, Any]], dag: dict[str, Any]) -> str:
    lines = ["flowchart TD"]
    status_class = {"done": "done", "ready": "ready", "blocked": "blocked"}
    for node in nodes:
        label = f"{node['id']}\\n{node['status']}"
        lines.append(f"  {node['id'].replace('-', '_')}[\"{label}\"]:::{status_class[node['status']]}")
    for raw_node in dag.get("nodes", []):
        target = raw_node["id"].replace("-", "_")
        for dep in raw_node.get("deps", []):
            lines.append(f"  {dep.replace('-', '_')} --> {target}")
        for dep in raw_node.get("optionalDeps", []):
            lines.append(f"  {dep.replace('-', '_')} -. optional .-> {target}")
    lines.extend(
        [
            "  classDef done fill:#d9fbe5,stroke:#248a3d,color:#111;",
            "  classDef ready fill:#fff4c2,stroke:#a87300,color:#111;",
            "  classDef blocked fill:#f2f2f2,stroke:#999,color:#555;",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the HyperSpec DAG.")
    parser.add_argument("--root", default=".", help="Project root to inspect.")
    parser.add_argument("--dag", default=None, help="Path to hyperspec-dag.json.")
    parser.add_argument("--change", default=None, help="Explicit active change name. Overrides .hyperspec-state.yaml and auto-detection.")
    parser.add_argument("--format", choices=("json", "mermaid"), default="json", help="Output format.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Project root does not exist: {root}", file=sys.stderr)
        return 2

    default_dag = Path(__file__).resolve().parents[1] / "hyperspec-dag.json"
    dag_path = Path(args.dag).resolve() if args.dag else default_dag
    dag = load_dag(dag_path)
    state = parse_state(root)
    change = infer_change(root, state, args.change)
    nodes, facts = build_nodes(root, dag, state, change)
    next_nodes = [node["id"] for node in nodes if node["status"] == "ready"]

    payload = {
        "root": str(root),
        "dag": str(dag_path),
        "activeChange": change,
        "phase": state.get("phase"),
        "checkpoint": state.get("checkpoint"),
        "explicitChange": args.change,
        "isComplete": all(node["status"] == "done" or node["optional"] for node in nodes),
        "next": next_nodes,
        "nodes": nodes,
        "facts": facts,
    }

    if args.format == "mermaid":
        print(mermaid(nodes, dag))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
