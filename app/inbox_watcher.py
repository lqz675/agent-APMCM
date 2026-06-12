"""扫描并管理 inbox/ 目录中的文件，支持增量加载。"""
import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INBOX_ROOT = PROJECT_ROOT / "inbox"
INBOX_SUBDIRS = ["problems", "papers", "references", "knowledge", "web_ai", "data"]
PROCESSED_CACHE = INBOX_ROOT / ".processed_files.json"


def ensure_inbox_dirs():
    """确保 inbox/ 及所有子目录存在，程序启动时调用一次。"""
    INBOX_ROOT.mkdir(parents=True, exist_ok=True)
    for sub in INBOX_SUBDIRS:
        (INBOX_ROOT / sub).mkdir(parents=True, exist_ok=True)


def _load_processed_log():
    """读取已处理文件记录，返回 {path: iso_timestamp} 字典。"""
    try:
        if PROCESSED_CACHE.exists():
            with open(PROCESSED_CACHE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_processed_log(data):
    """保存已处理文件记录到 JSON 文件。"""
    try:
        INBOX_ROOT.mkdir(parents=True, exist_ok=True)
        with open(PROCESSED_CACHE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def scan_subdir(subdir_name):
    """扫描 inbox/{subdir_name}/ 目录，返回所有支持文件的 Path 列表。

    - problems/papers/references/knowledge: 扫描 .pdf 文件
    - web_ai: 扫描 .pdf / .md / .txt 文件
    """
    subdir_path = INBOX_ROOT / subdir_name
    if not subdir_path.exists():
        return []

    extensions = [".pdf"]
    if subdir_name == "web_ai":
        extensions.extend([".md", ".txt"])
    elif subdir_name == "data":
        extensions = [".csv", ".xlsx", ".xls"]

    files = []
    for ext in extensions:
        files.extend(subdir_path.rglob(f"*{ext}"))
    return sorted(files, key=lambda p: p.stat().st_mtime)


def get_new_files(subdir_name):
    """对比 PROCESSED_CACHE，返回尚未处理过的新文件列表。"""
    all_files = scan_subdir(subdir_name)
    processed = _load_processed_log()
    return [f for f in all_files if str(f) not in processed]


def mark_as_processed(paths):
    """将这些路径记录到 PROCESSED_CACHE（记录时间为当前 ISO 时间戳）。"""
    if not paths:
        return
    processed = _load_processed_log()
    now = datetime.now().isoformat()
    for p in paths:
        processed[str(p)] = now
    _save_processed_log(processed)


def get_inbox_status():
    """返回各子目录的文件统计。

    Returns:
        dict: {"problems": {"total": int, "new": int}, ...}
    """
    status = {}
    for sub in INBOX_SUBDIRS:
        all_files = scan_subdir(sub)
        new_files = get_new_files(sub)
        status[sub] = {"total": len(all_files), "new": len(new_files)}
    return status


def read_web_ai_file(filename):
    """读取 inbox/web_ai/{filename} 文件内容并返回字符串。

    .pdf 文件调用 utils.load_file_as_text() 读取，其他格式直接 UTF-8 读取。
    若文件不存在，抛出 FileNotFoundError 并附带友好提示。

    Args:
        filename (str): web_ai 子目录下的文件名

    Returns:
        str: 文件内容

    Raises:
        FileNotFoundError: 文件不存在
    """
    from app.utils import load_file_as_text

    file_path = INBOX_ROOT / "web_ai" / filename
    if not file_path.exists():
        raise FileNotFoundError(
            f"文件不存在: {file_path}\n"
            f"请先将网页版 AI 的回复保存到 inbox/web_ai/ 目录下，"
            f"确保文件名正确。当前 web_ai 目录内容: "
            f"{[p.name for p in scan_subdir('web_ai')]}"
        )

    return load_file_as_text(str(file_path))


def read_data_file(filename):
    """从 inbox/data/{filename} 读取表格文件并返回文本摘要。

    调用 utils.load_tabular_file() 读取，支持 .csv / .xlsx / .xls。
    若文件不存在，返回错误提示字符串。

    Args:
        filename (str): data 子目录下的文件名

    Returns:
        str: 表格文件文本摘要
    """
    from app.utils import load_tabular_file

    file_path = INBOX_ROOT / "data" / filename
    if not file_path.exists():
        return f"❌ 文件不存在：inbox/data/{filename}"
    return load_tabular_file(str(file_path))
