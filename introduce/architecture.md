# APMCM Agent 架构文档

> v3.1 — 2026-06-12（新增 Excel/CSV 数据文件支持）

## 1. 项目结构

```
agent/
├── app/                                # 核心代码 (14 个模块)
│   ├── __init__.py                     # 包初始化（支撑相对导入）
│   ├── main.py                         # Streamlit 界面 + 9 阶段工作流引擎 + 全局侧边栏
│   ├── rag.py                          # FAISS 向量检索引擎 + inbox 增量加载
│   ├── model.py                        # LLM/Embedding/Rerank 多 API 调用层
│   ├── prompts.py                      # 8 个阶段 Prompt 模板工厂函数
│   ├── skills_runner.py                # 统一 Skill 调用入口
│   ├── prd_generator.py                # PRD + CLAUDE.md 自动生成
│   ├── quota_monitor.py                # Token 额度监控 + 平台交接
│   ├── utils.py                        # PDF 解析、表格文件读取、文本分块
│   ├── skills_bridge.py                # 外部 Skill 桥接层
│   ├── workflow_logger.py              # 双格式工作流日志 JSON + Markdown
│   ├── inbox_watcher.py                # ★ inbox/ 文件扫描与增量加载 (支持 data/)
│   ├── webai_bridge.py                 # ★ 网页版 AI 协作桥接层
│   └── memory_logger.py                # ★ 实时对话记忆记录器
├── inbox/                              # ★ 文件收件箱
│   ├── README.md
│   ├── problems/                       #   赛题 PDF（拖放即加载）
│   ├── papers/                         #   获奖论文 PDF
│   ├── references/                     #   参考文献 PDF
│   ├── knowledge/                      #   领域知识 PDF
│   ├── web_ai/                         #   网页版 AI 回复文件 (.md/.txt/.pdf)
│   └── data/                           # ★ CSV/Excel 数据文件 [v3.1]
│       └── README.md
├── memory/                             # ★ 对话记忆目录
│   ├── README.md
│   └── {session_id}/
│       ├── stage_01_input_20260612_143000.md
│       ├── stage_02_topic_selection_20260612_143200.md
│       └── ...
├── skills/                             # 外部 Skill 仓库
│   ├── codex-startup-pressure-test-skill/  # 方案压力测试模板
│   ├── skills/                         # mattpocock/skills (grill-me, tdd, hunt, diagnose)
│   ├── waza/                           # Waza (think, design, check, hunt 等 8 个技能)
│   ├── scipilot-figure-skill/          # 科学图表生成 (Python 可调用)
│   └── gpt_academic/                   # 论文润色与翻译 (71 个插件)
├── dataset/
│   ├── problems/                       # 历年赛题 PDF (支持子文件夹递归)
│   ├── papers/                         # 优秀获奖论文 PDF
│   ├── references/                     # 参考文献 PDF
│   ├── knowledge/                      # 数学建模领域知识库 PDF
│   ├── reference/                      # 选题后动态加载文献 PDF
│   ├── data/                           # ★ 结构化数据目录 [v3.1]
│   │   ├── README.md
│   │   ├── raw/                        #   赛题原始数据
│   │   ├── processed/                  #   经代码处理后的中间数据
│   │   └── external/                   #   外部公开数据集
│   └── cache/                          # 向量缓存 (.npy, 自动生成)
├── workspace/                          # 产出目录 (运行时生成)
│   └── {session_id}/
│       ├── PRD.md                      # 产品需求文档
│       ├── CLAUDE.md                   # Claude Code 操作手册
│       ├── model_solution.py           # 生成的代码
│       ├── solution/                   # 模块化代码
│       ├── figures/                    # 图表输出
│       ├── results/                    # JSON 结果
│       ├── paper_sections/             # 论文各节
│       └── webai_collab/               # ★ 网页版 AI 导出上下文包
├── logs/                               # 工作流日志 (session_*.json + session_*.md)
├── introduce/                          # 本文档 + 操作手册
├── update/                             # 架构变更日志
├── requirements.txt
├── .env                                # API 密钥配置 (已填入)
└── .env.example                        # 配置模板
```

## 2. 工作流

