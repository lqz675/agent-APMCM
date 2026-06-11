"""
skills_runner.py
统一的 Skill 调用接口。
调用任何 Skill 前先读取对应 SKILL.md，确保按规范使用。
"""
from pathlib import Path
from model import gpt_with_retry


SKILLS_BASE = Path(__file__).parent.parent / "skills"

# 项目内 Skills 的路径映射
SKILL_PATHS = {
    "pressure_test":  SKILLS_BASE / "codex-startup-pressure-test-skill" / "startup-pressure-test" / "SKILL.md",
    "star_up":        SKILLS_BASE / "waza" / "skills" / "star-up"       / "SKILL.md",
    "grill_me":       SKILLS_BASE / "skills" / "skills" / "productivity" / "grill-me" / "SKILL.md",
    "think":          SKILLS_BASE / "waza" / "skills" / "think"         / "SKILL.md",
    "check":          SKILLS_BASE / "waza" / "skills" / "check"         / "SKILL.md",
    "hunt":           SKILLS_BASE / "waza" / "skills" / "hunt"          / "SKILL.md",
    "tdd":            SKILLS_BASE / "skills" / "skills" / "engineering" / "tdd"    / "SKILL.md",
    "figure":         SKILLS_BASE / "scipilot-figure-skill"             / "SKILL.md",
    "gpt_academic":   SKILLS_BASE / "gpt_academic"                      / "SKILL.md",
}

# Claude Code 内置 Skill 对比说明（供用户参考）
CLAUDE_CODE_SKILLS = {
    "TodoWrite / TodoRead": "任务列表管理，追踪编码进度",
    "Bash":                 "执行终端命令、运行代码",
    "Read / Write / Edit":  "文件读写，精确编辑",
    "WebSearch":            "联网搜索最新资料",
    "Task":                 "启动子代理并行处理子任务",
}


def read_skill(skill_name: str) -> str:
    """读取 Skill 的 SKILL.md 说明文档"""
    path = SKILL_PATHS.get(skill_name)
    if path and path.exists():
        return path.read_text(encoding="utf-8")
    return f"[Skill '{skill_name}' 的 SKILL.md 未找到，路径: {path}]"


def run_skill(skill_name: str, context: str,
              extra_instruction: str = "", max_tokens: int = 2000) -> str:
    """
    通用 Skill 执行器：先读 SKILL.md，再按规范执行任务。
    
    Args:
        skill_name:        技能名（见 SKILL_PATHS）
        context:           当前任务上下文（赛题、建模方案等）
        extra_instruction: 额外指令
        max_tokens:        输出长度上限
    """
    skill_doc = read_skill(skill_name)
    prompt = f"""你是数学建模竞赛专家。请严格按照以下 Skill 说明执行任务。

=== Skill 说明 ===
{skill_doc[:2000]}

=== 任务上下文 ===
{context[:2000]}

=== 额外指令 ===
{extra_instruction or "按 Skill 说明完整执行"}

请按 Skill 规范输出结果："""
    return gpt_with_retry(prompt, max_tokens=max_tokens)


def run_pressure_test(question: str, modeling_plan: str) -> str:
    """运行 startup-pressure-test + star-up 压力测试，返回可行性报告"""
    ctx = f"赛题：{question[:400]}\n\n建模方案：{modeling_plan[:800]}"
    
    pressure = run_skill("pressure_test", ctx,
                         "对这个建模方案从技术可行性、时间可行性、数据可行性三个维度做压力测试，给出通过/有风险/不建议的明确结论",
                         max_tokens=1500)
    
    startup = run_skill("star_up", ctx,
                        "基于压力测试结果，给出启动这个方案的关键路径和最小可行实现步骤",
                        max_tokens=1000)
    
    return f"## 压力测试报告\n{pressure}\n\n## 启动分析\n{startup}"


def run_grill_me(prd_draft: str, user_feedback: str) -> str:
    """用 grill-me skill 根据用户反馈精炼 PRD"""
    ctx = f"当前 PRD 草稿：\n{prd_draft[:1500]}\n\n用户反馈：\n{user_feedback}"
    return run_skill("grill_me", ctx,
                     "根据用户反馈，用追问和挑战的方式找出 PRD 中的模糊点和潜在问题，然后给出修订建议",
                     max_tokens=1200)


def run_code_check(code: str, stage: str = "model") -> str:
    """用 think + check + tdd 对代码做三重审查"""
    ctx = f"当前代码（{stage} 阶段）：\n```python\n{code[:2000]}\n```"
    
    think_result = run_skill("think", ctx, "分析这段代码的设计决策是否合理，有哪些潜在改进方向", 600)
    check_result = run_skill("check", ctx, "按检查清单逐项审查：正确性/健壮性/可读性/竞赛规范合规性", 800)
    tdd_result   = run_skill("tdd",   ctx, "检查是否有 validate_output() 函数，测试覆盖是否充分", 400)
    
    return f"### think 分析\n{think_result}\n\n### check 审查\n{check_result}\n\n### TDD 检查\n{tdd_result}"


def get_skill_comparison() -> str:
    """返回项目 Skills vs Claude Code 内置 Skills 的对比说明"""
    project_skills = "\n".join(f"- **{k}**: {SKILL_PATHS[k].parent.name}" for k in SKILL_PATHS)
    cc_skills      = "\n".join(f"- **{k}**: {v}" for k, v in CLAUDE_CODE_SKILLS.items())
    return f"""## 项目 Skills（领域专业化）
{project_skills}

## Claude Code 内置 Skills（软件工程通用）
{cc_skills}

**使用原则**：数学建模领域问题优先用项目 Skills；文件操作、代码执行、任务管理用 Claude Code 内置 Skills。两者互补，不冲突。"""
