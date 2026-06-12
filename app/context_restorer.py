"""上下文重建器 — 重启后重建 RAG 索引和 LLM 上下文。"""
from pathlib import Path


def rebuild_rag_from_session(session_id, rag):
    """重启后从 workspace/{session_id}/uploads/ 和 inbox/ 重建 RAG 索引。

    Args:
        session_id (str): 会话 ID
        rag: RAG 实例（需有 add_inbox_files 方法）

    Returns:
        dict: {"uploads_loaded": int, "inbox_loaded": int, "total": int, "details": [str]}
    """
    from app.session_persistence import get_upload_dir
    from app.inbox_watcher import get_new_files, mark_as_processed

    details = []
    uploads_total = 0
    inbox_total = 0

    upload_dir = get_upload_dir(session_id)
    if upload_dir.exists():
        pdf_files = list(upload_dir.glob("*.pdf"))
        if pdf_files:
            try:
                n = rag.add_inbox_files("problems", pdf_files)
                uploads_total += n
                details.append(f"从 uploads/ 加载了 {n} 个 PDF")
            except Exception as e:
                details.append(f"uploads/ 加载失败: {e}")

    for sub in ["problems", "papers", "references", "knowledge"]:
        try:
            new_files = get_new_files(sub)
            if new_files:
                n = rag.add_inbox_files(sub, new_files)
                mark_as_processed(new_files)
                inbox_total += n
                details.append(f"从 inbox/{sub}/ 加载了 {n} 个文件")
        except Exception as e:
            details.append(f"inbox/{sub}/ 扫描失败: {e}")

    return {
        "uploads_loaded": uploads_total,
        "inbox_loaded": inbox_total,
        "total": uploads_total + inbox_total,
        "details": details,
    }


def build_context_summary(saved_state):
    """根据已恢复的 session 状态，生成给 LLM 的上下文摘要。

    Args:
        saved_state (dict): 从磁盘恢复的状态字典

    Returns:
        str: LLM 上下文摘要（Markdown 格式）
    """
    phase = saved_state.get("phase", "input")
    topic = saved_state.get("selected_topic") or "未选择"
    plan = saved_state.get("modeling_plan") or "未生成"
    prd = saved_state.get("prd_final") or saved_state.get("prd_draft") or "未生成"
    chat_history = saved_state.get("chat_history", [])

    summary = "## 会话恢复上下文\n"
    summary += f"- **当前阶段**: {phase}\n"
    summary += f"- **已选赛题**: {str(topic)[:200]}\n"
    summary += f"- **建模方案摘要**: {str(plan)[:500]}\n"

    if saved_state.get("prd_final"):
        summary += "- **PRD状态**: 已完成终稿\n"
    elif saved_state.get("prd_draft"):
        summary += "- **PRD状态**: 草稿中\n"
    else:
        summary += "- **PRD状态**: 未生成\n"

    if chat_history:
        summary += "\n## 最近对话（最近5条）\n"
        for msg in chat_history[-5:]:
            role = msg.get("role", "unknown")
            content = str(msg.get("content", ""))[:200]
            summary += f"- [{role}] {content}\n"

    summary += "\n注意：此摘要仅供恢复上下文，请基于此继续协助用户完成数学建模任务。"
    return summary


def needs_rag_rebuild(rag):
    """检查 RAG 实例的内存索引是否为空（需要重建）。

    Args:
        rag: RAG 实例

    Returns:
        bool: True 表示需要重建索引
    """
    if rag is None:
        return True

    has_problems = getattr(rag, "problem_index", None) is not None
    has_papers = getattr(rag, "paper_index", None) is not None

    if not has_problems and not has_papers:
        return True

    return False
