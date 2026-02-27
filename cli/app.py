"""命令行入口：项目管理、SRT 生成、视频生成。"""

from __future__ import annotations

import shlex
import shutil
import sys
from pathlib import Path

import typer
from click import ClickException
from click.exceptions import Exit as ClickExit
from prompt_toolkit import prompt
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

from cli.i18n import t
from cli.project_manager import (
    create_project,
    delete_project,
    get_context,
    get_language,
    list_projects,
    set_language,
    switch_project,
)
from src.config import load_config
from src.pipeline import run
from src.transcriber import ensure_srt


app = typer.Typer(help="Beat video editor CLI")
project_app = typer.Typer(help="Project management")
app.add_typer(project_app, name="project")
console = Console()


def _root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def _lang() -> str:
    return get_language(_root_dir())


def _ctx():
    return get_context(_root_dir())


def _yield_matches(candidates: list[str], word: str):
    for item in candidates:
        if item.startswith(word):
            yield Completion(item, start_position=-len(word))


class ReplCompleter(Completer):
    """交互式 CLI 补全器，支持多参数任意顺序补全。"""

    ROOT_COMMANDS = ["status", "generate", "exit", "quit", "lang", "srt", "project"]
    SRT_OPTIONS = ["--split-mode"]
    SRT_SPLIT_VALUES = ["word", "comma", "sentence", "none"]
    PROJECT_SUBCMDS = ["list", "create", "switch", "delete"]

    def __init__(self, root: Path) -> None:
        self.root = root

    def _current_word(self, document: Document) -> str:
        return document.get_word_before_cursor(WORD=True)

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor
        word = self._current_word(document)
        stripped = text.lstrip()
        tokens = stripped.split()

        if not tokens:
            yield from _yield_matches(self.ROOT_COMMANDS, word)
            return

        cmd = tokens[0]

        if len(tokens) == 1 and not text.endswith(" "):
            yield from _yield_matches(self.ROOT_COMMANDS, word)
            return

        if cmd == "lang":
            yield from _yield_matches(["zh", "en"], word)
            return

        if cmd == "project":
            if len(tokens) <= 2 and not (len(tokens) == 2 and text.endswith(" ")):
                yield from _yield_matches(self.PROJECT_SUBCMDS, word)
                return

            if len(tokens) >= 2:
                subcmd = tokens[1]
                if subcmd in {"switch", "delete"}:
                    projects = list_projects(self.root)
                    yield from _yield_matches(projects, word)
                    return
                if subcmd == "create":
                    if word.startswith("--"):
                        yield from _yield_matches(["--switch"], word)
                    return

        if cmd == "srt":
            if word.startswith("--") or text.endswith(" "):
                yield from _yield_matches(self.SRT_OPTIONS, word)

            if len(tokens) >= 2:
                last_token = tokens[-1]
                prev_token = tokens[-2] if len(tokens) >= 2 else ""

                if last_token == "--split-mode":
                    yield from _yield_matches(self.SRT_SPLIT_VALUES, "")
                    return

                if prev_token == "--split-mode":
                    yield from _yield_matches(self.SRT_SPLIT_VALUES, word)
                    return

            return


def _pick_split_mode(value: str | None, lang: str) -> str:
    if value:
        mode = value.strip().lower()
        if mode not in {"word", "comma", "sentence", "none"}:
            raise typer.BadParameter("split mode must be one of: word/comma/sentence/none")
        return mode

    return Prompt.ask(
        t("select_split_mode", lang),
        choices=["word", "comma", "sentence", "none"],
        default="word",
    ).strip().lower()


def _subtitles_dir(project_dir: Path) -> Path:
    return project_dir / "output" / "temp" / "subtitles"


def _active_subtitle_path(project_dir: Path) -> Path:
    return _subtitles_dir(project_dir) / "active.srt"


def _set_active_subtitle(project_dir: Path, source_path: str) -> str:
    """覆盖保存当前项目唯一可用字幕，返回最终路径。"""
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


def _get_active_subtitle(project_dir: Path) -> str | None:
    """读取当前项目唯一字幕；若存在多份则自动清理并保留最新一份。"""
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


