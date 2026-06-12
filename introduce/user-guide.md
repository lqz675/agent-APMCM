# APMCM Agent 操作手册

> v3.1 — 2026-06-12

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
- `dataset/data/raw/` — 赛题原始数据 CSV/Excel
- `dataset/data/processed/` — 处理后的中间数据
- `dataset/data/external/` — 外部公开数据集

**方式二：inbox/ 目录（拖放即加载）**

将文件拖放到 `inbox/` 对应子目录：
- `inbox/problems/` — 赛题 PDF
- `inbox/papers/` — 获奖论文 PDF
- `inbox/references/` — 参考文献 PDF
- `inbox/knowledge/` — 领域知识 PDF
- `inbox/web_ai/` — 网页版 AI 回复 (.md .txt .pdf)
- `inbox/data/` — ★ CSV/Excel 数据文件 [v3.1]

### 4. 启动 Agent

```powershell
cd G:\mathmodelAgent-APMCM\agent
python -m streamlit run app/main.py --server.headless true
```

浏览器访问 **http://localhost:8501**

---

## 二、界面布局

### 全局侧边栏

| 模块 | 功能 |
|------|------|
| 📊 项目仪表盘 | 8 阶段进度追踪 + 进度条 |
| 💰 Token 额度 | 实时用量监控 + 70%/90% 预警 + 多平台任务交接文档下载 |
| 📥 文件收件箱 | inbox/ 目录文件统计 + 扫描加载 + 📊 数据文件加载 |
| 🔗 AI 网页版协作 | 导出上下文 / 读取网页版 AI 回复 |
| 🛠️ Skills 说明 | 项目 Skills vs Claude Code 内置 Skills 对比 |
| 💬 随时提问 | 输入问题获取当前项目背景下的 AI 回答 |

---

## 三、使用流程

### 第 1 步：上传赛题 PDF

界面出现三个上传框，分别上传本次比赛的 3 个备选赛题 PDF 文件。

> **新方式**：也可以将赛题 PDF 直接放入 `inbox/problems/` 目录，在侧边栏"文件收件箱"中点击🔄扫描加载。

点击 **🚀 开始分析**

### 第 2 步：选题分析

Agent 自动从历史数据库检索相似题目并推荐最优选题。查看匹配分数和推荐分析，选择最终选题。

点击 **✅ 确认选题**

### 第 3 步：建模方案 + 压力测试 + PRD + 需求对齐

**3a. 建模方案生成** — Agent 自动生成完整数学建模方案。

**3b. 压力测试** — 点击 **🔬 运行压力测试**，从技术/时间/数据三维度评估。

**3c. 生成 PRD** — 点击 **📄 生成 PRD**，生成结构化产品需求文档。

**3d. 需求对齐（grill-me 循环）** — 输入反馈，反复对齐 2-3 轮后确认。

**3e. 生成 CLAUDE.md** — 点击 **✅ PRD 已对齐** 生成 AI 操作手册并进入编码。

### 第 4 步：代码生成 + 审查 + 论文节同步

Agent 生成完整 Python 代码（★ 自动附带已加载的数据文件摘要作为 Prompt 上下文）。

- 点击 **运行 Skill 审查** 执行 think + check + tdd 三重审查
- 选择论文章节 → 点击 **📖 生成这一节论文初稿**

点击 **✅ 符合预期，继续** 进入图表阶段。

### 第 5 步：图表方案

Agent 设计论文所需图表清单。点击 **📝 生成论文** 继续。

### 第 6 步：论文初稿

Agent 生成完整论文。点击 **✨ 润色论文** 继续。

### 第 7 步：论文润色 + 导出

选择润色类型（润色/翻译为英文/语法修正/逻辑优化），导出 Word (.docx) 或 Markdown。

---

## 四、核心功能详解

### 📥 文件收件箱

将 PDF 文件直接拖入 `inbox/problems/` 等子目录，点击侧边栏 **🔄 扫描新文件** 自动加载到 RAG。已处理文件记录在 `.processed_files.json` 中不重复加载。

### 📊 数据文件（CSV / Excel）[v3.1]

