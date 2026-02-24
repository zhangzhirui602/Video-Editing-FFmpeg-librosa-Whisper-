import { useState, useCallback, useRef } from 'react'
import Header from './components/Header'
import VideoUploadZone from './components/VideoUploadZone'
import AudioSubtitleZone from './components/AudioSubtitleZone'
import SettingsPanel from './components/SettingsPanel'
import ProgressPanel from './components/ProgressPanel'
import PreviewPanel from './components/PreviewPanel'
import { uploadFiles, startGenerate, subscribeProgress, getDownloadUrl } from './api'
import type {
  VideoItem,
  AudioFile,
  SubtitleFile,
  ProjectSettings,
  ProcessStage,
  LogEntry,
  ProcessStatus,
} from './types'

// ===== 处理阶段定义（与后端 stage id 对应） =====
const INITIAL_STAGES: ProcessStage[] = [
  { id: 'upload', label: '上传素材到服务器', progress: 0, status: 'pending' },
  { id: 'whisper', label: '语音识别 (Whisper)', progress: 0, status: 'pending' },
  { id: 'beat', label: '节拍检测 (Librosa)', progress: 0, status: 'pending' },
  { id: 'ffmpeg', label: 'FFmpeg 视频剪辑', progress: 0, status: 'pending' },
  { id: 'finalize', label: '生成最终文件', progress: 0, status: 'pending' },
]

// ===== 默认设置（与 .env 中的默认值一致） =====
const DEFAULT_SETTINGS: ProjectSettings = {
  beatSensitivity: 1.0,
  whisperModel: 'small',
  language: 'Swedish',
  beatsPerCut: 2,
  totalDuration: 21.08,
  videoWidth: 1080,
  videoHeight: 1920,
  fps: 30,
  tempPath: 'output/temp',
  outputPath: 'output',
}

