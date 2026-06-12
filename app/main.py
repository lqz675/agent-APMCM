import streamlit as st
import os
import sys
import io
from pathlib import Path
from datetime import datetime

APP_DIR = Path(__file__).parent
sys.path.insert(0, str(APP_DIR))

from rag import RAG
from model import gpt_analysis, gpt_with_retry, chat
from prompts import (
    get_topic_selection_prompt,
    get_modeling_prompt,
    get_coding_prompt,
    get_figure_prompt,
    get_paper_writing_prompt,
    get_polish_prompt,
    get_pressure_test_prompt,
    get_grill_me_prompt
)
from workflow_logger import WorkflowLogger
from skills_bridge import SCIPILOT_DIR, GPT_ACADEMIC_DIR, SKILLS_DIR
from skills_runner  import run_pressure_test, run_grill_me, run_code_check, get_skill_comparison
from prd_generator  import generate_prd, generate_claude_md, export_prd_file
from quota_monitor  import QuotaMonitor
from app.inbox_watcher import (
    ensure_inbox_dirs, get_inbox_status, get_new_files,
    mark_as_processed, read_data_file
)
from app.webai_bridge import (
    export_context_package, import_webai_response, list_export_files
)
from app.memory_logger import MemoryLogger
from app.utils import load_tabular_file, list_data_files
from app.session_persistence import (
    save_session, load_session, list_sessions,
    copy_uploaded_file, get_upload_dir, get_session_id_from_url,
    save_latest_session_id, get_latest_session_id
)
from app.context_restorer import (
    rebuild_rag_from_session, build_context_summary, needs_rag_rebuild
)

st.set_page_config(page_title="APMCM 数学建模 Agent", page_icon="🎓", layout="wide")


@st.cache_resource
def init_rag():
    return RAG(
        problems_dir="dataset/problems",
        papers_dir="dataset/papers",
        references_dir="dataset/references"
    )


if "rag" not in st.session_state:
    with st.spinner("正在初始化 RAG 引擎，首次加载需要向量化全部 PDF (~1分钟)..."):
        st.session_state.rag = init_rag()
if "logger" not in st.session_state:
    st.session_state.logger = WorkflowLogger()
if "phase" not in st.session_state:
    st.session_state.phase = "input"
if "topics" not in st.session_state:
    st.session_state.topics = []
if "selected_topic" not in st.session_state:
    st.session_state.selected_topic = None
if "modeling_plan" not in st.session_state:
    st.session_state.modeling_plan = None
if "coding_result" not in st.session_state:
    st.session_state.coding_result = None
if "figure_descriptions" not in st.session_state:
    st.session_state.figure_descriptions = None
if "paper_draft" not in st.session_state:
    st.session_state.paper_draft = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "_init_done" not in st.session_state:
    st.session_state._init_done = True

    if "session_id" not in st.session_state:
        recovered_id = (
            get_session_id_from_url(dict(st.query_params))
            or get_latest_session_id()
        )
        if recovered_id:
            st.session_state.session_id = recovered_id
        else:
            st.session_state.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        st.query_params["session"] = st.session_state.session_id
    except Exception:
        pass
    save_latest_session_id(st.session_state.session_id)

    saved = load_session(st.session_state.session_id)
    if saved:
        for k, v in saved.items():
            if k not in ("_init_done",):
                st.session_state[k] = v
        st.session_state.state_restored = True
    else:
        st.session_state.state_restored = False

