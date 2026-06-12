# APMCM Agent 架构文档

> v3 — 2026-06-12（新增 inbox_watcher / webai_bridge / memory_logger）

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
│   ├── utils.py                        # PDF 解析、文本分块、通用文件读取
│   ├── skills_bridge.py                # 外部 Skill 桥接层
│   ├── workflow_logger.py              # 双格式工作流日志 JSON + Markdown
│   ├── inbox_watcher.py                # ★ inbox/ 文件扫描与增量加载 [v3 新增]
│   ├── webai_bridge.py                 # ★ 网页版 AI 协作桥接层 [v3 新增]
│   └── memory_logger.py                # ★ 实时对话记忆记录器 [v3 新增]
├── inbox/                              # ★ 文件收件箱 [v3 新增]
│   ├── README.md
│   ├── problems/                       #   赛题 PDF（拖放即加载）
│   ├── papers/                         #   获奖论文 PDF
│   ├── references/                     #   参考文献 PDF
│   ├── knowledge/                      #   领域知识 PDF
│   └── web_ai/                         #   网页版 AI 回复文件 (.md/.txt/.pdf)
├── memory/                             # ★ 对话记忆目录 [v3 新增]
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
│       └── webai_collab/               # ★ 网页版 AI 导出上下文包 [v3 新增]
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
  └── 方式B: 拖文件到 inbox/problems/ 目录 → 自动扫描加载 [v3 新增]
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
│   get_coding_prompt() → DeepSeek-chat 生成 Python 代码     │
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
├── 📥 文件收件箱 [v3 新增]
│   ├── 显示 inbox/ 子目录文件统计
│   ├── 🔄 扫描新文件 → 自动加载到 RAG
│   └── 目录说明
├── 🔗 AI 网页版协作 [v3 新增]
│   ├── 📤 导出上下文给网页版 AI
│   ├── 📥 读取网页版 AI 回复
│   └── 导出历史记录
├── Skills 说明 (项目 vs Claude Code 对比)
└── 随时提问输入框 → 实时写入 memory/
```

## 3. 三类数据输入方式 [v3 新增]

| 方式 | 入口 | 触发 | 适用场景 |
|------|------|------|----------|
| 方式A | `st.file_uploader` | 用户在 Streamlit UI 上传 | 主工作流赛题 |
| 方式B | `inbox/` 子目录拖放 | 侧边栏"扫描新文件"或启动时 | 补充文献、知识库 |
| 方式C | `inbox/web_ai/` 文件 + 侧边栏输入文件名 | 用户点击"读取网页版AI回复" | 网页版 AI 协作 |

方式B 的加载流程：

```
inbox/{problems,papers,references,knowledge}/ 目录
  → inbox_watcher.scan_subdir() 扫描新文件
  → inbox_watcher.get_new_files() 对比 .processed_files.json
  → rag.add_inbox_files() 提取文本 → 分块 → 向量化 → 追加到 FAISS 索引
  → inbox_watcher.mark_as_processed() 写入缓存
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

每路检索采用三阶段管线：

```
用户查询
  │
  ├──→ BM25 关键词检索 (rank_bm25, 字级别分词)
  │
  ├──→ 向量检索 (FAISS IndexFlatIP, 余弦相似度)
  │
  ├──→ [可选] HyDE 查询增强: LLM 生成假设性建模思路 → 用假设文档 embedding 再检索
  │
  └──→ 双路结果合并 (向量权重 60% + BM25权重 40%)
       │
       ├──→ 相似度阈值过滤 (< 0.35 的结果丢弃)
       │
       ├──→ 同文件去重 (多个 chunk 命中同一文件只保留最高分)
       │
       └──→ [可选] Rerank 精排: Jina API → Qwen API 降级链
```

### 4.3 评分公式

`rag.py:topic_coverage_score()`:

```python
score = Σ(相似度 × 10) + Σ(相似度 × 15) + Σ(相似度 × 5)
      (问题匹配)          (论文匹配)          (参考文献匹配)
```

### 4.4 多源知识库

索引源从 3 路扩展到 5 路：

| 目录 | 加载时机 | 用途 |
|------|----------|------|
| `problems/` | 启动时 | 历年赛题 |
| `papers/` | 启动时 | 获奖论文 |
| `references/` (旧) | 启动时 | 参考文献(存量) |
| `knowledge/` | 启动时 | 领域知识库 |
| `reference/` | 选题确认后 | 动态推荐文献 |

