# APMCM 数学建模 Agent

> v3 — 基于 RAG + LLM + 多 Skill 协作的数学建模竞赛辅助系统

支持选题推荐、建模方案设计、压力测试、PRD 生成、代码生成与审查、论文撰写与润色的全流程自动化。

v3 新增：文件收件箱 (inbox/)、AI 网页版协作桥接 (webai_bridge)、实时对话记忆 (memory/)。

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
│   ├── utils.py                        # PDF 解析、文本分块、通用文件读取
│   ├── skills_bridge.py                # 外部 Skill 桥接层
│   ├── workflow_logger.py              # 双格式工作流日志 (JSON+MD)
│   ├── inbox_watcher.py                # ★ inbox/ 文件扫描与增量加载 [v3]
│   ├── webai_bridge.py                 # ★ 网页版 AI 协作桥接层 [v3]
│   ├── memory_logger.py                # ★ 实时对话记忆记录器 [v3]
│   └── __init__.py
├── inbox/                              # ★ 文件收件箱（拖放即加载）[v3]
│   ├── problems/ / papers/ / references/ / knowledge/ / web_ai/
│   └── README.md
├── memory/                             # ★ 对话记忆目录 [v3]
│   ├── README.md
│   └── {session_id}/stage_*.md
├── skills/                             # 外部 Skill 仓库
│   ├── codex-startup-pressure-test-skill/
│   ├── skills/                         # grill-me, tdd, hunt 等
│   ├── waza/                           # think, check, design 等
│   ├── scipilot-figure-skill/
│   └── gpt_academic/                   # 论文润色 (71 插件)
├── dataset/
│   ├── problems/ / papers/ / references/ / knowledge/ / reference/
│   └── cache/                          # 向量缓存（自动生成）
├── workspace/                          # 产出（运行时生成）+ webai_collab/ [v3]
├── logs/                               # 工作流日志
├── introduce/                          # 架构文档 + 操作手册
├── update/                             # 变更日志
├── requirements.txt
├── .env.example
└── README.md
```

## 快速开始

### Docker 部署（推荐）

```bash
# 1. 配置 API Key
cp .env.example .env
# 编辑 .env，填入真实密钥

# 2. (可选) 放入 PDF 数据
#    dataset/{problems,papers,knowledge}/   ← 系统知识库
#    inbox/{problems,papers,knowledge}/     ← 临时文件拖放 [v3]

# 3. 一键启动
docker-compose up -d
# 浏览器打开 http://localhost:8501
```

### 本地部署

```bash
cp .env.example .env      # 填入密钥
pip install -r requirements.txt
streamlit run app/main.py
```

## 工作流程

```
上传赛题 PDF (file_uploader 或 inbox/ 拖放)
  → 1. 选题分析 (RAG + LLM 推荐)
  → 2. 建模方案 + 压力测试 + PRD + 需求对齐 (一体化)
      ├── 生成建模方案
      ├── 运行压力测试 (技术/时间/数据 三维度)
      ├── 生成 PRD.md (产品需求文档)
      ├── grill-me 循环对齐
      └── 生成 CLAUDE.md (AI 操作手册)
  → 3. 代码生成 + 三重审查 + 论文节同步
  → 4. 图表方案设计
  → 5. 论文初稿
  → 6. 论文润色 + 导出 (Word / Markdown)
```

全局侧边栏提供：进度追踪、Token 额度监控（70%/90% 预警 + 一键生成多平台交接文档）、文件收件箱、AI网页版协作、Skills 说明、随时提问。

## v3 新功能

### 📥 文件收件箱

将 PDF 文件直接拖入 `inbox/{problems,papers,references,knowledge}/` 目录，在侧边栏点击"扫描新文件"即可自动加载到 RAG 知识库，无需浏览器上传。

### 🔗 AI 网页版协作

- **导出**：点击"导出上下文给网页版AI"打包当前阶段上下文为 .md 文件，上传给 ChatGPT/Claude 网页版
- **导入**：网页版 AI 回复保存到 `inbox/web_ai/`，输入文件名读取，对话框输入"使用网页AI方案"注入到工作流

### 🧠 对话记忆

所有对话实时保存到 `memory/{session_id}/stage_*.md`，按阶段分文件，每条消息即时 flush，支持：
- 回顾和复盘工作过程
- 上传给网页版 AI 提供完整上下文
- 提取关键决策点

## 三种文件输入方式

| 方式 | 入口 | 适用场景 |
|------|------|----------|
| 方式A | Streamlit file_uploader | 主工作流赛题 |
| 方式B | inbox/ 目录拖放 | 补充文献、知识库 |
| 方式C | inbox/web_ai/ + 侧边栏 | 网页版 AI 协作 |

## API Key 配置

`.env` 文件需要至少配置以下两个 Key：

| 变量 | 用途 | 获取地址 |
|------|------|----------|
| `DEEPSEEK_API_KEY` | LLM 对话 | https://platform.deepseek.com/api_keys |
| `NVIDIA_API_KEY` | 向量 Embedding | https://build.nvidia.com/explore/discover |

可选（启用 Rerank 精排时需配置其一）：

| 变量 | 用途 | 获取地址 |
|------|------|----------|
| `JINA_API_KEY` | Jina Reranker | https://jina.ai/embeddings/ |
| `COHERE_API_KEY` | Cohere Reranker | https://dashboard.cohere.com/api-keys |
| `QWEN_API_KEY` | 通义千问 Reranker | https://bailian.console.aliyun.com/ |

## 数据集

| 目录 | 用途 | 索引时机 |
|------|------|----------|
| `dataset/problems/` | 历年赛题 | 启动时 |
| `dataset/papers/` | 获奖论文 | 启动时 |
| `dataset/references/` | 参考文献 | 启动时 |
| `dataset/knowledge/` | 领域知识库 | 启动时 |
| `dataset/reference/` | 动态推荐文献 | 选题确认后 |
| `inbox/problems/` [v3] | 赛题 | 手动扫描 |
| `inbox/papers/` [v3] | 论文 | 手动扫描 |
| `inbox/references/` [v3] | 参考文献 | 手动扫描 |
| `inbox/knowledge/` [v3] | 知识库 | 手动扫描 |
| `inbox/web_ai/` [v3] | 网页AI回复 | 手动输入文件名 |

## Token 额度监控

系统自动追踪每次 LLM 调用的 token 消耗：
- 侧边栏实时显示用量进度条
- 达到 70% / 90% 时自动预警
- 一键生成任务交接文档，支持切换到 ChatGPT / Cursor / Codex / Claude Code 继续工作

## 文档

- 架构详情：`introduce/architecture.md`
- 操作手册：`introduce/user-guide.md`
- 变更日志：`update/`
