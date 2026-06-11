"""
quota_monitor.py
追踪 token 使用量，在额度耗尽前提醒用户并生成任务交接文档，
支持切换到 ChatGPT/Codex/Cursor 继续工作。
"""
import json
from pathlib import Path
from datetime import datetime


# 各平台 token 估算限制（近似值，保守估计）
PLATFORM_LIMITS = {
    "Claude Sonnet":   90_000,
    "Claude Opus 4.8": 80_000,
    "ChatGPT-4o":      120_000,
    "ChatGPT-5.5":     150_000,
}

ALERT_THRESHOLDS = [0.70, 0.90]   # 70% 和 90% 时提醒

# 各平台接力使用指引
PLATFORM_HANDOFF_GUIDE = {
    "ChatGPT 网页版": {
        "url":   "https://chat.openai.com",
        "tip":   "上传 PRD.md 和 CLAUDE.md 后发送：'请继续执行这个数学建模任务，从[当前阶段]开始'",
        "limit": "上传文件大小 < 50MB",
    },
    "Cursor": {
        "url":   "https://cursor.sh",
        "tip":   "打开项目目录，CLAUDE.md 会自动被读取，直接在 Composer 里说'继续'",
        "limit": "需要本地 Git 仓库",
    },
    "Codex (OpenAI)": {
        "url":   "https://platform.openai.com/codex",
        "tip":   "将 CLAUDE.md 作为 system prompt，将 PRD.md 作为第一条 user 消息",
        "limit": "需要 API key",
    },
    "Claude Code (新会话)": {
        "url":   "终端: claude",
        "tip":   "cd workspace/{session_id} && claude，新会话会自动读 CLAUDE.md",
        "limit": "需要订阅 Claude Pro",
    },
}


class QuotaMonitor:
    def __init__(self, platform: str = "Claude Sonnet"):
        self.platform     = platform
        self.limit        = PLATFORM_LIMITS.get(platform, 90_000)
        self.used_tokens  = 0
        self.stage_log    = []   # [{stage, tokens, timestamp}]
        self._alerted     = set()

    def record(self, stage: str, tokens: int):
        """记录一次 LLM 调用的 token 消耗（估算：字符数 / 3）"""
        self.used_tokens += tokens
        self.stage_log.append({
            "stage":     stage,
            "tokens":    tokens,
            "total":     self.used_tokens,
            "timestamp": datetime.now().isoformat(),
        })

    def estimate_tokens(self, text: str) -> int:
        """粗估 token 数（中英文混合按字符/2计算）"""
        return len(text) // 2

    @property
    def usage_ratio(self) -> float:
        return self.used_tokens / self.limit if self.limit > 0 else 0

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.limit - self.used_tokens)

    def should_alert(self) -> tuple[bool, float]:
        """返回 (是否需要提醒, 当前使用率)"""
        for threshold in ALERT_THRESHOLDS:
            if self.usage_ratio >= threshold and threshold not in self._alerted:
                self._alerted.add(threshold)
                return True, threshold
        return False, self.usage_ratio

    def get_status_text(self) -> str:
        pct = self.usage_ratio * 100
        remaining_k = self.remaining_tokens // 1000
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        return f"[{bar}] {pct:.0f}%  已用 {self.used_tokens:,} / {self.limit:,} tokens（剩余约 {remaining_k}k）"

    def generate_handoff_doc(self, session_id: str, current_stage: str,
                              completed_stages: list, workspace_path: str,
                              prd_summary: str = "") -> str:
        """生成任务交接文档，供切换平台时使用"""
        remaining_stages = self._get_remaining_stages(completed_stages)
        
        doc = f"""# APMCM 任务交接文档
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**当前平台**: {self.platform}（额度已用 {self.usage_ratio*100:.0f}%，需切换）
**工作目录**: {workspace_path}

---

## 当前进度

| 阶段 | 状态 |
|------|------|
"""
        all_stages = ["选题确认", "建模方法确认", "压力测试", "PRD生成",
                      "需求对齐(grill-me)", "代码生成", "图表生成", "论文撰写", "论文润色"]
        for s in all_stages:
            status = "✅ 已完成" if s in completed_stages else ("🔄 进行中" if s == current_stage else "⏳ 待执行")
            doc += f"| {s} | {status} |\n"

        doc += f"""
---

## 接续任务说明

你（新 AI 助手）需要从 **{current_stage}** 继续执行。

接续要做的事：
"""
        for i, stage in enumerate(remaining_stages, 1):
            doc += f"{i}. {stage}\n"

        doc += f"""
---

## 关键上下文

{prd_summary[:1000] if prd_summary else '详见工作目录中的 PRD.md 和 CLAUDE.md'}

**文件位置**：
- PRD: `{workspace_path}/PRD.md`
- CLAUDE.md: `{workspace_path}/CLAUDE.md`
- 已完成代码: `{workspace_path}/solution/`
- 已生成图表: `{workspace_path}/figures/`
- 已写论文节: `{workspace_path}/paper_sections/`

---

## 各平台接续方式
"""
        for platform, info in PLATFORM_HANDOFF_GUIDE.items():
            doc += f"""
### {platform}
- 地址：{info['url']}
- 操作：{info['tip'].format(session_id=session_id)}
- 注意：{info['limit']}
"""
        return doc

    def _get_remaining_stages(self, completed: list) -> list:
        all_stages = ["选题确认", "建模方法确认", "压力测试", "PRD生成",
                      "需求对齐(grill-me)", "代码生成", "图表生成", "论文撰写", "论文润色"]
        return [s for s in all_stages if s not in completed]

    def save_log(self, workspace_path: Path):
        """保存 token 使用日志"""
        workspace_path.mkdir(parents=True, exist_ok=True)
        log_path = workspace_path / "quota_log.json"
        log_path.write_text(
            json.dumps({
                "platform":    self.platform,
                "limit":       self.limit,
                "used":        self.used_tokens,
                "usage_pct":   round(self.usage_ratio * 100, 1),
                "stage_log":   self.stage_log,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
