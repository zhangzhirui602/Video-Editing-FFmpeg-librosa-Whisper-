import { useRef, useState } from 'react'
import { Download, Monitor, Play, Pause, Volume2, VolumeX, Maximize } from 'lucide-react'
import { motion } from 'framer-motion'
import type { ProcessStatus } from '../types'

interface Props {
  status: ProcessStatus
  /** 后端成品视频的 URL（如 http://localhost:8000/api/download/{task_id}） */
  resultVideoUrl: string | null
  resultVideoName: string
}

export default function PreviewPanel({ status, resultVideoUrl, resultVideoName }: Props) {
  const isReady = status === 'completed' && !!resultVideoUrl
  const videoRef = useRef<HTMLVideoElement>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)

  // 播放/暂停切换
  const togglePlay = () => {
    if (!videoRef.current) return
    if (isPlaying) {
      videoRef.current.pause()
    } else {
      videoRef.current.play()
    }
    setIsPlaying(!isPlaying)
  }

  // 静音切换
  const toggleMute = () => {
    if (!videoRef.current) return
    videoRef.current.muted = !isMuted
    setIsMuted(!isMuted)
  }

  // 全屏播放
  const enterFullscreen = () => {
    videoRef.current?.requestFullscreen()
  }

  // 进度条点击跳转
  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!videoRef.current || !duration) return
    const rect = e.currentTarget.getBoundingClientRect()
    const ratio = (e.clientX - rect.left) / rect.width
    videoRef.current.currentTime = ratio * duration
  }

  // 格式化时间 mm:ss
  const formatTime = (sec: number) => {
    const m = Math.floor(sec / 60)
    const s = Math.floor(sec % 60)
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  // 下载视频：直接在新窗口打开后端下载链接（跨域场景下 <a download> 无效）
  const handleDownload = () => {
    if (!resultVideoUrl) return
    window.open(resultVideoUrl, '_blank')
  }

  return (
    <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Monitor className="w-5 h-5 text-purple-400" />
          <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-300">
            成品预览
          </h2>
        </div>
        {isReady && (
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleDownload}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white
              text-xs font-medium px-3 py-1.5 rounded-lg transition-colors cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" />
            下载视频
          </motion.button>
        )}
      </div>

      {/* 视频播放器区域 */}
      <div className="aspect-video bg-zinc-950 rounded-lg border border-zinc-800 overflow-hidden relative group">
        {isReady ? (
          <>
            {/* 真实 <video> 播放器 */}
            <video
              ref={videoRef}
              src={resultVideoUrl}
              className="w-full h-full object-contain bg-black cursor-pointer"
              onClick={togglePlay}
              onTimeUpdate={() => setCurrentTime(videoRef.current?.currentTime ?? 0)}
              onLoadedMetadata={() => setDuration(videoRef.current?.duration ?? 0)}
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
              onEnded={() => setIsPlaying(false)}
              playsInline
            />

            {/* 中央播放/暂停大按钮（未播放时显示） */}
            {!isPlaying && (
              <button
                onClick={togglePlay}
                className="absolute inset-0 flex items-center justify-center bg-black/30
                  opacity-100 group-hover:opacity-100 transition-opacity cursor-pointer"
              >
                <div className="w-14 h-14 rounded-full bg-purple-600/80 flex items-center justify-center backdrop-blur-sm">
                  <Play className="w-6 h-6 text-white ml-0.5" />
                </div>
              </button>
            )}

            {/* 底部控制栏 */}
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent
              px-3 pb-2.5 pt-8 opacity-0 group-hover:opacity-100 transition-opacity">
              {/* 进度条（可点击跳转） */}
              <div
                className="h-1.5 bg-zinc-700 rounded-full overflow-hidden mb-2 cursor-pointer group/bar"
                onClick={handleSeek}
              >
                <div
                  className="h-full bg-purple-500 rounded-full relative"
                  style={{ width: duration ? `${(currentTime / duration) * 100}%` : '0%' }}
                >
                  {/* 进度条拖拽手柄 */}
                  <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full
                    shadow-md opacity-0 group-hover/bar:opacity-100 transition-opacity" />
                </div>
              </div>

              <div className="flex items-center justify-between">
                {/* 左侧控制 */}
                <div className="flex items-center gap-2">
                  <button onClick={togglePlay} className="cursor-pointer text-white/80 hover:text-white">
                    {isPlaying
                      ? <Pause className="w-4 h-4" />
                      : <Play className="w-4 h-4" />
                    }
                  </button>
                  <button onClick={toggleMute} className="cursor-pointer text-white/80 hover:text-white">
                    {isMuted
                      ? <VolumeX className="w-4 h-4" />
                      : <Volume2 className="w-4 h-4" />
                    }
                  </button>
                  <span className="text-xs text-zinc-400 font-mono ml-1">
                    {formatTime(currentTime)} / {formatTime(duration)}
                  </span>
                </div>

                {/* 右侧控制 */}
                <div className="flex items-center gap-2">
                  <button onClick={enterFullscreen} className="cursor-pointer text-white/80 hover:text-white">
                    <Maximize className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center gap-3">
            <Monitor className="w-12 h-12 text-zinc-800" />
            <p className="text-sm text-zinc-600">
              {status === 'processing' ? '视频生成中，请稍候...' : '等待视频生成完成...'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
