# APMCM Agent 操作手册

> v3 — 2026-06-12

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

**方式一：dataset/ 目录（启动时预加载）**

将 PDF 文件放入对应文件夹（支持子文件夹）：
- `dataset/problems/` — 历年赛题 PDF
- `dataset/papers/`   — 优秀获奖论文 PDF
- `dataset/references/` — 参考文献 PDF
- `dataset/knowledge/` — 数学建模领域知识库 PDF
- `dataset/reference/` — 选题后动态加载文献 PDF

**方式二：inbox/ 目录（拖放即加载）[v3 新增]**

将文件拖放到 `inbox/` 对应子目录，启动时或点击侧边栏"扫描新文件"自动加载到 RAG：
- `inbox/problems/` — 赛题 PDF
- `inbox/papers/` — 获奖论文 PDF
- `inbox/references/` — 参考文献 PDF
- `inbox/knowledge/` — 领域知识 PDF
- `inbox/web_ai/` — 网页版 AI 回复 (.md .txt .pdf)

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
| 📥 文件收件箱 [v3] | inbox/ 目录文件统计 + 一键扫描加载 |
| 🔗 AI 网页版协作 [v3] | 导出上下文 / 读取网页版 AI 回复 |
| 🛠️ Skills 说明 | 项目 Skills vs Claude Code 内置 Skills 对比 |
| 💬 随时提问 | 输入问题获取当前项目背景下的 AI 回答 |

---

## 三、使用流程

### 第 1 步：上传赛题 PDF

界面出现三个上传框，分别上传本次比赛的 3 个备选赛题 PDF 文件。

- 点击 "Browse files" 选择 PDF
- 上传后自动解析文本，显示 "已解析: xxx.pdf"
- 至少上传 1 个，最多 3 个

> **新方式 [v3]**：也可以将赛题 PDF 直接放入 `inbox/problems/` 目录，在侧边栏"文件收件箱"中点击🔄扫描加载。

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
- 生成 `CLAUDE.md` — Claude Code / opencode 的操作手册
- 加载 `dataset/reference/` 目录（选题后动态推荐文献）
- 自动进入编码阶段

### 第 4 步：代码生成 + 审查 + 论文节同步

Agent 生成完整 Python 代码，并新增以下功能：

**代码三重审查**
点击 **运行 Skill 审查**，Agent 自动执行 think + check + tdd 三重审查。

**同步生成论文节**
- 在下拉框选择对应论文章节（如"3.1 模型建立"）
- 点击 **📖 生成这一节论文初稿**
- Agent 根据代码实现自动生成对应论文节（学术语言 + LaTeX 公式 + 具体数值）
- 自动保存到 `workspace/{session_id}/paper_sections/`

点击 **✅ 符合预期，继续** 进入图表阶段。

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

## 四、新功能 [v3]

### 文件收件箱（inbox/）

将 PDF 文件直接拖入对应子目录，无需通过浏览器上传：

1. 打开 `agent/inbox/` 目录
2. 将 PDF 文件放入对应子目录（problems/papers/references/knowledge）
3. 在侧边栏点击 **📥 文件收件箱** → **🔄 扫描新文件**

已处理的文件记录在 `.processed_files.json` 中，不会重复加载。

### AI 网页版协作

#### 导出上下文给网页版 AI

1. 在侧边栏 **🔗 AI 网页版协作** 中点击 **📤 导出上下文给网页版 AI**
2. Agent 自动打包当前阶段的上下文（赛题、方案、PRD 摘要、对话历史）为 `.md` 文件
3. 找到导出路径，将文件内容上传给 ChatGPT/Claude 等网页版 AI
4. 网页版 AI 根据上下文提供针对性的协

助建议

#### 导入网页版 AI 回复

1. 将网页版 AI 的回复保存为 `.md` 或 `.txt` 文件，放入 `inbox/web_ai/`
2. 在侧边栏输入文件名，点击 **📥 读取网页版 AI 回复**
3. 在对话框中输入 **"使用网页AI方案"** 或 **"应用网页AI回复"**
4. Agent 自动将网页版 AI 的回复注入上下文进行后续处理