```
用户上传赛题
  ├── 方式A: st.file_uploader (原有)
  └── 方式B: 拖文件到 inbox/problems/ 目录 → 自动扫描加载
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│ 阶段1: input — 上传赛题                                    │
│   3 个 file_uploader 分别上传赛题 PDF → _extract_pdf() 解析 │
│   点击 "开始分析" → phase = "topic_selection"              │
│   MemoryLogger 开新阶段文件 stage_01_input_xxx.md          │
└──────────────────────────┬───────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────┐
│ 阶段2: topic_selection — 选题分析                          │
│   RAG.topic_coverage_score() → FAISS 检索 → 加权评分       │
│   DeepSeek-chat → 从 3 维度推荐                            │
│   用户选择最终选题 → phase = "modeling"                     │
└──────────────────────────┬───────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│ 阶段3: modeling — 建模方案 + 压力测试 + PRD + 需求对齐 (一体化)    │
│                                                                    │
│  3a. get_modeling_prompt() → LLM 生成建模方案                      │
│  3b. run_pressure_test() → startup-pressure-test + star-up         │
│  3c. generate_prd() → PRD.md                                      │
│  3d. grill-me 循环 → 用户反馈 + AI 追问 → 修订 PRD                 │
│  3e. generate_claude_md() → CLAUDE.md                              │
│  3f. load_references() → 加载 reference/ 文献                       │
│  → phase = "coding"                                                │
└──────────────────────────┬───────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────┐
│ 阶段4: coding — 代码生成 + 审查 + 论文节同步                │
│   get_coding_prompt() + 已加载数据摘要 → LLM 生成代码       │
│   run_code_check() → think + check + tdd 三重审查          │
│   论文节同步 → 选择段落 → LLM 生成对应论文节 Markdown       │
│   → "符合预期" → phase = "figure"                          │
└──────────────────────────┬───────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────┐
│ 阶段5: figure — 图表方案设计                               │
│   get_figure_prompt() → LLM 设计图表清单                   │
│   配合 scipilot-figure-skill 可直接渲染                   │
│   → phase = "paper"                                      │
└──────────────────────────┬───────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────┐
│ 阶段6: paper — 论文初稿                                    │
│   get_paper_writing_prompt() → LLM 撰写完整论文            │
│   → "润色论文" 或 "导出完成"                               │
└──────────────────────────┬───────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────┐
│ 阶段7: polish — 论文润色                                   │
│   get_polish_prompt() → LLM 润色/翻译/语法修正/逻辑优化     │
│   → phase = "done"                                       │
└──────────────────────────┬───────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────┐
│ done — 工作流完成                                         │
│   展示最终产出 + 日志文件路径                               │
│   "开始新会话" → 重置所有状态 + 新 MemoryLogger             │
└──────────────────────────────────────────────────────────┘
```

### 全局侧边栏（全流程可见）

```
项目仪表盘
├── 进度追踪: 8 个阶段勾选状态 + 进度条
├── Token 额度监控
│   ├── 平台选择 (Claude/ChatGPT)
│   ├── 用量进度条 [████░░░░]
│   ├── 70%/90% 阈值预警
│   └── 一键生成多平台任务交接文档
├── 📥 文件收件箱
│   ├── 显示 inbox/ 子目录文件统计
│   ├── 🔄 扫描新文件 → 自动加载 PDF 到 RAG
│   ├── 📊 数据文件（CSV / Excel）→ 按文件逐个加载预览
│   └── 已加载数据文件提示
├── 🔗 AI 网页版协作
│   ├── 📤 导出上下文给网页版 AI
│   ├── 📥 读取网页版 AI 回复
│   └── 导出历史记录
├── Skills 说明 (项目 vs Claude Code 对比)
└── 随时提问输入框 → 实时写入 memory/
```

## 3. 数据输入方式

| 方式 | 入口 | 触发 | 适用场景 |
|------|------|------|----------|
| 方式A | `st.file_uploader` | 用户在 Streamlit UI 上传 | 主工作流赛题 |
| 方式B | `inbox/` 子目录拖放 | 侧边栏"扫描新文件"或启动时 | 补充文献、知识库 |
| 方式C | `inbox/web_ai/` 文件 + 侧边栏输入文件名 | 用户点击"读取网页版AI回复" | 网页版 AI 协作 |
| 方式D | `inbox/data/` CSV/Excel + 侧边栏加载 | 用户点击"加载"按钮 | ★ 结构化数据文件 [v3.1] |

