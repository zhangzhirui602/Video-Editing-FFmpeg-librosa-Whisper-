"""歌词识别模块：使用 Whisper 识别音频歌词并生成 SRT 字幕文件。"""

import os
import shutil
import subprocess
from pathlib import Path


def _srt_time_to_ms(ts: str) -> int:
    """将 SRT 时间戳（HH:MM:SS,mmm）转换为毫秒。"""
    hh_mm_ss, ms = ts.split(",")
    hh, mm, ss = hh_mm_ss.split(":")
    return ((int(hh) * 60 + int(mm)) * 60 + int(ss)) * 1000 + int(ms)


def _ms_to_srt_time(total_ms: int) -> str:
    """将毫秒转换为 SRT 时间戳（HH:MM:SS,mmm）。"""
    total_ms = max(0, total_ms)
    ms = total_ms % 1000
    total_sec = total_ms // 1000
    ss = total_sec % 60
    total_min = total_sec // 60
    mm = total_min % 60
    hh = total_min // 60
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"


def _split_words(text: str) -> list[str]:
    """将文本按词拆分为逐词字幕。"""
    merged = " ".join(line.strip() for line in text.splitlines() if line.strip())
    if not merged:
        return []

    return [word for word in merged.split() if word]


def _normalize_srt_word_by_word(srt_path: str) -> None:
    """将字幕按词拆分，并在原时间段内按词长度重新分配每个词的显示时长。"""
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        return

    blocks = content.replace("\r\n", "\n").split("\n\n")
    parsed_entries: list[tuple[int, int, str]] = []

    for block in blocks:
        lines = [line for line in block.split("\n") if line.strip()]
        if not lines:
            continue

        time_index = -1
        for i, line in enumerate(lines):
            if "-->" in line:
                time_index = i
                break
        if time_index < 0:
            continue

        start_ts, end_ts = [part.strip() for part in lines[time_index].split("-->", maxsplit=1)]
        text = "\n".join(lines[time_index + 1:]).strip()
        if not text:
            continue

        start_ms = _srt_time_to_ms(start_ts)
        end_ms = _srt_time_to_ms(end_ts)
        if end_ms <= start_ms:
            continue

        parsed_entries.append((start_ms, end_ms, text))

    if not parsed_entries:
        return

    new_entries: list[tuple[int, int, str]] = []

    for start_ms, end_ms, text in parsed_entries:
        words = _split_words(text)
        if len(words) <= 1:
            new_entries.append((start_ms, end_ms, text.replace("\n", " ").strip()))
            continue

        duration = end_ms - start_ms
        weights = [max(len(word), 1) for word in words]
        total_weight = sum(weights)

        cursor = start_ms
        for idx, word in enumerate(words):
            if idx == len(words) - 1:
                seg_end = end_ms
            else:
                reserved = len(words) - idx - 1
                proposed = cursor + int(duration * weights[idx] / total_weight)
                max_end = end_ms - reserved
                seg_end = max(cursor + 1, min(proposed, max_end))

            new_entries.append((cursor, seg_end, word))
            cursor = seg_end

    output_lines: list[str] = []
    for index, (start_ms, end_ms, text) in enumerate(new_entries, start=1):
        output_lines.append(str(index))
        output_lines.append(f"{_ms_to_srt_time(start_ms)} --> {_ms_to_srt_time(end_ms)}")
        output_lines.append(text)
        output_lines.append("")

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines).rstrip() + "\n")


def ensure_srt(
    audio_path: str,
    srt_path: str,
    whisper_model: str,
    language: str,
    word_by_word_subtitle: bool,
    temp_dir: str,
) -> str:
    """
    确保 SRT 字幕文件存在。如果不存在则调用 whisper 命令行识别生成。

    参数:
        audio_path: 音频文件路径
        srt_path: 期望的 SRT 文件路径（与音频同名，后缀为 .srt）
        whisper_model: Whisper 模型大小（tiny/base/small/medium/large）
        language: 音频语言（如 Swedish、English、Chinese 等）
        word_by_word_subtitle: 是否将歌词拆分为逐词显示
        temp_dir: 临时目录（用于保存处理后的字幕副本）

    返回:
        SRT 文件路径
    """
    if os.path.isfile(srt_path):
        print(f"已找到字幕文件：{srt_path}")
    else:
        # 确保输出目录存在
        output_dir = os.path.dirname(srt_path)
        os.makedirs(output_dir, exist_ok=True)

        print(f"未找到字幕文件，正在使用 Whisper ({whisper_model}) 识别歌词...")
        subprocess.run(
            [
                "whisper", audio_path,
                "--model", whisper_model,
                "--language", language,
                "--output_dir", output_dir,
                "--output_format", "srt",
            ],
            check=True,
        )

        # whisper 命令行输出文件名与音频同名
        if not os.path.isfile(srt_path):
            print(f"[错误] Whisper 识别完成但未找到预期的字幕文件：{srt_path}")
            raise FileNotFoundError(srt_path)

        print(f"歌词识别完成，已保存到：{srt_path}")

    if word_by_word_subtitle:
        temp_sub_dir = Path(temp_dir) / "subtitles"
        temp_sub_dir.mkdir(parents=True, exist_ok=True)

        processed_srt_path = temp_sub_dir / f"{Path(srt_path).stem}.word_by_word.srt"
        shutil.copyfile(srt_path, processed_srt_path)
        _normalize_srt_word_by_word(str(processed_srt_path))
        print(f"字幕已重排为逐词显示（word by word）：{processed_srt_path}")
        return str(processed_srt_path)

    print("已关闭逐词字幕，保留原始字幕分段")
    return srt_path
