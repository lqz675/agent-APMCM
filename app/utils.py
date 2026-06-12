import os
import json
import hashlib
from pathlib import Path
from pypdf import PdfReader


def load_texts(folder):
    texts = []
    filenames = []
    if not os.path.exists(folder):
        return texts, filenames
    for root, dirs, files in os.walk(folder):
        for fn in sorted(files):
            if fn.endswith(".pdf"):
                path = os.path.join(root, fn)
                try:
                    txt = ""
                    pdf = PdfReader(path)
                    for page in pdf.pages:
                        extracted = page.extract_text()
                        if extracted:
                            txt += extracted + "\n"
                    if txt.strip():
                        texts.append(txt)
                        filenames.append(os.path.relpath(path, folder))
                except Exception:
                    continue
    return texts, filenames


def chunk_text(text, max_tokens=8000):
    paragraphs = text.split("\n")
    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) < max_tokens * 4:
            current += para + "\n"
        else:
            if current.strip():
                chunks.append(current.strip())
            current = para + "\n"
    if current.strip():
        chunks.append(current.strip())
    return chunks


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_config():
    config_path = Path(__file__).parent.parent / ".env"
    config = {}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    config[key.strip()] = val.strip().strip('"').strip("'")
    return config


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_file_as_text(filepath, max_chars=50000):
    """通用文件内容读取函数，根据扩展名选择读取方式。

    - .pdf → 使用 pypdf.PdfReader 逐页提取文本
    - .md / .txt / 其他 → 直接 UTF-8 读取

    Args:
        filepath (str | Path): 文件路径
        max_chars (int): 最大返回字符数，超出部分截断

    Returns:
        str: 读取到的文本内容

    Raises:
        FileNotFoundError: 文件不存在
        RuntimeError: 读取失败
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"文件不存在: {filepath}")

    try:
        ext = filepath.suffix.lower()
        if ext == ".pdf":
            txt = ""
            pdf = PdfReader(str(filepath))
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    txt += extracted + "\n"
        else:
            with open(filepath, "r", encoding="utf-8") as f:
                txt = f.read()
    except Exception as e:
        raise RuntimeError(f"读取文件失败: {filepath} - {e}") from e

    if txt is None:
        txt = ""

    original_len = len(txt)
    if original_len > max_chars:
        txt = txt[:max_chars] + f"\n\n[...内容已截断，原始长度 {original_len} 字符]"

    return txt


def load_tabular_file(filepath, max_rows=200):
    """读取 CSV 或 Excel 文件，返回适合注入 LLM 上下文的文本摘要。

    处理逻辑：
    - .csv  → pandas.read_csv，自动检测编码（先 utf-8，失败则 gbk）
    - .xlsx / .xls → pandas.read_excel，读取第一个 sheet
    - 只保留前 max_rows 行
    - 返回 Markdown 格式的摘要文本

    Args:
        filepath (str | Path): 文件路径
        max_rows (int): 最大预览行数

    Returns:
        str: 包含文件名、形状、列名、数据预览的 Markdown 文本

    Raises:
        ImportError: pandas 未安装
        FileNotFoundError: 文件不存在
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError(
            "需要安装 pandas 和 openpyxl 才能读取表格文件。\n"
            "请运行: pip install pandas openpyxl"
        )

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"文件不存在: {filepath}")

    ext = filepath.suffix.lower()

    if ext == ".csv":
        try:
            df = pd.read_csv(filepath, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(filepath, encoding="gbk")
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(filepath, engine="openpyxl" if ext == ".xlsx" else "xlrd")
    else:
        raise ValueError(f"不支持的文件格式: {ext}，仅支持 .csv / .xlsx / .xls")

    total_rows = len(df)
    preview = df.head(max_rows)
    markdown_table = preview.to_markdown(index=False)

    summary = (
        f"文件名: {filepath.name}\n"
        f"形状: {total_rows} 行 × {len(df.columns)} 列\n"
        f"列名: {', '.join(str(c) for c in df.columns)}\n\n"
        f"数据预览:\n{markdown_table}"
    )
    if total_rows > max_rows:
        summary += f"\n\n[...已截断，共 {total_rows} 行]"

    return summary


def list_data_files(data_dir):
    """列出指定目录下所有 CSV/Excel 文件的基本信息，不读取内容。

    Args:
        data_dir (str | Path): 数据目录路径

    Returns:
        list[dict]: 文件信息列表，每项包含 name/path/ext/size_kb/relative
    """
    data_dir = Path(data_dir)
    if not data_dir.exists():
        return []

    valid_exts = {".csv", ".xlsx", ".xls"}
    results = []
    for f in sorted(data_dir.rglob("*")):
        if f.is_file() and f.suffix.lower() in valid_exts:
            size_kb = round(f.stat().st_size / 1024, 1)
            results.append({
                "name": f.name,
                "path": str(f.absolute()),
                "ext": f.suffix.lower(),
                "size_kb": size_kb,
                "relative": str(f.relative_to(data_dir)),
            })
    return results


# ── 会话持久化 ──

SESSION_KEYS = [
    "phase", "topics", "selected_topic", "selected_topic_idx", "selected_sims",
    "modeling_plan", "pressure_report", "pressure_test_result",
    "prd_draft", "prd_final", "grill_rounds", "grill_result",
    "coding_result", "figure_descriptions", "paper_draft", "polished_paper",
    "paper_sections", "completed_stages", "reference_loaded",
    "topic_recommendation", "topic_sims", "topic_scores",
    "chat_history", "user_approach", "user_expectation",
    "loaded_data_files",
]


def save_session_snapshot(session_id, session_state):
    """将关键 session_state 序列化到 memory/{session_id}/session_snapshot.json"""
    from pathlib import Path
    import json

    snapshot = {}
    for key in SESSION_KEYS:
        val = session_state.get(key)
        if val is not None:
            try:
                json.dumps(val, ensure_ascii=False)
                snapshot[key] = val
            except (TypeError, ValueError):
                snapshot[key] = str(val)

    snapshot_dir = Path(__file__).resolve().parent.parent / "memory" / session_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snap_path = snapshot_dir / "session_snapshot.json"
    with open(snap_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    return str(snap_path)


def load_session_snapshot(session_id):
    """从 memory/{session_id}/session_snapshot.json 恢复会话状态"""
    import json
    from pathlib import Path

    snap_path = Path(__file__).resolve().parent.parent / "memory" / session_id / "session_snapshot.json"
    if not snap_path.exists():
        return {}
    with open(snap_path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_saved_sessions():
    """列出所有已保存的会话"""
    from pathlib import Path
    memory_root = Path(__file__).resolve().parent.parent / "memory"
    if not memory_root.exists():
        return []
    sessions = []
    for d in sorted(memory_root.iterdir(), reverse=True):
        snap = d / "session_snapshot.json"
        if snap.exists():
            sessions.append({"session_id": d.name, "snapshot_path": str(snap)})
    return sessions


def build_context_from_workspace(session_state):
    """重启后从 workspace 目录扫描文件，重建上下文摘要"""
    from pathlib import Path

    workspace = Path(__file__).resolve().parent.parent / "workspace" / session_state.get("session_id", "")
    context_parts = []

    prd_path = workspace / "PRD.md"
    if prd_path.exists() and not session_state.get("prd_final"):
        try:
            content = prd_path.read_text(encoding="utf-8")[:2000]
            session_state["prd_final"] = content
            context_parts.append(f"PRD已从workspace恢复（{len(content)}字符）")
        except Exception:
            pass

    code_path = workspace / "model_solution.py"
    if code_path.exists() and not session_state.get("coding_result"):
        try:
            content = code_path.read_text(encoding="utf-8")[:3000]
            session_state["coding_result"] = content
            context_parts.append(f"代码已从workspace恢复（{len(content)}字符）")
        except Exception:
            pass

    paper_path = workspace / "paper.md"
    if paper_path.exists() and not session_state.get("paper_draft"):
        try:
            content = paper_path.read_text(encoding="utf-8")[:3000]
            session_state["paper_draft"] = content
            context_parts.append(f"论文已从workspace恢复（{len(content)}字符）")
        except Exception:
            pass

    return context_parts
