# APMCM 数学建模 Agent

> v3.1 — 基于 RAG + LLM + 多 Skill 协作的数学建模竞赛辅助系统

支持选题推荐、建模方案设计、压力测试、PRD 生成、代码生成与审查、论文撰写与润色的全流程自动化。

v3.1 新增：CSV/Excel 数据文件支持（inbox/data/ + 分析数据关键词）。

## 项目结构

```
agent/
├── app/                                # 核心代码 (14 个模块)
│   ├── main.py                         # Streamlit 界面 + 9 阶段工作流 + 全局侧边栏
│   ├── rag.py                          # FAISS 多源向量检索引擎 + inbox 增量加载
│   ├── model.py                        # LLM / Embedding / Rerank 多 API 层
│   ├── prompts.py                      # 8 个阶段 Prompt 模板工厂
│   ├── skills_runner.py                # 统一 Skill 调用入口
│   ├── prd_generator.py                # PRD + CLAUDE.md 自动生成
│   ├── quota_monitor.py                # Token 额度监控 + 平台接力
│   ├── utils.py                        # PDF 解析、表格文件读取、文本分块
│   ├── skills_bridge.py                # 外部 Skill 桥接层
│   ├── workflow_logger.py              # 双格式工作流日志 (JSON+MD)
│   ├── inbox_watcher.py                # ★ inbox/ 文件扫描与增量加载
│   ├── webai_bridge.py                 # ★ 网页版 AI 协作桥接层
│   ├── memory_logger.py                # ★ 实时对话记忆记录器
│   └── __init__.py
├── inbox/                              # ★ 文件收件箱（拖放即加载）
│   ├── problems/ / papers/ / references/ / knowledge/ / web_ai/
│   ├── data/                           # ★ CSV/Excel 数据文件 [v3.1]
│   └── README.md
├── memory/                             # ★ 对话记忆目录
│   └── {session_id}/stage_*.md
├── skills/                             # 外部 Skill 仓库 (5 个)
├── dataset/
│   ├── problems/ / papers/ / references/ / knowledge/ / reference/
│   ├── data/                           # ★ 结构化数据 [v3.1]
│   │   ├── raw/ / processed/ / external/
│   │   └── README.md
│   └── cache/                          # 向量缓存
├── workspace/                          # 产出（运行时生成）+ webai_collab/
├── logs/ / introduce/ / update/
├── requirements.txt / .env.example
└── README.md
```

## 快速开始

```bash
cp .env.example .env      # 填入密钥
pip install -r requirements.txt
streamlit run app/main.py
# 访问 http://localhost:8501
```

## 工作流程

```
上传赛题 PDF (file_uploader 或 inbox/ 拖放)
  → 1. 选题分析 (RAG + LLM 推荐)
  → 2. 建模方案 + 压力测试 + PRD + 需求对齐 (一体化)
  → 3. 代码生成 + 三重审查 + ★ 数据文件自动注入
  → 4. 图表方案设计
  → 5. 论文初稿
  → 6. 论文润色 + 导出 (Word / Markdown)
```

## v3 核心功能

### 📥 文件收件箱

PDF 拖入 `inbox/` 对应子目录 → 侧边栏"扫描新文件" → 自动加载到 RAG。

### 📊 数据文件 [v3.1]

CSV/Excel 放入 `inbox/data/` → 侧边栏点击"加载" → 预览形状/列名/前 200 行 → 对话说"分析数据"自动引用。代码生成阶段自动注入到 Prompt。

### 🔗 AI 网页版协作

导出当前阶段上下文 → 上传给 ChatGPT/Claude 网页版 → 回复保存到 inbox/web_ai/ → 读取 → 对话注入。

### 🧠 对话记忆

所有对话实时保存到 `memory/{session_id}/stage_*.md`，按阶段分文件。

## 三种文件输入方式

| 方式 | 入口 | 适用场景 |
|------|------|----------|
| 方式A | Streamlit file_uploader | 主工作流赛题 |
| 方式B | inbox/ 目录拖放 | 补充文献、知识库 |
| 方式C | inbox/web_ai/ + 侧边栏 | 网页版 AI 协作 |
| 方式D | inbox/data/ + 侧边栏加载 | ★ CSV/Excel 数据 [v3.1] |

## 对话关键词触发

| 关键词 | 效果 |
|--------|------|
| "使用网页AI方案" / "应用网页AI回复" | 注入已读取的网页 AI 回复 |
| "分析数据" / "数据文件" | 注入已加载的 CSV/Excel 数据摘要 |

## API Key 配置

| 变量 | 用途 | 获取地址 |
|------|------|----------|
| `DEEPSEEK_API_KEY` | LLM 对话 | https://platform.deepseek.com/api_keys |
| `NVIDIA_API_KEY` | 向量 Embedding | https://build.nvidia.com/explore/discover |
| `JINA_API_KEY` (可选) | Jina Reranker | https://jina.ai/embeddings/ |

## 数据集

| 目录 | 格式 | 索引时机 |
|------|------|----------|
| `dataset/problems/` | PDF | 启动时 |
| `dataset/papers/` | PDF | 启动时 |
| `dataset/knowledge/` | PDF | 启动时 |
| `dataset/data/raw/` [v3.1] | CSV/Excel | 按需 |
| `inbox/data/` [v3.1] | CSV/Excel | 手动加载 |

## Token 额度监控

侧边栏实时显示用量进度条，70%/90% 自动预警，一键生成多平台任务交接文档。

## 文档

- 架构详情：`introduce/architecture.md`
- 操作手册：`introduce/user-guide.md`
- 变更日志：`update/`