### 对话记忆（memory/）

每次会话的完整对话过程自动保存到 `memory/{session_id}/` 目录：

```
memory/
└── 20260612_143000/
    ├── stage_01_input_20260612_143000.md
    ├── stage_02_topic_selection_20260612_143210.md
    └── ...
```

每阶段一个文件，消息实时追加写入。可用于：
- 回顾和复盘工作过程
- 上传给网页版 AI 提供完整上下文
- 提取关键决策点

---

## 五、Token 额度监控

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

## 六、产出文件结构

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
├── webai_collab/           # ★ 网页版 AI 协作导出 [v3]
│   └── export_modeling_20260612_143500.md
├── quota_log.json          # Token 用量日志
└── DONE.md                 # 完成报告
```

---

## 七、其他功能

### 与 Agent 对话

页面底部有对话输入框，可随时向 Agent 提问或给出反馈。所有对话实时写入 `memory/` 目录。

### 侧边栏提问

左侧仪表盘底部有「随时提问」输入框，Agent 会自动携带项目背景回答。

### 查看最终成果

点击 **📥 完成** 进入总结页，可切换标签查看：
- 建模方案 | 代码 | 图表方案 | 论文

### 查看工作日志

每次会话在 `logs/` 目录生成两个文件：
- `session_xxx.json` — 结构化日志（可用于程序分析）
- `session_xxx.md` — Markdown 格式日志（可用于发给 ChatGPT 网页版监督）

### 查看对话记忆

每次会话在 `memory/{session_id}/` 目录生成按阶段分文件的实时对话记录：
- `stage_01_input_xxx.md` 到 `stage_08_done_xxx.md`
- 每条消息即时写入，可用文本编辑器直接查看

### 重置会话

在完成页点击 **🔄 开始新会话** 清空所有状态重新开始。

---

## 八、常见问题

**Q: 启动时一直转圈？**
A: 首次启动需向量化全部 PDF（含 dataset/ 和 inbox/ 目录），等待 1-2 分钟即可。

**Q: embedding API 报错？**
A: 检查 `.env` 中 NVIDIA_API_KEY 是否正确，确认模型名为 `nvidia/nv-embed-v1`。

**Q: Chat 不回复？**
A: 检查 `.env` 中 DEEPSEEK_API_KEY 是否正确，确认网络能访问 `api.deepseek.com`。

**Q: 想换模型怎么办？**
A: 编辑 `.env` 中的 `MODEL_NAME` 和 `DEEPSEEK_BASE_URL`，重新启动即可。

**Q: PRD 和 CLAUDE.md 有什么用？**
A: PRD 是项目说明书（给人看），CLAUDE.md 是 AI 操作手册（给 AI 看）。

**Q: Token 额度不够怎么办？**
A: 在侧边栏下载任务交接文档，按指引切换到其他平台继续。

**Q: knowledge/ 和 reference/ 有什么区别？**
A: knowledge/ 是启动时预加载的领域知识库；reference/ 是选题确认后才加载的动态文献。

**Q: inbox/ 和 dataset/ 有什么区别？[v3]**
A: dataset/ 是系统级知识库，启动时全部加载；inbox/ 是用户级临时文件入口，支持增量按需加载，已处理文件不会重复索引。

**Q: 如何与网页版 AI 协作？[v3]**
A: 点击侧边栏"导出上下文给网页版AI"，将生成的 .md 文件复制给 ChatGPT/Claude 网页版；得到回复后保存文件到 inbox/web_ai/，在侧边栏输入文件名读取，然后在对话框输入"使用网页AI方案"即可注入。

**Q: 对话记忆保存在哪里？[v3]**
A: `memory/{session_id}/` 目录下，每个阶段一个 .md 文件，可随时用文本编辑器查看。
