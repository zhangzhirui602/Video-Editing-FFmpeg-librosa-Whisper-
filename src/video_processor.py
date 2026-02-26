"""视频处理模块：裁剪视频片段并拼接成完整视频。"""

import os
import subprocess


def cut_segments(
    cut_times: list[float],
    video_clips: list[str],
    temp_dir: str,
    video_width: int,
    video_height: int,
    fps: int,
    on_segment_progress=None,
) -> list[str]:
    """
    按切换时间点裁剪视频片段。

    参数:
        cut_times: 切换时间点列表
        video_clips: 视频素材路径列表（循环使用）
        temp_dir: 临时文件目录
        video_width: 输出视频宽度
        video_height: 输出视频高度
        fps: 输出帧率
        on_segment_progress: 可选回调 (当前序号, 总数)

    返回:
        裁剪后的视频片段路径列表
    """
    os.makedirs(temp_dir, exist_ok=True)
    segment_files = []
    total = len(cut_times) - 1

    scale_filter = (
        f"scale={video_width}:{video_height}:force_original_aspect_ratio=decrease,"
        f"pad={video_width}:{video_height}:(ow-iw)/2:(oh-ih)/2,setsar=1"
    )

    for i in range(total):
        start = cut_times[i]
        duration = cut_times[i + 1] - cut_times[i]
        clip_path = video_clips[i % len(video_clips)]
        out_file = os.path.join(temp_dir, f"seg_{i:03d}.mp4")

        print(f"处理第 {i+1} 段（{duration:.3f}s）...")
        if on_segment_progress:
            on_segment_progress(i, total)

        subprocess.run(
            [
                "ffmpeg", "-y", "-i", clip_path,
                "-t", str(duration),
                "-vf", scale_filter,
                "-r", str(fps), "-an",
                "-c:v", "libx264", "-preset", "fast",
                out_file,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        segment_files.append(out_file)

    return segment_files


def concat_with_audio(
    segment_files: list[str],
    audio_path: str,
    total_duration: float,
    temp_dir: str,
    output_path: str,
) -> None:
    """
    拼接视频片段并合入音频。

    参数:
        segment_files: 裁剪后的视频片段路径列表
        audio_path: 音频文件路径
        total_duration: 总时长（秒）
        temp_dir: 临时文件目录
        output_path: 输出文件路径
    """
    print("正在拼接视频...")
    concat_list = os.path.join(temp_dir, "concat_list.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        for seg in segment_files:
            f.write(f"file '{seg}'\n")

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", concat_list,
            "-i", audio_path,
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
            "-t", str(total_duration),
            output_path,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print("拼接完成！")