for k, v in {
    "uploaded_file_paths": [],
    "rag_rebuilt": False,
    "context_summary": "",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══ DEBUG PANEL ══
with st.sidebar:
    with st.expander("🔍 DEBUG", expanded=False):
        import json as _json
        sid = st.session_state.get("session_id", "?")
        st.write(f"session_id: `{sid}`")
        st.write(f"state_restored: `{st.session_state.get('state_restored')}`")
        st.write(f"rag_rebuilt: `{st.session_state.get('rag_rebuilt')}`")
        json_path = Path(__file__).resolve().parent.parent / "workspace" / sid / "session_state.json"
        st.write(f"json存在: `{json_path.exists()}`")
        if json_path.exists():
            d = _json.loads(json_path.read_text(encoding="utf-8"))
            st.write(f"phase: `{d.get('phase')}`")
            st.write(f"chat_history: {len(d.get('chat_history', []))} 条")
            st.write(f"uploaded_file_paths: {len(d.get('uploaded_file_paths', []))} 个")
        up_dir = Path(__file__).resolve().parent.parent / "workspace" / sid / "uploads"
        st.write(f"uploads目录: `{up_dir.exists()}` 文件数: {len(list(up_dir.iterdir())) if up_dir.exists() else 0}")

if "quota_monitor" not in st.session_state:
    st.session_state.quota_monitor = QuotaMonitor(platform="Claude Sonnet")
if "completed_stages" not in st.session_state:
    st.session_state.completed_stages = []
if "prd_draft" not in st.session_state:
    st.session_state.prd_draft = ""
if "prd_final" not in st.session_state:
    st.session_state.prd_final = ""
if "grill_rounds" not in st.session_state:
    st.session_state.grill_rounds = 0
if "pressure_report" not in st.session_state:
    st.session_state.pressure_report = ""
if "paper_sections" not in st.session_state:
    st.session_state.paper_sections = {}
if "reference_loaded" not in st.session_state:
    st.session_state.reference_loaded = False
if "memory_logger" not in st.session_state:
    st.session_state.memory_logger = None
if "webai_import_filename" not in st.session_state:
    st.session_state.webai_import_filename = ""
if "webai_imported_content" not in st.session_state:
    st.session_state.webai_imported_content = ""
if "inbox_last_scan" not in st.session_state:
    st.session_state.inbox_last_scan = None
if "loaded_data_files" not in st.session_state:
    st.session_state.loaded_data_files = {}

if st.session_state.memory_logger is None:
    st.session_state.memory_logger = MemoryLogger(st.session_state.session_id)

ensure_inbox_dirs()

logger = st.session_state.logger
rag = st.session_state.rag

PHASE_DOWNSTREAM = {
    "input":        ["topic_sims","topic_scores","topic_recommendation","modeling_plan","coding_result","paper_draft","pressure_report","prd_draft","prd_final","figure_descriptions","polished_paper","paper_sections","selected_topic","selected_topic_idx","selected_sims","completed_stages","grill_rounds","pressure_test_result","grill_result"],
    "topic_selection":["modeling_plan","coding_result","paper_draft","pressure_report","prd_draft","prd_final","figure_descriptions","polished_paper","paper_sections","selected_topic","selected_topic_idx","selected_sims","completed_stages","grill_rounds","pressure_test_result","grill_result"],
    "modeling":      ["pressure_report","prd_draft","prd_final","coding_result","paper_draft","figure_descriptions","polished_paper","paper_sections","grill_result"],
    "coding":        ["paper_draft","figure_descriptions","polished_paper","paper_sections"],
    "figure":        ["paper_draft","polished_paper"],
    "paper":         ["polished_paper"],
}

def clear_downstream(phase):
    """回到某阶段时，清除该阶段及之后所有下游结果"""
    for key in PHASE_DOWNSTREAM.get(phase, []):
        st.session_state.pop(key, None)

def autosave():
    """保存当前 session 状态到磁盘（带错误保护）"""
    ok = save_session(st.session_state.session_id, dict(st.session_state))
    save_latest_session_id(st.session_state.session_id)
    return ok

if (st.session_state.state_restored
        and not st.session_state.rag_rebuilt
        and needs_rag_rebuild(st.session_state.get("rag"))):
    with st.spinner("🔄 检测到重启，正在重新扫描文件恢复上下文..."):
        report = rebuild_rag_from_session(
            st.session_state.session_id,
            st.session_state.rag
        )
        st.session_state.rag_rebuilt = True
        st.session_state.context_summary = build_context_summary(dict(st.session_state))
        if report["total"] > 0:
            st.toast(f"✅ 已恢复 {report['total']} 个文件的知识库索引", icon="📚")

# === 全局侧边栏：进度 + 额度监控 + 提问入口 ===
with st.sidebar:
    with st.expander("💾 会话管理", expanded=False):
        st.caption(f"当前 Session: `{st.session_state.session_id}`")
        phase_label = st.session_state.get("phase", "input")
        st.caption(f"当前阶段: **{phase_label}**")
        if st.session_state.get("state_restored"):
            st.success("✅ 已从磁盘恢复上次进度")
        if st.button("💾 立即保存进度", key="btn_manual_save"):
            save_session(st.session_state.session_id, dict(st.session_state))
            st.toast("✅ 进度已保存", icon="💾")
        st.divider()
        st.caption("历史会话（点击可恢复）：")
        sessions = list_sessions()
        if sessions:
            for s in sessions[:5]:
                label = f"[{s['phase']}] {s['session_id']} · {s['saved_at'][:16]}"
                if st.button(label, key=f"restore_{s['session_id']}"):
                    target_id = s["session_id"]
                    saved = load_session(target_id)
                    if saved:
                        keys_to_clear = [k for k in st.session_state.keys() if k != "_init_done"]
                        for key in keys_to_clear:
                            del st.session_state[key]
                        for k, v in saved.items():
                            st.session_state[k] = v
                        st.session_state.session_id = target_id
                        st.session_state.state_restored = True
                        st.session_state.rag_rebuilt = False
                        st.session_state.context_summary = ""
                        save_latest_session_id(target_id)
                        try:
                            st.query_params["session"] = target_id
                        except Exception:
                            pass
                        st.rerun()
                    else:
                        st.error(f"无法加载会话 {target_id}，session_state.json 不存在")
        else:
            st.caption("（暂无历史会话）")
        st.divider()
        st.caption("本次已上传文件：")
        upload_dir = get_upload_dir(st.session_state.session_id)
        all_files = list(upload_dir.glob("*")) if upload_dir.exists() else []
        if all_files:
            for f in all_files:
                st.text(f"📄 {f.name}")
        else:
            st.caption("（暂无）")

    st.divider()

    st.header("📊 项目仪表盘")

    # 进度追踪
    all_stages = ["选题确认", "建模方法确认", "压力测试", "PRD生成",
                  "需求对齐", "代码生成", "图表生成", "论文撰写", "论文润色"]
    completed  = st.session_state.completed_stages
    progress   = len(completed) / len(all_stages)

    st.progress(progress, text=f"整体进度 {len(completed)}/{len(all_stages)}")
    for s in all_stages:
        icon = "✅" if s in completed else ("🔄" if s == st.session_state.get("phase", "") else "⏳")
        st.caption(f"{icon} {s}")

    st.divider()

    # 额度监控
    qm = st.session_state.quota_monitor
    st.subheader("💰 Token 额度")

    platform_choice = st.selectbox(
        "当前平台",
        ["Claude Sonnet", "Claude Opus 4.8", "ChatGPT-4o", "ChatGPT-5.5"],
        key="platform_select"
    )
    if platform_choice != qm.platform:
        st.session_state.quota_monitor = QuotaMonitor(platform=platform_choice)
        qm = st.session_state.quota_monitor

    st.code(qm.get_status_text(), language=None)

    # 额度预警
    should_alert, threshold = qm.should_alert()
    if should_alert:
        workspace = Path("workspace") / st.session_state.get("session_id", "default")
        handoff   = qm.generate_handoff_doc(
            session_id     = st.session_state.get("session_id", "default"),
            current_stage  = st.session_state.get("phase", "未知"),
            completed_stages = completed,
            workspace_path = str(workspace.absolute()),
            prd_summary    = st.session_state.get("prd_final", "")[:500],
        )
        st.warning(f"⚠️ 额度已用 {threshold*100:.0f}%，建议准备切换平台")
        with st.expander("📋 查看任务交接文档"):
            st.markdown(handoff)
            buf = io.BytesIO(handoff.encode("utf-8"))
            st.download_button("⬇️ 下载交接文档", buf, "任务交接.md", "text/markdown")

    st.divider()

    # 文件收件箱
    with st.expander("📥 文件收件箱", expanded=False):
        st.caption("将文件直接拖入对应目录，agent 启动时自动加载")
        inbox_path = Path(__file__).resolve().parent.parent / "inbox"
        st.code(str(inbox_path), language=None)
        if st.button("🔄 扫描新文件", key="btn_scan_inbox"):
            status = get_inbox_status()
            for subdir, info in status.items():
                label = {"problems":"赛题","papers":"论文","references":"参考文献",
                         "knowledge":"知识库","web_ai":"网页AI回复"}.get(subdir, subdir)
                new_badge = f"  🆕 {info['new']} 个新文件" if info["new"] > 0 else ""
                st.write(f"**{label}**: {info['total']} 个文件{new_badge}")
            total_loaded = 0
            rag = st.session_state.get("rag")
            if rag:
                for sub in ["problems","papers","references","knowledge"]:
                    new_files = get_new_files(sub)
                    if new_files:
                        n = rag.add_inbox_files(sub, new_files)
                        mark_as_processed(new_files)
                        total_loaded += n
                if total_loaded > 0:
                    st.success(f"✅ 已加载 {total_loaded} 个新文件到知识库")
        st.caption("📂 子目录：problems / papers / references / knowledge / web_ai / data")

        st.divider()
        st.caption("📊 数据文件（CSV / Excel）")
        st.caption("将数据文件放入 inbox/data/ 目录后点击加载：")

        data_path = Path(__file__).resolve().parent.parent / "inbox" / "data"
        st.code(str(data_path), language=None)

        data_files = list_data_files(data_path)
        if data_files:
            for f in data_files:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text(f"📄 {f['name']} ({f['size_kb']} KB)")
                with col2:
                    btn_key = f"load_data_{f['name']}"
                    if st.button("加载", key=btn_key):
                        summary = read_data_file(f["name"])
                        st.session_state.loaded_data_files[f["name"]] = summary
                        st.session_state.memory_logger.log_system_event(
                            "加载数据文件", f["name"]
                        )
                        st.success(f"✅ 已加载 {f['name']}")
                        st.text_area("预览", value=summary[:300]+"...", height=100, disabled=True)
        else:
            st.caption("（inbox/data/ 目录下暂无数据文件）")

        if st.session_state.get("loaded_data_files"):
            names = list(st.session_state.loaded_data_files.keys())
            st.info(f'💡 已加载 {len(names)} 个数据文件：{", ".join(names)}\n可在提问时说"分析数据"自动引用')

    st.divider()

    # AI 网页版协作
    with st.expander("🔗 AI 网页版协作", expanded=False):
        st.caption("将当前阶段上下文导出，上传给网页版 AI；或读取网页版 AI 的回复")
        if st.button("📤 导出上下文给网页版 AI", key="btn_export_webai"):
            workspace_root = Path(__file__).resolve().parent.parent / "workspace"
            export_path = export_context_package(
                phase=st.session_state.get("phase", "input"),
                session_id=st.session_state.session_id,
                context=dict(st.session_state),
                workspace_root=workspace_root
            )
            st.success("✅ 已导出")
            st.code(str(export_path), language=None)
            st.caption("请到上述路径找到文件，上传给网页版 AI")
        st.divider()
        st.caption("将网页版 AI 的回复保存到 inbox/web_ai/ 目录后，在此输入文件名：")
        filename_input = st.text_input(
            "回复文件名（如 chatgpt_reply.md）",
            key="webai_filename_input",
            placeholder="chatgpt_reply.md"
        )
        if st.button("📥 读取网页版 AI 回复", key="btn_import_webai"):
            if filename_input.strip():
                content = import_webai_response(filename_input.strip())
                st.session_state.webai_imported_content = content
                if content.startswith("❌"):
                    st.error(content)
                else:
                    st.success(f"✅ 已读取 {len(content)} 字符")
                    st.text_area("回复内容预览", value=content[:500]+"...", height=150, disabled=True)
            else:
                st.warning("请先输入文件名")
        if st.session_state.get("webai_imported_content"):
            st.info("💡 网页版 AI 回复已就绪，可在对话框中输入\"使用网页AI方案\"来应用")
        st.divider()
        st.caption("本次 session 已导出的文件：")
        workspace_root_exports = Path(__file__).resolve().parent.parent / "workspace"
        exports = list_export_files(st.session_state.session_id, workspace_root_exports)
        if exports:
            for e in exports[-5:]:
                st.text(f"📄 {e['filename']}")
        else:
            st.caption("（暂无导出记录）")

    st.divider()

    # Skill 对比查询
    with st.expander("🛠️ Skills 说明"):
        st.markdown(get_skill_comparison())

    st.divider()

    # 用户随时提问
    st.subheader("💬 随时提问")
    user_question = st.text_input("对当前项目有什么疑问？", key="sidebar_question", placeholder="例如：为什么选这个模型？")
    if user_question and st.button("提问", key="sidebar_ask"):
        st.session_state.memory_logger.log_message("user", user_question)
        ctx = f"""项目进度：{completed}
当前阶段：{st.session_state.get('phase', '未知')}
建模方案摘要：{(st.session_state.get('modeling_plan') or '')[:400]}
PRD摘要：{(st.session_state.get('prd_final') or st.session_state.get('prd_draft') or '')[:400]}"""
        from model import gpt_with_retry
        answer = gpt_with_retry(f"用户问题：{user_question}\n\n项目背景：{ctx}", max_tokens=500)
        qm.record("用户提问", qm.estimate_tokens(answer))
        st.session_state.memory_logger.log_message("assistant", answer)
        st.info(answer)

st.title("🎓 APMCM 数学建模比赛 Agent")
st.caption("基于 RAG + LLM + 多Skill 协作的数学建模助手")

# ============ Phase 1: Input ============
if st.session_state.phase == "input":
    st.header("📝 上传赛题 PDF")

    UPLOAD_ROOT = Path(__file__).resolve().parent.parent / "workspace" / "upload"
    for d in [UPLOAD_ROOT / "1", UPLOAD_ROOT / "2", UPLOAD_ROOT / "3"]:
        d.mkdir(parents=True, exist_ok=True)

    def _extract_pdf(file_bytes):
        from pypdf import PdfReader
        from io import BytesIO
        txt = ""
        pdf = PdfReader(BytesIO(file_bytes))
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                txt += extracted + "\n"
        return txt.strip()

    def _read_folder_topic(folder_num):
        """从 workspace/upload/{folder_num}/ 读取第一个 PDF 文件"""
        folder = UPLOAD_ROOT / str(folder_num)
        if folder.exists():
            pdfs = list(folder.glob("*.pdf"))
            if pdfs:
                return pdfs[0]
        return None

    # 扫描各文件夹中的已有文件
    st.markdown(f"文件路径: `{UPLOAD_ROOT.absolute()}`")
    st.caption("将赛题 PDF 放入对应子文件夹（1/2/3），或通过下方上传区域上传。要删除选题，从对应文件夹中删除 PDF 文件即可。")

    col1, col2, col3 = st.columns(3)
    uploaded_texts = [None, None, None]
    uploaded_names = [None, None, None]
    topic_files = [None, None, None]

    for i, col in enumerate([col1, col2, col3]):
        folder_num = str(i + 1)
        folder = UPLOAD_ROOT / folder_num
        with col:
            st.subheader(f"选题 {folder_num}")

            # 显示已有文件
            existing_pdf = _read_folder_topic(folder_num)
            if existing_pdf:
                topic_files[i] = existing_pdf
                st.info(f"📄 {existing_pdf.name}")
                if st.button("🗑️ 删除", key=f"del_topic_{i}"):
                    existing_pdf.unlink()
                    st.rerun()

            # 上传区域
            uploaded = st.file_uploader(
                f"上传PDF", type=["pdf"], key=f"upload_{i}",
                help=f"上传赛题{folder_num}，会保存到 upload/{folder_num}/"
            )
            if uploaded:
                dest = folder / uploaded.name
                dest.write_bytes(uploaded.getvalue())
                with st.spinner(f"解析选题{folder_num}..."):
                    topic_files[i] = dest
                    st.session_state[f"extracted_{i}"] = _extract_pdf(dest.read_bytes())
                st.session_state[f"uploaded_name_{i}"] = uploaded.name
                autosave()
                st.success(f"已保存: {uploaded.name}")
                st.rerun()

    # 从已有文件读取文本
    for i in range(3):
        if topic_files[i]:
            pdf_path = topic_files[i]
            st.session_state[f"extracted_{i}"] = _extract_pdf(pdf_path.read_bytes())
            st.session_state[f"uploaded_name_{i}"] = pdf_path.name
            uploaded_texts[i] = st.session_state[f"extracted_{i}"]
            uploaded_names[i] = pdf_path.name

    if st.button("🚀 开始分析", type="primary", use_container_width=True):
        topics = []
        for i in range(3):
            t = uploaded_texts[i] or st.session_state.get(f"extracted_{i}")
            if t:
                topics.append(t)
                uploaded_names[i] = st.session_state.get(f"uploaded_name_{i}", f"选题{i+1}")
        if not topics:
            st.error("请至少上传一个赛题 PDF")
        else:
            # 清除上次所有分析结果，从当前文件重新开始
            for key in ["topic_sims", "topic_scores", "topic_recommendation",
                        "modeling_plan", "coding_result", "paper_draft",
                        "pressure_report", "prd_draft", "prd_final",
                        "figure_descriptions", "polished_paper", "paper_sections",
                        "selected_topic", "selected_topic_idx", "selected_sims",
                        "completed_stages", "grill_rounds", "pressure_test_result",
                        "grill_result"]:
                st.session_state.pop(key, None)
            st.session_state.topics = topics
            logger.log_user_input(f"用户上传了{len(topics)}个赛题PDF: {[n for n in uploaded_names if n]}")
            st.session_state.phase = "topic_selection"
            st.session_state.memory_logger.new_stage(st.session_state.phase)
            st.session_state.memory_logger.log_system_event(
                "进入阶段: topic_selection",
                f"session_id={st.session_state.session_id}"
            )
            autosave()
            st.rerun()

# ============ Phase 2: Topic Selection ============
elif st.session_state.phase == "topic_selection":
    st.header("📊 选题分析")

    if st.button("⬅️ 返回上传赛题", key="back_to_input"):
        clear_downstream("input")
        st.session_state.phase = "input"
        st.session_state.memory_logger.new_stage("input")
        st.session_state.memory_logger.log_system_event("返回阶段: input", "用户从选题分析返回")
        autosave()
        st.rerun()

    topics = st.session_state.topics
    if "topic_sims" not in st.session_state:
        with st.spinner("正在检索历史数据,分析各选题..."):
            sims_list = []
            scores = []
            for i, topic in enumerate(topics):
                with st.status(f"分析选题 {i+1}..."):
                    score, sims = rag.topic_coverage_score(topic, topk=5)
                    scores.append(score)
                    sims_list.append(sims)
                    st.write(f"选题{i+1} 匹配分数: {score}")
                    st.write(f"  - 相似历史题: {len(sims['sim_questions'])} 道")
                    st.write(f"  - 相关论文: {len(sims['sim_papers'])} 篇")
                    st.write(f"  - 参考文献: {len(sims['sim_refs'])} 篇")

            prompt = get_topic_selection_prompt(topics, sims_list)
            recommendation = gpt_with_retry(prompt)
            st.session_state.topic_recommendation = recommendation
            st.session_state.topic_sims = sims_list
            st.session_state.topic_scores = scores
            logger.log_topic_selection(topics, scores, recommendation)

    st.markdown("### 🤖 Agent 选题推荐")
    st.markdown(st.session_state.topic_recommendation)

    st.divider()
    st.markdown("### 📊 数据库匹配分数")
    for i, (topic, score, sims) in enumerate(zip(topics, st.session_state.topic_scores, st.session_state.topic_sims)):
        st.metric(f"选题{i+1}", f"{score} 分",
                  f"相似题:{len(sims['sim_questions'])} | 论文:{len(sims['sim_papers'])} | 参考:{len(sims['sim_refs'])}")

    col_a, col_b = st.columns(2)
    with col_a:
        selected_idx = st.selectbox("选择最终选题", range(len(topics)),
                                    format_func=lambda x: f"选题{x+1}")
    with col_b:
        if st.button("✅ 确认选题,开始建模", type="primary"):
            st.session_state.selected_topic = topics[selected_idx]
            st.session_state.selected_topic_idx = selected_idx
            st.session_state.selected_sims = st.session_state.topic_sims[selected_idx]
            logger.log_user_feedback("topic_selection", f"用户选择选题{selected_idx+1}")
            st.session_state.phase = "modeling"
            st.session_state.memory_logger.new_stage(st.session_state.phase)
            st.session_state.memory_logger.log_system_event(
                "进入阶段: modeling",
                f"session_id={st.session_state.session_id}"
            )
            autosave()
            st.rerun()

# ============ Phase 3: Modeling ============
elif st.session_state.phase == "modeling":
    st.header("🔬 数学建模方案")

    if st.button("⬅️ 返回选题分析", key="back_to_topic"):
        clear_downstream("topic_selection")
        st.session_state.phase = "topic_selection"
        st.session_state.memory_logger.new_stage("topic_selection")
        st.session_state.memory_logger.log_system_event("返回阶段: topic_selection")
        autosave()
        st.rerun()

    selected_topic = st.session_state.selected_topic
    selected_sims = st.session_state.selected_sims

    if "modeling_plan" not in st.session_state or st.session_state.modeling_plan is None:
        with st.spinner("正在生成建模方案..."):
            approach = st.session_state.get("user_approach", "")
            prompt = get_modeling_prompt(selected_topic, selected_sims, approach)
            modeling_plan = gpt_with_retry(prompt, max_tokens=6000)
            st.session_state.modeling_plan = modeling_plan
            logger.log_modeling(modeling_plan)
            autosave()

    st.markdown(st.session_state.modeling_plan)

    # === 步骤A：压力测试（在建模方案生成后自动触发）===
    if st.session_state.get("modeling_plan") and not st.session_state.get("pressure_report"):
        if st.button("🔬 运行压力测试（startup-pressure-test + star-up）", key="run_pressure"):
            with st.spinner("正在运行 startup-pressure-test 和 star-up 技能..."):
                report = run_pressure_test(
                    question      = st.session_state.selected_topic,
                    modeling_plan = st.session_state.modeling_plan,
                )
                st.session_state.pressure_report = report
                qm = st.session_state.quota_monitor
                qm.record("压力测试", qm.estimate_tokens(report))
                if "压力测试" not in st.session_state.completed_stages:
                    st.session_state.completed_stages.append("压力测试")
                autosave()

    if st.session_state.get("pressure_report"):
        with st.expander("📋 压力测试报告", expanded=True):
            st.markdown(st.session_state.pressure_report)

    # === 步骤B：生成 PRD ===
    if st.session_state.get("pressure_report") and not st.session_state.get("prd_draft"):
        if st.button("📄 生成 PRD（产品需求文档）", key="gen_prd"):
            workspace = Path("workspace") / st.session_state.session_id
            with st.spinner("正在生成 PRD..."):
                prd = generate_prd(
                    question       = st.session_state.selected_topic,
                    modeling_plan  = st.session_state.modeling_plan,
                    pressure_report= st.session_state.pressure_report,
                    align_context  = {},
                    session_id     = st.session_state.session_id,
                )
                st.session_state.prd_draft = prd
                qm = st.session_state.quota_monitor
                qm.record("PRD生成", qm.estimate_tokens(prd))
                export_prd_file(prd, workspace, st.session_state.session_id)
                if "PRD生成" not in st.session_state.completed_stages:
                    st.session_state.completed_stages.append("PRD生成")
                autosave()

    if st.session_state.get("prd_draft"):
        with st.expander("📄 PRD 当前版本", expanded=True):
            st.markdown(st.session_state.prd_draft)

    # === 步骤C：grill-me 需求对齐循环 ===
    if st.session_state.get("prd_draft"):
        st.subheader("🔥 需求对齐（grill-me）")
        st.caption(f"已对齐 {st.session_state.grill_rounds} 轮 | 建议 2-3 轮后确认最终 PRD")

        user_prd_feedback = st.text_area(
            "对 PRD 有什么不满意或想调整的地方？（直接说，AI 会追问并修订）",
            key="prd_feedback",
            placeholder="例如：我觉得用神经网络更合适 / 时间计划太紧 / 第3章结构不清晰..."
        )
        col_grill, col_confirm = st.columns(2)

        with col_grill:
            if st.button("💬 发起一轮对齐", key="run_grill") and user_prd_feedback:
                with st.spinner("grill-me 追问分析中..."):
                    grill_result = run_grill_me(st.session_state.prd_draft, user_prd_feedback)
                    qm = st.session_state.quota_monitor
                    qm.record("需求对齐", qm.estimate_tokens(grill_result))
                    st.session_state.grill_rounds += 1

                st.subheader("🎯 对齐分析与修订建议")
                st.markdown(grill_result)
                if "需求对齐" not in st.session_state.completed_stages:
                    st.session_state.completed_stages.append("需求对齐")

        with col_confirm:
            if st.button("✅ PRD 已对齐，生成最终版 + CLAUDE.md", key="confirm_prd"):
                workspace = Path("workspace") / st.session_state.session_id
                workspace.mkdir(parents=True, exist_ok=True)

                st.session_state.prd_final = st.session_state.prd_draft
                claude_md_path = generate_claude_md(
                    prd           = st.session_state.prd_final,
                    modeling_plan = st.session_state.modeling_plan,
                    workspace_path= workspace,
                    session_id    = st.session_state.session_id,
                )
                qm = st.session_state.quota_monitor
                qm.record("CLAUDE.md生成", 500)
                autosave()

                st.success(f"✅ CLAUDE.md 已生成：`{claude_md_path}`")
                st.code(f"cd {workspace.absolute()}\nopencode\n# 或\nclaude", language="bash")

                if not st.session_state.reference_loaded:
                    from rag import RAG
                    if hasattr(st.session_state, "rag") and st.session_state.rag.load_references():
                        st.info("📚 reference/ 知识库已加载")
                        st.session_state.reference_loaded = True

                st.session_state.phase = "coding"
                st.session_state.memory_logger.new_stage(st.session_state.phase)
                st.session_state.memory_logger.log_system_event(
                    "进入阶段: coding",
                    f"session_id={st.session_state.session_id}"
                )
                autosave()
                st.rerun()

    st.divider()
    user_approach = st.text_area("补充建模方向建议(可选)", key="user_approach_input",
                                  placeholder="例如:希望使用动态规划方法...")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 重新生成方案"):
            clear_downstream("modeling")
            if user_approach:
                st.session_state.user_approach = user_approach
            del st.session_state.modeling_plan
            st.rerun()
    with col2:
        if st.button("🧪 压力测试", type="primary"):
            logger.log_user_feedback("modeling", "用户确认建模方案,进入压力测试")
            st.session_state.phase = "pressure_test"
            st.session_state.memory_logger.new_stage(st.session_state.phase)
            st.session_state.memory_logger.log_system_event(
                "进入阶段: pressure_test",
                f"session_id={st.session_state.session_id}"
            )
            autosave()
            st.rerun()
    with col3:
        if st.button("⏭️ 跳过测试"):
            logger.log_user_feedback("modeling", "用户跳过测试,直接进入代码生成")
            st.session_state.phase = "coding"
            st.session_state.memory_logger.new_stage(st.session_state.phase)
            st.session_state.memory_logger.log_system_event(
                "进入阶段: coding",
                f"session_id={st.session_state.session_id}"
            )
            autosave()
            st.rerun()

# ============ Phase 4: Pressure Test ============
elif st.session_state.phase == "pressure_test":
    st.header("🧪 建模方案压力测试")

    modeling_plan = st.session_state.modeling_plan

    if "pressure_test_result" not in st.session_state:
        with st.spinner("正在进行压力测试..."):
            prompt = get_pressure_test_prompt(modeling_plan)
            test_result = gpt_with_retry(prompt)
            st.session_state.pressure_test_result = test_result
            logger.log_pressure_test(test_result)

    st.markdown(st.session_state.pressure_test_result)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 返回修改方案"):
            clear_downstream("modeling")
            st.session_state.phase = "modeling"
            st.session_state.memory_logger.new_stage(st.session_state.phase)
            st.session_state.memory_logger.log_system_event(
                "进入阶段: modeling",
                f"session_id={st.session_state.session_id}"
            )
            autosave()
            st.rerun()
    with col2:
        if st.button("✅ 方案通过,对齐用户期望", type="primary"):
            st.session_state.phase = "grill_me"
            st.session_state.memory_logger.new_stage(st.session_state.phase)
            st.session_state.memory_logger.log_system_event(
                "进入阶段: grill_me",
                f"session_id={st.session_state.session_id}"
            )
            autosave()
            st.rerun()

# ============ Phase 5: Grill Me ============
elif st.session_state.phase == "grill_me":
    st.header("🎯 用户期望对齐")

    modeling_plan = st.session_state.modeling_plan
    user_expectation = st.text_area(
        "请输入你的预期和目标",
        value=st.session_state.get("user_expectation", ""),
        height=150,
        placeholder="例如:我期望方案能够获得省级一等奖,并且代码实现简单..."
    )

    if st.button("🔍 评估方案是否符合预期", type="primary") and user_expectation:
        with st.spinner("正在评估..."):
            st.session_state.user_expectation = user_expectation
            prompt = get_grill_me_prompt(modeling_plan, user_expectation)
            grill_result = gpt_with_retry(prompt)
            st.session_state.grill_result = grill_result
            logger.log_grill_me(grill_result)

    if "grill_result" in st.session_state:
        st.markdown(st.session_state.grill_result)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 返回调整方案"):
                clear_downstream("modeling")
                st.session_state.phase = "modeling"
                st.session_state.memory_logger.new_stage(st.session_state.phase)
                st.session_state.memory_logger.log_system_event(
                    "进入阶段: modeling",
                    f"session_id={st.session_state.session_id}"
                )
                autosave()
                st.rerun()
        with col2:
            if st.button("✅ 方案对齐,开始编码", type="primary"):
                st.session_state.phase = "coding"
                st.session_state.memory_logger.new_stage(st.session_state.phase)
                st.session_state.memory_logger.log_system_event(
                    "进入阶段: coding",
                    f"session_id={st.session_state.session_id}"
                )
                autosave()
                st.rerun()

# ============ Phase 6: Coding ============
elif st.session_state.phase == "coding":
    st.header("💻 代码生成")

    if st.button("⬅️ 返回建模方案", key="back_to_modeling"):
        clear_downstream("modeling")
        st.session_state.phase = "modeling"
        st.session_state.memory_logger.new_stage("modeling")
        autosave()
        st.rerun()

    if st.session_state.coding_result is None:
        with st.spinner("正在生成Python代码..."):
            data_context = ""
            if st.session_state.get("loaded_data_files"):
                data_context = "\n\n## 可用数据文件\n"
                for fname, summary in st.session_state.loaded_data_files.items():
                    data_context += f"\n### {fname}\n{summary}\n"
            topic_with_data = st.session_state.selected_topic + data_context
            prompt = get_coding_prompt(
                topic_with_data,
                st.session_state.modeling_plan,
                st.session_state.selected_sims
            )
            coding_result = gpt_with_retry(prompt, max_tokens=8000)
            st.session_state.coding_result = coding_result
            logger.log_coding(coding_result)
            autosave()

    st.code(st.session_state.coding_result, language="python")

    # === 代码审查（think + check + TDD）===
    if st.session_state.get("coding_result"):
        with st.expander("🔍 代码三重审查（think + check + TDD）", expanded=False):
            if st.button("运行 Skill 审查", key="run_code_check"):
                with st.spinner("运行 think / check / tdd 审查..."):
                    review = run_code_check(st.session_state.coding_result)
                    qm = st.session_state.quota_monitor
                    qm.record("代码审查", qm.estimate_tokens(review))
                    st.markdown(review)

        st.subheader("📝 同步生成对应论文节")
        section_name = st.selectbox("这段代码对应论文哪一节？",
                                     ["3.1 模型建立", "3.2 求解方法", "4.1 结果分析", "4.2 敏感性分析"])
        if st.button("📖 生成这一节论文初稿", key="gen_paper_section"):
            with st.spinner(f"生成 {section_name} 初稿..."):
                from model import gpt_with_retry
                section_prompt = f"""根据以下代码实现，写出数学建模论文的 {section_name} 节。
要求：学术语言，包含 LaTeX 公式，引用代码中的具体数值，300-500字。

代码：
{st.session_state.coding_result[:1500]}

建模方案背景：
{st.session_state.get('modeling_plan','')[:400]}"""
                section = gpt_with_retry(section_prompt, max_tokens=800)
                qm = st.session_state.quota_monitor
                qm.record(f"论文节-{section_name}", qm.estimate_tokens(section))
                st.session_state.paper_sections[section_name] = section

                workspace = Path("workspace") / st.session_state.session_id / "paper_sections"
                workspace.mkdir(parents=True, exist_ok=True)
                safe_name = section_name.replace(" ", "_").replace(".", "")
                (workspace / f"{safe_name}.md").write_text(section, encoding="utf-8")

            st.markdown(section)
            st.success(f"✅ {section_name} 已保存")

        st.info("👆 请确认以上代码和论文节是否符合预期，再进入下一阶段")
        col_ok, col_redo = st.columns(2)
        with col_ok:
            if st.button("✅ 符合预期，继续", key="coding_ok"):
                if "代码生成" not in st.session_state.completed_stages:
                    st.session_state.completed_stages.append("代码生成")
                st.session_state.phase = "figure"
                st.session_state.memory_logger.new_stage(st.session_state.phase)
                st.session_state.memory_logger.log_system_event(
                    "进入阶段: figure",
                    f"session_id={st.session_state.session_id}"
                )
                autosave()
                st.rerun()
        with col_redo:
            if st.button("🔄 重新生成", key="coding_redo"):
                st.session_state.coding_result = None
                st.rerun()

    # === 代码保存与 opencode 集成 ===
    workspace = Path("workspace") / st.session_state.session_id
    col_save, col_claude = st.columns(2)

    with col_save:
        if st.button("💾 保存代码到本地文件夹", key="save_code"):
            workspace.mkdir(parents=True, exist_ok=True)
            code_path = workspace / "model_solution.py"
            code_path.write_text(st.session_state.coding_result, encoding="utf-8")

            readme_content = f"""# 数学建模代码
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
赛题: {(st.session_state.get('selected_topic') or '')[:80]}

## 运行方式
```bash
pip install pyomo scipy gekko matplotlib pandas numpy
python model_solution.py
```

## 建模方案摘要
{(st.session_state.get('modeling_plan') or '')[:400]}
"""
            (workspace / "README.md").write_text(readme_content, encoding="utf-8")
            st.success(f"✅ 代码已保存到 `{workspace.absolute()}`")
            st.code(f"cd {workspace.absolute()}\npython model_solution.py", language="bash")

    with col_claude:
        if st.button("🤖 生成 opencode 指令文件", key="gen_claude"):
            workspace.mkdir(parents=True, exist_ok=True)
            (workspace / "problem.txt").write_text(
                st.session_state.get("selected_topic", ""), encoding="utf-8"
            )
            (workspace / "modeling_plan.md").write_text(
                st.session_state.get("modeling_plan", ""), encoding="utf-8"
            )

            claudemd = f"""# 数学建模任务 — 由 APMCM Agent 生成
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 赛题（完整文本见 problem.txt）
{(st.session_state.get('selected_topic') or '')[:300]}...

## 已确认的建模方案（详见 modeling_plan.md）
{(st.session_state.get('modeling_plan') or '')[:500]}...

## 你需要完成的工作
请在 `solution/` 子目录创建以下文件，每个文件写完后立即运行验证：

1. `solution/data_processing.py`
   - 数据读取和预处理
   - 输出数据摘要统计和异常值检测结果

2. `solution/model.py`
   - 核心数学模型（按建模方案实现）
   - 包含 validate_output() 函数自检
   - 使用 Pyomo 或 Scipy（根据建模方案选择）

3. `solution/solver.py`
   - 调用 model.py 求解
   - 格式化输出求解结果

4. `solution/sensitivity.py`
   - 对关键参数做敏感性分析
   - 输出敏感性表格

5. `solution/figures.py`
   - 生成论文所需图表（Nature 期刊风格）
   - 保存为 figures/fig_*.png

## 约束
- 所有代码使用中文注释
- 每个模块有独立的 if __name__ == "__main__": 测试块
- 有错误时打印具体原因，不要静默失败
- 完成后在此 CLAUDE.md 底部追加运行结果摘要
"""
            (workspace / "CLAUDE.md").write_text(claudemd, encoding="utf-8")
            st.success(f"✅ opencode 指令文件已生成")
            st.code(f"cd {workspace.absolute()}\nopencode\n# 或\nclaude", language="bash")
            st.info("在终端进入该目录后运行 opencode 或 claude，它会自动读取 CLAUDE.md 开始工作")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 重新生成代码"):
            clear_downstream("coding")
            del st.session_state.coding_result
            st.rerun()
    with col2:
        if st.button("📊 生成图表", type="primary"):
            st.session_state.phase = "figure"
            st.session_state.memory_logger.new_stage(st.session_state.phase)
            st.session_state.memory_logger.log_system_event(
                "进入阶段: figure",
                f"session_id={st.session_state.session_id}"
            )
            autosave()
            st.rerun()
    with col3:
        if st.button("⏭️ 跳过图表"):
            st.session_state.phase = "paper"
            st.session_state.memory_logger.new_stage(st.session_state.phase)
            st.session_state.memory_logger.log_system_event(
                "进入阶段: paper",
                f"session_id={st.session_state.session_id}"
            )
            autosave()
            st.rerun()

# ============ Phase 7: Figure ============
elif st.session_state.phase == "figure":
    st.header("📊 图表生成方案")

    if st.button("⬅️ 返回代码生成", key="back_to_coding"):
        clear_downstream("coding")
        st.session_state.phase = "coding"
        st.session_state.memory_logger.new_stage("coding")
        autosave()
        st.rerun()

    if st.session_state.figure_descriptions is None:
        with st.spinner("正在设计图表方案..."):
            prompt = get_figure_prompt(
                st.session_state.selected_topic,
                st.session_state.modeling_plan,
                st.session_state.coding_result or ""
            )
            figure_desc = gpt_with_retry(prompt)
            st.session_state.figure_descriptions = figure_desc
            logger.log_figure(figure_desc)

    st.markdown(st.session_state.figure_descriptions)

    st.info("💡 安装 scipilot-figure-skill 后可直接在Python中生成图表:")
    st.code(
        "from skills_bridge import profile_data, setup_style, export_figure\n"
        "# 示例: setup_style('nature'); export_figure(fig, 'result')",
        language="python"
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 重新生成图表方案"):
            clear_downstream("figure")
            del st.session_state.figure_descriptions
            st.rerun()
    with col2:
        if st.button("📝 生成论文初稿", type="primary"):
            st.session_state.phase = "paper"
            st.session_state.memory_logger.new_stage(st.session_state.phase)
            st.session_state.memory_logger.log_system_event(
                "进入阶段: paper",
                f"session_id={st.session_state.session_id}"
            )
            autosave()
            st.rerun()

# ============ Phase 8: Paper ============
elif st.session_state.phase == "paper":
    st.header("📝 论文初稿")

    if st.button("⬅️ 返回图表方案", key="back_to_figure"):
        clear_downstream("figure")
        st.session_state.phase = "figure"
        st.session_state.memory_logger.new_stage("figure")
        autosave()
        st.rerun()

    if st.session_state.paper_draft is None:
        with st.spinner("正在生成论文初稿..."):
            prompt = get_paper_writing_prompt(
                st.session_state.selected_topic,
                st.session_state.modeling_plan,
                st.session_state.coding_result or "",
                st.session_state.figure_descriptions or ""
            )
            paper_draft = gpt_with_retry(prompt, max_tokens=8000)
            st.session_state.paper_draft = paper_draft
            logger.log_paper_draft(paper_draft)
            autosave()

    st.markdown(st.session_state.paper_draft)

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 重新生成论文"):
            clear_downstream("paper")
            del st.session_state.paper_draft
            st.rerun()
    with col2:
        if st.button("✨ 润色论文", type="primary"):
            st.session_state.phase = "polish"
            st.session_state.memory_logger.new_stage(st.session_state.phase)
            st.session_state.memory_logger.log_system_event(
                "进入阶段: polish",
                f"session_id={st.session_state.session_id}"
            )
            autosave()
            st.rerun()
    with col3:
        if st.button("📥 导出完成"):
            st.session_state.phase = "done"
            st.session_state.memory_logger.new_stage(st.session_state.phase)
            st.session_state.memory_logger.log_system_event(
                "进入阶段: done",
                f"session_id={st.session_state.session_id}"
            )
            autosave()
            st.rerun()

# ============ Phase 9: Polish ============
elif st.session_state.phase == "polish":
    st.header("✨ 论文润色")

    if st.button("⬅️ 返回论文初稿", key="back_to_paper"):
        clear_downstream("paper")
        st.session_state.phase = "paper"
        st.session_state.memory_logger.new_stage("paper")
        autosave()
        st.rerun()

    polish_type = st.selectbox("润色类型", ["润色", "翻译为英文", "学术语法修正", "逻辑优化"])

    if st.button("🚀 开始润色", type="primary"):
        with st.spinner(f"正在进行{polish_type}..."):
            prompt = get_polish_prompt(st.session_state.paper_draft, polish_type)
            polished = gpt_with_retry(prompt, max_tokens=8000)
            st.session_state.polished_paper = polished
            logger.log_paper_polish(polished)

    if "polished_paper" in st.session_state:
        st.markdown("### 润色结果")
        st.markdown(st.session_state.polished_paper)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 重新润色"):
                del st.session_state.polished_paper
                st.rerun()
        with col2:
            if st.button("📥 完成,查看总结", type="primary"):
                st.session_state.phase = "done"
                st.session_state.memory_logger.new_stage(st.session_state.phase)
                st.session_state.memory_logger.log_system_event(
                    "进入阶段: done",
                    f"session_id={st.session_state.session_id}"
                )
                autosave()
                st.rerun()

        # === 论文导出 ===
        st.divider()
        st.subheader("📄 导出论文")
        export_col1, export_col2 = st.columns(2)

        with export_col1:
            if st.button("📥 导出为 Word 文档 (.docx)", key="export_docx"):
                try:
                    from docx import Document as DocxDocument
                    from docx.shared import Pt, Inches
                    from docx.enum.text import WD_ALIGN_PARAGRAPH

                    paper_text = st.session_state.get(
                        "polished_paper",
                        st.session_state.get("paper_draft", "")
                    )

                    doc = DocxDocument()

                    title = doc.add_heading("数学建模竞赛论文", 0)
                    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

                    for line in paper_text.split("\n"):
                        line = line.strip()
                        if not line:
                            continue
                        if line.startswith("# "):
                            doc.add_heading(line[2:], level=1)
                        elif line.startswith("## "):
                            doc.add_heading(line[3:], level=2)
                        elif line.startswith("### "):
                            doc.add_heading(line[4:], level=3)
                        elif line.startswith("$$") or line.startswith("\\begin"):
                            p = doc.add_paragraph()
                            run = p.add_run(f"[公式] {line}")
                            run.font.name = "Courier New"
                            run.font.size = Pt(9)
                        else:
                            doc.add_paragraph(line)

                    buf = io.BytesIO()
                    doc.save(buf)
                    buf.seek(0)

                    st.download_button(
                        label="⬇️ 点击下载 .docx",
                        data=buf.getvalue(),
                        file_name=f"apmcm_paper_{st.session_state.session_id}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key="download_docx"
                    )
                except ImportError:
                    st.error("请先安装 python-docx：pip install python-docx")

        with export_col2:
            if st.button("📝 导出为 Markdown 文件", key="export_md"):
                paper_text = st.session_state.get(
                    "polished_paper",
                    st.session_state.get("paper_draft", "")
                )
                workspace = Path("workspace") / st.session_state.session_id
                workspace.mkdir(parents=True, exist_ok=True)
                paper_path = workspace / "paper.md"
                paper_path.write_text(paper_text, encoding="utf-8")
                st.success(f"✅ 论文已保存到 `{paper_path.absolute()}`")
                st.code(
                    f"# 转换为 PDF（需要安装 pandoc 和 xelatex）\n"
                    f"cd {workspace.absolute()}\n"
                    f"pandoc paper.md -o paper.pdf --pdf-engine=xelatex "
                    f"-V mainfont='SimSun' -V geometry:margin=2.5cm",
                    language="bash"
                )

# ============ Done ============
elif st.session_state.phase == "done":
    st.header("🎉 工作流程完成!")

    summary = logger.get_summary()
    st.markdown(f"""
    ### 会话总结
    - **Session ID**: {summary['session_id']}
    - **总步骤数**: {summary['total_steps']}
    - **日志文件**: `{summary['log_file']}`
    - **Markdown日志**: `{summary['md_file']}`
    """)

    st.markdown("### 各阶段完成情况")
    for phase, count in summary['phases'].items():
        st.markdown(f"- {phase}: {count} 步")

    st.divider()
    st.markdown("### 📄 最终产出")

    tab1, tab2, tab3, tab4 = st.tabs(["建模方案", "代码", "图表方案", "论文"])

    with tab1:
        if st.session_state.modeling_plan:
            st.markdown(st.session_state.modeling_plan)
    with tab2:
        if st.session_state.coding_result:
            st.code(st.session_state.coding_result, language="python")
    with tab3:
        if st.session_state.figure_descriptions:
            st.markdown(st.session_state.figure_descriptions)
    with tab4:
        paper = st.session_state.get("polished_paper") or st.session_state.paper_draft
        if paper:
            st.markdown(paper)

    if st.button("🔄 开始新会话"):
        for key in list(st.session_state.keys()):
            if key not in ["rag"]:
                del st.session_state[key]
        st.session_state.logger = WorkflowLogger()
        st.session_state.rag = rag
        st.session_state.phase = "input"
        st.session_state.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.query_params["session"] = st.session_state.session_id
        st.session_state.memory_logger = MemoryLogger(st.session_state.session_id)
        st.session_state.memory_logger.new_stage("input")
        st.session_state.memory_logger.log_system_event(
            "新会话开始",
            f"session_id={st.session_state.session_id}"
        )
        st.rerun()

# ═══════════════════════════════════════════════════════════
# 💬 对话面板（始终可见，与工作区独立）
# ═══════════════════════════════════════════════════════════
st.divider()
chat_col, chat_info_col = st.columns([4, 1])
with chat_col:
    st.header("💬 与 Agent 对话")
with chat_info_col:
    chat_count = len(st.session_state.get("chat_history", []))
    st.caption(f"共 {chat_count} 条消息")

chat_container = st.container(height=400, border=True)
with chat_container:
    if st.session_state.get("chat_history"):
        for msg in st.session_state.chat_history:
            role_label = "🧑 你" if msg["role"] == "user" else "🤖 Agent"
            with st.chat_message(msg["role"]):
                st.markdown(f"**{role_label}** — {msg['content'][:2000]}")
    else:
        st.caption("对话记录将在这里显示。上传赛题后即可与 Agent 交流。")

st.caption("")
chat_input = st.chat_input("向Agent提问或提供反馈...")
if chat_input:
    webai_content = st.session_state.get("webai_imported_content", "")
    if webai_content and ("使用网页AI方案" in chat_input or "应用网页AI回复" in chat_input):
        chat_input = f"【网页版AI方案】\n{webai_content}\n\n【用户指令】\n{chat_input}"
        st.session_state.webai_imported_content = ""

    if ("分析数据" in chat_input or "数据文件" in chat_input) \
            and st.session_state.get("loaded_data_files"):
        data_inject = "\n".join(
            f"【{k}】\n{v}" for k, v in st.session_state.loaded_data_files.items()
        )
        chat_input = f"以下是已加载的数据文件内容：\n{data_inject}\n\n用户问题：{chat_input}"

    st.session_state.chat_history.append({"role": "user", "content": chat_input})
    st.session_state.memory_logger.log_message("user", chat_input)
    with st.spinner("Agent思考中..."):
        ctx = f"""当前阶段: {st.session_state.phase}
已选赛题: {(st.session_state.get('selected_topic') or '未选择')[:500]}
建模方案摘要: {(st.session_state.get('modeling_plan') or '未生成')[:800]}
压力测试: {(st.session_state.get('pressure_report') or '未生成')[:300]}
PRD: {(st.session_state.get('prd_final') or st.session_state.get('prd_draft') or '未生成')[:300]}
代码摘要: {(st.session_state.get('coding_result') or '未生成')[:500]}
论文摘要: {(st.session_state.get('paper_draft') or '未生成')[:300]}"""
        messages_to_send = []
        if st.session_state.get("context_summary"):
            messages_to_send.append({
                "role": "system",
                "content": st.session_state.context_summary
            })
            st.session_state.context_summary = ""
        messages_to_send.append({
            "role": "system",
            "content": f"""你是APMCM数学建模Agent助手，全程参与用户的建模竞赛准备。你可以：
- 解释当前阶段的决策逻辑和方法选择理由
- 回答关于建模方案、代码、论文的任何问题
- 根据用户反馈调整方向和策略
请用中文回答，简洁有针对性。

{ctx}""",
        })
        recent_history = st.session_state.chat_history[-20:]
        messages_to_send.extend(recent_history)
        response = chat(messages_to_send)
    st.session_state.chat_history.append({"role": "assistant", "content": response})
    st.session_state.memory_logger.log_message("assistant", response)
    st.rerun()

autosave()
