"""MCP Server：将视频编辑工具包装为 MCP 工具，供 AI 客户端调用。"""

from __future__ import annotations

import shutil
import threading
import time
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from cli.project_manager import (
    create_project as _create_project,
    delete_project as _delete_project,
    get_context,
    list_projects as _list_projects,
    switch_project as _switch_project,
)
from src.config import load_config
from src.pipeline import run as _run
from src.transcriber import ensure_srt

mcp = FastMCP("video-editor")

# ---------------------------------------------------------------------------
# 后台任务状态追踪
# ---------------------------------------------------------------------------

_job_lock = threading.Lock()
_job_status: dict = {
    "running": False,
    "project": None,
    "started_at": None,
    "done": False,
    "result": None,
    "error": None,
}


# ---------------------------------------------------------------------------
# Internal helpers（源自 cli/app.py，保持与 CLI 一致的字幕管理策略）
# ---------------------------------------------------------------------------

def _root() -> Path:
    """项目根目录：server.py 所在目录。"""
    return Path(__file__).resolve().parent


def _subtitles_dir(project_dir: Path) -> Path:
    return project_dir / "output" / "temp" / "subtitles"


def _active_subtitle_path(project_dir: Path) -> Path:
    return _subtitles_dir(project_dir) / "active.srt"


