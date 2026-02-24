"""主流程编排模块：串联歌词识别、节拍检测、视频裁剪、拼接、字幕烧录。"""

from typing import Callable, Optional

from src.config import load_config
from src.transcriber import ensure_srt
from src.beat_detector import detect_beats
from src.video_processor import cut_segments, concat_with_audio
from src.subtitle import burn_subtitles


# 进度回调类型：(stage_id, message, percent)
ProgressCallback = Callable[[str, str, int], None]


def _default_progress(stage: str, message: str, percent: int) -> None:
    """默认进度回调：直接 print（CLI 模式）。"""
    print(f"[{stage}] {message} ({percent}%)")


def run(on_progress: Optional[ProgressCallback] = None) -> None:
    """执行完整的视频编辑流程（从 .env 加载配置）。"""
    cfg = load_config()
    run_with_config(cfg, on_progress)


def run_with_config(
    cfg: dict,
    on_progress: Optional[ProgressCallback] = None,
) -> str:
    """
    使用给定配置字典执行完整的视频编辑流程。

    参数:
        cfg: 配置字典（与 load_config() 返回格式一致）
        on_progress: 可选的进度回调函数

    返回:
        最终输出视频的文件路径
    """
    report = on_progress or _default_progress

    # ===== 第一步：确保字幕文件存在 =====
    report("whisper", "正在检查字幕文件...", 0)
    cfg["srt_path"] = ensure_srt(
        cfg["audio_path"],
        cfg["srt_path"],
        cfg["whisper_model"],
        cfg["language"],
    )
    report("whisper", "字幕文件已就绪", 100)

    # ===== 第二步：检测节拍 =====
    report("beat", "正在分析音频节拍...", 0)
    cut_times = detect_beats(
        cfg["audio_path"],
        cfg["total_duration"],
        cfg["beats_per_cut"],
    )
    report("beat", f"检测到 {len(cut_times) - 1} 个切换点", 100)

    # ===== 第三步：按节拍裁剪视频片段 =====
    total_segments = len(cut_times) - 1
    report("ffmpeg", f"开始裁剪 {total_segments} 个视频片段...", 0)

    segment_files = cut_segments(
        cut_times,
        cfg["video_clips"],
        cfg["temp_dir"],
        cfg["video_width"],
        cfg["video_height"],
        cfg["fps"],
        on_segment_progress=lambda i, n: report(
            "ffmpeg",
            f"正在裁剪第 {i+1}/{n} 段...",
            int((i + 1) / n * 60),  # 裁剪占 ffmpeg 阶段的 0-60%
        ),
    )
    report("ffmpeg", "视频片段裁剪完成", 60)

    # ===== 第四步：拼接视频并合入音频 =====
    report("ffmpeg", "正在拼接视频并合入音频...", 65)
    concat_with_audio(
        segment_files,
        cfg["audio_path"],
        cfg["total_duration"],
        cfg["temp_dir"],
        cfg["output_no_sub"],
    )
    report("ffmpeg", "视频拼接完成", 85)

    # ===== 第五步：烧录字幕 =====
    report("ffmpeg", "正在烧录字幕...", 90)
    burn_subtitles(
        cfg["output_no_sub"],
        cfg["final_output"],
        cfg["srt_path"],
        cfg["font_size"],
        cfg["font_color"],
        cfg["outline_color"],
    )
    report("ffmpeg", "字幕烧录完成", 100)

    report("finalize", f"视频生成完成：{cfg['final_output']}", 100)
    return cfg["final_output"]