### 表格数据加载流程 [v3.1]

```
用户将 .csv / .xlsx / .xls 放入 inbox/data/
  → 侧边栏"文件收件箱"显示文件列表（名称 + 大小）
  → 用户点击"加载" → read_data_file() → load_tabular_file()
     → pandas 读取 → 生成摘要（形状/列名/前N行 Markdown 表格）
     → 存入 st.session_state.loaded_data_files
  → 用户对话中说"分析数据" → 自动注入所有已加载数据摘要
  → 在 coding 阶段自动拼接数据摘要到 Prompt
```

## 4. 选题推荐算法

### 4.1 向量检索流程

```
PDF 文件 → pypdf.PdfReader 逐页提取文本
         → 头尾分块: 取前 1500 + 后 1500 字符 (短文本不分块)
         → UTF-8 清洗 (非法字符替换)
         → NVIDIA nv-embed-v1 API → 4096 维浮点向量
         → L2 归一化 → FAISS IndexFlatIP 索引 (内积 = 余弦相似度)
         → 缓存为 dataset/cache/{name}_chunk_vectors.npy
```

### 4.2 混合检索架构

```
用户查询
  │
  ├──→ BM25 关键词检索 (rank_bm25, 字级别分词)
  │
  ├──→ 向量检索 (FAISS IndexFlatIP, 余弦相似度)
  │
  ├──→ [可选] HyDE 查询增强
  │
  └──→ 双路结果合并 (向量权重 60% + BM25权重 40%)
       │
       ├──→ 相似度阈值过滤 (< 0.35 的结果丢弃)
       ├──→ 同文件去重
       └──→ [可选] Rerank 精排: Jina → Qwen → Cohere 降级链
```

### 4.3 评分公式

```python
score = Σ(相似度 × 10) + Σ(相似度 × 15) + Σ(相似度 × 5)
      (问题匹配)          (论文匹配)          (参考文献匹配)
```

### 4.4 多源知识库

| 目录 | 加载时机 | 用途 |
|------|----------|------|
| `problems/` | 启动时 | 历年赛题 |
| `papers/` | 启动时 | 获奖论文 |
| `references/` (旧) | 启动时 | 参考文献(存量) |
| `knowledge/` | 启动时 | 领域知识库 |
| `reference/` | 选题确认后 | 动态推荐文献 |

### 4.5 Inbox 增量加载

```python
RAG.add_inbox_files(subdir_name, file_paths) → int

# 映射关系:
"problems"   → self.problem_index   (+ texts, chunks, files)
"papers"     → self.paper_index     (+ texts, chunks, files)
"references" → self.ref_index       (+ texts, chunks, files)
"knowledge"  → self.knowledge_index (+ texts)
```

## 5. 对话记忆系统

### 5.1 MemoryLogger 类

每条 user/assistant/system 消息实时追加写入 `memory/{session_id}/` 对应阶段文件。

```
memory/{session_id}/
├── stage_01_input_20260612_143000.md
├── stage_02_topic_selection_20260612_143210.md
├── stage_03_modeling_20260612_144500.md
└── ...
```

### 5.2 写入时机

- `new_stage(phase)`: 每次阶段切换时创建新文件并写文件头（幂等）
- `log_message(role, content)`: 每条用户/Agent 消息写入
- `log_system_event(event, detail)`: 系统事件（阶段切换、技能调用、数据文件加载等）

### 5.3 线程安全

所有写操作通过 `threading.Lock()` 加锁 + 立即 `flush()`，保证并发安全。

## 6. 网页版 AI 协作桥接

### 6.1 webai_bridge 模块

```
导出方向:  session_state → export_context_package() → workspace/{session_id}/webai_collab/export_{phase}_{ts}.md
           └── 用户手动上传给网页版 AI

导入方向:  网页版 AI 回复保存到 inbox/web_ai/ → import_webai_response(filename)
           └── 用户在侧边栏输入文件名 → 读取内容 → 在对话框注入
```

