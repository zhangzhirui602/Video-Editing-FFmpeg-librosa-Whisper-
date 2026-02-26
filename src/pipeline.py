"""主流程编排模块：串联歌词识别、节拍检测、视频裁剪、拼接、字幕烧录。"""

from src.config import load_config
from src.transcriber import ensure_srt
from src.beat_detector import detect_beats
from src.video_processor import cut_segments, concat_with_audio
from src.subtitle import burn_subtitles


def run() -> None:
    """执行完整的视频编辑流程。"""
    # 第一步：加载配置
    cfg = load_config()

    # 第二步：确保字幕文件存在（不存在则用 Whisper 识别）
    cfg["srt_path"] = ensure_srt(
        cfg["audio_path"],
        cfg["srt_path"],
        cfg["whisper_model"],
        cfg["language"],
        cfg["word_by_word_subtitle"],
        cfg["temp_dir"],
    )

    # 第三步：检测节拍，获取切换时间点
    cut_times = detect_beats(
        cfg["audio_path"],
        cfg["total_duration"],
        cfg["beats_per_cut"],
    )

    # 第四步：按节拍裁剪视频片段
    segment_files = cut_segments(
        cut_times,
        cfg["video_clips"],
        cfg["temp_dir"],
        cfg["video_width"],
        cfg["video_height"],
        cfg["fps"],
    )

    # 第五步：拼接视频并合入音频
    concat_with_audio(
        segment_files,
        cfg["audio_path"],
        cfg["total_duration"],
        cfg["temp_dir"],
        cfg["output_no_sub"],
    )

    # 第六步：烧录字幕
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
    )
