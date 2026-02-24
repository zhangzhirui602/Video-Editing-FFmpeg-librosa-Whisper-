"""配置模块：从 .env 文件加载并校验所有配置项。"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv


def _require(name: str, value: str | None) -> str:
    """校验必填项，缺失时给出中文提示并退出。"""
    if not value:
        print(f"[错误] 缺少必填配置项：{name}，请在 .env 文件中设置。")
        sys.exit(1)
    return value


def _check_file(path: str, name: str) -> str:
    """校验文件是否存在。"""
    if not os.path.isfile(path):
        print(f"[错误] {name} 指定的文件不存在：{path}")
        sys.exit(1)
    return path


def _resolve(path: str, root: Path) -> str:
    """将相对路径解析为基于项目根目录的绝对路径，绝对路径原样返回。"""
    p = Path(path)
    if not p.is_absolute():
        p = root / p
    return str(p.resolve())


def load_config() -> dict:
    """加载 .env 配置并返回配置字典。"""
    # 项目根目录（src 的上一级）
    root = Path(__file__).resolve().parent.parent
    env_path = root / ".env"
    load_dotenv(env_path)

    # 必填项（相对路径会基于项目根目录解析）
    audio_path = _check_file(
        _resolve(_require("AUDIO_PATH", os.getenv("AUDIO_PATH")), root),
        "AUDIO_PATH",
    )

    # SRT 路径：如果未配置，则自动根据音频文件名生成（放在 raw_materials/lyric/ 下）
    srt_env = os.getenv("SRT_PATH")
    if srt_env:
        srt_path = _resolve(srt_env, root)
    else:
        audio_stem = Path(audio_path).stem
        srt_path = str(root / "raw_materials" / "lyric" / f"{audio_stem}.srt")

    total_duration = float(
        _require("TOTAL_DURATION", os.getenv("TOTAL_DURATION"))
    )

    # Whisper 参数
    whisper_model = os.getenv("WHISPER_MODEL", "small")
    language = _require("LANGUAGE", os.getenv("LANGUAGE"))

    # 视频素材目录：扫描目录下所有视频文件
    video_dir = _resolve(
        os.getenv("VIDEO_DIR", "raw_materials/videos"), root
    )
    if not os.path.isdir(video_dir):
        print(f"[错误] VIDEO_DIR 指定的目录不存在：{video_dir}")
        sys.exit(1)

    video_exts = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
    video_clips = sorted(
        str(p) for p in Path(video_dir).iterdir()
        if p.is_file() and p.suffix.lower() in video_exts
    )
    if not video_clips:
        print(f"[错误] VIDEO_DIR 目录下没有找到视频文件：{video_dir}")
        sys.exit(1)
    print(f"找到 {len(video_clips)} 个视频素材")

    # 有默认值的配置项
    beats_per_cut = int(os.getenv("BEATS_PER_CUT", "2"))
    temp_dir = _resolve(os.getenv("TEMP_DIR", "output/temp"), root)
    output_no_sub = _resolve(os.getenv("OUTPUT_NO_SUB", "output/no_sub.mp4"), root)
    final_output = _resolve(os.getenv("FINAL_OUTPUT", "output/final.mp4"), root)

    video_width = int(os.getenv("VIDEO_WIDTH", "1080"))
    video_height = int(os.getenv("VIDEO_HEIGHT", "1920"))
    fps = int(os.getenv("FPS", "30"))

    font_size = int(os.getenv("FONT_SIZE", "18"))
    font_color = os.getenv("FONT_COLOR", "&H00FFFFFF")
    outline_color = os.getenv("OUTLINE_COLOR", "&H00000000")

    return {
        "audio_path": audio_path,
        "srt_path": srt_path,
        "total_duration": total_duration,
        "beats_per_cut": beats_per_cut,
        "temp_dir": temp_dir,
        "output_no_sub": output_no_sub,
        "final_output": final_output,
        "video_clips": video_clips,
        "video_width": video_width,
        "video_height": video_height,
        "fps": fps,
        "font_size": font_size,
        "font_color": font_color,
        "outline_color": outline_color,
        "whisper_model": whisper_model,
        "language": language,
    }
