"""歌词识别模块：使用 Whisper 识别音频歌词并生成 SRT 字幕文件。"""

import os
import re
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


def _split_by_comma(text: str) -> list[str]:
    """按逗号分割文本。"""
    merged = " ".join(line.strip() for line in text.splitlines() if line.strip())
    if not merged:
        return []

    parts = re.split(r"[，,]+", merged)
    return [part.strip() for part in parts if part.strip()]


def _split_by_sentence(text: str) -> list[str]:
    """按句子终止符分割文本。"""
    merged = " ".join(line.strip() for line in text.splitlines() if line.strip())
    if not merged:
        return []

    parts = re.split(r"(?<=[。！？!?\.])\s*", merged)
    return [part.strip() for part in parts if part.strip()]


def _split_text(text: str, split_mode: str) -> list[str]:
    """按指定模式切分字幕文本。"""
    if split_mode == "word":
        return _split_words(text)
    if split_mode == "comma":
        return _split_by_comma(text)
    if split_mode == "sentence":
        return _split_by_sentence(text)
    return [" ".join(line.strip() for line in text.splitlines() if line.strip())]


def _find_generated_srt(audio_path: str, output_dir: str) -> str | None:
    """在输出目录中查找 Whisper 生成的 SRT（兼容不同命名规则）。"""
    out_dir = Path(output_dir)
    if not out_dir.is_dir():
        return None

    all_srts = sorted(
        [p for p in out_dir.iterdir() if p.is_file() and p.suffix.lower() == ".srt"],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not all_srts:
        return None

    audio_name = Path(audio_path).name.lower()
    audio_stem = Path(audio_path).stem.lower()

    for p in all_srts:
        if p.stem.lower() == audio_stem:
            return str(p)

    for p in all_srts:
        stem = p.stem.lower()
        if stem == audio_name or stem.startswith(audio_stem):
            return str(p)

    if len(all_srts) == 1:
        return str(all_srts[0])

    return None


def _transcribe_with_whisper(
    audio_path: str,
    whisper_model: str,
    language: str,
) -> dict:
    """调用 Whisper 并返回原始结果（含逐词时间戳）。"""
    import whisper

    model = whisper.load_model(whisper_model)
    return model.transcribe(
        audio_path,
        language=language,
        fp16=False,
        condition_on_previous_text=False,
        word_timestamps=True,
        temperature=0,
    )


def _write_segment_srt(result: dict, out_path: str) -> None:
    """将 Whisper 结果写为句子级 SRT，片段起始时间用第一个单词的真实时间替换。"""
    lines: list[str] = []
    index = 1
    for seg in result.get("segments", []):
        words = seg.get("words", [])
        start_s = float(words[0]["start"]) if words else float(seg["start"])
        end_s = float(words[-1]["end"]) if words else float(seg["end"])
        text = seg["text"].strip()
        if not text:
            continue
        start_ms = int(round(start_s * 1000))
        end_ms = max(start_ms + 1, int(round(end_s * 1000)))
        lines += [str(index), f"{_ms_to_srt_time(start_ms)} --> {_ms_to_srt_time(end_ms)}", text, ""]
        index += 1

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")


def _write_word_srt(result: dict, out_path: str) -> None:
    """将 Whisper 结果写为单词级 SRT，每个单词使用 Whisper 的真实时间戳。"""
    lines: list[str] = []
    index = 1
    all_words: list[dict] = []
    for seg in result.get("segments", []):
        all_words.extend(seg.get("words", []))

    for i, w in enumerate(all_words):
        word = w.get("word", "").strip()
        if not word:
            continue
        start_ms = int(round(float(w["start"]) * 1000))
        # 结束时间：用下一个单词的开始时间（减去缓冲），避免字幕在间隙持续显示
        if i + 1 < len(all_words):
            next_start_ms = int(round(float(all_words[i + 1]["start"]) * 1000))
            end_ms = max(start_ms + 1, min(int(round(float(w["end"]) * 1000)), next_start_ms - 80))
        else:
            end_ms = max(start_ms + 1, int(round(float(w["end"]) * 1000)))
        lines += [str(index), f"{_ms_to_srt_time(start_ms)} --> {_ms_to_srt_time(end_ms)}", word, ""]
        index += 1

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")


def _generate_srt_with_whisper_api(
    audio_path: str,
    whisper_model: str,
    language: str,
    output_dir: str,
) -> str:
    """通过 Whisper API 生成句子级 SRT，返回路径。"""
    result = _transcribe_with_whisper(audio_path, whisper_model, language)
    stem = Path(audio_path).stem
    out_path = str(Path(output_dir) / f"{stem}.srt")
    _write_segment_srt(result, out_path)
    return out_path


def _clamp_srt_gaps(srt_path: str, gap_buffer_ms: int = 80) -> None:
    """
    修复 Whisper 时间戳偏移问题：将每条字幕的结束时间限制到下一条开始时间之前
    gap_buffer_ms 毫秒处，避免字幕在静音段继续显示。
    """
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if not content:
        return

    blocks = content.replace("\r\n", "\n").split("\n\n")
    entries: list[tuple[int, int, str]] = []

    for block in blocks:
        lines = [l for l in block.split("\n") if l.strip()]
        if not lines:
            continue
        time_index = next((i for i, l in enumerate(lines) if "-->" in l), -1)
        if time_index < 0:
            continue
        start_ts, end_ts = [p.strip() for p in lines[time_index].split("-->", maxsplit=1)]
        text = "\n".join(lines[time_index + 1:]).strip()
        if not text:
            continue
        entries.append((_srt_time_to_ms(start_ts), _srt_time_to_ms(end_ts), text))

    if not entries:
        return

    clamped: list[tuple[int, int, str]] = []
    for i, (start_ms, end_ms, text) in enumerate(entries):
        if i + 1 < len(entries):
            next_start = entries[i + 1][0]
            max_end = max(start_ms + 1, next_start - gap_buffer_ms)
            end_ms = min(end_ms, max_end)
        clamped.append((start_ms, end_ms, text))

    output_lines: list[str] = []
    for index, (start_ms, end_ms, text) in enumerate(clamped, start=1):
        output_lines.append(str(index))
        output_lines.append(f"{_ms_to_srt_time(start_ms)} --> {_ms_to_srt_time(end_ms)}")
        output_lines.append(text)
        output_lines.append("")

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines).rstrip() + "\n")


