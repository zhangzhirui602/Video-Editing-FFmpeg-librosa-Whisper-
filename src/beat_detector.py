"""节拍检测模块：使用 librosa 分析音频节拍，生成切换时间点。"""

import librosa


def detect_beats(audio_path: str, total_duration: float, beats_per_cut: int) -> list[float]:
    """
    检测音频节拍并计算视频切换时间点。

    参数:
        audio_path: 音频文件路径
        total_duration: 音频总时长（秒）
        beats_per_cut: 每隔几拍切换一次

    返回:
        切换时间点列表（包含起点和终点）
    """
    print("正在分析节拍...")
    y, sr = librosa.load(audio_path, sr=None, mono=True)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()

    # 按 beats_per_cut 间隔取切换点
    cut_times = [beat_times[i] for i in range(0, len(beat_times) - beats_per_cut, beats_per_cut)]
    if cut_times[-1] < total_duration:
        cut_times.append(total_duration)

    print(f"共 {len(cut_times)-1} 个切换点")
    return cut_times