将 `.csv` / `.xlsx` / `.xls` 文件放入 `inbox/data/` 目录，在侧边栏文件收件箱中：

1. 查看文件列表（名称 + 大小）
2. 点击每个文件旁的 **加载** 按钮 → 自动解析并显示预览（形状/列名/前 200 行）
3. 在对话框输入 **"分析数据"** 或 **"数据文件"** → Agent 自动将所有已加载数据摘要注入对话

进入代码生成阶段时，已加载的数据摘要会自动拼接到 Prompt 中，无需手动操作。

### 🔗 AI 网页版协作

**导出**：点击 **📤 导出上下文给网页版 AI** → 打包当前阶段上下文为 .md → 上传给 ChatGPT/Claude 网页版。

**导入**：网页版 AI 回复保存到 `inbox/web_ai/` → 侧边栏输入文件名 → 点击 **📥 读取** → 对话框输入 **"使用网页AI方案"** 注入。

### 🧠 对话记忆

所有对话实时保存到 `memory/{session_id}/stage_*.md`，按阶段分文件，每条消息即时写入。

---

## 五、Token 额度监控

### 预警机制

| 阈值 | 行为 |
|------|------|
| 70% | 侧边栏黄色警告 + 生成任务交接文档 |
| 90% | 再次警告 + 更新交接文档 |

### 平台切换

| 平台 | 操作方式 |
|------|----------|
| ChatGPT 网页版 | 上传 PRD.md 和 CLAUDE.md，发送接续指令 |
| Cursor | 打开项目目录，CLAUDE.md 自动被读取 |
| Codex (OpenAI) | CLAUDE.md 作为 system prompt |
| Claude Code 新会话 | `cd workspace/{session_id} && claude` |

---

## 六、产出文件结构

```
workspace/{session_id}/
├── PRD.md                  # 产品需求文档
├── CLAUDE.md               # AI 操作手册
├── model_solution.py       # 生成的代码
├── README.md               # 运行说明
├── problem.txt             # 赛题文本
├── modeling_plan.md        # 建模方案
├── solution/               # 模块化代码
│   ├── data_processing.py
│   ├── model.py
│   ├── solver.py
│   ├── sensitivity.py
│   └── figures.py
├── figures/                # 图表输出
├── results/                # JSON 结果
├── paper_sections/         # 论文各节
├── webai_collab/           # 网页版 AI 导出
├── quota_log.json          # Token 用量日志
└── DONE.md                 # 完成报告
```

---

## 七、其他功能

### 与 Agent 对话

页面底部有对话输入框，支持关键词触发：
- **"使用网页AI方案"** / **"应用网页AI回复"** → 注入网页版 AI 回复
- **"分析数据"** / **"数据文件"** → 注入已加载的 CSV/Excel 数据摘要

### 查看日志

- `logs/session_xxx.json` + `logs/session_xxx.md` — 工作流日志
- `memory/{session_id}/stage_*.md` — 对话记忆

### 重置会话

完成页点击 **🔄 开始新会话** 清空所有状态重新开始。

---

## 八、常见问题

**Q: 如何加载 CSV/Excel 数据？[v3.1]**
A: 将文件放入 `inbox/data/`，在侧边栏"文件收件箱"中找到文件并点击"加载"按钮。之后在对话中说"分析数据"即可自动引用。

**Q: 数据文件支持什么格式？[v3.1]**
A: `.csv`（UTF-8/GBK 自动检测）、`.xlsx`、`.xls`。需要安装依赖：`pip install pandas openpyxl`。

**Q: 数据会重复加载吗？**
A: CSV/Excel 数据通过侧边栏按钮按需加载，只加载本次点击的文件。与 PDF 不同，不经过 RAG 向量化，直接以文本摘要形式注入 Prompt。

**Q: inbox/ 和 dataset/ 有什么区别？**
A: dataset/ 是系统级知识库，启动时全部加载；inbox/ 是用户级临时文件入口，支持手动按需加载。

**Q: 如何与网页版 AI 协作？**
A: 侧边栏导出 .md 上下文包 → 复制给网页版 AI → 回复保存到 inbox/web_ai/ → 输入文件名读取 → 对话说"使用网页AI方案"注入。