class _GenerateProgressView:
    """生成流程的动态进度条视图。"""

    STAGE_LABELS = {
        "srt": "字幕准备",
        "beat": "节拍分析",
        "cut": "视频切片",
        "concat": "拼接合成",
        "burn": "字幕烧录",
    }

    def __init__(self, progress: Progress) -> None:
        self.progress = progress
        self.overall_task = progress.add_task("总进度", total=5)
        self.cut_task = progress.add_task("切片进度", total=1, visible=False)

    def on_event(self, event: str, payload: dict) -> None:
        stage = str(payload.get("stage", ""))
        label = self.STAGE_LABELS.get(stage, stage)

        if event == "stage_start":
            self.progress.update(self.overall_task, description=f"总进度 · {label}")
            if stage == "cut":
                total = max(int(payload.get("total", 1)), 1)
                self.progress.reset(self.cut_task, total=total, completed=0, visible=True)
                self.progress.update(self.cut_task, description=f"切片进度 · 0/{total}")
            return

        if event == "stage_progress" and stage == "cut":
            done = int(payload.get("done", 0))
            total = max(int(payload.get("total", 1)), 1)
            self.progress.update(self.cut_task, completed=done, total=total)
            self.progress.update(self.cut_task, description=f"切片进度 · {done}/{total}")
            return

        if event == "stage_done":
            self.progress.advance(self.overall_task, 1)
            if stage == "cut":
                self.progress.update(self.cut_task, visible=False)
            if stage == "burn":
                self.progress.update(self.overall_task, description="总进度 · 完成")


def _run_interactive_shell() -> bool:
    """启动持续交互模式，直到用户输入 exit/quit。"""
    if not sys.stdin.isatty():
        return False

    console.print("[dim]Interactive mode: enter commands like 'status', 'project list', 'generate'.[/dim]")
    console.print("[dim]Type 'exit' or 'quit' to leave.[/dim]")

    cmd = typer.main.get_command(app)
    history_path = str(_root_dir() / "projects" / ".repl_history")
    history = FileHistory(history_path)

    while True:
        context = _ctx()
        try:
            raw = prompt(
                f"{context.current_project} > ",
                completer=ReplCompleter(context.root),
                complete_while_typing=True,
                history=history,
                auto_suggest=AutoSuggestFromHistory(),
            ).strip()
        except (EOFError, KeyboardInterrupt):
            console.print("[cyan]Bye.[/cyan]")
            return False

        if not raw:
            continue

        lowered = raw.lower()
        if lowered in {"exit", "quit"}:
            console.print("[cyan]Bye.[/cyan]")
            return False

        try:
            args = shlex.split(raw, posix=False)
        except ValueError as ex:
            console.print(f"[red]Parse error:[/red] {ex}")
            continue

        try:
            cmd.main(args=args, prog_name="beat-video-editor", standalone_mode=False)
            if args and args[0] == "lang":
                console.print("[dim]Language changed, restarting CLI session...[/dim]")
                return True
        except (ClickExit, EOFError, KeyboardInterrupt):
            console.print("[cyan]Bye.[/cyan]")
            return False
        except ClickException as ex:
            ex.show()
        except SystemExit as ex:
            if ex.code not in (0, None):
                console.print(f"[red]Command exited with code {ex.code}[/red]")
        except Exception as ex:
            console.print(f"[red]Error:[/red] {ex}")


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context) -> None:
    """显示当前项目与语言。"""
    if ctx.invoked_subcommand:
        return

    while True:
        lang = _lang()
        context = _ctx()
        console.print(
            Panel.fit(
                f"[bold cyan]{t('app_title', lang)}[/bold cyan]\n"
                f"{t('current_project', lang)}: [bold]{context.current_project}[/bold]\n"
                f"Language: [bold]{lang}[/bold]",
                border_style="cyan",
            )
        )
        console.print("Commands: project | srt | generate | lang | status")
        should_restart = _run_interactive_shell()
        if not should_restart:
            break


@app.command("status")
def status_command() -> None:
    """查看当前状态。"""
    lang = _lang()
    context = _ctx()
    console.print(
        Panel.fit(
            f"{t('current_project', lang)}: [bold]{context.current_project}[/bold]\n"
            f"Language: [bold]{lang}[/bold]\n"
            f"Project dir: [bold]{context.project_dir}[/bold]",
            border_style="green",
        )
    )


@app.command("lang")
def lang_command(language: str = typer.Argument(..., help="zh or en")) -> None:
    """切换 CLI 显示语言。"""
    root = _root_dir()
    lang = set_language(root, language)
    console.print(f"[green]{t('lang_set', lang)}[/green]: [bold]{lang}[/bold]")


@project_app.command("list")
def project_list_command() -> None:
    """列出项目。"""
    context = _ctx()
    names = list_projects(context.root)
    lang = _lang()

    table = Table(title="Projects")
    table.add_column("Name", style="cyan")
    table.add_column("Current", justify="center")
    for name in names:
        marker = "*" if name == context.current_project else ""
        table.add_row(name, marker)
    console.print(table)
    console.print(f"{t('current_project', lang)}: [bold]{context.current_project}[/bold]")


