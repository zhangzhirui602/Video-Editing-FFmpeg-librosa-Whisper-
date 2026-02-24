import { Film, Wifi, WifiOff } from 'lucide-react'
import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'

export default function Header() {
  // 模拟 API 连接状态
  const [connected, setConnected] = useState(true)

  useEffect(() => {
    // 模拟连接状态切换（真实场景中通过心跳检测）
    const interval = setInterval(() => {
      setConnected(true)
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <header className="flex items-center justify-between px-6 py-3 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-sm sticky top-0 z-50">
      {/* Logo 与项目名称 */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-purple-600 to-violet-500 flex items-center justify-center">
          <Film className="w-5 h-5 text-white" />
        </div>
        <h1 className="text-lg font-bold tracking-tight">
          AutoCut <span className="text-purple-400">Pro</span>
        </h1>
      </div>

      {/* API 连接状态指示器 */}
      <motion.div
        className="flex items-center gap-2 text-sm"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        {connected ? (
          <>
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500" />
            </span>
            <Wifi className="w-4 h-4 text-green-400" />
            <span className="text-zinc-400">Local API Connected</span>
          </>
        ) : (
          <>
            <span className="h-2.5 w-2.5 rounded-full bg-red-500" />
            <WifiOff className="w-4 h-4 text-red-400" />
            <span className="text-zinc-500">Disconnected</span>
          </>
        )}
      </motion.div>
    </header>
  )
}
