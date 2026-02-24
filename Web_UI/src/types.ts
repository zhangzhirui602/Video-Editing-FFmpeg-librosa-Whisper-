// ===== 项目核心类型定义 =====

/** 视频素材项 */
export interface VideoItem {
  id: string
  file: File
  name: string
  size: number
  thumbnailUrl: string
  previewUrl: string
  duration?: number
}

/** 音频文件 */
export interface AudioFile {
  id: string
  file: File
  name: string
  size: number
}

/** 字幕文件 */
export interface SubtitleFile {
  id: string
  file: File
  name: string
  size: number
}

/** 项目设置参数 */
export interface ProjectSettings {
  beatSensitivity: number
  whisperModel: string
  language: string
  beatsPerCut: number
  totalDuration: number
  videoWidth: number
  videoHeight: number
  fps: number
  tempPath: string
  outputPath: string
}

/** 处理阶段 */
export interface ProcessStage {
  id: string
  label: string
  progress: number
  status: 'pending' | 'running' | 'completed'
}

/** 终端日志条目 */
export interface LogEntry {
  timestamp: string
  message: string
  type: 'info' | 'success' | 'warning' | 'error'
}

/** 整体处理状态 */
export type ProcessStatus = 'idle' | 'processing' | 'completed' | 'error'
