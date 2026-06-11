"""
prd_generator.py
根据建模方案和对齐结果生成 PRD 和 CLAUDE.md，
PRD 是给用户和团队看的，CLAUDE.md 是给 Claude Code 执行的。
"""
from pathlib import Path
from datetime import datetime
from model import gpt_with_retry
from skills_runner import get_skill_comparison


def generate_prd(question: str, modeling_plan: str,
                 pressure_report: str, align_context: dict,
                 session_id: str) -> str:
    """生成结构化 PRD（产品需求文档）"""
    prompt = f"""你是数学建模竞赛项目经理，请根据以下信息生成完整的 PRD 文档。
格式严格按模板，内容要具体可执行。

赛题（前500字）：
{question[:500]}

建模方案：
{modeling_plan[:1000]}

压力测试报告：
{pressure_report[:800]}

用户对齐信息：
{str(align_context)}

请生成以下结构的 PRD（Markdown 格式）：

# APMCM 数学建模 PRD
**会话ID**: {session_id} | **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 1. 问题重述（100字以内，用自己的话）
## 2. 核心建模方法（方法名 + 一句话理由）
## 3. 技术方案
   ### 3.1 数学模型（核心公式，LaTeX格式）
   ### 3.2 求解器与工具
   ### 3.3 数据处理方案
## 4. 执行计划（阶段 + 预计耗时）
   | 阶段 | 内容 | 预计时间 | 成功标准 |
## 5. 风险与缓解措施
## 6. 论文结构规划（章节标题列表）
## 7. 待用户确认的关键决策（列出3-5个需要用户明确的点）"""

    return gpt_with_retry(prompt, max_tokens=2500)


def generate_claude_md(prd: str, modeling_plan: str,
                       workspace_path: Path, session_id: str) -> Path:
    """根据 PRD 生成 CLAUDE.md，这是 Claude Code 的操作手册"""
    skill_comparison = get_skill_comparison()
    
    content = f"""# APMCM 项目操作手册
> 会话: {session_id} | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
> **本文件由 Agent PRD 自动生成，是你在本项目中的唯一行动指南**

---

## 你的当前任务

基于已确认的 PRD 和建模方案，实现可运行的数学建模代码并完成对应论文节。

---

## PRD 摘要
{prd[:2000]}

---

## 完整建模方案
{modeling_plan[:1500]}

---

## 执行规范（每个编码步骤必须遵守）

### 编码前（think skill）
在开始任何文件前，先在注释里写：
```
# === 设计决策 ===
# 为什么选这个方案：
# 最大风险点：
# 验收标准：
# ================
```

### 编码中（tdd skill）
每个模块必须有：
1. `validate_output(result)` — 先定义验收函数
2. 实现代码
3. `if __name__ == "__main__": validate_output(solve())`

### 编码后（check skill）
每个文件完成后自问：
- [ ] 中文注释完整？
- [ ] 无硬编码路径？
- [ ] 错误处理有明确报错信息？
- [ ] 数值结果保留4位有效数字？
- [ ] 随机种子已设置（np.random.seed(42)）？

### 遇到 Bug（hunt skill）
1. 先隔离：最小复现代码
2. 再假设：列出3个可能原因
3. 逐一验证，不要乱改

---

## 文件结构（必须遵守）
```
workspace/{session_id}/
├── solution/
│   ├── data_processing.py   # 数据处理
│   ├── model.py             # 核心模型
│   ├── solver.py            # 求解输出
│   ├── sensitivity.py       # 敏感性分析
│   └── figures.py           # 图表生成
├── figures/                 # 图表输出目录
├── results/                 # JSON 结果目录
├── paper_sections/          # 每完成一段代码对应的论文节
│   ├── sec_model.md
│   ├── sec_results.md
│   └── sec_sensitivity.md
└── DONE.md                  # 完成报告
```

---

## 完成每个 solution/ 文件后

**立即执行**：
1. 运行该文件验证无报错
2. 在 `paper_sections/` 写对应的论文节（Markdown）：
   - 说明这段代码对应论文第几章
   - 包含关键公式（LaTeX）
   - 包含结果数值
3. 在聊天里向用户汇报：当前产出是什么，结果是否符合预期

---

{skill_comparison}

---

## 完成信号
全部完成后创建 `DONE.md`，格式：
```markdown
# 完成报告
## 各文件状态
## 核心数值结果
## 生成的图表
## 给论文作者的备注
```
"""
    path = workspace_path / "CLAUDE.md"
    path.write_text(content, encoding="utf-8")
    return path


def export_prd_file(prd: str, workspace_path: Path, session_id: str) -> Path:
    """将 PRD 保存为独立 Markdown 文件"""
    workspace_path.mkdir(parents=True, exist_ok=True)
    path = workspace_path / "PRD.md"
    path.write_text(prd, encoding="utf-8")
    return path
