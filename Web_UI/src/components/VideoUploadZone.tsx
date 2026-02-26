import { useCallback, useRef, useState } from 'react'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  rectSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, X, GripVertical, Play, Pause } from 'lucide-react'
import type { VideoItem } from '../types'

// ===== 单个可排序视频卡片组件 =====
function SortableVideoCard({
  item,
  index,
  onRemove,
}: {
  item: VideoItem
  index: number
  onRemove: (id: string) => void
}) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [isHovering, setIsHovering] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)

  // dnd-kit sortable hook
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: item.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  // 鼠标悬停时播放视频预览
  const handleMouseEnter = () => {
    setIsHovering(true)
    videoRef.current?.play()
    setIsPlaying(true)
  }

  const handleMouseLeave = () => {
    setIsHovering(false)
    if (videoRef.current) {
      videoRef.current.pause()
      videoRef.current.currentTime = 0
    }
    setIsPlaying(false)
  }

  const togglePlay = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause()
      } else {
        videoRef.current.play()
      }
      setIsPlaying(!isPlaying)
    }
  }

  return (
    <motion.div
      ref={setNodeRef}
      style={style}
      layout
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: isDragging ? 0.5 : 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      transition={{ duration: 0.2 }}
      className={`relative group bg-zinc-800 rounded-lg border overflow-hidden
        ${isDragging ? 'border-purple-500 z-50' : 'border-zinc-700 hover:border-zinc-600'}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {/* 序号标签 */}
      <div className="absolute top-2 left-2 z-10 bg-black/70 text-xs font-mono text-purple-300 px-1.5 py-0.5 rounded">
        #{index + 1}
      </div>

      {/* 删除按钮 */}
      <button
        onClick={() => onRemove(item.id)}
        className="absolute top-2 right-2 z-10 bg-black/70 hover:bg-red-600/80 rounded p-1
          opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
      >
        <X className="w-3.5 h-3.5" />
      </button>

      {/* 拖拽把手 */}
      <div
        {...attributes}
        {...listeners}
        className="absolute top-2 left-1/2 -translate-x-1/2 z-10 bg-black/70 rounded px-2 py-0.5
          opacity-0 group-hover:opacity-100 transition-opacity cursor-grab active:cursor-grabbing"
      >
        <GripVertical className="w-4 h-4 text-zinc-400" />
      </div>

      {/* 视频预览区域 */}
      <div className="aspect-video bg-zinc-900 relative">
        <video
          ref={videoRef}
          src={item.previewUrl}
          className="w-full h-full object-cover"
          muted
          loop
          playsInline
          poster={item.thumbnailUrl}
        />

        {/* 播放/暂停按钮覆盖层 */}
        {isHovering && (
          <button
            onClick={togglePlay}
            className="absolute inset-0 flex items-center justify-center bg-black/20
              transition-colors cursor-pointer"
          >
            {isPlaying ? (
              <Pause className="w-8 h-8 text-white/80" />
            ) : (
              <Play className="w-8 h-8 text-white/80" />
            )}
          </button>
        )}
      </div>

      {/* 文件信息 */}
      <div className="p-2.5">
        <p className="text-xs text-zinc-300 truncate font-medium">{item.name}</p>
        <p className="text-xs text-zinc-500 mt-0.5">
          {(item.size / 1024 / 1024).toFixed(1)} MB
        </p>
      </div>
    </motion.div>
  )
}

// ===== 视频上传与排序区主组件 =====
interface Props {
  videos: VideoItem[]
  onVideosChange: (videos: VideoItem[]) => void
}

export default function VideoUploadZone({ videos, onVideosChange }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  // 拖拽排序传感器配置
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  )

  // 处理文件上传
  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files) return
      const newItems: VideoItem[] = Array.from(files)
        .filter((f) => f.type.startsWith('video/'))
        .map((file) => {
          const url = URL.createObjectURL(file)
          return {
            id: crypto.randomUUID(),
            file,
            name: file.name,
            size: file.size,
            thumbnailUrl: url,
            previewUrl: url,
          }
        })
      onVideosChange([...videos, ...newItems])
    },
    [videos, onVideosChange]
  )

  // 拖拽文件到上传区
  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      handleFiles(e.dataTransfer.files)
    },
    [handleFiles]
  )

  // 拖拽排序结束回调
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (over && active.id !== over.id) {
      const oldIndex = videos.findIndex((v) => v.id === active.id)
      const newIndex = videos.findIndex((v) => v.id === over.id)
      onVideosChange(arrayMove(videos, oldIndex, newIndex))
    }
  }

  const removeVideo = (id: string) => {
    const item = videos.find((v) => v.id === id)
    if (item) URL.revokeObjectURL(item.previewUrl)
    onVideosChange(videos.filter((v) => v.id !== id))
  }

  return (
    <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-300">
          视频素材 <span className="text-zinc-500 font-normal normal-case">（拖拽排序）</span>
        </h2>
        <span className="text-xs text-zinc-500">{videos.length} 个文件</span>
      </div>

      {/* 上传区域 */}
      {videos.length === 0 ? (
        <div
          onClick={() => fileInputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          className="border-2 border-dashed border-zinc-700 hover:border-purple-500/50 rounded-lg
            p-10 flex flex-col items-center justify-center gap-3 cursor-pointer
            transition-colors group"
        >
          <Upload className="w-10 h-10 text-zinc-600 group-hover:text-purple-400 transition-colors" />
          <p className="text-sm text-zinc-500 group-hover:text-zinc-400">
            拖拽视频文件到此处，或 <span className="text-purple-400">点击上传</span>
          </p>
          <p className="text-xs text-zinc-600">支持 MP4, MOV, AVI, MKV</p>
        </div>
      ) : (
        <>
          {/* 可排序视频网格 */}
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext items={videos.map((v) => v.id)} strategy={rectSortingStrategy}>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                <AnimatePresence>
                  {videos.map((item, index) => (
                    <SortableVideoCard
                      key={item.id}
                      item={item}
                      index={index}
                      onRemove={removeVideo}
                    />
                  ))}
                </AnimatePresence>

                {/* 添加更多按钮 */}
                <div
                  onClick={() => fileInputRef.current?.click()}
                  onDrop={handleDrop}
                  onDragOver={(e) => e.preventDefault()}
                  className="aspect-video border-2 border-dashed border-zinc-700 hover:border-purple-500/50
                    rounded-lg flex flex-col items-center justify-center gap-2 cursor-pointer
                    transition-colors group"
                >
                  <Upload className="w-6 h-6 text-zinc-600 group-hover:text-purple-400 transition-colors" />
                  <span className="text-xs text-zinc-500">添加更多</span>
                </div>
              </div>
            </SortableContext>
          </DndContext>
        </>
      )}

      {/* 隐藏的文件输入 */}
      <input
        ref={fileInputRef}
        type="file"
        accept="video/*"
        multiple
        className="hidden"
        onChange={(e) => {
          handleFiles(e.target.files)
          e.target.value = ''
        }}
      />
    </div>
  )
}
