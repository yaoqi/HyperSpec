#!/usr/bin/env python3
"""Generate a HyperSpec project profile.

The script is intentionally dependency-free so Codex can run it in constrained
workspaces. It prints JSON by default and can also create/update
`.hyperspec-state.yaml` with `--write-state`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SOURCE_DIRS = ("src", "lib", "app", "apps", "packages", "modules", "cmd", "internal", "pkg")
IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "node_modules",
    "target",
    "build",
    "dist",
    ".next",
    ".nuxt",
    ".venv",
    "venv",
    "__pycache__",
}
LANGUAGE_BY_EXT = {
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".py": "python",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".swift": "swift",
}
FRAMEWORK_MARKERS = {
    "spring-boot": ("spring-boot", "springboot"),
    "spring": ("org.springframework", "spring-framework"),
    "react": ("react",),
    "next": ("next",),
    "vue": ("vue",),
    "nuxt": ("nuxt",),
    "angular": ("@angular/core",),
    "express": ("express",),
    "nestjs": ("@nestjs/core",),
    "fastapi": ("fastapi",),
    "django": ("django",),
    "flask": ("flask",),
    "pytest": ("pytest",),
    "gin": ("github.com/gin-gonic/gin",),
    "echo": ("github.com/labstack/echo",),
    "actix": ("actix-web",),
    "rocket": ("rocket",),
}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError:
        return {}


def iter_source_files(root: Path):
    candidates = [root / name for name in SOURCE_DIRS if (root / name).exists()]
    if not candidates:
        candidates = [root]

    for base in candidates:
        if not base.exists():
            continue
        for current, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            for filename in files:
                path = Path(current) / filename
                if path.suffix.lower() in LANGUAGE_BY_EXT:
                    yield path


def detect_languages(root: Path) -> list[str]:
    counts = Counter(LANGUAGE_BY_EXT[path.suffix.lower()] for path in iter_source_files(root))
    return [language for language, _ in counts.most_common(2)]


def dependency_blobs(root: Path) -> list[str]:
    blobs: list[str] = []

    package_json = root / "package.json"
    if package_json.exists():
        pkg = load_json(package_json)
        deps = {}
        for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
            deps.update(pkg.get(key, {}) or {})
        blobs.extend(deps.keys())

    for name in ("pom.xml", "build.gradle", "build.gradle.kts", "go.mod", "Cargo.toml", "pyproject.toml", "requirements.txt"):
        path = root / name
        if path.exists():
            blobs.append(read_text(path))

    return blobs


def detect_frameworks(root: Path) -> list[str]:
    haystack = "\n".join(dependency_blobs(root)).lower()
    frameworks = []
    for framework, markers in FRAMEWORK_MARKERS.items():
        if any(marker.lower() in haystack for marker in markers):
            frameworks.append(framework)
    return frameworks


def detect_build_tool(root: Path) -> str:
    if (root / "pom.xml").exists():
        return "maven"
    if (root / "gradlew").exists() or (root / "gradlew.bat").exists() or (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        return "gradle"
    if (root / "package.json").exists():
        if (root / "pnpm-lock.yaml").exists():
            return "pnpm"
        if (root / "yarn.lock").exists():
            return "yarn"
        return "npm"
    if (root / "go.mod").exists():
        return "go"
    if (root / "Cargo.toml").exists():
        return "cargo"
    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
        return "python"
    return "unknown"


def package_script(root: Path, script: str) -> bool:
    package_json = root / "package.json"
    if not package_json.exists():
        return False
    pkg = load_json(package_json)
    return script in (pkg.get("scripts", {}) or {})


def detect_commands(root: Path, build_tool: str) -> tuple[str | None, str | None]:
    if build_tool == "maven":
        extra = " -gs ./settings.xml" if (root / "settings.xml").exists() else ""
        return f"mvn compile{extra}", f"mvn test{extra}"
    if build_tool == "gradle":
        gradle = ".\\gradlew.bat" if os.name == "nt" and (root / "gradlew.bat").exists() else "./gradlew"
        return f"{gradle} compileJava", f"{gradle} test"
    if build_tool == "npm":
        return ("npm run build" if package_script(root, "build") else None, "npm test" if package_script(root, "test") else None)
    if build_tool == "pnpm":
        return ("pnpm run build" if package_script(root, "build") else None, "pnpm test" if package_script(root, "test") else None)
    if build_tool == "yarn":
        return ("yarn build" if package_script(root, "build") else None, "yarn test" if package_script(root, "test") else None)
    if build_tool == "go":
        return "go build ./...", "go test ./..."
    if build_tool == "cargo":
        return "cargo build", "cargo test"
    if build_tool == "python":
        return None, "pytest" if shutil.which("pytest") else None
    return None, None


def detect_structure(root: Path) -> str:
    if (root / "go.work").exists():
        return "monorepo"
    if (root / "packages").is_dir() or (root / "modules").is_dir() or (root / "apps").is_dir():
        return "monorepo"
    pom_count = sum(1 for _ in root.glob("**/pom.xml"))
    package_count = sum(1 for path in root.glob("**/package.json") if "node_modules" not in path.parts)
    if pom_count > 1 or package_count > 1:
        return "monorepo"
    return "single-module"


def detect_ci(root: Path) -> bool:
    return any(
        path.exists()
        for path in (
            root / ".github" / "workflows",
            root / ".gitlab-ci.yml",
            root / "Jenkinsfile",
            root / "azure-pipelines.yml",
            root / ".circleci" / "config.yml",
        )
    )


def command_exists(command: str | None) -> bool | None:
    if not command:
        return None
    executable = command.split()[0]
    if executable.startswith("."):
        return True
    return shutil.which(executable) is not None


def verify_compile(root: Path, command: str | None, should_run: bool) -> dict[str, Any]:
    if not command:
        return {"status": "skipped", "reason": "compile_command is null"}
    if not should_run:
        return {"status": "not-run", "reason": "use --verify-compile to execute compile_command"}
    try:
        result = subprocess.run(
            command,
            cwd=str(root),
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=120,
        )
        return {
            "status": "passed" if result.returncode == 0 else "failed",
            "exit_code": result.returncode,
            "output_tail": result.stdout[-4000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {"status": "timeout", "output_tail": (exc.stdout or "")[-4000:]}


def build_profile(root: Path, verify: bool) -> dict[str, Any]:
    build_tool = detect_build_tool(root)
    compile_command, test_command = detect_commands(root, build_tool)
    profile = {
        "languages": detect_languages(root),
        "frameworks": detect_frameworks(root),
        "build_tool": build_tool,
        "compile_command": compile_command,
        "test_command": test_command,
        "structure": detect_structure(root),
        "has_ci": detect_ci(root),
        "command_availability": {
            "compile": command_exists(compile_command),
            "test": command_exists(test_command),
        },
    }
    profile["compile_verification"] = verify_compile(root, compile_command, verify)
    return profile


def yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "[" + ", ".join(str(item) for item in value) + "]"
    if isinstance(value, str):
        if value == "" or re.search(r"[:#\[\]{}]|^\s|\s$", value):
            return json.dumps(value, ensure_ascii=False)
        return value
    return str(value)


def state_yaml(profile: dict[str, Any], active_change: str | None) -> str:
    lines = [
        "version: 1",
        f"active_change: {yaml_scalar(active_change)}",
        "phase: propose",
        "checkpoint: profiler-done",
        "project_profile:",
    ]
    for key in ("languages", "frameworks", "build_tool", "compile_command", "test_command", "structure", "has_ci"):
        lines.append(f"  {key}: {yaml_scalar(profile.get(key))}")
    lines.append("  command_availability:")
    for key, value in profile.get("command_availability", {}).items():
        lines.append(f"    {key}: {yaml_scalar(value)}")
    verification = profile.get("compile_verification", {})
    lines.append("  compile_verification:")
    for key, value in verification.items():
        if key == "output_tail" and isinstance(value, str):
            lines.append("    output_tail: |-")
            for line in value.splitlines()[-80:]:
                lines.append(f"      {line}")
        else:
            lines.append(f"    {key}: {yaml_scalar(value)}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a HyperSpec project profile.")
    parser.add_argument("--root", default=".", help="Project root to inspect.")
    parser.add_argument("--write-state", action="store_true", help="Write .hyperspec-state.yaml in the project root.")
    parser.add_argument("--verify-compile", action="store_true", help="Run the inferred compile command.")
    parser.add_argument("--active-change", default=None, help="Optional active change name for the state file.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Project root does not exist: {root}", file=sys.stderr)
        return 2

    profile = build_profile(root, args.verify_compile)
    payload = {"root": str(root), "project_profile": profile}

    if args.write_state:
        state_path = root / ".hyperspec-state.yaml"
        state_path.write_text(state_yaml(profile, args.active_change), encoding="utf-8")
        payload["state_file"] = str(state_path)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
