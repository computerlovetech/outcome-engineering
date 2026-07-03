"""Install the bundled Outcome Engineering agent skills into agent config
dirs (ported from the old package; skills now live in oe_cli/skills)."""

from __future__ import annotations

import os
import shutil
from importlib import resources
from pathlib import Path

SKILL_NAME = "oe-cli"
SKILL_NAMES = (
    SKILL_NAME,
    "oe-grill",
    "oe-graph-audit",
    "oe-validate",
    "oe-best-practices",
)


def skill_target(agent: str) -> Path:
    normalized = agent.lower()
    if normalized == "codex":
        return codex_skill_target()
    if normalized == "claude":
        return claude_skill_target()
    raise ValueError(f"unsupported agent {agent!r}; expected codex, claude, or all")


def project_skill_target(kind: str, cwd: Path | None = None) -> Path:
    return project_skill_root(kind, cwd=cwd) / SKILL_NAME


def project_skill_root(kind: str, cwd: Path | None = None) -> Path:
    root = (cwd or Path.cwd()).resolve()
    normalized = kind.lower()
    if normalized in {"", "claude"}:
        return root / ".claude" / "skills"
    if normalized == "agents":
        return root / ".agents" / "skills"
    raise ValueError("unsupported --skills value; use --skills, --skills=claude, or --skills=agents")


def codex_skill_target() -> Path:
    return codex_skill_root() / SKILL_NAME


def codex_skill_root() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home) / "skills"
    return Path.home() / ".codex" / "skills"


def claude_skill_target() -> Path:
    return claude_skill_root() / SKILL_NAME


def claude_skill_root() -> Path:
    claude_home = os.environ.get("CLAUDE_HOME")
    if claude_home:
        return Path(claude_home) / "skills"
    return Path.home() / ".claude" / "skills"


def install_skill(target: Path | None = None, force: bool = False) -> Path:
    destination = (target or codex_skill_target()).expanduser()
    return copy_skill(destination, force=force)


def install_skills_for_agent(agent: str, force: bool = False) -> list[Path]:
    normalized = agent.lower()
    if normalized == "all":
        installed: list[Path] = []
        for name in ("codex", "claude"):
            installed.extend(copy_skills(agent_skill_root(name), force=force))
        return installed
    return copy_skills(agent_skill_root(normalized), force=force)


def install_project_skills(kind: str = "claude", cwd: Path | None = None, force: bool = False) -> list[Path]:
    return copy_skills(project_skill_root(kind, cwd=cwd), force=force)


def agent_skill_root(agent: str) -> Path:
    normalized = agent.lower()
    if normalized == "codex":
        return codex_skill_root()
    if normalized == "claude":
        return claude_skill_root()
    raise ValueError(f"unsupported agent {agent!r}; expected codex, claude, or all")


def copy_skill(destination: Path, force: bool = False, skill_name: str = SKILL_NAME) -> Path:
    destination = destination.expanduser()
    source = resources.files("oe_cli") / "skills" / skill_name

    if destination.exists():
        if not force:
            raise FileExistsError(f"{destination} already exists. Re-run with --force to replace it.")
        if destination.is_dir():
            shutil.rmtree(destination)
        else:
            destination.unlink()

    destination.parent.mkdir(parents=True, exist_ok=True)
    with resources.as_file(source) as source_path:
        shutil.copytree(source_path, destination)
    return destination


def copy_skills(destination_root: Path, force: bool = False) -> list[Path]:
    destination_root = destination_root.expanduser()
    return [
        copy_skill(destination_root / skill_name, force=force, skill_name=skill_name)
        for skill_name in SKILL_NAMES
    ]


def parse_skills_option(args: list[str]) -> str:
    """Parse trailing `--skills[=kind]` args of `oe install`."""
    if not args:
        raise ValueError("nothing to install; use --skills or --skills=agents")
    kind: str | None = None
    for arg in args:
        if arg == "--skills":
            kind = "claude"
        elif arg.startswith("--skills="):
            kind = arg.split("=", 1)[1]
        else:
            raise ValueError(f"unknown install option: {arg}")
    if kind is None:
        raise ValueError("nothing to install; use --skills or --skills=agents")
    return kind
