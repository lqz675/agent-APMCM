# APMCM 数学建模 Agent

基于 RAG + LLM + 多 Skill 协作的数学建模竞赛辅助系统，覆盖从选题到论文润色的全流程自动化。

## 快速上手（3 步）

### 1. 配置 API Key

```powershell
cd agent
Copy-Item .env.example .env
```

用记事本打开 `.env`，填入两个必填密钥：

```
DEEPSEEK_API_KEY=sk-xxxxxxxx        # 在 https://platform.deepseek.com/api_keys 获取
NVIDIA_API_KEY=nvapi-xxxxxxxx       # 在 https://build.nvidia.com 获取
```

可选（启用重排序精排时配置其一）：

```
JINA_API_KEY=       # https://jina.ai
COHERE_API_KEY=     # https://dashboard.cohere.com
QWEN_API_KEY=       # https://bailian.console.aliyun.com
```

### 2. 安装依赖

```powershell
pip install -r requirements.txt
```

### 3. 启动

```powershell
python -m streamlit run app/main.py --server.headless true
```

浏览器访问 **http://localhost:8501**，首次启动会自动向量化 PDF（约 1 分钟），之后秒开。

---

## 功能概览

```
上传赛题 PDF
  → 选题分析（RAG 检索历史赛题 + LLM 评分推荐）
  → 建模方案 + 压力测试 + PRD + 需求对齐
  → 代码生成 + think/check/tdd 三重审查 + 论文节同步
  → 图表方案设计
  → 论文初稿
  → 论文润色（润色/英译/语法修正/逻辑优化）+ 导出 Word/Markdown
```

### 侧边栏工具

| 模块 | 说明 |
|------|------|
| 项目仪表盘 | 8 阶段进度追踪 |
| Token 额度 | 实时用量监控，70%/90% 自动预警，一键生成多平台交接文档 |
| 文件收件箱 | 拖文件到 `inbox/` 目录，点击扫描即可加载 PDF 到知识库；支持 CSV/Excel 数据文件加载 |
| AI 网页版协作 | 导出当前阶段上下文给 ChatGPT/Claude 网页版，读取回复并注入工作流 |
| Skills 说明 | 内置 6 个 Skill 说明 |
| 随时提问 | 基于当前项目背景的 AI 问答 |

---

## 三种文件输入方式

| 方式 | 操作 | 适用场景 |
|------|------|----------|
| 浏览器上传 | 界面点击 Browse files 选择 PDF | 开始新赛题 |
| inbox 拖放 | 将 PDF 拖入 `inbox/problems/` 等目录，点"扫描新文件" | 补充文献、知识库 |
| 网页 AI 回复 | 回复保存到 `inbox/web_ai/`，侧边栏输入文件名读取 | 与 ChatGPT/Claude 协作 |

### 数据文件（CSV / Excel）

将数据文件放入 `inbox/data/`，在侧边栏"文件收件箱"中点击 **加载**。后续在对话中说"分析数据"即可自动引用，代码生成阶段也会自动注入。

---

## 对话关键词

| 说这句话 | 效果 |
|----------|------|
| "使用网页AI方案" 或 "应用网页AI回复" | 将已读取的网页 AI 回复注入上下文 |
| "分析数据" 或 "数据文件" | 将已加载的 CSV/Excel 数据摘要注入上下文 |

---

## 项目结构

