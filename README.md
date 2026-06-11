# APMCM 数学建模 Agent

基于 RAG + LLM + 多 Skill 协作的数学建模竞赛辅助系统。支持选题推荐、建模方案设计、压力测试、PRD 生成、代码生成与审查、论文撰写与润色的全流程自动化。

## 项目结构

```
agent/
├── app/                                # 核心代码 (11 个模块)
│   ├── main.py                         # Streamlit 界面 + 全局仪表盘侧边栏
│   ├── rag.py                          # FAISS 多源向量检索引擎
│   ├── model.py                        # LLM / Embedding / Rerank 多 API 层
│   ├── prompts.py                      # 8 个阶段 Prompt 模板工厂
│   ├── skills_runner.py                # 统一 Skill 调用入口 [v2 新增]
│   ├── prd_generator.py                # PRD + CLAUDE.md 自动生成 [v2 新增]
│   ├── quota_monitor.py                # Token 额度监控 + 平台接力 [v2 新增]
│   ├── utils.py                        # PDF 解析、文本分块、配置
│   ├── skills_bridge.py                # 外部 Skill 桥接层
│   ├── workflow_logger.py              # 双格式工作流日志 (JSON+MD)
│   └── __init__.py
├── skills/                             # 外部 Skill 仓库 (转为本地文件)
│   ├── codex-startup-pressure-test-skill/  # 方案压力测试
│   ├── skills/                         # grill-me, tdd, hunt 等
│   ├── waza/                           # think, check, design 等
│   ├── scipilot-figure-skill/          # 科学图表生成
│   └── gpt_academic/                   # 论文润色 (71 插件)
├── dataset/
│   ├── problems/                       # 历年赛题 PDF
│   ├── papers/                         # 获奖论文 PDF
│   ├── references/                     # 参考文献 PDF
│   ├── knowledge/                      # 领域知识库（启动时预加载）
│   ├── reference/                      # 动态推荐文献（选题后加载）
│   └── cache/                          # 向量缓存（自动生成）
├── logs/                               # 工作流日志
├── workspace/                           # 产出（运行时生成）
├── introduce/                          # 架构文档 + 操作手册
├── update/                             # 变更日志
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## 快速开始

### Docker 部署（推荐）

```bash
# 1. 配置 API Key
cp .env.example .env
# 编辑 .env，填入真实密钥：
#   DEEPSEEK_API_KEY=...
#   NVIDIA_API_KEY=...

# 2. (可选) 放入 PDF 数据到 dataset/ 子目录
#    dataset/problems/   ← 赛题
#    dataset/papers/     ← 论文
#    dataset/knowledge/  ← 领域知识

# 3. 一键启动
docker-compose up -d
# 浏览器打开 http://localhost:8501
```

### 本地部署

```bash
# 1. 配置
cp .env.example .env      # 填入密钥
pip install -r requirements.txt

# 2. 启动
streamlit run app/main.py
# 或
python -m streamlit run app/main.py --server.headless true
```

## 工作流程

```
上传赛题 PDF
  → 1. 选题分析 (RAG + LLM 推荐)
  → 2. 建模方案 + 压力测试 + PRD + 需求对齐 (一体化)
      ├── 生成建模方案
      ├── 运行压力测试 (技术/时间/数据 三维度)
      ├── 生成 PRD.md (产品需求文档)
      ├── grill-me 循环对齐
      └── 生成 CLAUDE.md (Claude Code 操作手册)
  → 3. 代码生成 + 三重审查 + 论文节同步
  → 4. 图表方案设计
  → 5. 论文初稿
  → 6. 论文润色 + 导出 (Word / Markdown)
```

全局侧边栏提供：进度追踪、Token 额度监控（70%/90% 预警 + 一键生成多平台交接文档）、Skills 说明、随时提问。

## API Key 配置

`.env` 文件需要至少配置以下两个 Key：

| 变量 | 用途 | 获取地址 |
|------|------|----------|
| `DEEPSEEK_API_KEY` | LLM 对话 | https://platform.deepseek.com/api_keys |
| `NVIDIA_API_KEY` | 向量 Embedding | https://build.nvidia.com/explore/discover (任选模型 → Get API Key) |

可选（启用 Rerank 精排时需配置其一）：

| 变量 | 用途 | 获取地址 |
|------|------|----------|
| `JINA_API_KEY` | Jina Reranker | https://jina.ai/embeddings/ (注册后免费额度) |
| `COHERE_API_KEY` | Cohere Reranker | https://dashboard.cohere.com/api-keys |
| `QWEN_API_KEY` | 通义千问 Reranker | https://bailian.console.aliyun.com/#/home (百炼平台 → API-KEY 管理) |

## 数据集

`dataset/` 子目录支持递归扫描 PDF。空目录有 `.gitkeep` 占位，clone 后可立即使用：

| 目录 | 用途 | 索引时机 |
|------|------|----------|
| `problems/` | 历年赛题 | 启动时 |
| `papers/` | 获奖论文 | 启动时 |
| `references/` | 参考文献 | 启动时 |
| `knowledge/` | 领域知识库 | 启动时 |
| `reference/` | 动态推荐文献 | 选题确认后 |

不放数据也能用，Agent 凭 LLM 自身知识仍可工作，但推荐精度会下降。

## Token 额度监控

系统自动追踪每次 LLM 调用的 token 消耗：
- 侧边栏实时显示用量进度条
- 达到 70% / 90% 时自动预警
- 一键生成任务交接文档，支持切换到 ChatGPT / Cursor / Codex / Claude Code 继续工作

## 文档

- 架构详情：`introduce/architecture.md`
- 操作手册：`introduce/user-guide.md`
- 变更日志：`update/`
