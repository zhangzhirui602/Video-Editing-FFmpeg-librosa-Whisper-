"""启动 FastAPI 后端服务。"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["src"],          # 只监听 src/ 目录的 Python 代码变化
        reload_includes=["*.py"],     # 只关注 .py 文件
    )
