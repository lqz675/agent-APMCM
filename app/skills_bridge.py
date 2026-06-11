import os
import sys
import subprocess
import tempfile
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent / "skills"

SCIPILOT_DIR = SKILLS_DIR / "scipilot-figure-skill" / "scripts"
GPT_ACADEMIC_DIR = SKILLS_DIR / "gpt_academic"
RAGFLOW_SDK_DIR = SKILLS_DIR / "ragflow" / "sdk" / "python"


def _ensure_scipilot_path():
    if str(SCIPILOT_DIR) not in sys.path:
        sys.path.insert(0, str(SCIPILOT_DIR))


def profile_data(data_source, group_cols=None):
    _ensure_scipilot_path()
    from profile_data import profile_data as _profile_data
    return _profile_data(data_source, group_cols)


def setup_style(journal="nature", lang="en", use_sciplots=True, serif_for_zh=True):
    _ensure_scipilot_path()
    from setup_style import setup_style as _setup_style
    return _setup_style(journal, lang, use_sciplots, serif_for_zh)


def export_figure(fig, basename, formats=None, dpi=300, size_inches=None, grayscale_preview=False):
    _ensure_scipilot_path()
    from export_figure import export_figure as _export_figure
    return _export_figure(fig, basename, formats, dpi, size_inches, grayscale_preview)


def check_figure(path, min_dpi=300, target_inches=None):
    _ensure_scipilot_path()
    from check_figure import check_figure as _check_figure
    return _check_figure(path, min_dpi, target_inches)


def gpt_academic_polish(text, api_key=None, base_url=None):
    config_py = GPT_ACADEMIC_DIR / "config.py"
    if not config_py.exists():
        return "gpt_academic 未正确克隆,请检查 skills/gpt_academic/ 目录"

    result = subprocess.run(
        [sys.executable, "-c", f"""
import sys
sys.path.insert(0, r"{GPT_ACADEMIC_DIR}")
from toolbox import get_conf, ChatGLMHandler
API_KEY = "{api_key or ''}"
API_URL_REDIRECT = {{"https://api.openai.com/v1/chat/completions": "{base_url or 'https://api.openai.com/v1/chat/completions'}"}}
# Fallback: use OpenAI direct call for polish
from openai import OpenAI
client = OpenAI(api_key=API_KEY or None, base_url="{base_url or 'https://api.openai.com/v1'}")
resp = client.chat.completions.create(
    model="gpt-4o",
    messages=[{{"role":"system","content":"你是学术论文编辑,请润色以下论文"}},{{"role":"user","content":"{text[:4000]}"}}],
    max_tokens=4096
)
print(resp.choices[0].message.content)
"""],
        capture_output=True, text=True, timeout=120,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    )
    if result.returncode != 0:
        return f"润色出错: {result.stderr}"
    return result.stdout


def ragflow_sdk_query(api_key, base_url, dataset_name, query_text, topk=5):
    sdk_path = str(RAGFLOW_SDK_DIR)
    if sdk_path not in sys.path:
        sys.path.insert(0, sdk_path)
    try:
        from ragflow_sdk import RAGFlow
        rag = RAGFlow(api_key=api_key, base_url=base_url)
        ds = rag.get_dataset(name=dataset_name)
        if ds is None:
            ds = rag.create_dataset(name=dataset_name)
        results = ds.retrieve(question=query_text, top_k=topk)
        return results
    except ImportError:
        return "请先安装 ragflow-sdk: pip install ragflow-sdk"
    except Exception as e:
        return f"RAGFlow查询出错: {e}"