def _normalize_srt_by_mode(srt_path: str, split_mode: str) -> None:
    """按模式拆分字幕，并在原时间段内按片段长度重新分配时长。"""
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
        parts = _split_text(text, split_mode)
        if len(parts) <= 1:
            new_entries.append((start_ms, end_ms, text.replace("\n", " ").strip()))
            continue

        duration = end_ms - start_ms
        weights = [max(len(part), 1) for part in parts]
        total_weight = sum(weights)

        cursor = start_ms
        for idx, part in enumerate(parts):
            if idx == len(parts) - 1:
                seg_end = end_ms
            else:
                reserved = len(parts) - idx - 1
                proposed = cursor + int(duration * weights[idx] / total_weight)
                max_end = end_ms - reserved
                seg_end = max(cursor + 1, min(proposed, max_end))

            new_entries.append((cursor, seg_end, part))
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
    split_mode: str,
    temp_dir: str,
    srt_source_path: str | None = None,
    verbose: bool = True,
) -> str:
    """
    确保 SRT 字幕文件存在。如果不存在则调用 whisper 命令行识别生成。

    参数:
        audio_path: 音频文件路径
        srt_path: 期望的 SRT 文件路径（与音频同名，后缀为 .srt）
        whisper_model: Whisper 模型大小（tiny/base/small/medium/large）
        language: 音频语言（如 Swedish、English、Chinese 等）
        split_mode: SRT 拆分方式（word/comma/sentence/none）
        temp_dir: 临时目录（用于保存处理后的字幕副本）
        srt_source_path: 可选的外部原始 SRT 路径，会先导入到 srt_path
        verbose: 是否输出处理日志

    返回:
        SRT 文件路径
    """
    if os.path.isfile(srt_path):
        if verbose:
            print(f"已找到字幕文件：{srt_path}")
        whisper_result = None  # 已有缓存，无 Whisper 结果
    elif srt_source_path and os.path.isfile(srt_source_path):
        output_dir = os.path.dirname(srt_path)
        os.makedirs(output_dir, exist_ok=True)
        shutil.copyfile(srt_source_path, srt_path)
        if verbose:
            print(f"已导入原始字幕到 lyric 目录：{srt_path}")
        whisper_result = None
    else:
        output_dir = os.path.dirname(srt_path)
        os.makedirs(output_dir, exist_ok=True)

        if verbose:
            print(f"未找到字幕文件，正在使用 Whisper ({whisper_model}) 识别歌词...")

        try:
            whisper_result = _transcribe_with_whisper(audio_path, whisper_model, language)
            _write_segment_srt(whisper_result, srt_path)
        except Exception as exc:
            if verbose:
                print(f"[警告] Whisper API 调用失败（{exc}），回退到命令行模式...")
            whisper_result = None
            command = [
                "whisper", audio_path,
                "--model", whisper_model,
                "--language", language,
                "--output_dir", output_dir,
                "--output_format", "srt",
            ]
            result = subprocess.run(command, check=False, capture_output=not verbose, text=True)
            if result.returncode != 0:
                message = (result.stderr or result.stdout or "whisper failed").strip()
                raise RuntimeError(message)

        if not os.path.isfile(srt_path):
            detected_srt = _find_generated_srt(audio_path, output_dir)
            if detected_srt:
                os.replace(detected_srt, srt_path)
            else:
                if verbose:
                    existing = sorted(str(p.name) for p in Path(output_dir).glob("*.srt"))
                    print(f"[错误] Whisper 识别完成但未找到预期字幕：{srt_path}")
                    print(f"[错误] {output_dir} 下现有 srt：{existing}")
                raise FileNotFoundError(srt_path)

        if verbose:
            print(f"歌词识别完成，已保存到：{srt_path}")

    normalized_mode = split_mode.strip().lower()
    if normalized_mode not in {"word", "comma", "sentence", "none"}:
        raise ValueError(f"unsupported split_mode: {split_mode}")

    temp_sub_dir = Path(temp_dir) / "subtitles"
    temp_sub_dir.mkdir(parents=True, exist_ok=True)
    processed_srt_path = temp_sub_dir / f"{Path(srt_path).stem}.{normalized_mode}.srt"

    if normalized_mode == "word" and whisper_result is not None:
        # 直接使用 Whisper 逐词时间戳写 SRT，无需比例估算
        _write_word_srt(whisper_result, str(processed_srt_path))
        if verbose:
            print(f"字幕已按逐词真实时间戳生成：{processed_srt_path}")
        return str(processed_srt_path)

    if normalized_mode != "none":
        shutil.copyfile(srt_path, processed_srt_path)
        _normalize_srt_by_mode(str(processed_srt_path), normalized_mode)
        _clamp_srt_gaps(str(processed_srt_path))
        if verbose:
            print(f"字幕已按模式重排（{normalized_mode}）：{processed_srt_path}")
        return str(processed_srt_path)

    if verbose:
        print("保留原始字幕分段（none）")
    _clamp_srt_gaps(srt_path)
    return srt_path
