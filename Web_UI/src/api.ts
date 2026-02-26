/**
 * API 客户端：与 FastAPI 后端通信。
 * 所有请求指向 http://localhost:8000。
 */

const API_BASE = 'http://localhost:8000'

/** 上传返回值 */
export interface UploadResult {
  video_paths: string[]
  audio_path: string | null
  srt_path: string | null
}

/** 生成请求参数 */
export interface GenerateConfig {
  video_paths: string[]
  audio_path: string
  srt_path: string | null
  whisper_model: string
  language: string
  beat_sensitivity: number
  beats_per_cut: number
  total_duration: number
  video_width: number
  video_height: number
  fps: number
  temp_path: string
  output_path: string
}

/** SSE 进度事件 */
export interface ProgressEvent {
  stage: string
  message: string
  percent: number
}

/**
 * 上传视频、音频、字幕文件到后端
 */
export async function uploadFiles(
  videos: File[],
  audio: File | null,
  subtitle: File | null,
): Promise<UploadResult> {
  const formData = new FormData()

  // 按照前端排序的顺序添加视频文件
  videos.forEach((file) => {
    formData.append('videos', file)
  })

  if (audio) {
    formData.append('audio', audio)
  }

  if (subtitle) {
    formData.append('subtitle', subtitle)
  }

  const res = await fetch(`${API_BASE}/api/upload`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    throw new Error(`上传失败: ${res.status} ${res.statusText}`)
  }

  return res.json()
}

/**
 * 发起视频生成请求，返回 task_id
 */
export async function startGenerate(config: GenerateConfig): Promise<string> {
  const res = await fetch(`${API_BASE}/api/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })

  if (!res.ok) {
    throw new Error(`生成请求失败: ${res.status} ${res.statusText}`)
  }

  const data = await res.json()
  return data.task_id
}

/**
 * 通过 SSE 订阅处理进度
 */
export function subscribeProgress(
  taskId: string,
  onEvent: (event: ProgressEvent) => void,
  onDone: () => void,
  onError: (error: string) => void,
): () => void {
  const eventSource = new EventSource(`${API_BASE}/api/progress/${taskId}`)

  eventSource.onmessage = (e) => {
    try {
      const data: ProgressEvent = JSON.parse(e.data)

      if (data.stage === 'end') {
        eventSource.close()
        onDone()
        return
      }

      if (data.stage === 'error') {
        eventSource.close()
        onError(data.message)
        return
      }

      onEvent(data)
    } catch {
      // 忽略解析错误（如心跳）
    }
  }

  eventSource.onerror = () => {
    eventSource.close()
    onError('SSE 连接中断')
  }

  // 返回取消订阅函数
  return () => eventSource.close()
}

/**
 * 获取成品视频的下载 URL
 */
export function getDownloadUrl(taskId: string): string {
  return `${API_BASE}/api/download/${taskId}`
}
