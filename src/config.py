"""配置模块：从 .env 文件加载并校验所有配置项。"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import librosa


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


def _to_bool(value: str | None, default: bool) -> bool:
    """将环境变量字符串转换为布尔值。"""
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _pick_unique_audio(song_dir: Path) -> str:
    """从 song 目录中读取唯一音频文件；多于一个时提示用户保留唯一音频。"""
    exts = {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"}
    if not song_dir.is_dir():
        print(f"[错误] 未找到音频目录：{song_dir}")
        sys.exit(1)

    files = sorted(
        p for p in song_dir.iterdir()
        if p.is_file() and p.suffix.lower() in exts
    )
    if not files:
        print(f"[错误] 音频目录中没有可用音频文件：{song_dir}")
        sys.exit(1)

    if len(files) > 1:
        names = ", ".join(p.name for p in files)
        print(f"[错误] song 目录中存在多个音频文件，请只保留一个：{song_dir}")
        print(f"       当前文件：{names}")
        sys.exit(1)

    return str(files[0].resolve())


def _resolve_video_dir(content_root: Path, value: str | None) -> str:
    """解析视频素材目录，默认使用 raw_materials/videos。"""
    if value:
        return _resolve(value, content_root)

    return str((content_root / "raw_materials" / "videos").resolve())


def _resolve_total_duration(audio_path: str, value: str | None) -> float:
    """解析时长，未配置时从音频文件自动计算。"""
    if value:
        return float(value)
    return float(librosa.get_duration(path=audio_path))


def load_config(project_dir: Path | None = None, verbose: bool = True, require_videos: bool = True) -> dict:
    """加载 .env 配置并返回配置字典。"""
    # 项目根目录（src 的上一级）
    root = Path(__file__).resolve().parent.parent
    env_path = root / ".env"
    load_dotenv(env_path)
    content_root = project_dir if project_dir else root

    # 音频：项目模式下始终自动发现 song 目录下的唯一音频；
    # 无项目时才读取 .env 中的 AUDIO_PATH 作为后备
    song_dir = content_root / "raw_materials" / "song"
    if project_dir is not None:
        audio_path = _pick_unique_audio(song_dir)
    else:
        audio_env = os.getenv("AUDIO_PATH")
        if audio_env:
            audio_path = _check_file(
                _resolve(audio_env, content_root),
                "AUDIO_PATH",
            )
        else:
            audio_path = _pick_unique_audio(song_dir)

    # SRT 路径：原始歌词始终归档到 raw_materials/lyric/ 下
    srt_env = os.getenv("SRT_PATH")
    audio_stem = Path(audio_path).stem
    raw_lyric_srt_path = str(content_root / "raw_materials" / "lyric" / f"{audio_stem}.srt")
    srt_source_path = None
    if srt_env:
        resolved_srt = _resolve(srt_env, content_root)
        if project_dir is None:
            srt_path = resolved_srt
        else:
            srt_path = raw_lyric_srt_path
            if Path(resolved_srt).resolve() != Path(srt_path).resolve():
                srt_source_path = resolved_srt
    else:
        srt_path = raw_lyric_srt_path

    total_duration = _resolve_total_duration(audio_path, os.getenv("TOTAL_DURATION"))

    # Whisper 参数
    whisper_model = os.getenv("WHISPER_MODEL", "small")
    language = _require("LANGUAGE", os.getenv("LANGUAGE"))

    # 视频素材目录：扫描目录下所有视频文件
    video_dir = _resolve_video_dir(content_root, os.getenv("VIDEO_DIR"))
    video_exts = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
    if require_videos:
        if not os.path.isdir(video_dir):
            print(f"[错误] VIDEO_DIR 指定的目录不存在：{video_dir}")
            sys.exit(1)
        video_clips = sorted(
            str(p) for p in Path(video_dir).iterdir()
            if p.is_file() and p.suffix.lower() in video_exts
        )
        if not video_clips:
            print(f"[错误] VIDEO_DIR 目录下没有找到视频文件：{video_dir}")
            sys.exit(1)
        if verbose:
            print(f"找到 {len(video_clips)} 个视频素材")
    else:
        video_clips = (
            sorted(
                str(p) for p in Path(video_dir).iterdir()
                if p.is_file() and p.suffix.lower() in video_exts
            )
            if os.path.isdir(video_dir)
            else []
        )

    # 有默认值的配置项
    beats_per_cut = int(os.getenv("BEATS_PER_CUT", "2"))
    temp_dir = _resolve(os.getenv("TEMP_DIR", "output/temp"), content_root)
    output_no_sub = _resolve(os.getenv("OUTPUT_NO_SUB", "output/no_sub.mp4"), content_root)
    final_output = _resolve(os.getenv("FINAL_OUTPUT", "output/final.mp4"), content_root)

    video_width = int(os.getenv("VIDEO_WIDTH", "1080"))
    video_height = int(os.getenv("VIDEO_HEIGHT", "1920"))
    fps = int(os.getenv("FPS", "30"))

    font_size = int(os.getenv("FONT_SIZE", "18"))
    font_name = os.getenv("FONT_NAME", "Times New Roman")
    font_color = os.getenv("FONT_COLOR", "&H00FFFFFF")
    outline_color = os.getenv("OUTLINE_COLOR", "&H00000000")
    auto_fit_font_size = _to_bool(os.getenv("AUTO_FIT_FONT_SIZE"), True)
    word_by_word_subtitle = _to_bool(os.getenv("WORD_BY_WORD_SUBTITLE"), True)
    split_mode = os.getenv("SRT_SPLIT_MODE")
    if not split_mode:
        split_mode = "word" if word_by_word_subtitle else "none"
    split_mode = split_mode.strip().lower()
    if split_mode not in {"word", "comma", "sentence", "none"}:
        print(f"[错误] SRT_SPLIT_MODE 不支持：{split_mode}")
        sys.exit(1)

    return {
        "audio_path": audio_path,
        "srt_path": srt_path,
        "srt_source_path": srt_source_path,
        "total_duration": total_duration,
        "beats_per_cut": beats_per_cut,
        "temp_dir": temp_dir,
        "output_no_sub": output_no_sub,
        "final_output": final_output,
        "video_clips": video_clips,
        "video_width": video_width,
        "video_height": video_height,
        "fps": fps,
        "font_name": font_name,
        "font_size": font_size,
        "font_color": font_color,
        "outline_color": outline_color,
        "auto_fit_font_size": auto_fit_font_size,
        "word_by_word_subtitle": word_by_word_subtitle,
        "split_mode": split_mode,
        "whisper_model": whisper_model,
        "language": language,
    }
