import { Settings, ChevronDown, FolderOpen } from 'lucide-react'
import type { ProjectSettings } from '../types'

interface Props {
  settings: ProjectSettings
  onChange: (settings: ProjectSettings) => void
}

/**
 * 调用浏览器原生目录选择器 (File System Access API)
 * 支持 Chromium 内核浏览器；不支持时回退为手动输入提示
 */
async function pickDirectory(): Promise<string | null> {
  if ('showDirectoryPicker' in window) {
    try {
      const dirHandle = await (window as any).showDirectoryPicker({ mode: 'readwrite' })
      return dirHandle.name
    } catch {
      return null
    }
  }
  alert('当前浏览器不支持目录选择器，请手动输入路径或使用 Chrome / Edge 浏览器。')
  return null
}

// 通用样式常量
const inputClass = `w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2.5 text-sm text-zinc-200
  placeholder:text-zinc-600 hover:border-zinc-600 focus:border-purple-500 focus:outline-none transition-colors`
const selectClass = `${inputClass} appearance-none cursor-pointer`
const labelClass = 'text-sm text-zinc-400 mb-2 block'

export default function SettingsPanel({ settings, onChange }: Props) {
  const update = (key: keyof ProjectSettings, value: string | number) => {
    onChange({ ...settings, [key]: value })
  }

  const handlePickDir = async (key: 'tempPath' | 'outputPath') => {
    const selected = await pickDirectory()
    if (selected) update(key, selected)
  }

  return (
    <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-5">
      <div className="flex items-center gap-2 mb-5">
        <Settings className="w-5 h-5 text-purple-400" />
        <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-300">参数配置</h2>
      </div>

      <div className="space-y-5">
        {/* ===== 音频/语音参数 ===== */}
        <div className="grid grid-cols-2 gap-4">
          {/* 音频语言 */}
          <div>
            <label className={labelClass}>音频语言</label>
            <div className="relative">
              <select
                value={settings.language}
                onChange={(e) => update('language', e.target.value)}
                className={selectClass}
              >
                <option value="Chinese">Chinese (中文)</option>
                <option value="English">English</option>
                <option value="Japanese">Japanese</option>
                <option value="Korean">Korean</option>
                <option value="Swedish">Swedish</option>
                <option value="French">French</option>
                <option value="German">German</option>
                <option value="Spanish">Spanish</option>
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500 pointer-events-none" />
            </div>
          </div>

          {/* Whisper 模型 */}
          <div>
            <label className={labelClass}>Whisper 模型</label>
            <div className="relative">
              <select
                value={settings.whisperModel}
                onChange={(e) => update('whisperModel', e.target.value)}
                className={selectClass}
              >
                <option value="tiny">tiny (最快)</option>
                <option value="base">base</option>
                <option value="small">small</option>
                <option value="medium">medium</option>
                <option value="large">large (最精确)</option>
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500 pointer-events-none" />
            </div>
          </div>
        </div>

        {/* ===== 节拍与时长参数 ===== */}
        <div className="grid grid-cols-2 gap-4">
          {/* 音频总时长 */}
          <div>
            <label className={labelClass}>音频总时长 (秒)</label>
            <input
              type="number"
              min="1"
              step="0.1"
              value={settings.totalDuration}
              onChange={(e) => update('totalDuration', parseFloat(e.target.value) || 0)}
              className={`${inputClass} font-mono`}
            />
          </div>

          {/* 每拍切换数 */}
          <div>
            <label className={labelClass}>每几拍切换</label>
            <input
              type="number"
              min="1"
              max="16"
              step="1"
              value={settings.beatsPerCut}
              onChange={(e) => update('beatsPerCut', parseInt(e.target.value) || 1)}
              className={`${inputClass} font-mono`}
            />
          </div>
        </div>

        {/* 节拍检测灵敏度 */}
        <div>
          <label className="flex justify-between text-sm text-zinc-400 mb-2">
            <span>节拍检测灵敏度</span>
            <span className="text-purple-400 font-mono">{settings.beatSensitivity.toFixed(1)}</span>
          </label>
          <input
            type="range"
            min="0.1"
            max="2.0"
            step="0.1"
            value={settings.beatSensitivity}
            onChange={(e) => update('beatSensitivity', parseFloat(e.target.value))}
            className="w-full h-1.5 bg-zinc-700 rounded-full appearance-none cursor-pointer
              [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4
              [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-purple-500
              [&::-webkit-slider-thumb]:shadow-[0_0_8px_rgba(168,85,247,0.5)]
              [&::-webkit-slider-thumb]:cursor-pointer"
          />
          <div className="flex justify-between text-xs text-zinc-600 mt-1">
            <span>低</span>
            <span>高</span>
          </div>
        </div>

        {/* ===== 视频输出参数 ===== */}
        <div className="grid grid-cols-3 gap-4">
          {/* 视频宽度 */}
          <div>
            <label className={labelClass}>宽度 (px)</label>
            <input
              type="number"
              min="320"
              step="1"
              value={settings.videoWidth}
              onChange={(e) => update('videoWidth', parseInt(e.target.value) || 1080)}
              className={`${inputClass} font-mono`}
            />
          </div>

          {/* 视频高度 */}
          <div>
            <label className={labelClass}>高度 (px)</label>
            <input
              type="number"
              min="320"
              step="1"
              value={settings.videoHeight}
              onChange={(e) => update('videoHeight', parseInt(e.target.value) || 1920)}
              className={`${inputClass} font-mono`}
            />
          </div>

          {/* 帧率 */}
          <div>
            <label className={labelClass}>帧率 (FPS)</label>
            <input
              type="number"
              min="15"
              max="120"
              step="1"
              value={settings.fps}
              onChange={(e) => update('fps', parseInt(e.target.value) || 30)}
              className={`${inputClass} font-mono`}
            />
          </div>
        </div>

        {/* ===== 路径配置 ===== */}
        {/* 临时文件路径 */}
        <div>
          <label className={labelClass}>临时文件路径</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={settings.tempPath}
              onChange={(e) => update('tempPath', e.target.value)}
              placeholder="output/temp"
              className={`flex-1 min-w-0 ${inputClass} font-mono`}
            />
            <button
              type="button"
              onClick={() => handlePickDir('tempPath')}
              title="选择文件夹"
              className="shrink-0 bg-zinc-800 border border-zinc-700 hover:border-purple-500/60
                rounded-lg px-3 flex items-center justify-center transition-colors cursor-pointer group"
            >
              <FolderOpen className="w-4 h-4 text-zinc-500 group-hover:text-purple-400 transition-colors" />
            </button>
          </div>
        </div>

        {/* 输出路径 */}
        <div>
          <label className={labelClass}>输出路径</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={settings.outputPath}
              onChange={(e) => update('outputPath', e.target.value)}
              placeholder="output"
              className={`flex-1 min-w-0 ${inputClass} font-mono`}
            />
            <button
              type="button"
              onClick={() => handlePickDir('outputPath')}
              title="选择文件夹"
              className="shrink-0 bg-zinc-800 border border-zinc-700 hover:border-purple-500/60
                rounded-lg px-3 flex items-center justify-center transition-colors cursor-pointer group"
            >
              <FolderOpen className="w-4 h-4 text-zinc-500 group-hover:text-purple-400 transition-colors" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