`retrieve_with_knowledge()` 方法统一查询所有已加载的索引，返回结构化结果。

### 4.5 Inbox 增量加载 [v3 新增]

```python
RAG.add_inbox_files(subdir_name, file_paths) → int

# 映射关系:
"problems"   → self.problem_index   (+ texts, chunks, files)
"papers"     → self.paper_index     (+ texts, chunks, files)
"references" → self.ref_index       (+ texts, chunks, files)
"knowledge"  → self.knowledge_index (+ texts)
```

## 5. 对话记忆系统 [v3 新增]

### 5.1 MemoryLogger 类

每条 user/assistant/system 消息实时追加写入 `memory/{session_id}/` 对应阶段文件。

```
memory/{session_id}/
├── stage_01_input_20260612_143000.md
├── stage_02_topic_selection_20260612_143210.md
├── stage_03_modeling_20260612_144500.md
└── ...
```

### 5.2 文件格式

```markdown
# APMCM Agent 对话记忆
- **Session**: 20260612_143000
- **阶段**: 1 — input
- **开始时间**: 2026-06-12 14:30:00

---

## [14:30:05] 👤 用户
（用户消息内容）

## [14:30:15] 🤖 Agent
（Agent 回复内容）

## [14:32:00] ⚙️ 系统
**进入阶段: topic_selection**
session_id=20260612_143000
```

### 5.3 写入时机

- `new_stage(phase)`: 每次阶段切换时创建新文件并写文件头（幂等）
- `log_message(role, content)`: 每条用户/Agent 消息写入
- `log_system_event(event, detail)`: 系统事件（阶段切换、技能调用等）

### 5.4 线程安全

所有写操作通过 `threading.Lock()` 加锁 + 立即 `flush()`，保证并发安全。

## 6. 网页版 AI 协作桥接 [v3 新增]

### 6.1 webai_bridge 模块

```
导出方向:  session_state → export_context_package() → workspace/{session_id}/webai_collab/export_{phase}_{ts}.md
           └── 用户手动上传给网页版 AI

导入方向:  网页版 AI 回复保存到 inbox/web_ai/ → import_webai_response(filename)
           └── 用户在侧边栏输入文件名 → 读取内容 → 在对话框注入
```

### 6.2 导出上下文包格式

```markdown
---
# APMCM Agent → 网页版 AI 上下文包
**导出时间**: 2026-06-12 14:35:00
**当前阶段**: modeling
**Session ID**: 20260612_143000

## 赛题内容 / 已选赛题
## 建模方案（摘要）
## 压力测试报告（摘要）
## PRD 最终版（摘要）
## 当前阶段任务说明
## 对话历史（最近 10 条）
---
```

### 6.3 导入注入

用户在对话框输入 "使用网页AI方案" 或 "应用网页AI回复" 时，Agent 自动将 `webai_imported_content` 注入为消息前缀，并在使用后清空。

## 7. Skill 清单

### 7.1 统一调用层

所有 Skill 通过 `skills_runner.py` 统一调度，在调用前自动读取对应 `SKILL.md` 确保按规范使用。

| 函数 | 调用 Skill | 用途 |
|------|-----------|------|
| `run_pressure_test()` | pressure-test + star-up | 方案可行性报告 |
| `run_grill_me()` | grill-me | PRD 需求对齐 |
| `run_code_check()` | think + check + tdd | 代码三重审查 |
| `read_skill()` | 任意 | 读取 SKILL.md |

### 7.2 Skill 路径映射

```
skills_runner.SKILL_PATHS = {
    "pressure_test" → codex-startup-pressure-test-skill/startup-pressure-test/SKILL.md
    "star_up"       → waza/skills/star-up/SKILL.md
    "grill_me"      → skills/skills/skills/productivity/grill-me/SKILL.md
    "think"         → waza/skills/think/SKILL.md
    "check"         → waza/skills/check/SKILL.md
    "hunt"          → waza/skills/hunt/SKILL.md
    "tdd"           → skills/skills/skills/engineering/tdd/SKILL.md
    "figure"        → scipilot-figure-skill/SKILL.md
    "gpt_academic"  → gpt_academic/SKILL.md
}
```

### 7.3 调度表

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

## 8. API 架构

### 8.1 Chat 层

```
chat_client (OpenAI SDK)
  ├── Base URL: https://api.deepseek.com
  ├── Model: deepseek-chat (可配置)
  ├── API Key: sk-f245...
  └── 函数: chat(), gpt_analysis(), gpt_with_retry()
```

### 8.2 Embedding 层