def _get_active_subtitle(project_dir: Path) -> str | None:
    """返回当前激活字幕路径；不存在时返回 None。"""
    subtitles_dir = _subtitles_dir(project_dir)
    if not subtitles_dir.is_dir():
        return None

    files = sorted(
        subtitles_dir.glob("*.srt"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not files:
        return None

    latest = files[0]
    active = _active_subtitle_path(project_dir)
    if latest.resolve() != active.resolve():
        shutil.copyfile(latest, active)

    for p in subtitles_dir.glob("*.srt"):
        if p.resolve() != active.resolve() and p.exists():
            p.unlink()

    return str(active)


def _set_active_subtitle(project_dir: Path, source_path: str) -> str:
    """将 source_path 的 SRT 覆盖保存为当前项目唯一激活字幕，返回最终路径。"""
    subtitles_dir = _subtitles_dir(project_dir)
    subtitles_dir.mkdir(parents=True, exist_ok=True)
    target = _active_subtitle_path(project_dir)

    with open(source_path, "rb") as f:
        data = f.read()

    for p in subtitles_dir.glob("*.srt"):
        if p.exists():
            p.unlink()

    with open(target, "wb") as f:
        f.write(data)

    return str(target)


# ---------------------------------------------------------------------------
# MCP 工具
# ---------------------------------------------------------------------------

@mcp.tool()
def list_projects() -> str:
    """列出所有项目，并标注当前激活项目（以 [active] 标记）。"""
    root = _root()
    ctx = get_context(root)
    names = _list_projects(root)

    if not names:
        return "(no projects)"

    lines = [
        f"{name} [active]" if name == ctx.current_project else name
        for name in names
    ]
    return "\n".join(lines)


@mcp.tool()
def create_project(name: str, switch: bool = False) -> str:
    """创建新项目。

    Args:
        name: 项目名称（不能含特殊字符 \\ / : * ? \" < > |）
        switch: 创建后是否立即切换到该项目（默认 False）
    """
    root = _root()
    try:
        path = _create_project(root, name)
    except FileExistsError:
        return f"Error: project '{name}' already exists."
    except ValueError as ex:
        return f"Error: {ex}"

    if switch:
        _switch_project(root, name)
        return f"Created and switched to project '{name}': {path}"

    return f"Created project '{name}': {path}"


@mcp.tool()
def switch_project(name: str) -> str:
    """切换当前项目。

    Args:
        name: 要切换到的项目名称
    """
    root = _root()
    try:
        _switch_project(root, name)
    except FileNotFoundError:
        return f"Error: project '{name}' not found."

    return f"Switched to project '{name}'."


@mcp.tool()
def delete_project(name: str) -> str:
    """删除项目及其所有内容（不能删除 default 项目）。

    Args:
        name: 要删除的项目名称
    """
    root = _root()
    try:
        current = _delete_project(root, name)
    except FileNotFoundError:
        return f"Error: project '{name}' not found."
    except ValueError as ex:
        return f"Error: {ex}"

    return f"Deleted project '{name}'. Current project is now '{current}'."


@mcp.tool()
def get_status() -> str:
    """查看当前项目状态，包括：项目名、目录、音频路径、语言、split_mode、字幕路径和输出路径。"""
    root = _root()
    ctx = get_context(root)

    try:
        cfg = load_config(project_dir=ctx.project_dir, verbose=False, require_videos=False)
        audio_path = cfg.get("audio_path", "(not found)")
        language = cfg.get("language", "(not set)")
        split_mode = cfg.get("split_mode", "(not set)")
        srt_path = cfg.get("srt_path", "(not set)")
        final_output = cfg.get("final_output", "(not set)")
    except SystemExit:
        # load_config 在缺少必填项（如 LANGUAGE）时会调用 sys.exit；此处捕获并友好提示
        audio_path = "(config error — check .env)"
        language = "(not set)"
        split_mode = "(not set)"
        srt_path = "(not set)"
        final_output = "(not set)"

    active_srt = _get_active_subtitle(ctx.project_dir)

    return (
        f"Current project : {ctx.current_project}\n"
        f"Project dir     : {ctx.project_dir}\n"
        f"Audio           : {audio_path}\n"
        f"Language        : {language}\n"
        f"Split mode      : {split_mode}\n"
        f"Lyric SRT       : {srt_path}\n"
        f"Active SRT      : {active_srt or '(none)'}\n"
        f"Final output    : {final_output}"
    )


@mcp.tool()
def generate_srt(split_mode: str = "word") -> str:
    """为当前项目的音频生成 SRT 字幕文件。

    Args:
        split_mode: 字幕拆分方式，可选 word（逐词）/ comma（逗号）/ sentence（句子）/ none（整段），默认 word
    """
    if split_mode not in {"word", "comma", "sentence", "none"}:
        return "Error: split_mode must be one of: word, comma, sentence, none."

    root = _root()
    ctx = get_context(root)
    cfg = load_config(project_dir=ctx.project_dir, verbose=False, require_videos=False)

    srt_path = ensure_srt(
        cfg["audio_path"],
        cfg["srt_path"],
        cfg["whisper_model"],
        cfg["language"],
        split_mode,
        cfg["temp_dir"],
        srt_source_path=None,
        verbose=False,
    )

    active_path = _set_active_subtitle(ctx.project_dir, srt_path)
    return f"SRT generated: {active_path}"


@mcp.tool()
def generate_video() -> str:
    """基于当前项目的素材（音频 + 视频 + 字幕）在后台生成最终视频。

    立即返回，生成在后台运行。请用 get_video_status 查询进度和结果。
    若尚无激活字幕，将先以默认 split_mode（word）自动生成字幕再继续。
    """
    with _job_lock:
        if _job_status["running"]:
            return (
                f"A video generation job is already running for project "
                f"'{_job_status['project']}'. Use get_video_status to check progress."
            )

    root = _root()
    ctx = get_context(root)

    def _worker() -> None:
        with _job_lock:
            _job_status.update({
                "running": True,
                "project": ctx.current_project,
                "started_at": time.time(),
                "done": False,
                "result": None,
                "error": None,
            })
        try:
            cfg = load_config(project_dir=ctx.project_dir, verbose=False)
            active_srt = _get_active_subtitle(ctx.project_dir)
            if not active_srt:
                srt_path = ensure_srt(
                    cfg["audio_path"],
                    cfg["srt_path"],
                    cfg["whisper_model"],
                    cfg["language"],
                    cfg["split_mode"],
                    cfg["temp_dir"],
                    cfg.get("srt_source_path"),
                    verbose=False,
                )
                active_srt = _set_active_subtitle(ctx.project_dir, srt_path)
            _run(
                project_dir=ctx.project_dir,
                prepared_srt_path=active_srt,
                quiet=True,
            )
            with _job_lock:
                _job_status.update({"running": False, "done": True, "result": cfg["final_output"]})
        except Exception as exc:  # noqa: BLE001
            with _job_lock:
                _job_status.update({"running": False, "done": True, "error": str(exc)})

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    return (
        f"Video generation started for project '{ctx.current_project}'. "
        "This usually takes 3–10 minutes. Use get_video_status to check progress."
    )


@mcp.tool()
def get_video_status() -> str:
    """查询后台视频生成任务的当前状态和结果。"""
    with _job_lock:
        status = dict(_job_status)

    if not status["project"]:
        return "No video generation job has been started yet."

    if status["running"]:
        elapsed = int(time.time() - (status["started_at"] or time.time()))
        minutes, seconds = divmod(elapsed, 60)
        return (
            f"Running — project: {status['project']}, "
            f"elapsed: {minutes}m {seconds}s. Please check again in a moment."
        )

    if status["error"]:
        return f"Failed — project: {status['project']}\nError: {status['error']}"

    return f"Done — video saved to: {status['result']}"


if __name__ == "__main__":
    import os
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)  # type: ignore[arg-type]
