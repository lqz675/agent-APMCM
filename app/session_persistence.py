"""会话持久化 — 保存/恢复 session_state 到 workspace/ 目录。"""
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = PROJECT_ROOT / "workspace"

PERSISTENT_FIELDS = [
    "phase",
    "session_id",
    "chat_history",
    "selected_topic",
    "topics_text",
    "modeling_plan",
    "prd_draft",
    "prd_final",
    "pressure_report",
    "uploaded_file_paths",
    "loaded_data_files",
    "webai_imported_content",
    "completed_stages",
    "coding_result",
    "figure_descriptions",
    "paper_draft",
    "polished_paper",
    "paper_sections",
    "grill_rounds",
    "reference_loaded",
]


def save_session(session_id, state):
    """从 state 中提取持久化字段，原子写入 workspace/{session_id}/session_state.json。

    Args:
        session_id (str): 会话 ID
        state (dict): 当前的 session_state 或部分状态字典
    """
    session_dir = WORKSPACE_ROOT / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    snapshot = {}
    for key in PERSISTENT_FIELDS:
        val = state.get(key)
        if val is None:
            continue
        try:
            json.dumps(val, ensure_ascii=False)
            snapshot[key] = val
        except (TypeError, ValueError):
            try:
                snapshot[key] = str(val)
            except Exception:
                pass

    snapshot["saved_at"] = datetime.now().isoformat()

    tmp_path = session_dir / "session_state.json.tmp"
    target_path = session_dir / "session_state.json"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    tmp_path.replace(target_path)


def load_session(session_id):
    """从 workspace/{session_id}/session_state.json 读取已保存状态。

    Args:
        session_id (str): 会话 ID

    Returns:
        dict | None: 恢复的状态字典，若不存在或解析失败返回 None
    """
    file_path = WORKSPACE_ROOT / session_id / "session_state.json"
    if not file_path.exists():
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        result = {}
        for key in PERSISTENT_FIELDS:
            if key in data:
                result[key] = data[key]
        result["saved_at"] = data.get("saved_at", "")
        return result
    except (json.JSONDecodeError, OSError):
        return None


def list_sessions():
    """扫描 workspace/ 下所有含 session_state.json 的子目录。

    Returns:
        list[dict]: 按 saved_at 倒序排列的会话列表
    """
    if not WORKSPACE_ROOT.exists():
        return []

    sessions = []
    for d in sorted(WORKSPACE_ROOT.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        state_file = d / "session_state.json"
        if not state_file.exists():
            continue
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            upload_dir = d / "uploads"
            upload_count = len(list(upload_dir.glob("*"))) if upload_dir.exists() else 0
            sessions.append({
                "session_id": d.name,
                "phase": data.get("phase", "unknown"),
                "saved_at": data.get("saved_at", ""),
                "upload_count": upload_count,
            })
        except Exception:
            sessions.append({
                "session_id": d.name,
                "phase": "unknown",
                "saved_at": "",
                "upload_count": 0,
            })

    sessions.sort(key=lambda x: x["saved_at"], reverse=True)
    return sessions


def get_upload_dir(session_id):
    """返回 workspace/{session_id}/uploads/ 并确保目录存在。

    Args:
        session_id (str): 会话 ID

    Returns:
        Path: uploads 目录路径
    """
    upload_dir = WORKSPACE_ROOT / session_id / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def copy_uploaded_file(session_id, file_bytes, filename):
    """将上传文件字节写入持久化目录。

    若同名文件已存在，不覆盖，直接返回已有路径。

    Args:
        session_id (str): 会话 ID
        file_bytes (bytes): 文件字节数据
        filename (str): 原始文件名

    Returns:
        Path: 保存后的文件路径
    """
    upload_dir = get_upload_dir(session_id)
    target = upload_dir / filename
    if not target.exists():
        target.write_bytes(file_bytes)
    return target


def get_session_id_from_url(query_params):
    """从 Streamlit query_params 读取 session 参数。

    Args:
        query_params (dict): st.query_params 转换后的字典

    Returns:
        str | None: session_id 或 None
    """
    sid = query_params.get("session", "")
    if isinstance(sid, list):
        sid = sid[0] if sid else ""
    return sid if sid else None
