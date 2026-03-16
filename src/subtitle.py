"""字幕烧录模块：将 SRT 字幕烧录到视频中。"""

import subprocess


def _iter_srt_text_lines(srt_path: str):
    """遍历 SRT 中每条字幕文本（合并为单行）。"""
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read().replace("\r\n", "\n").strip()

    if not content:
        return

    blocks = content.split("\n\n")
    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue

        time_index = -1
        for i, line in enumerate(lines):
            if "-->" in line:
                time_index = i
                break
        if time_index < 0:
            continue

        text = " ".join(lines[time_index + 1:]).strip()
        if text:
            yield text


def _estimate_text_units(text: str) -> float:
    """估算文本视觉宽度单位（用于字号计算，越大表示越宽）。"""
    total = 0.0
    for ch in text:
        if ch in "MW@#%&":
            total += 1.0
        elif ch.isupper():
            total += 0.78
        elif ch.islower():
            total += 0.62
        elif ch.isdigit():
            total += 0.62
        elif ch.isspace():
            total += 0.34
        else:
            total += 0.44
    return total


def _fit_font_size_for_single_line(srt_path: str, video_width: int, requested_size: int) -> int:
    """根据最长字幕估算单行可容纳字号，返回实际使用字号。"""
    max_units = 0.0
    for text in _iter_srt_text_lines(srt_path):
        max_units = max(max_units, _estimate_text_units(text))

    if max_units <= 0:
        return requested_size

    # 预留更保守的左右安全边距，避免首尾被裁切
    side_margin = max(int(video_width * 0.08), 64)
    available_width = max(video_width - side_margin * 2, 120)

    # 经验系数：单位宽度对应到字号像素，取保守值避免裁边
    estimated_size = int(available_width / (max_units * 0.9))

    # 限制最小字号，避免过小不可读；并且不超过用户请求字号
    return max(6, min(requested_size, estimated_size))


def burn_subtitles(
    input_path: str,
    output_path: str,
    srt_path: str,
    video_width: int,
    video_height: int,
    font_name: str,
    font_size: int,
    font_color: str,
    outline_color: str,
    auto_fit_font_size: bool,
    verbose: bool = True,
) -> None:
    """
    将字幕烧录到视频中。

    参数:
        input_path: 无字幕的输入视频路径
        output_path: 最终输出视频路径
        srt_path: SRT 字幕文件路径
        video_width: 输出视频宽度（用于自动估算单行字号）
        video_height: 输出视频高度（用于字幕渲染尺寸对齐）
        font_name: 字幕字体名称
        font_size: 字幕字号
        font_color: 字幕主颜色（ASS 格式）
        outline_color: 字幕描边颜色（ASS 格式）
        auto_fit_font_size: 是否自动缩小字号以尽量单行显示
    """
    if verbose:
        print("正在烧录字幕...")
    actual_font_size = font_size
    if auto_fit_font_size:
        actual_font_size = _fit_font_size_for_single_line(srt_path, video_width, font_size)
        if actual_font_size < font_size:
            if verbose:
                print(f"检测到字幕较长，字号自动从 {font_size} 调整为 {actual_font_size} 以尽量单行显示")
    else:
        if verbose:
            print(f"已关闭字号自动适配，使用固定字号 {font_size}")

    # FFmpeg subtitles 滤镜需要将路径中的反斜杠替换为正斜杠，冒号需要转义
    srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")

    subtitle_filter = (
        f"subtitles='{srt_escaped}':"
        f"original_size={video_width}x{video_height}:"
        f"force_style='FontName={font_name},"
        f"FontSize={actual_font_size},"
        f"PrimaryColour={font_color},"
        f"OutlineColour={outline_color},"
        f"Outline=0,Shadow=0,Alignment=10,WrapStyle=2'"
    )

    subprocess.run(
        [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", subtitle_filter,
            "-c:a", "copy",
            output_path,
        ],
        check=True,
        stdout=subprocess.DEVNULL if not verbose else None,
        stderr=subprocess.DEVNULL if not verbose else None,
    )
    if verbose:
        print(f"Done! Final video: {output_path}")
