import os
import json
from datetime import datetime
from pathlib import Path


class WorkflowLogger:
    def __init__(self, log_dir="logs"):
        self.log_dir = Path(__file__).parent.parent / log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"session_{self.session_id}.json"
        self.md_file = self.log_dir / f"session_{self.session_id}.md"
        self.steps = []
        self._save()

    def log(self, phase, action, content, metadata=None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "phase": phase,
            "action": action,
            "content": content,
            "metadata": metadata or {}
        }
        self.steps.append(entry)
        self._save()
        return entry

    def log_user_input(self, question):
        return self.log("user_input", "用户输入问题", question)

    def log_topic_selection(self, topics, sims_scores, recommendation):
        return self.log("topic_selection", "选题分析",
                        recommendation,
                        {"topics": topics, "scores": sims_scores})

    def log_modeling(self, modeling_plan):
        return self.log("modeling", "建模方案生成", modeling_plan[:500])

    def log_pressure_test(self, test_result):
        return self.log("pressure_test", "压力测试", test_result)

    def log_grill_me(self, alignment_result):
        return self.log("grill_me", "用户对齐评估", alignment_result)

    def log_coding(self, code):
        return self.log("coding", "代码生成", code[:500])

    def log_figure(self, figure_desc):
        return self.log("figure", "图表生成", figure_desc)

    def log_paper_draft(self, paper):
        return self.log("paper_draft", "论文初稿", paper[:500])

    def log_paper_polish(self, polished):
        return self.log("paper_polish", "论文润色", polished[:500])

    def log_user_feedback(self, phase, feedback):
        return self.log("user_feedback", f"用户反馈-{phase}", feedback)

    def _save(self):
        with open(self.log_file, "w", encoding="utf-8") as f:
            json.dump({
                "session_id": self.session_id,
                "started_at": self.steps[0]["timestamp"] if self.steps else "",
                "steps": self.steps
            }, f, ensure_ascii=False, indent=2)
        self._save_markdown()

    def _save_markdown(self):
        lines = [
            f"# APMCM Agent 工作流日志",
            f"**Session**: {self.session_id}",
            f"**开始时间**: {self.steps[0]['timestamp'] if self.steps else 'N/A'}",
            "",
            "---",
            ""
        ]
        for i, step in enumerate(self.steps, 1):
            lines.append(f"## 步骤 {i}: {step['phase']} - {step['action']}")
            lines.append(f"**时间**: {step['timestamp']}")
            lines.append("")
            content = step['content']
            if len(content) > 2000:
                content = content[:2000] + "\n\n... (内容过长已截断)"
            lines.append(content)
            if step.get('metadata'):
                lines.append(f"\n**元数据**: `{json.dumps(step['metadata'], ensure_ascii=False)}`")
            lines.append("")
            lines.append("---")
            lines.append("")

        with open(self.md_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def get_summary(self):
        phases = {}
        for step in self.steps:
            p = step['phase']
            if p not in phases:
                phases[p] = 0
            phases[p] += 1
        return {
            "session_id": self.session_id,
            "total_steps": len(self.steps),
            "phases": phases,
            "log_file": str(self.log_file),
            "md_file": str(self.md_file)
        }
