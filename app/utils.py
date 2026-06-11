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
