# 节拍视频编辑器

自动根据音乐节拍切换视频片段，并烧录字幕，生成最终视频。

## 前置要求

- **FFmpeg**：需要提前安装并加入系统 PATH。下载地址：https://ffmpeg.org/download.html
- **uv**：Python 项目管理工具

### 安装 uv

打开终端（PowerShell 或 CMD），运行以下命令：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

安装完成后重启终端，输入 `uv --version` 确认安装成功。

## 快速开始

### 1. 配置 .env 文件

复制 `.env.example` 为 `.env`，然后修改其中的路径和参数：

```
copy .env.example .env
```

用记事本打开 `.env`，按照注释填写每个配置项：

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| `AUDIO_PATH` | 音频文件路径 | `D:\素材\music.mp3` |
| `SRT_PATH` | SRT 字幕文件路径 | `D:\素材\subtitle.srt` |
| `TOTAL_DURATION` | 音频总时长（秒） | `30.0` |
| `BEATS_PER_CUT` | 每几拍切换一次视频 | `2` |
| `TEMP_DIR` | 临时文件目录 | `D:\输出\temp` |
| `OUTPUT_NO_SUB` | 无字幕中间文件路径 | `D:\输出\no_sub.mp4` |
| `FINAL_OUTPUT` | 最终输出视频路径 | `D:\输出\final.mp4` |
| `VIDEO_CLIPS` | 视频素材路径，逗号分隔 | `D:\素材\1.mp4,D:\素材\2.mp4` |
| `VIDEO_WIDTH` | 输出宽度（默认 1080） | `1080` |
| `VIDEO_HEIGHT` | 输出高度（默认 1920） | `1920` |
| `FPS` | 帧率（默认 30） | `30` |
| `FONT_NAME` | 字幕字体（默认新罗马） | `Times New Roman` |
| `FONT_SIZE` | 字幕字号上限（默认 18，过长会自动缩小以尽量单行显示） | `18` |
| `AUTO_FIT_FONT_SIZE` | 是否自动缩小字号以尽量单行显示（默认开启） | `true` |
| `FONT_COLOR` | 字幕颜色（默认白色） | `&H00FFFFFF` |
| `OUTLINE_COLOR` | 字幕描边颜色（当前默认不启用描边） | `&H00000000` |
| `WORD_BY_WORD_SUBTITLE` | 是否逐词显示歌词（默认开启） | `true` |

### 2. 运行程序

在项目根目录打开终端，运行：

```bash
uv run python main.py
```

首次运行时 uv 会自动安装所有依赖，之后会依次执行：
1. 分析音频节拍
2. 按节拍裁剪视频片段
3. 拼接视频并合入音乐
4. 烧录字幕

处理完成后，最终视频会保存在 `FINAL_OUTPUT` 指定的路径。

## 常见问题

### Q: 提示"ffmpeg 不是内部或外部命令"
FFmpeg 没有安装或没有加入系统 PATH。请下载 FFmpeg 并将其 bin 目录添加到系统环境变量 PATH 中。

### Q: 提示"缺少必填配置项"
请检查 `.env` 文件是否存在，以及对应的配置项是否已填写。

### Q: 提示文件不存在
请确认 `.env` 中填写的音频、字幕、视频素材路径是否正确，文件是否存在。

### Q: 视频比例不对
调整 `VIDEO_WIDTH` 和 `VIDEO_HEIGHT`。竖屏视频用 `1080x1920`，横屏用 `1920x1080`。

### Q: 临时文件占用空间
处理完成后可以手动删除 `TEMP_DIR` 指定的目录。
