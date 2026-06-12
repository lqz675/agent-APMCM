"""将用户与 agent 的每一轮对话实时追加写入 memory/ 目录下的 Markdown 文件。

每个 session 独立存放，每个阶段一个文件，阶段内消息追加到同一文件。
"""
import json
import threading
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEMORY_ROOT = PROJECT_ROOT / "memory"

PHASE_ORDER = {
    "input": 1,
    "topic_selection": 2,
    "modeling": 3,
    "coding": 4,
    "figure": 5,
    "paper": 6,
    "polish": 7,
    "done": 8,
}

ROLE_DISPLAY = {
    "user": "👤 用户",
    "assistant": "🤖 Agent",
    "system": "⚙️ 系统",
}


class MemoryLogger:
    """实时对话记忆记录器，按 session + 阶段分文件存储。"""

    def __init__(self, session_id):
        """初始化 MemoryLogger。

        Args:
            session_id (str): 会话 ID，用于创建 memory/{session_id}/ 子目录
        """
        MEMORY_ROOT.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id
        self.memory_dir = MEMORY_ROOT / session_id
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.current_phase = None
        self.current_file = None
        self.stage_count = 0
        self._lock = threading.Lock()

    def new_stage(self, phase):
        """切换到新阶段，创建新文件并写入文件头。

        如果 phase 与当前阶段相同，不重复创建（幂等）。

        Args:
            phase (str): 阶段英文名
        """
        if phase == self.current_phase:
            return

        self.current_phase = phase
        self.stage_count = PHASE_ORDER.get(phase, 99)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"stage_{self.stage_count:02d}_{phase}_{timestamp}.md"
        self.current_file = self.memory_dir / filename

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = f"""# APMCM Agent 对话记忆
- **Session**: {self.session_id}
- **阶段**: {self.stage_count} — {phase}
- **开始时间**: {now_str}

---

"""
        with self._lock:
            self.current_file.write_text(header, encoding="utf-8")

    def log_message(self, role, content, metadata=None):
        """将一条消息追加写入当前文件。

        若当前文件未创建，先调用 new_stage("input")。

        Args:
            role (str): 消息角色（user / assistant / system）
            content (str): 消息内容
            metadata (dict, optional): 附加元数据，会以 JSON 格式追加
        """
        if self.current_file is None:
            self.new_stage("input")

        timestamp = datetime.now().strftime("%H:%M:%S")
        role_str = ROLE_DISPLAY.get(role, role)

        entry = f"## [{timestamp}] {role_str}\n{content}\n\n"

        if metadata:
            meta_str = json.dumps(metadata, ensure_ascii=False)
            entry += f"> `{meta_str}`\n\n"

        with self._lock:
            with open(self.current_file, "a", encoding="utf-8") as f:
                f.write(entry)
                f.flush()

    def log_system_event(self, event, detail=""):
        """记录系统事件（阶段切换、技能调用、文件操作等）。

        Args:
            event (str): 事件名称
            detail (str): 事件详情
        """
        self.log_message("system", f"**{event}**\n{detail}")

    def get_current_file_path(self):
        """返回当前文件的绝对路径字符串，若无则返回 None。"""
        if self.current_file:
            return str(self.current_file.absolute())
        return None

    def get_all_stage_files(self):
        """返回当前 session 所有阶段文件列表。

        Returns:
            list[dict]: [{"stage": int, "phase": str, "path": str, "filename": str}, ...]
        """
        if not self.memory_dir.exists():
            return []

        results = []
        for f in sorted(self.memory_dir.glob("stage_*.md")):
            name = f.name
            try:
                parts = name.replace(".md", "").split("_", 3)
                stage_num = int(parts[1]) if len(parts) >= 2 else 0
                phase_name = parts[2] if len(parts) >= 3 else "unknown"
            except (ValueError, IndexError):
                stage_num = 0
                phase_name = "unknown"

            results.append({
                "stage": stage_num,
                "phase": phase_name,
                "path": str(f.absolute()),
                "filename": name,
            })

        return sorted(results, key=lambda x: x["stage"])
