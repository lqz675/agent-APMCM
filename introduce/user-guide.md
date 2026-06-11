# APMCM Agent 操作手册

## 一、环境准备

### 1. 配置 API Key

```powershell
cd G:\mathmodelAgent-APMCM\agent
Copy-Item .env.example .env
```

编辑 `.env` 文件：
```
DEEPSEEK_API_KEY=你的DeepSeek密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat
NVIDIA_API_KEY=你的NVIDIA密钥
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_EMBED_MODEL=nvidia/nv-embed-v1
```

### 2. 安装依赖

```powershell
pip install -r requirements.txt
```

### 3. 放置数据（可选，增强检索效果）

将 PDF 文件放入对应文件夹（支持子文件夹）：
- `dataset/problems/` — 历年赛题 PDF
- `dataset/papers/`   — 优秀获奖论文 PDF
- `dataset/references/` — 参考文献 PDF
- `dataset/knowledge/` — 数学建模领域知识库 PDF (新增)
- `dataset/reference/` — 选题后动态加载文献 PDF (新增，选题确认前不索引)

> 不放也可以，Agent 通过 LLM 知识仍可工作，但推荐效果会打折扣。

### 4. 启动 Agent

```powershell
cd G:\mathmodelAgent-APMCM\agent
python -m streamlit run app/main.py --server.headless true
```

浏览器访问 **http://localhost:8501**

> 首次启动会自动向量化全部 PDF 并缓存（约 1 分钟），之后秒开。

---

## 二、界面布局

### 全局侧边栏（左侧，全流程可见）

| 模块 | 功能 |
|------|------|
| 📊 项目仪表盘 | 8 阶段进度追踪 + 进度条 |
| 💰 Token 额度 | 实时用量监控 + 70%/90% 预警 + 多平台任务交接文档下载 |
| 🛠️ Skills 说明 | 项目 Skills vs Claude Code 内置 Skills 对比 |
| 💬 随时提问 | 输入问题获取当前项目背景下的 AI 回答 |

---

## 三、使用流程

### 第 1 步：上传赛题 PDF

界面出现三个上传框，分别上传本次比赛的 3 个备选赛题 PDF 文件。

- 点击 "Browse files" 选择 PDF
- 上传后自动解析文本，显示 "已解析: xxx.pdf"
- 至少上传 1 个，最多 3 个

点击 **🚀 开始分析**

### 第 2 步：选题分析

Agent 自动从历史数据库检索相似题目并推荐最优选题。

- 查看每个选题的「数据库匹配分数」
- 阅读 Agent 的详细推荐分析
- 在下拉框中选择最终选题

点击 **✅ 确认选题**

### 第 3 步：建模方案 + 压力测试 + PRD + 需求对齐

这是工作流中最核心的阶段，将原来分散的多个阶段整合为一体化流程：

**3a. 建模方案生成**
Agent 自动生成完整数学建模方案，包括问题分析、符号说明、3 种方案对比、推荐推导、创新点。

**3b. 压力测试**
点击 **🔬 运行压力测试** 按钮，Agent 从技术可行性、时间可行性、数据可行性三个维度评估方案，给出「通过 / 有风险 / 不建议」的明确结论。

**3c. 生成 PRD（产品需求文档）**
点击 **📄 生成 PRD** 按钮，Agent 生成结构化产品需求文档，包含：
- 问题重述、核心建模方法、技术方案(数学模型/求解器/数据处理)
- 执行计划(阶段+耗时)、风险与缓解措施
- 论文结构规划、待用户确认的关键决策

PRD 自动保存为 `workspace/{session_id}/PRD.md`。

**3d. 需求对齐（grill-me 循环）**
在 PRD 生成后，你可以反复反馈修改意见：
- 在文本框输入不满意的地方（例如："时间计划太紧"、"想用神经网络"）
- 点击 **💬 发起一轮对齐**，Agent 会追问挑战并给出修订建议
- 建议对齐 2-3 轮后确认

**3e. 生成 CLAUDE.md**
点击 **✅ PRD 已对齐，生成最终版 + CLAUDE.md** 按钮，Agent 自动：
- 确认 PRD 最终版
- 生成 `CLAUDE.md` — Claude Code / opencode 的操作手册，包含执行规范(think/tdd/check/hunt)、文件结构、Skills 说明
- 加载 `dataset/reference/` 目录（选题后动态推荐文献）
- 自动进入编码阶段

### 第 4 步：代码生成 + 审查 + 论文节同步

Agent 生成完整 Python 代码，并新增以下功能：

**代码三重审查**
点击 **运行 Skill 审查**，Agent 自动执行 think + check + tdd 三重审查：
- think: 设计决策是否合理
- check: 正确性/健壮性/可读性/竞赛规范合规性
- tdd: 检查 validate_output() 函数和测试覆盖

**同步生成论文节**
- 在下拉框选择对应论文章节（如"3.1 模型建立"）
- 点击 **📖 生成这一节论文初稿**
- Agent 根据代码实现自动生成对应论文节（学术语言 + LaTeX 公式 + 具体数值）
- 自动保存到 `workspace/{session_id}/paper_sections/`

点击 **✅ 符合预期，继续** 进入图表阶段。

> 如果结果不满意，点击 **🔄 重新生成** 即可。

### 第 5 步：图表方案

