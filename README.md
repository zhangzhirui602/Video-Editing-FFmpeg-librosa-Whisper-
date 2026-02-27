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
| `LANGUAGE` | 音频语言（必填，传给 Whisper） | `Chinese` / `Swedish` / `English` |
| `WHISPER_MODEL` | Whisper 模型大小 | `small` / `medium` / `large` |
| `SRT_PATH` | SRT 字幕文件路径（可选，留空则自动生成） | `D:\素材\subtitle.srt` |
| `TOTAL_DURATION` | 音频总时长（秒，留空自动计算） | `30.0` |
| `BEATS_PER_CUT` | 每几拍切换一次视频 | `2` |
| `TEMP_DIR` | 临时文件目录 | `D:\输出\temp` |
| `OUTPUT_NO_SUB` | 无字幕中间文件路径 | `D:\输出\no_sub.mp4` |
| `FINAL_OUTPUT` | 最终输出视频路径 | `D:\输出\final.mp4` |
| `VIDEO_WIDTH` | 输出宽度（默认 1080） | `1080` |
| `VIDEO_HEIGHT` | 输出高度（默认 1920） | `1920` |
| `FPS` | 帧率（默认 30） | `30` |
| `FONT_NAME` | 字幕字体（默认新罗马） | `Times New Roman` |
| `FONT_SIZE` | 字幕字号上限（默认 18，过长会自动缩小以尽量单行显示） | `18` |
| `AUTO_FIT_FONT_SIZE` | 是否自动缩小字号以尽量单行显示（默认开启） | `true` |
| `FONT_COLOR` | 字幕颜色（默认白色） | `&H00FFFFFF` |
| `OUTLINE_COLOR` | 字幕描边颜色（当前默认不启用描边） | `&H00000000` |
| `WORD_BY_WORD_SUBTITLE` | 是否逐词显示歌词（默认开启） | `true` |

> **音频文件**：无需在 `.env` 中指定路径。将唯一一个音频文件放入项目的 `raw_materials/song/` 目录，程序会自动发现。若该目录下存在多个音频文件，程序会报错并列出文件名，需手动保留一个。

### 2. 运行 CLI

在项目根目录打开终端，运行：

```bash
uv run python main.py
```

查看帮助：

```bash
uv run python main.py --help
```

常用命令：

```bash
# 先启动交互 CLI（进入后会看到类似 default > 的提示符）
python main.py

# 在 CLI 提示符里输入以下命令：

# 查看当前项目与语言
status

# 项目管理
project list
project create demo --switch
project switch default
project delete demo -y

# 切换界面语言（中/英）
lang zh
lang en

# 生成 SRT（支持按词/逗号/句子/不拆分；模型与语言从 .env 读取）
srt
srt --split-mode word
srt --split-mode comma
srt --split-mode sentence

# 基于当前项目素材生成视频
generate

# 退出交互 CLI
exit
```

## CLI 全部命令

### 交互模式（推荐）

先启动：

```bash
python main.py
```

进入后可用命令：

```bash
# 状态
status

# 语言
lang zh
lang en

# 项目管理
project list
project create <name>
project create <name> --switch
project switch <name>
project delete <name>
project delete <name> -y

# 字幕生成（会更新 output/temp/subtitles/active.srt）
# 模型与语言从 .env 中的 WHISPER_MODEL / LANGUAGE 读取
srt
srt --split-mode word
srt --split-mode comma
srt --split-mode sentence
srt --split-mode none

# 视频生成（始终使用当前项目 output/temp/subtitles/active.srt）
generate

# 退出
exit
quit
```

### 一次性命令模式（不进入交互）

```bash
python main.py --help
python main.py status
python main.py lang zh
python main.py lang en

python main.py project list
python main.py project create <name>
python main.py project create <name> --switch
python main.py project switch <name>
python main.py project delete <name>
python main.py project delete <name> -y

python main.py srt
python main.py srt --split-mode word
python main.py srt --split-mode comma
python main.py srt --split-mode sentence
python main.py srt --split-mode none

python main.py generate
```

### 补全与历史

- 交互模式支持 `Tab` 自动补全（命令、子命令、项目名、`split-mode` 选项）
- 支持历史记录（方向键↑/↓），历史文件在 `projects/.repl_history`

首次运行时 uv 会自动安装所有依赖。`generate` 命令会依次执行：
1. 分析音频节拍
2. 按节拍裁剪视频片段
3. 拼接视频并合入音乐
4. 烧录字幕

处理完成后，最终视频会保存在当前项目目录下的 `output` 中。

## 多项目目录结构

CLI 会自动创建 `projects` 目录，每个项目互相隔离：

```text
projects/
	<project_name>/
		raw_materials/
			lyric/
			song/
			videos/
		output/
			temp/
				segs/
				subtitles/
```

## 常见问题

### Q: 提示"ffmpeg 不是内部或外部命令"
FFmpeg 没有安装或没有加入系统 PATH。请下载 FFmpeg 并将其 bin 目录添加到系统环境变量 PATH 中。

### Q: 提示"缺少必填配置项"
请检查 `.env` 文件是否存在，以及对应的配置项是否已填写。

### Q: 提示文件不存在
请确认 `.env` 中填写的字幕、视频素材路径是否正确，文件是否存在。

### Q: 提示 song 目录中存在多个音频文件
每个项目的 `raw_materials/song/` 目录下只能放一个音频文件（`.mp3`、`.wav`、`.m4a` 等），删除多余的文件后重试。

### Q: 视频比例不对
调整 `VIDEO_WIDTH` 和 `VIDEO_HEIGHT`。竖屏视频用 `1080x1920`，横屏用 `1920x1080`。

### Q: 临时文件占用空间
处理完成后可以手动删除 `TEMP_DIR` 指定的目录。