### 6.2 导入注入

用户在对话框输入 "使用网页AI方案" 或 "应用网页AI回复" 时，Agent 自动将 `webai_imported_content` 注入为消息前缀。

## 7. 表格数据文件支持 [v3.1]

### 7.1 函数概览

```python
# utils.py
load_tabular_file(filepath, max_rows=200) → str
  # .csv  → pandas.read_csv (utf-8 → gbk 自动回退)
  # .xlsx / .xls → pandas.read_excel
  # 返回: 文件名/形状/列名/前 N 行 Markdown 表格

list_data_files(data_dir) → list[dict]
  # 列出目录下所有 .csv/.xlsx/.xls 文件信息

# inbox_watcher.py
read_data_file(filename) → str
  # 从 inbox/data/{filename} 读取表格
  # 调用 load_tabular_file() 返回摘要
```

### 7.2 数据注入时机

| 场景 | 触发方式 | 注入位置 |
|------|----------|----------|
| 代码生成阶段 | 自动 | `loaded_data_files` 摘要拼接到 `get_coding_prompt()` 参数末尾 |
| 对话中分析数据 | 关键词"分析数据"或"数据文件" | 所有已加载数据摘要拼接到用户消息前 |

### 7.3 数据目录结构

```
inbox/data/            # 临时上传，session 内有效
dataset/data/
├── raw/               # 赛题原始数据
├── processed/         # 代码处理后的中间数据
└── external/          # 外部公开数据集
```

## 8. Skill 清单

### 8.1 统一调用层

| 函数 | 调用 Skill | 用途 |
|------|-----------|------|
| `run_pressure_test()` | pressure-test + star-up | 方案可行性报告 |
| `run_grill_me()` | grill-me | PRD 需求对齐 |
| `run_code_check()` | think + check + tdd | 代码三重审查 |
| `read_skill()` | 任意 | 读取 SKILL.md |

### 8.2 调度表

| 阶段 | 主要 Skill | 辅助 | 触发 |
|---|---|---|---|
| 1. 上传 | — | — | 用户操作 |
| 2. 选题 | rag (FAISS+BM25) | — | 自动 |
| 3. 建模+PRD | pressure-test, grill-me | think, star-up | 用户递进 |
| 4. 编码 | tdd | think, check, hunt | 自动 |
| 5. 图表 | scipilot-figure | — | 自动/手动 |
| 6. 论文 | — | — | 自动 |
| 7. 润色 | gpt_academic | — | 用户选择 |
| 调试 | diagnose, hunt | — | 对话/侧边栏触发 |

## 9. API 架构

### 9.1 Chat 层

```
chat_client (OpenAI SDK)
  ├── Base URL: https://api.deepseek.com
  ├── Model: deepseek-chat (可配置)
  └── 函数: chat(), gpt_analysis(), gpt_with_retry()
```

### 9.2 Embedding 层

```
embed_client (OpenAI SDK)
  ├── Base URL: https://integrate.api.nvidia.com/v1
  ├── Model: nvidia/nv-embed-v1
  └── 函数: get_embedding(text, max_chars=1500) → 4096 维浮点向量
```

### 9.3 Rerank 层

```
rerank(query, documents, top_n, provider) → list[dict]
  降级逻辑: provider="qwen" → Cohere → Jina → 再试 Qwen
```

## 10. 数据流

### 10.1 主数据流

```
1. PDF 文件 → pypdf 提取 → 头尾分块 → NVIDIA Embedding → FAISS IndexFlatIP → .npy 缓存

2. 用户查询 → 双路召回(FAISS + BM25) → 加权合并 → 阈值过滤 → [可选] HyDE → [可选] Rerank

3. Prompt 拼接 → 相似文本 + 用户问题 → DeepSeek-chat → 结果

4. 日志: workflow_logger → logs/session_*.json + logs/session_*.md

5. Token: QuotaMonitor.record() → 70%/90% 预警 → 任务交接文档
```

### 10.2 v3 新增数据流

