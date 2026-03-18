"""视频处理模块：裁剪视频片段并拼接成完整视频。"""

import os
import subprocess
from typing import Callable


STYLE_PRESETS: dict[str, str] = {
    "vintage_film": (
        # --- normalize: 把任意来源素材拍平到中性基准 ---
        "normalize=blackpt=black:whitept=white:smoothing=0,"
        "eq=contrast=0.9:saturation=0.85:gamma=1.0,"
        "colorbalance=rs=0:gs=0:bs=0:rm=0:gm=0:bm=0,"
        # --- vintage grade: 在中性基准上做胶片调色 ---
        "curves="
        "r='0/0.07\\:0.3/0.22\\:0.6/0.50\\:1/0.85'"
        ":g='0/0.09\\:0.3/0.26\\:0.6/0.55\\:1/0.90'"
        ":b='0/0.04\\:0.3/0.16\\:0.6/0.40\\:1/0.72',"
        "colorbalance=rs=0.10:gs=0.15:bs=-0.10:rm=0.05:gm=0.08:bm=-0.08,"
        "eq=contrast=0.82:saturation=0.65,"
        # --- bloom: 模拟闪光灯高光溢出 ---
        "split[main][bloom];"
        "[bloom]gblur=sigma=30,eq=brightness=0.15[bloom_out];"
        "[main][bloom_out]blend=all_mode=screen:all_opacity=0.25,"
        "noise=c0s=18:allf=t,"
        "gblur=sigma=1.2,"
        "vignette=PI/3.5"
    ),
    "fresh_natural": (
        # --- normalize: 把任意来源素材拍平到中性基准 ---
        "normalize=blackpt=black:whitept=white:smoothing=0,"
        "eq=contrast=0.9:saturation=0.85:gamma=1.0,"
        "colorbalance=rs=0:gs=0:bs=0:rm=0:gm=0:bm=0,"
        # --- fresh natural grade ---
        "eq=brightness=0.06:saturation=1.1,"
        "colorbalance=rs=-0.1:gs=0.05:bs=0.1:rm=-0.05:gm=0.1:bm=0.1,"
        "unsharp=3:3:0.3"
    ),
    "dreamy_soft": (
        # --- normalize: 把任意来源素材拍平到中性基准 ---
        "normalize=blackpt=black:whitept=white:smoothing=0,"
        "eq=contrast=0.9:saturation=0.85:gamma=1.0,"
        "colorbalance=rs=0:gs=0:bs=0:rm=0:gm=0:bm=0,"
        # --- dreamy grade: 暖调柔雾高光溢出 ---
        "split[main][bloom];"
        "[bloom]gblur=sigma=40,"
        "curves=red='0/0.05\\:1/0.95':green='0/0.03\\:1/0.82':blue='0/0.0\\:1/0.65',"
        "eq=brightness=0.12[bloom_out];"
        "[main][bloom_out]blend=all_mode=screen:all_opacity=0.42,"
        "curves=red='0/0.10\\:0.5/0.56\\:1/0.94'"
        ":green='0/0.08\\:0.5/0.48\\:1/0.85'"
        ":blue='0/0.04\\:0.5/0.36\\:1/0.70',"
        "colorbalance=rs=0.08:gs=-0.02:bs=-0.08:rm=0.10:gm=0.02:bm=-0.06,"
        "eq=brightness=0.04:contrast=0.76:saturation=0.72,"
        "gblur=sigma=1.0"
    ),
    "cinematic": (
        # --- normalize: 把任意来源素材拍平到中性基准 ---
        "normalize=blackpt=black:whitept=white:smoothing=0,"
        "eq=contrast=0.9:saturation=0.85:gamma=1.0,"
        "colorbalance=rs=0:gs=0:bs=0:rm=0:gm=0:bm=0,"
        # --- cinematic grade ---
        "eq=contrast=1.3:saturation=0.9,"
        "colorbalance=rs=-0.05:gs=-0.02:bs=0.15:rm=-0.05:gm=-0.02:bm=0.1,"
        "drawbox=x=0:y=0:w=iw:h=ih*0.04:color=black:t=fill,"
        "drawbox=x=0:y=ih*0.96:w=iw:h=ih*0.04:color=black:t=fill"
    ),
    "bw_classic": (
        # --- normalize: 把任意来源素材拍平到中性基准 ---
        "normalize=blackpt=black:whitept=white:smoothing=0,"
        "eq=contrast=0.9:saturation=0.85:gamma=1.0,"
        "colorbalance=rs=0:gs=0:bs=0:rm=0:gm=0:bm=0,"
        # --- bw classic grade ---
        "hue=s=0,"
        "eq=contrast=1.4,"
        "noise=c0s=6:allf=t"
    ),
}


def cut_segments(
    cut_times: list[float],
    video_clips: list[str],
    temp_dir: str,
    video_width: int,
    video_height: int,
    fps: int,
    progress_callback: Callable[[int, int], None] | None = None,
    verbose: bool = True,
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

    返回:
        裁剪后的视频片段路径列表
    """
    os.makedirs(temp_dir, exist_ok=True)
    segs_dir = os.path.join(temp_dir, "segs")
    os.makedirs(segs_dir, exist_ok=True)
    segment_files = []

    scale_filter = (
        f"scale={video_width}:{video_height}:force_original_aspect_ratio=decrease,"
        f"pad={video_width}:{video_height}:(ow-iw)/2:(oh-ih)/2,setsar=1"
    )

    for i in range(len(cut_times) - 1):
        start = cut_times[i]
        duration = cut_times[i + 1] - cut_times[i]
        clip_path = video_clips[i % len(video_clips)]
        out_file = os.path.join(segs_dir, f"seg_{i:03d}.mp4")

        if verbose:
            print(f"处理第 {i+1} 段（{duration:.3f}s）...")
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
        if progress_callback:
            progress_callback(i + 1, len(cut_times) - 1)

    return segment_files


def concat_with_audio(
    segment_files: list[str],
    audio_path: str,
    total_duration: float,
    temp_dir: str,
    output_path: str,
    verbose: bool = True,
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
    if verbose:
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
    if verbose:
        print("拼接完成！")
