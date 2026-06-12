# APMCM 数学建模 Agent

基于 RAG + LLM + 多 Skill 协作的数学建模竞赛辅助系统。

## 快速上手

### 1. 配置 API Key

复制 `.env.example` 为 `.env`，用记事本打开填入密钥：

```
DEEPSEEK_API_KEY=sk-xxxxxxxx     # https://platform.deepseek.com/api_keys
NVIDIA_API_KEY=nvapi-xxxxxxxx    # https://build.nvidia.com
```

### 2. 安装 & 启动

```bash
pip install -r requirements.txt
python -m streamlit run app/main.py --server.headless true
```

浏览器访问 **http://localhost:8501**。首次启动会向量化 `dataset/` 中的 PDF（约 1 分钟），之后秒开。

> Docker 部署：`docker-compose up -d`

---

## 界面布局

```
┌─ 左侧边栏 ─────────────┬─ 中间操作区 ─────────────────┬─ 右侧 ─┐
│ 项目仪表盘（进度）       │                              │        │
│ Token 额度监控           │   各阶段操作界面              │ 可选   │
│ 文件收件箱               │   （上传/选题/建模/代码…）    │ 折叠   │
│ AI 协作 / Skills         │                              │ 对话区 │
│ 随时提问                 │   模型输出结果展示            │        │
└─────────────────────────┴──────────────────────────────┴────────┘
                              │
                    底部全宽对话输入框
```

---

## 完整工作流程

### 阶段 1：上传赛题

1. 将 3 个备选赛题 PDF 分别放入 `workspace/upload/1/` `2/` `3/` 文件夹，或在界面 file_uploader 中上传
2. 点击 **🚀 开始分析** → 清除历史结果 → 进入选题分析

> 要删除选题：直接删除对应文件夹中的 PDF 文件，或点击界面 🗑️ 按钮

### 阶段 2：选题分析

- Agent 用 RAG 检索历史赛题和获奖论文，为 3 个选题打分
- 展示 LLM 推荐理由和数据库匹配分数
- 用户选择最终选题 → 点击 **✅ 确认选题**

导航：**⬅️ 返回上传** | **→ 建模方案**（如果已生成则亮起，否则灰色不可点击）

### 阶段 3：建模方案

核心阶段，包含多个步骤：

| 步骤 | 按钮 | 说明 |
|------|------|------|
| 生成方案 | 自动 | LLM 生成：问题分析 → 符号说明 → 3 种方案对比 → 推荐推导 → 创新点 |
| 选择数据 | 多选框 | 从 `inbox/data/` 选择 CSV/Excel 文件注入 Prompt |
| 压力测试 | 🔬 运行压力测试 | Skill 评估技术/时间/数据可行性 |
| 生成 PRD | 📄 生成 PRD | 输出 7 章结构化产品需求文档 → `workspace/PRD.md` |
| 生成 CLAUDE.md | 🤖 生成 CLAUDE.md | LLM 读取 `prepare_claude/` 文件夹内容后生成操作手册 |
| 需求对齐 | 💬 发起对齐 | grill-me 循环：用户反馈 → AI 追问 → 修订建议 |
| 确认 PRD | ✅ PRD 已对齐 | 确认最终版，进入编码 |

**外部参考**：可以在底部选择 `inbox/web_ai/` 中的 `.md` 文件或上传 `.md`，点击 🔄 重新生成方案时 LLM 会综合这些内容。

**重新生成规则**：点击 🔄 重新生成方案 → 旧结果归档到 `workspace/rubbish/` → 清空下游 → 从头生成

### 阶段 4：代码生成

进入后自动准备：

```
workspace/coding/{选题号}/prepare_{选题号}/
├── topic.md           # 赛题
├── modeling_plan.md   # 建模方案
├── references.md      # 相似题/论文参考
├── PRD.md             # 产品需求文档
├── CLAUDE.md          # 执行规范
└── *.csv / *.xlsx     # 数据文件
```

