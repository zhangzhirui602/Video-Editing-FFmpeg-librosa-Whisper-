"""字幕烧录模块：将 SRT 字幕烧录到视频中。"""

import subprocess


def burn_subtitles(
    input_path: str,
    output_path: str,
    srt_path: str,
    font_size: int,
    font_color: str,
    outline_color: str,
) -> None:
    """
    将字幕烧录到视频中。

    参数:
        input_path: 无字幕的输入视频路径
        output_path: 最终输出视频路径
        srt_path: SRT 字幕文件路径
        font_size: 字幕字号
        font_color: 字幕主颜色（ASS 格式）
        outline_color: 字幕描边颜色（ASS 格式）
    """
    print("正在烧录字幕...")
    # FFmpeg subtitles 滤镜需要将路径中的反斜杠替换为正斜杠，冒号需要转义
    srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")

    subtitle_filter = (
        f"subtitles='{srt_escaped}':"
        f"force_style='FontSize={font_size},"
        f"PrimaryColour={font_color},"
        f"OutlineColour={outline_color},"
        f"Outline=2,Alignment=2'"
    )

    subprocess.run(
        [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", subtitle_filter,
            "-c:a", "copy",
            output_path,
        ],
        check=True,
    )
    print(f"Done! Final video: {output_path}")
