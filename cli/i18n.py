"""简易中英双语文案。"""

TEXTS = {
    "app_title": {
        "zh": "节拍视频编辑器 CLI",
        "en": "Beat Video Editor CLI",
    },
    "current_project": {
        "zh": "当前项目",
        "en": "Current project",
    },
    "project_created": {
        "zh": "项目创建成功",
        "en": "Project created",
    },
    "project_deleted": {
        "zh": "项目删除成功",
        "en": "Project deleted",
    },
    "project_switched": {
        "zh": "已切换项目",
        "en": "Project switched",
    },
    "project_exists": {
        "zh": "项目已存在",
        "en": "Project already exists",
    },
    "project_not_found": {
        "zh": "项目不存在",
        "en": "Project not found",
    },
    "lang_set": {
        "zh": "语言已切换",
        "en": "Language switched",
    },
    "select_split_mode": {
        "zh": "请选择 SRT 分割方式 (word/comma/sentence/none)",
        "en": "Choose SRT split mode (word/comma/sentence/none)",
    },
    "srt_generated": {
        "zh": "SRT 生成完成",
        "en": "SRT generated",
    },
    "audio_missing": {
        "zh": "当前项目未找到音频，请先把音频放入 raw_materials/song",
        "en": "No audio found. Put audio into raw_materials/song first",
    },
    "ask_generate_srt": {
        "zh": "未找到字幕，是否先生成 SRT？",
        "en": "No SRT found. Generate SRT first?",
    },
    "generate_done": {
        "zh": "视频生成完成",
        "en": "Video generation completed",
    },
    "operation_cancelled": {
        "zh": "操作已取消",
        "en": "Operation cancelled",
    },
    "srt_overwrite_confirm": {
        "zh": "已存在旧的 SRT 文件，是否重新识别并覆盖？",
        "en": "An existing SRT file was found. Re-generate and overwrite?",
    },
    "progress_overall": {
        "zh": "总进度",
        "en": "Overall",
    },
    "progress_overall_done": {
        "zh": "总进度 · 完成",
        "en": "Overall · Done",
    },
    "progress_cut_task": {
        "zh": "切片进度",
        "en": "Clip progress",
    },
    "stage_srt": {
        "zh": "字幕准备",
        "en": "Subtitle prep",
    },
    "stage_beat": {
        "zh": "节拍分析",
        "en": "Beat analysis",
    },
    "stage_cut": {
        "zh": "视频切片",
        "en": "Video cutting",
    },
    "stage_concat": {
        "zh": "拼接合成",
        "en": "Concatenating",
    },
    "stage_burn": {
        "zh": "字幕烧录",
        "en": "Burning subs",
    },
}


def t(key: str, lang: str) -> str:
    """根据语言返回文案。"""
    item = TEXTS.get(key, {})
    if lang in item:
        return item[lang]
    return item.get("zh", key)
