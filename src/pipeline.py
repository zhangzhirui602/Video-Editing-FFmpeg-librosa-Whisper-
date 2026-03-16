"""主流程编排模块：串联歌词识别、节拍检测、视频裁剪、拼接、字幕烧录。"""

from pathlib import Path
from typing import Any, Callable

from src.config import load_config
from src.transcriber import ensure_srt
from src.beat_detector import detect_beats
from src.video_processor import cut_segments, concat_with_audio
from src.subtitle import burn_subtitles


PipelineProgressCallback = Callable[[str, dict[str, Any]], None]


def _emit(progress_callback: PipelineProgressCallback | None, event: str, **payload: Any) -> None:
    if progress_callback:
        progress_callback(event, payload)


def run(
    project_dir: Path | None = None,
    split_mode_override: str | None = None,
    prepared_srt_path: str | None = None,
    progress_callback: PipelineProgressCallback | None = None,
    quiet: bool = False,
) -> None:
    """执行完整的视频编辑流程。"""
    # 第一步：加载配置
    cfg = load_config(project_dir=project_dir, verbose=not quiet)
    if split_mode_override:
        cfg["split_mode"] = split_mode_override

    # 第二步：确保字幕文件存在（不存在则用 Whisper 识别）
    _emit(progress_callback, "stage_start", stage="srt")
    if prepared_srt_path:
        cfg["srt_path"] = prepared_srt_path
    else:
        cfg["srt_path"] = ensure_srt(
            cfg["audio_path"],
            cfg["srt_path"],
            cfg["whisper_model"],
            cfg["language"],
            cfg["split_mode"],
            cfg["temp_dir"],
            cfg.get("srt_source_path"),
            verbose=not quiet,
        )
    _emit(progress_callback, "stage_done", stage="srt")

    # 第三步：检测节拍，获取切换时间点
    _emit(progress_callback, "stage_start", stage="beat")
    cut_times = detect_beats(
        cfg["audio_path"],
        cfg["total_duration"],
        cfg["beats_per_cut"],
        verbose=not quiet,
    )
    _emit(progress_callback, "stage_done", stage="beat")

    # 第四步：按节拍裁剪视频片段
    cut_total = max(len(cut_times) - 1, 0)
    _emit(progress_callback, "stage_start", stage="cut", total=cut_total)

    def _on_cut_progress(done: int, total: int) -> None:
        _emit(progress_callback, "stage_progress", stage="cut", done=done, total=total)

    segment_files = cut_segments(
        cut_times,
        cfg["video_clips"],
        cfg["temp_dir"],
        cfg["video_width"],
        cfg["video_height"],
        cfg["fps"],
        progress_callback=_on_cut_progress if progress_callback else None,
        verbose=not quiet,
    )
    _emit(progress_callback, "stage_done", stage="cut")

    # 第五步：拼接视频并合入音频
    _emit(progress_callback, "stage_start", stage="concat")
    concat_with_audio(
        segment_files,
        cfg["audio_path"],
        cfg["total_duration"],
        cfg["temp_dir"],
        cfg["output_no_sub"],
        verbose=not quiet,
    )
    _emit(progress_callback, "stage_done", stage="concat")

    # 第六步：烧录字幕
    _emit(progress_callback, "stage_start", stage="burn")
    burn_subtitles(
        cfg["output_no_sub"],
        cfg["final_output"],
        cfg["srt_path"],
        cfg["video_width"],
        cfg["video_height"],
        cfg["font_name"],
        cfg["font_size"],
        cfg["font_color"],
        cfg["outline_color"],
        cfg["auto_fit_font_size"],
        verbose=not quiet,
    )
    _emit(progress_callback, "stage_done", stage="burn")