Agent 设计论文所需图表清单：
- 图表类型、展示目的、配色方案
- Nature/IEEE 等期刊风格建议

点击 **📝 生成论文** 继续。

### 第 6 步：论文初稿

Agent 生成完整论文，包含：
- 摘要 → 问题重述 → 模型建立 → 求解 → 检验 → 评价 → 参考文献

点击 **✨ 润色论文** 继续。

### 第 7 步：论文润色 + 导出

选择润色类型：
- **润色** — 语法修正和表达优化
- **翻译为英文** — 中译英
- **学术语法修正** — 严格学术规范
- **逻辑优化** — 增强论证连贯性

导出格式：
- **导出为 Word (.docx)** — 可编辑的 Word 文档
- **导出为 Markdown** — 保存到 workspace，可用 pandoc 转 PDF

---

## 四、Token 额度监控

### 工作原理

Agent 在每次 LLM 调用后自动估算 token 消耗并记录。侧边栏实时显示用量进度条。

### 预警机制

| 阈值 | 行为 |
|------|------|
| 70% | 侧边栏黄色警告 + 生成任务交接文档 |
| 90% | 再次警告 + 更新交接文档 |

### 切换平台

点击 **📋 查看任务交接文档** → **⬇️ 下载交接文档**，然后：

| 平台 | 操作方式 |
|------|----------|
| ChatGPT 网页版 | 上传 PRD.md 和 CLAUDE.md，发送接续指令 |
| Cursor | 打开项目目录，CLAUDE.md 自动被读取 |
| Codex (OpenAI) | CLAUDE.md 作为 system prompt，PRD.md 作为首条消息 |
| Claude Code 新会话 | `cd workspace/{session_id} && claude` |

### 平台切换

在侧边栏选择当前使用的平台：
- Claude Sonnet（默认，约 90K tokens/会话）
- Claude Opus 4.8（约 80K tokens/会话）
- ChatGPT-4o（约 120K tokens/会话）
- ChatGPT-5.5（约 150K tokens/会话）

---

## 五、产出文件结构

每次会话在 `workspace/{session_id}/` 下生成：

```
workspace/{session_id}/
├── PRD.md                  # 产品需求文档
├── CLAUDE.md               # Claude Code 操作手册
├── model_solution.py       # 生成的代码
├── README.md               # 运行说明
├── problem.txt             # 赛题文本
├── modeling_plan.md        # 建模方案
├── solution/               # 模块化代码（由 Claude Code 生成）
│   ├── data_processing.py
│   ├── model.py
│   ├── solver.py
│   ├── sensitivity.py
│   └── figures.py
├── figures/                # 图表输出
├── results/                # JSON 结果
├── paper_sections/         # 论文各节 Markdown
│   ├── sec_model.md
│   ├── sec_results.md
│   └── sec_sensitivity.md
├── quota_log.json          # Token 用量日志
└── DONE.md                 # 完成报告
```

---

## 六、其他功能

### 与 Agent 对话

页面底部有对话输入框，可随时向 Agent 提问或给出反馈。

### 侧边栏提问

左侧仪表盘底部有「随时提问」输入框，Agent 会自动携带项目背景回答。

### 查看最终成果

点击 **📥 完成** 进入总结页，可切换标签查看：
- 建模方案 | 代码 | 图表方案 | 论文

### 查看工作日志

每次会话在 `logs/` 目录生成两个文件：
- `session_xxx.json` — 结构化日志（可用于程序分析）
- `session_xxx.md` — Markdown 格式日志（可用于发给 ChatGPT 网页版监督）

### 查看 Token 日志

每次会话在 `workspace/{session_id}/` 下生成 `quota_log.json`，记录每次 LLM 调用的 stage、tokens、timestamp。

### 重置会话

点击左侧 **🔄 重置会话** 清空所有状态重新开始（需通过旧版 UI 路径或刷新页面）。

---

## 七、常见问题

**Q: 启动时一直转圈？**
A: 首次启动需向量化全部 PDF（含 knowledge/ 目录），等待 1-2 分钟即可。后续启动很快。

**Q: embedding API 报错？**
A: 检查 `.env` 中 NVIDIA_API_KEY 是否正确，确认模型名为 `nvidia/nv-embed-v1`。

**Q: Chat 不回复？**
A: 检查 `.env` 中 DEEPSEEK_API_KEY 是否正确，确认网络能访问 `api.deepseek.com`。

**Q: 想换模型怎么办？**
A: 编辑 `.env` 中的 `MODEL_NAME` 和 `DEEPSEEK_BASE_URL`，重新启动即可。支持任何 OpenAI 兼容 API。

**Q: PRD 和 CLAUDE.md 有什么用？**
A: PRD 是项目说明书（给人看），CLAUDE.md 是 Claude Code 操作手册（给 AI 看）。后者可在 opencode / Claude Code 新会话中自动加载，让 AI 从当前进度继续工作。

**Q: Token 额度不够怎么办？**
A: 在侧边栏下载任务交接文档，按指引切换到其他平台（ChatGPT/Cursor/Codex）继续。

**Q: knowledge/ 和 reference/ 有什么区别？**
A: knowledge/ 是启动时预加载的领域知识库（如教材、方法论 PDF）；reference/ 是选题确认后才加载的动态文献（如大模型推荐的特定论文）。分离设计避免启动时加载不必要的文献。
