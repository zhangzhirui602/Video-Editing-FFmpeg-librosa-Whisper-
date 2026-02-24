import { useRef } from 'react'
import { Music, FileText, X, Upload } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import type { AudioFile, SubtitleFile } from '../types'

interface Props {
  audio: AudioFile | null
  subtitle: SubtitleFile | null
  onAudioChange: (audio: AudioFile | null) => void
  onSubtitleChange: (subtitle: SubtitleFile | null) => void
}

/** 通用文件上传卡片 */
function FileCard({
  icon: Icon,
  label,
  accept,
  file,
  onFileChange,
  onRemove,
  color,
}: {
  icon: typeof Music
  label: string
  accept: string
  file: { name: string; size: number } | null
  onFileChange: (file: File) => void
  onRemove: () => void
  color: string
}) {
  const inputRef = useRef<HTMLInputElement>(null)

  return (
    <div className="flex-1">
      <label className="text-xs text-zinc-500 mb-2 block uppercase tracking-wider">{label}</label>
      {file ? (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`flex items-center gap-3 bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-3`}
        >
          <Icon className={`w-5 h-5 ${color} shrink-0`} />
          <div className="min-w-0 flex-1">
            <p className="text-sm text-zinc-200 truncate">{file.name}</p>
            <p className="text-xs text-zinc-500">{(file.size / 1024).toFixed(0)} KB</p>
          </div>
          <button
            onClick={onRemove}
            className="text-zinc-500 hover:text-red-400 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </motion.div>
      ) : (
        <div
          onClick={() => inputRef.current?.click()}
          className="flex items-center gap-3 border border-dashed border-zinc-700 hover:border-zinc-600
            rounded-lg px-4 py-3 cursor-pointer transition-colors group"
        >
          <Upload className="w-5 h-5 text-zinc-600 group-hover:text-zinc-400 transition-colors" />
          <span className="text-sm text-zinc-500 group-hover:text-zinc-400">点击上传{label}</span>
        </div>
      )}
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0]
          if (f) onFileChange(f)
          e.target.value = ''
        }}
      />
    </div>
  )
}

export default function AudioSubtitleZone({ audio, subtitle, onAudioChange, onSubtitleChange }: Props) {
  return (
    <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-5">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-300 mb-4">
        音频与字幕
      </h2>
      <div className="flex flex-col sm:flex-row gap-4">
        <FileCard
          icon={Music}
          label="背景音乐"
          accept="audio/*"
          file={audio}
          color="text-emerald-400"
          onFileChange={(f) =>
            onAudioChange({ id: crypto.randomUUID(), file: f, name: f.name, size: f.size })
          }
          onRemove={() => onAudioChange(null)}
        />
        <FileCard
          icon={FileText}
          label="歌词/字幕 (SRT)"
          accept=".srt,.lrc,.txt,.ass"
          file={subtitle}
          color="text-amber-400"
          onFileChange={(f) =>
            onSubtitleChange({ id: crypto.randomUUID(), file: f, name: f.name, size: f.size })
          }
          onRemove={() => onSubtitleChange(null)}
        />
      </div>
    </div>
  )
}