```
embed_client (OpenAI SDK)
  ├── Base URL: https://integrate.api.nvidia.com/v1
  ├── Model: nvidia/nv-embed-v1
  ├── API Key: nvapi-ust2Ja...
  ├── 函数: get_embedding(text, max_chars=1500)
  │   ├── 去换行 → UTF-8 清洗 → 截断到 max_chars
  │   └── 返回 4096 维浮点向量
  └── 调用方: rag.py._build_index(), rag.py.search()
```

### 8.3 Rerank 层

```
rerank(query, documents, top_n, provider) [model.py]
  ├── provider="jina" (默认)
  │   ├── POST https://api.jina.ai/v1/rerank
  │   └── Model: jina-reranker-v2-base-multilingual
  ├── provider="qwen"
  │   ├── OpenAI SDK → https://dashscope.aliyuncs.com/compatible-mode/v1
  │   └── Qwen3-Reranker-8B 余弦相似度排序
  └── provider="cohere"
      ├── POST https://api.cohere.ai/v2/rerank
      └── Model: rerank-multilingual-v3.0

降级逻辑: provider="qwen" 明确调用 → Cohere (如已配置) → Jina → 最后再试 Qwen
```

## 9. 数据流

### 9.1 主数据流

```
1. PDF 文件
   → pypdf.PdfReader 逐页提取
   → 头尾分块 (前 1500 + 后 1500 字符)
   → UTF-8 清洗
   → NVIDIA API (批量 10 条/次) → 4096 维向量
   → L2 归一化
   → FAISS IndexFlatIP
   → .npy 缓存

2. 用户查询
   → get_embedding(text[:1500])
   → 双路召回: FAISS (余弦相似度) + BM25 (关键词)
   → 合并加权 (向量 60% + BM25 40%)
   → 阈值过滤 (< 0.35 丢弃)
   → [可选] HyDE 双路查询 + 1.2 倍加权合并
   → [可选] Rerank 精排

3. Prompt 拼接
   → 相似文本 (+ 相似度分数) + 用户问题
   → prompts.py 条件渲染 (低于阈值则告知LLM凭数学原理作答)
   → DeepSeek-chat → 结果

4. 日志记录
   → workflow_logger.log() → logs/session_*.json + logs/session_*.md

5. Token 追踪
   → QuotaMonitor.record() → 用量日志
   → 70%/90% 预警 → 生成多平台任务交接文档
```

### 9.2 新增数据流 [v3]

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
   → memory_logger.new_stage() → 阶段切换时开新文件