界面展示所有准备文件的清单。点击 **🚀 开始生成代码** → LLM 读取全部 `.md` 文件 → 生成 Python 代码 → 自动保存到 `workspace/coding/{选题号}/solution.py`。

代码审查和论文节同步：

| 按钮 | 说明 |
|------|------|
| 运行 Skill 审查 | think + check + tdd 三重审查 |
| 🧠 理解代码并生成摘要 | LLM 阅读代码 → `writing/{n}/prepare/code_summary.md` |
| 🧠 理解建模方案并生成摘要 | LLM 阅读方案 → `writing/{n}/prepare/model_summary.md` |
| 📖 生成这一节论文初稿 | 从 prepare 文件夹读取摘要 → 生成对应论文章节 |

### 阶段 5：图表方案

- LLM 设计图表清单（带编号：图表1-1 线性回归曲线）
- 方案文本保存到 `workspace/picture/figure_plan.md`
- 实际图表图片在代码运行后生成到 `workspace/picture/fig_*.png`

### 阶段 6：论文初稿

- 自动汇总 `workspace/writing/{选题号}/` 下所有节论文
- 如果已有分节论文 → 整合为完整论文
- 如果无分节 → LLM 从头生成完整论文
- 保存到 `workspace/writing/{选题号}/paper_complete.md`

### 阶段 7：论文润色

- 4 种润色类型：润色 / 翻译为英文 / 学术语法修正 / 逻辑优化
- 润色结果保存到 `workspace/writing/{选题号}/paper_polished.md`
- 可导出为 Word (.docx) 或 Markdown

---

## 导航规则

每个阶段顶部有双向导航按钮：

| ← 返回 | → 前进 | 启用条件 |
|--------|--------|----------|
| — | 🚀 开始分析 | 至少一个文件 |
| 返回上传 | → 建模方案 | `modeling_plan` 已存在 |
| 返回选题 | → 代码生成 | `coding_result` 已存在 |
| 返回建模 | → 图表方案 | `figure_descriptions` 已存在 |
| 返回代码 | → 论文初稿 | `paper_draft` 已存在 |
| 返回图表 | → 论文润色 | `polished_paper` 已存在 |
| 返回论文 | → 完成 | 始终可用 |

**→ 按钮灰色** = 下一阶段还没生成，不可点击。仅浏览不触发任何操作。**🔄 重新生成**才会清除下游并归档旧结果。

---

## 文件系统结构

```
workspace/
├── upload/               # 赛题上传（1/2/3 文件夹，固定位置）
│   ├── 1/                # 赛题1 PDF
│   ├── 2/                # 赛题2 PDF
│   └── 3/                # 赛题3 PDF
├── PRD.md                # 产品需求文档（建模阶段生成）
├── CLAUDE.md             # AI 操作手册（LLM 理解后生成）
├── prepare_claude/       # CLAUDE.md 生成前的准备工作文件
├── coding/               # 代码输出
│   └── {n}/              # 选题编号
│       ├── prepare_{n}/  # 代码生成的输入文件
│       └── solution.py   # 生成的代码
├── writing/              # 论文输出
│   └── {n}/
│       ├── prepare/      # 代码/方案摘要（LLM 先行理解）
│       ├── *_*.md        # 分节论文
│       ├── paper_complete.md   # 完整论文
│       └── paper_polished.md   # 润色版
├── picture/              # 图表输出
│   ├── figure_plan.md    # 图表方案说明
│   └── fig_*.png         # 运行代码生成的图片
└── rubbish/              # 归档旧结果（按时间戳分目录）
```

**关键原则**：所有文件在 `workspace/` 本地生成，前端仅用于展示。刷新/重启后可从文件恢复进度。

---

## 对话记忆

所有对话实时写入 `memory/{session_id}/stage_*.md`，每个阶段一个文件。即使刷新页面，对话记录也不会丢失。

---

## Token 额度监控

侧边栏实时显示用量进度条。触发 70%/90% 预警时自动生成多平台任务交接文档。

---

## 文档

- 架构详情：`introduce/architecture.md`
- 操作手册：`introduce/user-guide.md`