export default function App() {
  // ===== 核心状态管理 =====
  const [videos, setVideos] = useState<VideoItem[]>([])
  const [audio, setAudio] = useState<AudioFile | null>(null)
  const [subtitle, setSubtitle] = useState<SubtitleFile | null>(null)
  const [settings, setSettings] = useState<ProjectSettings>(DEFAULT_SETTINGS)

  // ===== 处理进度状态 =====
  const [processStatus, setProcessStatus] = useState<ProcessStatus>('idle')
  const [stages, setStages] = useState<ProcessStage[]>(INITIAL_STAGES)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [overallProgress, setOverallProgress] = useState(0)

  // ===== 成品下载 =====
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null)

  const unsubRef = useRef<(() => void) | null>(null)

  // 添加日志条目
  const addLog = useCallback((message: string, type: LogEntry['type'] = 'info') => {
    const now = new Date()
    const timestamp = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`
    setLogs((prev) => [...prev, { timestamp, message, type }])
  }, [])

  // 更新某个阶段的状态
  const updateStage = useCallback((stageId: string, status: ProcessStage['status'], progress: number) => {
    setStages((prev) =>
      prev.map((s) => (s.id === stageId ? { ...s, status, progress } : s))
    )
  }, [])

  // ===== 真实 API 调用流程 =====
  const handleGenerate = useCallback(async () => {
    // 校验必填素材
    if (videos.length === 0) {
      addLog('请先上传至少一个视频素材', 'error')
      return
    }
    if (!audio) {
      addLog('请先上传背景音乐', 'error')
      return
    }

    // 关闭上一次的 SSE 连接
    if (unsubRef.current) {
      unsubRef.current()
      unsubRef.current = null
    }

    // 重置所有状态，直接开始新一轮生成
    setProcessStatus('processing')
    setStages(INITIAL_STAGES)
    setLogs([])
    setOverallProgress(0)
    setDownloadUrl(null)

    try {
      // ===== 第一步：上传文件到后端 =====
      updateStage('upload', 'running', 0)
      addLog('正在上传素材到后端服务器...', 'info')

      const videoFiles = videos.map((v) => v.file)
      const uploadResult = await uploadFiles(
        videoFiles,
        audio.file,
        subtitle?.file ?? null,
      )

      updateStage('upload', 'completed', 100)
      addLog(`上传完成：${uploadResult.video_paths.length} 个视频`, 'success')
      setOverallProgress(10)

      // ===== 第二步：发起生成请求 =====
      addLog('正在提交生成任务...', 'info')

      const taskId = await startGenerate({
        video_paths: uploadResult.video_paths,
        audio_path: uploadResult.audio_path!,
        srt_path: uploadResult.srt_path,
        whisper_model: settings.whisperModel,
        language: settings.language,
        beat_sensitivity: settings.beatSensitivity,
        beats_per_cut: settings.beatsPerCut,
        total_duration: settings.totalDuration,
        video_width: settings.videoWidth,
        video_height: settings.videoHeight,
        fps: settings.fps,
        temp_path: settings.tempPath,
        output_path: settings.outputPath,
      })

      addLog(`任务已创建，ID: ${taskId.slice(0, 8)}...`, 'info')

      // ===== 第三步：通过 SSE 监听实时进度 =====
      let lastStage = ''

      const unsub = subscribeProgress(
        taskId,
        // onEvent：收到后端推送的进度事件
        (event) => {
          // 阶段切换时，自动将上一阶段标记为完成
          if (event.stage !== lastStage && lastStage) {
            updateStage(lastStage, 'completed', 100)
          }
          lastStage = event.stage

          if (event.stage === 'done') return

          updateStage(event.stage, 'running', event.percent)

          // 根据阶段权重计算总体进度（上传已占 10%）
          const stageWeights: Record<string, [number, number]> = {
            whisper: [10, 30],
            beat: [30, 45],
            ffmpeg: [45, 90],
            finalize: [90, 100],
          }
          const range = stageWeights[event.stage]
          if (range) {
            const [min, max] = range
            const overall = min + ((event.percent / 100) * (max - min))
            setOverallProgress(Math.round(overall))
          }

          addLog(event.message, event.stage === 'error' ? 'error' : 'info')
        },
        // onDone：全部完成
        () => {
          setStages((prev) => prev.map((s) => ({ ...s, status: 'completed' as const, progress: 100 })))
          setOverallProgress(100)
          setProcessStatus('completed')
          setDownloadUrl(getDownloadUrl(taskId))
          addLog('===== 全部处理完成 =====', 'success')
        },
        // onError：出错
        (error) => {
          setProcessStatus('error')
          addLog(`处理失败: ${error}`, 'error')
        },
      )

      unsubRef.current = unsub
    } catch (err) {
      setProcessStatus('error')
      addLog(`请求失败: ${err instanceof Error ? err.message : String(err)}`, 'error')
    }
  }, [processStatus, videos, audio, subtitle, settings, addLog, updateStage])

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1 p-4 md:p-6 max-w-[1600px] mx-auto w-full">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          {/* ===== 左栏: 素材上传 + 音频字幕 + 设置 ===== */}
          <div className="lg:col-span-7 xl:col-span-8 space-y-5">
            <VideoUploadZone videos={videos} onVideosChange={setVideos} />
            <AudioSubtitleZone
              audio={audio}
              subtitle={subtitle}
              onAudioChange={setAudio}
              onSubtitleChange={setSubtitle}
            />
            <SettingsPanel settings={settings} onChange={setSettings} />
          </div>

          {/* ===== 右栏: 进度控制 + 成品预览 ===== */}
          <div className="lg:col-span-5 xl:col-span-4 space-y-5">
            <ProgressPanel
              status={processStatus}
              stages={stages}
              logs={logs}
              overallProgress={overallProgress}
              onGenerate={handleGenerate}
            />
            <PreviewPanel
              status={processStatus}
              resultVideoUrl={downloadUrl}
              resultVideoName="final_output.mp4"
            />
          </div>
        </div>
      </main>

      <footer className="text-center py-4 text-xs text-zinc-600 border-t border-zinc-900">
        AutoCut Pro &mdash; FFmpeg + Librosa + Whisper 自动化视频剪辑工具
      </footer>
    </div>
  )
}
