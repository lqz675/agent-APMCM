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
