"""在 agent 工作流与 AI 网页版之间搭建文件交换桥梁。

- 导出方向：将当前阶段上下文打包为 .md 文件
- 导入方向：从 inbox/web_ai/ 读取网页版 AI 的回复
"""
import json
from pathlib import Path
from datetime import datetime

from app.utils import load_file_as_text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEBAI_EXPORT_SUBDIR = "webai_collab"


def export_context_package(phase, session_id, context, workspace_root):
    """将当前阶段上下文打包为 Markdown 文件并保存。

    保存路径：workspace_root/{session_id}/webai_collab/export_{phase}_{YYYYMMDD_HHMMSS}.md

    Args:
        phase (str): 当前阶段英文名
        session_id (str): 会话 ID
        context (dict): 完整的 session_state 或上下文字典
        workspace_root (Path): workspace 根目录 Path 对象

    Returns:
        Path: 导出文件的路径
    """
    export_dir = workspace_root / session_id / WEBAI_EXPORT_SUBDIR
    export_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"export_{phase}_{timestamp}.md"
    export_path = export_dir / filename

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    content = f"""---
# APMCM Agent → 网页版 AI 上下文包
**导出时间**: {now_str}
**当前阶段**: {phase}
**Session ID**: {session_id}

## 赛题内容
{context.get("topics", "（未上传）")}

## 已选赛题
{context.get("selected_topic", "（未选择）")}

## 建模方案（摘要）
{str(context.get("modeling_plan", "（未生成）"))[:2000]}

## 压力测试报告（摘要）
{str(context.get("pressure_report", "（未生成）"))[:1000]}

## PRD 最终版（摘要）
{str(context.get("prd_final", context.get("prd_draft", "（未生成）")))[:2000]}

## 当前阶段任务说明
{_get_phase_instruction(phase)}

## 对话历史（最近 10 条）
{_format_chat_history(context.get("chat_history", [])[-10:])}
---

> 此文件由 APMCM Agent 自动生成，请上传给网页版 AI 以获取协作帮助。
"""
    export_path.write_text(content, encoding="utf-8")
    return export_path


def _get_phase_instruction(phase):
    """根据 phase 返回一段给网页版 AI 的任务说明文字。

    Args:
        phase (str): 当前阶段英文名

    Returns:
        str: 任务说明文字
    """
    instructions = {
        "input": "请帮我分析上传的赛题，提取关键信息",
        "topic_selection": "请基于上述赛题和已有分析，帮我进一步确认最优选题",
        "modeling": "请审查以下建模方案，提出改进意见",
        "coding": "请审查以下代码生成方案，检查数学逻辑和代码结构",
        "figure": "请审查图表设计方案，提出改进建议",
        "paper": "请审查论文初稿，提出润色建议",
        "polish": "请对论文进行学术润色",
    }
    return instructions.get(phase, "请基于上述上下文继续协助完成任务")


def _format_chat_history(history):
    """将 chat_history 格式化为 Markdown 文本。

    Args:
        history (list): 聊天记录列表，每条格式 {"role": str, "content": str}

    Returns:
        str: Markdown 格式的聊天历史
    """
    if not history:
        return "（暂无对话记录）"

    lines = []
    for msg in history:
        role = msg.get("role", "unknown")
        content = str(msg.get("content", ""))
        truncated = content[:300] + ("..." if len(content) > 300 else "")
        lines.append(f"**{role}**: {truncated}")

    return "\n\n".join(lines)


def import_webai_response(filename):
    """从 inbox/web_ai/{filename} 读取网页版 AI 的回复。

    Args:
        filename (str): 文件名（如 chatgpt_reply.md）

    Returns:
        str: 文件内容字符串；若文件不存在，返回错误提示字符串（不抛异常）
    """
    from app.inbox_watcher import read_web_ai_file

    try:
        return read_web_ai_file(filename)
    except FileNotFoundError as e:
        return f"❌ {e}"


def list_export_files(session_id, workspace_root):
    """列出当前 session 所有已导出的文件。

    Args:
        session_id (str): 会话 ID
        workspace_root (Path): workspace 根目录 Path 对象

    Returns:
        list[dict]: [{"filename": str, "phase": str, "path": str, "created_at": str}, ...]
    """
    export_dir = workspace_root / session_id / WEBAI_EXPORT_SUBDIR
    if not export_dir.exists():
        return []

    results = []
    for f in sorted(export_dir.glob("export_*.md")):
        name = f.name
        stem = f.stem  # export_{phase}_{timestamp}
        parts = stem.split("_", 2)  # ["export", phase, timestamp]
        phase = parts[1] if len(parts) >= 2 else "unknown"
        ts_raw = parts[2] if len(parts) >= 3 else ""
        created_at = ts_raw
        if len(ts_raw) == 15:  # YYYYMMDD_HHMMSS
            created_at = f"{ts_raw[:4]}-{ts_raw[4:6]}-{ts_raw[6:8]} {ts_raw[9:11]}:{ts_raw[11:13]}:{ts_raw[13:15]}"

        results.append({
            "filename": name,
            "phase": phase,
            "path": str(f),
            "created_at": created_at,
        })

    return sorted(results, key=lambda x: x["filename"], reverse=True)
