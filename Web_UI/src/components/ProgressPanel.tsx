import { useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { Loader2, CheckCircle2, Circle, Terminal, Sparkles } from 'lucide-react'
import type { ProcessStage, LogEntry, ProcessStatus } from '../types'

interface Props {
  status: ProcessStatus
  stages: ProcessStage[]
  logs: LogEntry[]
  overallProgress: number
  onGenerate: () => void
}

export default function ProgressPanel({ status, stages, logs, overallProgress, onGenerate }: Props) {
  const logContainerRef = useRef<HTMLDivElement>(null)

  // 自动滚动日志到底部
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [logs])

  return (
    <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-5">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-purple-400" />
          <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-300">
            生成控制
          </h2>
        </div>
      </div>

      {/* 生成按钮 */}
      <motion.button
        whileHover={{ scale: status === 'idle' ? 1.02 : 1 }}
        whileTap={{ scale: status === 'idle' ? 0.98 : 1 }}
        onClick={onGenerate}
        disabled={status === 'processing'}
        className={`w-full py-3.5 rounded-lg text-sm font-semibold transition-all cursor-pointer
          ${status === 'processing'
            ? 'bg-zinc-800 text-zinc-500 cursor-not-allowed'
            : status === 'completed'
              ? 'bg-gradient-to-r from-purple-600 to-violet-500 hover:from-purple-500 hover:to-violet-400 text-white shadow-[0_0_20px_rgba(168,85,247,0.3)]'
              : status === 'error'
                ? 'bg-red-600 hover:bg-red-500 text-white'
                : 'bg-gradient-to-r from-purple-600 to-violet-500 hover:from-purple-500 hover:to-violet-400 text-white shadow-[0_0_20px_rgba(168,85,247,0.3)]'
          }`}
      >
        {status === 'processing' ? (
          <span className="flex items-center justify-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            正在处理中...
          </span>
        ) : status === 'completed' ? (
          <span className="flex items-center justify-center gap-2">
            <CheckCircle2 className="w-4 h-4" />
            重新生成视频
          </span>
        ) : status === 'error' ? (
          '重试生成'
        ) : (
          '开始生成视频'
        )}
      </motion.button>

      {/* 进度条与阶段 */}
      {status !== 'idle' && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="mt-5 space-y-4"
        >
          {/* 总进度条 */}
          <div>
            <div className="flex justify-between text-xs text-zinc-400 mb-1.5">
              <span>总进度</span>
              <span className="font-mono text-purple-400">{Math.round(overallProgress)}%</span>
            </div>
            <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
              <motion.div
                className="h-full rounded-full bg-gradient-to-r from-purple-600 to-violet-400"
                initial={{ width: 0 }}
                animate={{ width: `${overallProgress}%` }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
              />
            </div>
          </div>

          {/* 各阶段状态 */}
          <div className="space-y-2">
            {stages.map((stage) => (
              <div key={stage.id} className="flex items-center gap-3">
                {stage.status === 'completed' ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                ) : stage.status === 'running' ? (
                  <Loader2 className="w-4 h-4 text-purple-400 animate-spin shrink-0" />
                ) : (
                  <Circle className="w-4 h-4 text-zinc-600 shrink-0" />
                )}
                <span
                  className={`text-xs flex-1 ${
                    stage.status === 'running'
                      ? 'text-zinc-200'
                      : stage.status === 'completed'
                        ? 'text-zinc-400'
                        : 'text-zinc-600'
                  }`}
                >
                  {stage.label}
                </span>
                {stage.status === 'running' && (
                  <span className="text-xs font-mono text-purple-400">{stage.progress}%</span>
                )}
              </div>
            ))}
          </div>

          {/* 模拟终端日志 */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Terminal className="w-4 h-4 text-zinc-500" />
              <span className="text-xs text-zinc-500 uppercase tracking-wider">Terminal Log</span>
            </div>
            <div
              ref={logContainerRef}
              className="bg-zinc-950 border border-zinc-800 rounded-lg p-3 h-40 overflow-y-auto font-mono text-xs"
            >
              {logs.map((log, i) => (
                <div key={i} className="flex gap-2 leading-relaxed">
                  <span className="text-zinc-600 shrink-0">{log.timestamp}</span>
                  <span
                    className={
                      log.type === 'error'
                        ? 'text-red-400'
                        : log.type === 'success'
                          ? 'text-emerald-400'
                          : log.type === 'warning'
                            ? 'text-amber-400'
                            : 'text-zinc-400'
                    }
                  >
                    {log.message}
                  </span>
                </div>
              ))}
              {status === 'processing' && (
                <span className="inline-block w-1.5 h-3.5 bg-purple-400 animate-pulse ml-1" />
              )}
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}