@project_app.command("create")
def project_create_command(
    name: str = typer.Argument(..., help="project name"),
    switch: bool = typer.Option(False, "--switch", help="switch to the new project"),
) -> None:
    """创建项目。"""
    lang = _lang()
    context = _ctx()
    try:
        path = create_project(context.root, name)
    except FileExistsError:
        console.print(f"[red]{t('project_exists', lang)}[/red]: {name}")
        raise typer.Exit(code=1)
    except ValueError:
        console.print("[red]Invalid project name[/red]")
        raise typer.Exit(code=1)

    if switch:
        switch_project(context.root, name)
        console.print(f"[green]{t('project_switched', lang)}[/green]: [bold]{name}[/bold]")

    console.print(f"[green]{t('project_created', lang)}[/green]: [bold]{path}[/bold]")


@project_app.command("delete")
def project_delete_command(
    name: str = typer.Argument(..., help="project name"),
    yes: bool = typer.Option(False, "--yes", "-y", help="skip confirmation"),
) -> None:
    """删除项目。"""
    lang = _lang()
    context = _ctx()

    if not yes:
        ok = Confirm.ask(f"Delete project [bold]{name}[/bold]?", default=False)
        if not ok:
            console.print(f"[yellow]{t('operation_cancelled', lang)}[/yellow]")
            raise typer.Exit(code=0)

    try:
        current = delete_project(context.root, name)
    except FileNotFoundError:
        console.print(f"[red]{t('project_not_found', lang)}[/red]: {name}")
        raise typer.Exit(code=1)
    except ValueError as ex:
        console.print(f"[red]{ex}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[green]{t('project_deleted', lang)}[/green]: [bold]{name}[/bold]")
    console.print(f"{t('current_project', lang)}: [bold]{current}[/bold]")


@project_app.command("switch")
def project_switch_command(name: str = typer.Argument(..., help="project name")) -> None:
    """切换项目。"""
    lang = _lang()
    context = _ctx()
    try:
        switch_project(context.root, name)
    except FileNotFoundError:
        console.print(f"[red]{t('project_not_found', lang)}[/red]: {name}")
        raise typer.Exit(code=1)

    console.print(f"[green]{t('project_switched', lang)}[/green]: [bold]{name}[/bold]")


@app.command("srt")
def srt_command(
    split_mode: str | None = typer.Option(None, "--split-mode", help="word/comma/sentence/none"),
) -> None:
    """基于当前项目音频生成 SRT。"""
    lang = _lang()
    context = _ctx()
    cfg = load_config(project_dir=context.project_dir, verbose=False, require_videos=False)
    mode = _pick_split_mode(split_mode, lang)
    active_srt = _get_active_subtitle(context.project_dir)
    source_hint = cfg.get("srt_source_path")
    if not source_hint and active_srt and not Path(cfg["srt_path"]).is_file():
        source_hint = active_srt

    srt_path = ensure_srt(
        cfg["audio_path"],
        cfg["srt_path"],
        cfg["whisper_model"],
        cfg["language"],
        mode,
        cfg["temp_dir"],
        source_hint,
        verbose=False,
    )
    active_path = _set_active_subtitle(context.project_dir, srt_path)
    console.print(f"[green]{t('srt_generated', lang)}[/green]: [bold]{active_path}[/bold]")


@app.command("generate")
def generate_command(
) -> None:
    """基于当前项目素材生成视频。"""
    lang = _lang()
    context = _ctx()
    cfg = load_config(project_dir=context.project_dir, verbose=False)

    active_srt = _get_active_subtitle(context.project_dir)
    if not active_srt:
        ok = Confirm.ask(t("ask_generate_srt", lang), default=True)
        if not ok:
            console.print(f"[yellow]{t('operation_cancelled', lang)}[/yellow]")
            raise typer.Exit(code=0)

        selected_mode = _pick_split_mode(None, lang)
        generated_srt = ensure_srt(
            cfg["audio_path"],
            cfg["srt_path"],
            cfg["whisper_model"],
            cfg["language"],
            selected_mode,
            cfg["temp_dir"],
            cfg.get("srt_source_path"),
            verbose=False,
        )
        active_srt = _set_active_subtitle(context.project_dir, generated_srt)

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        reporter = _GenerateProgressView(progress)
        run(
            project_dir=context.project_dir,
            prepared_srt_path=active_srt,
            progress_callback=reporter.on_event,
            quiet=True,
        )
    console.print(f"[green]{t('generate_done', lang)}[/green]: [bold]{cfg['final_output']}[/bold]")