```
6. Inbox 文件加载
   → inbox_watcher.scan_subdir() 扫描新 PDF
   → utils.load_file_as_text() 提取文本
   → rag.add_inbox_files() 分块 + 向量化 + 追加索引

7. 网页版 AI 协作
   → webai_bridge.export_context_package() → .md 导出
   → webai_bridge.import_webai_response() → 读取回复 → 注入对话

8. 对话记忆
   → memory_logger.log_message() → 实时 flush 到 memory/{session_id}/stage_*.md

9. 表格数据加载 [v3.1]
   → load_tabular_file() → pandas 读取 → Markdown 摘要
   → 侧边栏加载按钮 → loaded_data_files 字典
   → coding Prompt 自动注入 / 对话"分析数据"触发注入
```

## 11. 模块详解

### 11.1 main.py

**功能**: Streamlit UI + 工作流状态机。

**关键 Session State 变量**:

| 变量 | 类型 | 用途 |
|---|---|---|
| phase | str | 当前阶段 |
| topics | list[str] | 上传的赛题文本 |
| selected_topic | str | 用户选中的赛题 |
| modeling_plan | str | 生成的建模方案 |
| coding_result | str | 生成的代码 |
| paper_draft | str | 论文初稿 |
| chat_history | list | 对话历史 |
| memory_logger | MemoryLogger | 实时对话记忆 |
| webai_imported_content | str | 已读取的网页AI回复 |
| loaded_data_files | dict | ★ 已加载的表格数据摘要 [v3.1] |

### 11.2 rag.py

| 方法 | 用途 |
|---|---|
| `add_inbox_files` | ★ inbox 新文件增量加载到索引 |
| `retrieve_with_knowledge` | 综合检索所有已加载索引 |
| `topic_coverage_score` | 相似度加权评分 |

### 11.3 inbox_watcher.py

| 函数 | 用途 |
|---|---|
| `ensure_inbox_dirs()` | 确保 6 个子目录存在（含 data/） |
| `scan_subdir(name)` | 扫描子目录 — data/ 扫描 .csv/.xlsx/.xls |
| `read_data_file(filename)` | ★ 读取 inbox/data/ 下表格文件 [v3.1] |
| `read_web_ai_file(filename)` | 读取 inbox/web_ai/ 下文件 |

### 11.4 webai_bridge.py

| 函数 | 用途 |
|---|---|
| `export_context_package()` | 打包当前阶段上下文 → .md 文件 |
| `import_webai_response()` | 读取 inbox/web_ai/ 下网页 AI 回复 |
| `list_export_files()` | 列出已导出的上下文包文件列表 |

### 11.5 memory_logger.py

**类**: `MemoryLogger` — 实时记录对话，按 session + 阶段分文件存储，`threading.Lock()` 线程安全 + 立即 `flush()`。

### 11.6 utils.py

| 函数 | 用途 |
|---|---|
| `load_texts(folder)` | 递归遍历文件夹，pypdf 提取所有 PDF 文本 |
| `load_file_as_text(filepath, max_chars)` | 通用文件读取 (.pdf/.md/.txt)，支持截断 |
| `load_tabular_file(filepath, max_rows)` | ★ CSV/Excel → Markdown 摘要 [v3.1] |
| `list_data_files(data_dir)` | ★ 列出目录下表格文件信息 [v3.1] |
| `chunk_text(text, max_tokens)` | 按段落分块 |
| `load_config()` | 读取 .env 文件 |
| `save_json / load_json` | JSON 读写 |

### 11.7 other modules

`prompts.py` / `skills_runner.py` / `prd_generator.py` / `quota_monitor.py` / `skills_bridge.py` / `workflow_logger.py` — 保持不变。

## 12. 更新日志

| 日期 | 版本 | 内容 |
|---|---|---|
| 2026-06-10 | v1 | 项目搭建、RAG 引擎、9 阶段工作流、6 个 Skill 集成 |
| 2026-06-11 | v1.1 | Reranker 多 Provider、RAG 7 方向改进 |
| 2026-06-12 | v2 | skills_runner 统一调用层、PRD+CLAUDE.md、QuotaMonitor、多源索引 |
| 2026-06-12 | v3 | inbox_watcher + webai_bridge + memory_logger |
| 2026-06-12 | v3.1 | ★ CSV/Excel 数据文件支持：load_tabular_file、inbox/data/、分析数据关键词 |