```
agent/
├── app/
│   ├── main.py              # Streamlit 界面 + 9 阶段工作流引擎
│   ├── rag.py               # FAISS 向量检索引擎（BM25 + HyDE + Rerank）
│   ├── model.py             # LLM / Embedding / Rerank 多 API 调用层
│   ├── prompts.py           # 8 个阶段 Prompt 模板
│   ├── utils.py             # PDF/CSV/Excel 文件读取、文本分块
│   ├── skills_runner.py     # 统一 Skill 调用入口（pressure-test/grill-me/think/check/tdd）
│   ├── prd_generator.py     # PRD + CLAUDE.md 自动生成
│   ├── quota_monitor.py     # Token 额度监控 + 平台切换
│   ├── inbox_watcher.py     # inbox/ 目录文件扫描与加载
│   ├── webai_bridge.py      # 网页版 AI 协作上下文导出/导入
│   ├── memory_logger.py     # 实时对话记忆（按 session + 阶段分文件）
│   ├── skills_bridge.py     # 外部 Skill 桥接层
│   └── workflow_logger.py   # 工作流日志 (JSON + Markdown)
├── dataset/                 # 系统知识库（启动时加载）
│   ├── problems/            # 历年赛题 PDF
│   ├── papers/              # 获奖论文 PDF
│   ├── references/          # 参考文献 PDF
│   ├── knowledge/           # 领域知识库 PDF
│   ├── data/                # 结构化数据 (raw/processed/external)
│   └── cache/               # 向量缓存 (.npy)
├── inbox/                   # 文件收件箱（拖放即加载）
│   ├── problems/ / papers/ / references/ / knowledge/
│   ├── web_ai/              # 网页版 AI 回复
│   └── data/                # CSV/Excel 数据文件
├── memory/                  # 对话记忆（每条消息实时写入）
├── skills/                  # 外部 Skill 仓库
├── workspace/               # 产出目录（运行时生成）
├── logs/                    # 工作流日志
├── introduce/               # 架构文档 + 操作手册
├── requirements.txt
└── .env.example
```

---

## 数据集

| 目录 | 格式 | 何时加载 |
|------|------|----------|
| `dataset/problems/` | PDF | 启动时 |
| `dataset/papers/` | PDF | 启动时 |
| `dataset/references/` | PDF | 启动时 |
| `dataset/knowledge/` | PDF | 启动时 |
| `dataset/reference/` | PDF | 选题确认后 |
| `inbox/problems/` | PDF | 手动扫描 |
| `inbox/papers/` | PDF | 手动扫描 |
| `inbox/knowledge/` | PDF | 手动扫描 |
| `inbox/data/` | CSV/Excel | 手动加载 |

> 不放数据也能用，Agent 凭 LLM 自身知识仍可工作，但推荐精度会下降。

---

## Token 额度监控

每次 LLM 调用后自动估算 token 消耗，侧边栏实时显示进度条。触发 70%/90% 预警时自动生成多平台任务交接文档，支持切换到 ChatGPT / Cursor / Codex / Claude Code 继续工作。

---

## RAG 检索技术栈

- **分块策略**: 头尾分块（前 1500 + 后 1500 字符）
- **向量模型**: NVIDIA nv-embed-v1（4096 维）
- **向量索引**: FAISS IndexFlatIP（余弦相似度，L2 归一化）
- **混合检索**: FAISS（60%）+ BM25（40%）
- **查询增强**: HyDE（LLM 生成假设文档再检索）
- **精排**: Jina / Qwen / Cohere 三通道降级

---

## 内置 Skill

| Skill | 用途 | 所属阶段 |
|-------|------|----------|
| startup-pressure-test | 方案可行性报告（技术/时间/数据三维度） | 建模 |
| grill-me | PRD 需求对齐追问 | 建模 |
| think | 设计决策审查 | 编码 |
| check | 正确性/健壮性/规范检查 | 编码 |
| tdd | 测试驱动验证 | 编码 |
| scipilot-figure | 科学图表生成（Nature 风格） | 图表 |
| gpt_academic | 论文润色与翻译（71 插件） | 润色 |

---

## 产出文件

每次会话在 `workspace/{session_id}/` 下生成：

```
PRD.md                # 产品需求文档
CLAUDE.md             # Claude Code / opencode 操作手册
model_solution.py     # 生成的 Python 代码
solution/             # 模块化代码（data_processing/model/solver/sensitivity/figures）
paper_sections/       # 论文各节 Markdown
webai_collab/         # 网页版 AI 导出上下文包
quota_log.json        # Token 用量日志
```

对话记忆保存在 `memory/{session_id}/stage_*.md`，每条消息实时写入。

---

## 文档

- 架构详情：`introduce/architecture.md`
- 操作手册：`introduce/user-guide.md`
- 变更日志：`update/`

## License

MIT
