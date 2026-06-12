"""会话持久化 — 保存/恢复 session_state 到 workspace/ 目录。"""
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = PROJECT_ROOT / "workspace"
LATEST_SESSION_FILE = WORKSPACE_ROOT / ".latest_session"

PERSISTENT_FIELDS = [
    "phase",
    "session_id",
    "chat_history",
    "selected_topic",
    "selected_topic_idx",
    "selected_sims",
    "topics",
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
    "topic_recommendation",
    "topic_sims",
    "topic_scores",
]
UPLOAD_EXTRACT_FIELDS = [
    "extracted_0", "extracted_1", "extracted_2",
    "uploaded_name_0", "uploaded_name_1", "uploaded_name_2",
]


def save_session(session_id, state):
    """保存 session 状态到磁盘，返回是否成功。

    Args:
        session_id (str): 会话 ID
        state (dict): 当前的 session_state

    Returns:
        bool: 写入成功返回 True
    """
    try:
        session_dir = WORKSPACE_ROOT / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        json_path = session_dir / "session_state.json"
        tmp_path = session_dir / "session_state.json.tmp"

        to_save = {"saved_at": datetime.now().isoformat()}
        all_fields = PERSISTENT_FIELDS + UPLOAD_EXTRACT_FIELDS
        for field in all_fields:
            val = state.get(field)
            if val is None:
                continue
            try:
                json.dumps(val, ensure_ascii=False)
                to_save[field] = val
            except (TypeError, ValueError):
                pass

        tmp_path.write_text(
            json.dumps(to_save, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(json_path)
        return True
    except Exception as e:
        import traceback
        print(f"[session_persistence] save_session 失败: {e}")
        traceback.print_exc()
        return False


def load_session(session_id):
    """从磁盘加载 session 状态，失败时返回 None。

    Args:
        session_id (str): 会话 ID

    Returns:
        dict | None: 恢复的状态字典
    """
    try:
        json_path = WORKSPACE_ROOT / session_id / "session_state.json"
        if not json_path.exists():
            print(f"[session_persistence] load_session: 文件不存在 {json_path}")
            return None
        text = json_path.read_text(encoding="utf-8")
        data = json.loads(text)
        print(f"[session_persistence] load_session 成功: phase={data.get('phase')}, "
              f"chat_history={len(data.get('chat_history', []))} 条")
        return data
    except Exception as e:
        print(f"[session_persistence] load_session 失败: {e}")
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
            data = json.loads(state_file.read_text(encoding="utf-8"))
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


def save_latest_session_id(session_id):
    """把最近使用的 session_id 写入 workspace/.latest_session 文件。

    Args:
        session_id (str): 会话 ID
    """
    try:
        WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
        LATEST_SESSION_FILE.write_text(session_id, encoding="utf-8")
    except Exception as e:
        print(f"[session_persistence] save_latest_session_id 失败: {e}")


def get_latest_session_id():
    """从 workspace/.latest_session 读取最近的 session_id。

    Returns:
        str | None: session_id 或 None
    """
    try:
        if LATEST_SESSION_FILE.exists():
            sid = LATEST_SESSION_FILE.read_text(encoding="utf-8").strip()
            if sid and (WORKSPACE_ROOT / sid / "session_state.json").exists():
                return sid
    except Exception as e:
        print(f"[session_persistence] get_latest_session_id 失败: {e}")
    return None
