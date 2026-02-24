"""FastAPI 后端服务：提供文件上传、视频生成、进度推送、成品下载接口。"""

import json
import os
import queue
import shutil
import threading
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from src.pipeline import run_with_config

# 项目根目录
ROOT = Path(__file__).resolve().parent.parent

app = FastAPI(title="AutoCut Pro API")

# CORS：允许前端 dev server 跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== 任务状态存储（内存，单进程够用） =====
# task_id -> { "status", "output_path", "queue" (SSE 消息队列) }
tasks: dict[str, dict] = {}
# 最新的 task_id（用于下载最新成品）
latest_task_id: Optional[str] = None


# ===== 数据模型 =====
class GenerateRequest(BaseModel):
    """前端提交的生成请求"""
    video_paths: list[str]           # 服务端视频文件路径列表（按顺序）
    audio_path: str                  # 服务端音频文件路径
    srt_path: Optional[str] = None   # 服务端字幕文件路径（可选）
    whisper_model: str = "base"
    language: str = "Chinese"
    beat_sensitivity: float = 1.0
    beats_per_cut: int = 2
    total_duration: float = 30.0
    output_resolution: str = "1920x1080"
    video_width: int = 1080
    video_height: int = 1920
    fps: int = 30
    temp_path: str = "output/temp"
    output_path: str = "output"


# ===== 文件上传接口 =====
@app.post("/api/upload")
async def upload_files(
    videos: list[UploadFile] = File(default=[]),
    audio: Optional[UploadFile] = File(default=None),
    subtitle: Optional[UploadFile] = File(default=None),
):
    """
    接收前端上传的视频、音频、字幕文件。
    保存到 raw_materials/ 对应子目录，返回服务端文件路径。
    """
    result = {"video_paths": [], "audio_path": None, "srt_path": None}

    # 清空上次上传的文件，确保每次都是全新的素材
    video_dir = ROOT / "raw_materials" / "videos" / "uploaded"
    if video_dir.exists():
        shutil.rmtree(video_dir)
    video_dir.mkdir(parents=True, exist_ok=True)
    for v in videos:
        dest = video_dir / v.filename
        with open(dest, "wb") as f:
            content = await v.read()
            f.write(content)
        result["video_paths"].append(str(dest))

    # 保存音频文件
    if audio:
        audio_dir = ROOT / "raw_materials" / "song"
        audio_dir.mkdir(parents=True, exist_ok=True)
        dest = audio_dir / audio.filename
        with open(dest, "wb") as f:
            content = await audio.read()
            f.write(content)
        result["audio_path"] = str(dest)

    # 保存字幕文件
    if subtitle:
        srt_dir = ROOT / "raw_materials" / "lyric"
        srt_dir.mkdir(parents=True, exist_ok=True)
        dest = srt_dir / subtitle.filename
        with open(dest, "wb") as f:
            content = await subtitle.read()
            f.write(content)
        result["srt_path"] = str(dest)

    return result


# ===== 视频生成接口 =====
@app.post("/api/generate")
async def generate_video(req: GenerateRequest):
    """
    接收配置参数，在后台线程中运行 pipeline。
    返回 task_id，前端用它查询进度和下载成品。
    """
    global latest_task_id

    # 清理旧任务，释放内存
    tasks.clear()

    task_id = str(uuid.uuid4())
    latest_task_id = task_id

    # 解析输出路径
    temp_dir = str(ROOT / req.temp_path) if not Path(req.temp_path).is_absolute() else req.temp_path
    output_dir = str(ROOT / req.output_path) if not Path(req.output_path).is_absolute() else req.output_path
    os.makedirs(output_dir, exist_ok=True)

    # 清理上次的临时文件和输出文件，确保干净的工作环境
    if os.path.isdir(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)

    final_output = os.path.join(output_dir, "final.mp4")
    output_no_sub = os.path.join(output_dir, "no_sub.mp4")
    # 删除旧的输出文件
    for old_file in [final_output, output_no_sub]:
        if os.path.isfile(old_file):
            os.remove(old_file)

    # 如果没有提供字幕路径，根据音频文件名自动生成
    srt_path = req.srt_path
    if not srt_path:
        audio_stem = Path(req.audio_path).stem
        srt_path = str(ROOT / "raw_materials" / "lyric" / f"{audio_stem}.srt")

    # 构建与 load_config() 兼容的配置字典
    cfg = {
        "audio_path": req.audio_path,
        "srt_path": srt_path,
        "total_duration": req.total_duration,
        "beats_per_cut": req.beats_per_cut,
        "temp_dir": temp_dir,
        "output_no_sub": output_no_sub,
        "final_output": final_output,
        "video_clips": req.video_paths,
        "video_width": req.video_width,
        "video_height": req.video_height,
        "fps": req.fps,
        "font_size": 18,
        "font_color": "&H00FFFFFF",
        "outline_color": "&H00000000",
        "whisper_model": req.whisper_model,
        "language": req.language,
    }

    # 创建 SSE 消息队列
    msg_queue: queue.Queue = queue.Queue()
    tasks[task_id] = {
        "status": "processing",
        "output_path": final_output,
        "queue": msg_queue,
    }

    def progress_callback(stage: str, message: str, percent: int):
        """将进度事件放入队列，供 SSE 端点消费。"""
        event = {"stage": stage, "message": message, "percent": percent}
        msg_queue.put(event)

    def worker():
        """后台线程运行 pipeline。"""
        try:
            run_with_config(cfg, on_progress=progress_callback)
            tasks[task_id]["status"] = "completed"
            msg_queue.put({"stage": "done", "message": "全部处理完成", "percent": 100})
        except Exception as e:
            tasks[task_id]["status"] = "error"
            msg_queue.put({"stage": "error", "message": str(e), "percent": 0})
        # 放入结束哨兵
        msg_queue.put(None)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    return {"task_id": task_id}


# ===== SSE 进度推送 =====
@app.get("/api/progress/{task_id}")
async def progress_stream(task_id: str):
    """通过 Server-Sent Events 推送实时进度。"""
    if task_id not in tasks:
        return {"error": "task not found"}

    msg_queue = tasks[task_id]["queue"]

    def event_generator():
        while True:
            try:
                event = msg_queue.get(timeout=30)
            except queue.Empty:
                # 发送心跳保持连接
                yield ": heartbeat\n\n"
                continue

            if event is None:
                # 结束哨兵
                yield f"data: {json.dumps({'stage': 'end', 'message': '流结束', 'percent': 100})}\n\n"
                break

            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ===== 成品下载 =====
@app.get("/api/download/{task_id}")
async def download_video(task_id: str):
    """下载生成完毕的最终视频文件。"""
    if task_id not in tasks:
        return {"error": "task not found"}

    task = tasks[task_id]
    if task["status"] != "completed":
        return {"error": "video not ready yet"}

    output_path = task["output_path"]
    if not os.path.isfile(output_path):
        return {"error": f"output file not found: {output_path}"}

    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename="final_output.mp4",
    )