```

## 10. 模块详解

### 10.1 main.py

**功能**: Streamlit UI + 工作流状态机。

**核心设计**:
- `@st.cache_resource` 装饰 `init_rag()` 确保 RAG 引擎只初始化一次
- `st.session_state` 管理全部状态
- 全局侧边栏: 进度追踪 + 额度监控 + 文件收件箱 + AI网页版协作 + Skills 说明 + 随时提问
- 每个 `elif st.session_state.phase == "xxx":` 块渲染一个阶段的 UI
- 每个阶段切换自动触发 `MemoryLogger.new_stage()` [v3]
- 所有对话消息实时写入 `memory/` [v3]
- 支持 "使用网页AI方案" 触发词注入外源内容 [v3]

**关键 Session State 变量**:

| 变量 | 类型 | 用途 |
|---|---|---|
| phase | str | 当前阶段 |
| topics | list[str] | 上传的赛题文本 |
| selected_topic | str | 用户选中的赛题 |
| modeling_plan | str | 生成的建模方案 |
| pressure_report | str | 压力测试报告 |
| prd_draft / prd_final | str | PRD 草稿/最终版 |
| grill_rounds | int | grill-me 对齐轮数 |
| coding_result | str | 生成的代码 |
| paper_draft | str | 论文初稿 |
| paper_sections | dict | 论文各节内容 |
| quota_monitor | QuotaMonitor | Token 额度追踪 |
| completed_stages | list | 已完成阶段列表 |
| chat_history | list | 对话历史 |
| memory_logger | MemoryLogger | ★ 实时对话记忆 [v3] |
| webai_imported_content | str | ★ 已读取的网页AI回复 [v3] |

### 10.2 rag.py

**类**: `RAG`

**索引方式**: FAISS IndexFlatIP (内积 = 余弦相似度)，L2 归一化，阈值过滤 (默认 0.35)

**检索管线**: 双路召回 (FAISS 向量 + BM25 关键词) → 合并加权 → 阈值过滤 → [可选] HyDE 双路增强 → [可选] Rerank 精排

**分块策略**: 头尾分块 (前 1500 + 后 1500 字符)，短文本 (<2000 字符) 不分块

**多源索引**: 启动时加载 `problems/`、`papers/`、`references/`、`knowledge/`，选题确认后动态加载 `reference/`

| 方法 | 用途 |
|---|---|
| `__init__` | 加载 PDF → 头尾分块 → 批量向量化 → IndexFlatIP → BM25 |
| `_build_index` | 批量向量化 + FAISS IndexFlatIP + .npy 缓存 |
| `_build_index_for_dir` | 为指定目录构建 FAISS 索引 |
| `_search_dual` | HyDE 增强检索 (原题 + 假设文档 双路) |
| `search` | 简单向量检索，供 retrieve_with_knowledge 使用 |
| `_hyde_query` | LLM 生成假设性建模思路 |
| `query` | 三索引并行检索，支持 use_hyde/use_rerank 开关 |
| `topic_coverage_score` | 相似度加权评分 + has_coverage 标志位 |
| `search_filtered` | 按年份/题型条件过滤检索 |
| `load_references` | 选题确认后动态加载 reference/ 目录 |
| `retrieve_with_knowledge` | 综合检索所有已加载索引 |
| `add_inbox_files` | ★ inbox 新文件增量加载到索引 [v3] |
| `_extract_metadata` | 自动从文件路径提取年份和题型标签 |

### 10.3 inbox_watcher.py [v3 新增]

**功能**: 监控 `inbox/` 目录，扫描新文件并追踪处理状态。

| 函数 | 用途 |
|---|---|
| `ensure_inbox_dirs()` | 确保 inbox/ 及 5 个子目录存在 |
| `scan_subdir(name)` | 扫描指定子目录，返回支持的文件列表 |
| `get_new_files(name)` | 对比缓存返回未处理的新文件 |
| `mark_as_processed(paths)` | 记录文件已处理 (时间戳写入 .processed_files.json) |
| `get_inbox_status()` | 返回各子目录文件统计 (total/new) |
| `read_web_ai_file(filename)` | 读取 inbox/web_ai/ 下文件内容 |

### 10.4 webai_bridge.py [v3 新增]

**功能**: 在 agent 工作流与网页版 AI 之间搭建文件交换桥梁。

| 函数 | 用途 |
|---|---|
| `export_context_package(phase, id, ctx, root)` | 打包当前阶段上下文 → .md 文件 |
| `import_webai_response(filename)` | 读取 inbox/web_ai/ 下网页 AI 回复 |
| `list_export_files(session_id, root)` | 列出已导出的上下文包文件列表 |
| `_get_phase_instruction(phase)` | 根据阶段返回协作提示文字 |
| `_format_chat_history(history)` | 格式化对话历史为 Markdown |

### 10.5 memory_logger.py [v3 新增]

**类**: `MemoryLogger`

**功能**: 实时记录对话，按 session + 阶段分文件存储。

| 方法 | 用途 |
|---|---|
| `__init__(session_id)` | 创建 memory/{session_id}/ 目录 |
| `new_stage(phase)` | 切换阶段 → 创建新文件 + 写文件头（幂等） |
| `log_message(role, content, meta)` | 追加一条消息到当前文件 |
| `log_system_event(event, detail)` | 记录系统事件 |
| `get_current_file_path()` | 返回当前文件路径 |
| `get_all_stage_files()` | 返回所有阶段文件列表 |

特点: `threading.Lock()` 线程安全 + 立即 `flush()` 实时保存。

### 10.6 model.py

| 函数 | 签名 | 用途 |
|---|---|---|
| `get_embedding` | `(text, max_chars=1500) → list[float]` | NVIDIA API 单条向量化 |
| `get_embeddings_batch` | `(texts, max_chars=1500) → list[list[float]]` | NVIDIA API 批量向量化 (10条/批) |
| `chat` | `(messages, model, max_tokens, temp, stream) → str` | OpenAI 兼容聊天 |
| `gpt_analysis` | `(prompt, max_tokens, temp) → str` | 单轮对话封装 |
| `gpt_with_retry` | `(prompt, max_tokens, retries=3) → str` | 指数退避重试 |
| `rerank` | `(query, docs, top_n, provider) → list[dict]` | 多 Provider 重排 |
| `_rerank_qwen` | `(query, docs, top_n) → list[dict]` | Qwen 余弦相似度重排 |

### 10.7 prompts.py

| 函数 | 角色 | 输出要求 |
|---|---|---|
| `get_topic_selection_prompt` | 特等奖教练 | 3 维度评分 + 推荐排名 |
| `get_modeling_prompt` | 建模教练 | 问题分析/符号/假设/3方案/推导/创新点 |
| `get_coding_prompt` | 编程教练 | 数据处理/Pyomo-Scipy-GEKKO/求解/敏感性 |
| `get_figure_prompt` | 可视化专家 | 图表类型/配色/Nature 风格 |
| `get_paper_writing_prompt` | 论文教练 | 摘要→重述→模型→检验→评价→参考 |
| `get_polish_prompt` | 学术编辑 | 润色/英译/语法修正/逻辑优化 |
| `get_pressure_test_prompt` | 评审专家 | 5 维度评分 + 风险清单 |
| `get_grill_me_prompt` | 项目评估 | 期望对齐 5 角度 + 是否通过判断 |

### 10.8 skills_runner.py

| 函数 | 用途 |
|---|---|
| `read_skill(skill_name)` | 读取指定 Skill 的 SKILL.md |
| `run_skill(skill_name, context, ...)` | 通用 Skill 执行器 |
| `run_pressure_test(question, plan)` | 压力测试 + star-up 启动分析 |
| `run_grill_me(prd_draft, feedback)` | grill-me 需求对齐 |
| `run_code_check(code, stage)` | think + check + tdd 三重代码审查 |
| `get_skill_comparison()` | 项目 Skills vs Claude Code 内置 Skills 对比 |

### 10.9 prd_generator.py

| 函数 | 用途 |
|---|---|
| `generate_prd(question, plan, report, context, id)` | 生成结构化 PRD Markdown |
| `generate_claude_md(prd, plan, path, id)` | 生成 Claude Code 操作手册 |
| `export_prd_file(prd, path, id)` | 保存 PRD.md 到 workspace |

### 10.10 quota_monitor.py

**类**: `QuotaMonitor`

| 方法 | 用途 |
|---|---|
| `record(stage, tokens)` | 记录一次 LLM 调用的 token 消耗 |
| `estimate_tokens(text)` | 粗估 token 数（字符数/2） |
| `usage_ratio` | 当前使用率 (0.0~1.0) |
| `should_alert()` | 检查是否触发 70%/90% 预警 |
| `get_status_text()` | 生成用量进度条字符串 |
| `generate_handoff_doc(...)` | 生成多平台任务交接文档 |

### 10.11 utils.py

| 函数 | 用途 |
|---|---|
| `load_texts(folder)` | 递归遍历文件夹，pypdf 提取所有 PDF 文本 |
| `load_file_as_text(filepath, max_chars)` | ★ 通用文件读取 (.pdf/.md/.txt)，支持截断 [v3] |
| `chunk_text(text, max_tokens)` | 按段落分块 (非滑动窗口，无重叠) |
| `load_config()` | 读取 .env 文件返回 dict |
| `file_hash(path)` | SHA-256 文件哈希 |
| `save_json / load_json` | JSON 读写 |

### 10.12 skills_bridge.py / workflow_logger.py

保持 v2 架构不变，详见 `update/` 变更日志。

## 11. 扩展指南

### 新增 Skill
1. clone 仓库到 `skills/`
2. 在 `skills_runner.py` 的 `SKILL_PATHS` 中注册路径
3. 添加 `run_xxx()` 封装函数

### 切换 LLM
修改 `.env` 中的 `MODEL_NAME`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_API_KEY`。

### 新增工作流阶段
1. `main.py` 添加 `elif phase == "new_phase":` + `new_stage()` 调用
2. 侧边栏 `all_stages` 列表添加阶段名
3. `prompts.py` 添加 Prompt 模板
4. `workflow_logger.py` 添加 log 方法

## 12. 更新日志

| 日期 | 版本 | 内容 |
|---|---|---|
| 2026-06-10 | v1 | 项目搭建、RAG 引擎、9 阶段工作流、6 个 Skill 集成 |
| 2026-06-11 | v1.1 | Reranker 多 Provider、RAG 7 方向改进 |
| 2026-06-12 | v2 | skills_runner 统一调用层、PRD+CLAUDE.md 自动生成、QuotaMonitor、多源索引 |
| 2026-06-12 | v3 | inbox_watcher + webai_bridge + memory_logger、文件收件箱、网页AI协作、实时对话记忆 |

详见 `update/` 目录。
