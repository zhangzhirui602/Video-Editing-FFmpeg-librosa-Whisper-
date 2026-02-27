"""项目管理：创建、删除、切换当前项目，以及路径解析。"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path


DEFAULT_PROJECT_NAME = "default"
STATE_FILE_NAME = ".state.json"


@dataclass(frozen=True)
class ProjectContext:
    """当前项目上下文。"""

    root: Path
    projects_root: Path
    current_project: str
    project_dir: Path


def _state_file(projects_root: Path) -> Path:
    return projects_root / STATE_FILE_NAME


def _default_state() -> dict:
    return {
        "current_project": DEFAULT_PROJECT_NAME,
        "language": "zh",
    }


def _load_state(projects_root: Path) -> dict:
    state_path = _state_file(projects_root)
    if not state_path.exists():
        return _default_state()

    with state_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    state = _default_state()
    state.update(data)
    return state


def _save_state(projects_root: Path, state: dict) -> None:
    projects_root.mkdir(parents=True, exist_ok=True)
    with _state_file(projects_root).open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _ensure_project_structure(project_dir: Path) -> None:
    (project_dir / "raw_materials" / "lyric").mkdir(parents=True, exist_ok=True)
    (project_dir / "raw_materials" / "song").mkdir(parents=True, exist_ok=True)
    (project_dir / "raw_materials" / "videos").mkdir(parents=True, exist_ok=True)
    (project_dir / "output" / "temp" / "subtitles").mkdir(parents=True, exist_ok=True)


def _ensure_bootstrap(root: Path) -> None:
    projects_root = root / "projects"
    projects_root.mkdir(parents=True, exist_ok=True)

    state = _load_state(projects_root)
    default_project = projects_root / DEFAULT_PROJECT_NAME
    _ensure_project_structure(default_project)

    current_project = state.get("current_project", DEFAULT_PROJECT_NAME)
    current_dir = projects_root / current_project
    if not current_dir.exists():
        state["current_project"] = DEFAULT_PROJECT_NAME
        _save_state(projects_root, state)


def get_context(root: Path) -> ProjectContext:
    """读取当前项目上下文，不存在时自动初始化。"""
    _ensure_bootstrap(root)
    projects_root = root / "projects"
    state = _load_state(projects_root)
    current_project = state["current_project"]

    return ProjectContext(
        root=root,
        projects_root=projects_root,
        current_project=current_project,
        project_dir=projects_root / current_project,
    )


def get_language(root: Path) -> str:
    """读取当前界面语言。"""
    _ensure_bootstrap(root)
    state = _load_state(root / "projects")
    value = str(state.get("language", "zh")).lower()
    return "en" if value == "en" else "zh"


def set_language(root: Path, language: str) -> str:
    """设置界面语言，返回最终生效值。"""
    lang = language.lower()
    if lang not in {"zh", "en"}:
        raise ValueError("language must be zh or en")

    projects_root = root / "projects"
    _ensure_bootstrap(root)
    state = _load_state(projects_root)
    state["language"] = lang
    _save_state(projects_root, state)
    return lang


def list_projects(root: Path) -> list[str]:
    """列出所有项目名。"""
    _ensure_bootstrap(root)
    projects_root = root / "projects"
    names = []
    for p in sorted(projects_root.iterdir()):
        if not p.is_dir():
            continue
        names.append(p.name)
    return names


def create_project(root: Path, name: str) -> Path:
    """创建项目目录及标准结构。"""
    if not name or any(ch in name for ch in "\\/:*?\"<>|"):
        raise ValueError("invalid project name")

    projects_root = root / "projects"
    _ensure_bootstrap(root)
    target = projects_root / name
    if target.exists():
        raise FileExistsError(name)

    _ensure_project_structure(target)
    return target


def switch_project(root: Path, name: str) -> Path:
    """切换当前项目。"""
    projects_root = root / "projects"
    _ensure_bootstrap(root)
    target = projects_root / name
    if not target.is_dir():
        raise FileNotFoundError(name)

    state = _load_state(projects_root)
    state["current_project"] = name
    _save_state(projects_root, state)
    return target


def delete_project(root: Path, name: str) -> str:
    """删除项目目录及内容，返回新的当前项目名。"""
    projects_root = root / "projects"
    _ensure_bootstrap(root)

    if name == DEFAULT_PROJECT_NAME:
        raise ValueError("default project cannot be deleted")

    target = projects_root / name
    if not target.is_dir():
        raise FileNotFoundError(name)

    shutil.rmtree(target)

    state = _load_state(projects_root)
    if state.get("current_project") == name:
        state["current_project"] = DEFAULT_PROJECT_NAME
        _save_state(projects_root, state)

    return state.get("current_project", DEFAULT_PROJECT_NAME)
