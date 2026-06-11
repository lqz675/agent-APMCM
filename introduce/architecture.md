# APMCM Agent 架构文档

## 1. 项目结构

```
agent/
├── app/                                # 核心代码 (11 个模块)
│   ├── __init__.py                     # 包初始化（支撑相对导入）
│   ├── main.py                         # Streamlit 界面 + 9 阶段工作流引擎
│   ├── rag.py                          # FAISS 向量检索引擎
│   ├── model.py                        # LLM/Embedding/Rerank 多 API 调用层
│   ├── prompts.py                      # 8 个阶段 Prompt 模板工厂函数
│   ├── skills_runner.py                # 统一 Skill 调用入口 (新增)
│   ├── prd_generator.py                # PRD + CLAUDE.md 自动生成 (新增)
│   ├── quota_monitor.py                # Token 额度监控 + 平台交接 (新增)
│   ├── utils.py                        # PDF 解析、文本分块、配置读取、缓存
│   ├── skills_bridge.py                # 外部 Skill 桥接层
│   └── workflow_logger.py              # 双格式工作流日志 JSON + Markdown
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
│   ├── knowledge/                       # 数学建模领域知识库 PDF (新增)
│   ├── reference/                       # 选题后动态加载文献 PDF (新增)
│   └── cache/                          # 向量缓存 (.npy, 自动生成)
├── workspace/                          # 产出目录 (运行时生成)
│   └── {session_id}/
│       ├── PRD.md                      # 产品需求文档
│       ├── CLAUDE.md                   # Claude Code 操作手册
│       ├── model_solution.py           # 生成的代码
│       ├── solution/                   # 模块化代码
│       ├── figures/                    # 图表输出
│       ├── results/                    # JSON 结果
│       └── paper_sections/             # 论文各节
├── logs/                               # 工作流日志 (session_*.json + session_*.md)
├── introduce/                          # 本文档 + 操作手册
├── update/                             # 架构变更日志
├── requirements.txt
├── .env                                # API 密钥配置 (已填入)
└── .env.example                        # 配置模板
```

## 2. 工作流

```
用户上传赛题 PDF (st.file_uploader x3)
  → pypdf 解析文本 → 进入工作流
      │
      ▼
┌──────────────────────────────────────────────────────────┐
│ 阶段1: input — 上传赛题                                    │
│   3 个 file_uploader 分别上传赛题 PDF → _extract_pdf() 解析 │
│   点击 "开始分析" → phase = "topic_selection"              │
└──────────────────────────┬───────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────┐
│ 阶段2: topic_selection — 选题分析                          │
│   RAG.topic_coverage_score() → FAISS 检索 → 加权评分       │
│   DeepSeek-chat → 从 3 维度 (获奖难度/可行性/文献支撑) 推荐  │
│   用户选择最终选题 → phase = "modeling"                     │
└──────────────────────────┬───────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ 阶段3: modeling — 建模方案 + 压力测试 + PRD + 需求对齐 (一体化)    │
│                                                                    │
│  3a. get_modeling_prompt() → LLM 生成建模方案                      │
│  3b. run_pressure_test() → startup-pressure-test + star-up         │
│      (技术/时间/数据 三维度可行性报告)                               │
│  3c. generate_prd() → PRD.md (结构化产品需求文档)                    │
│  3d. grill-me 循环 → 用户反馈 + AI 追问 → 修订 PRD                 │
│  3e. generate_claude_md() → CLAUDE.md (Claude Code 操作手册)        │
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
│   → "开始新会话" 重置所有状态                              │
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
├── Skills 说明 (项目 vs Claude Code 对比)
└── 随时提问输入框
```

## 3. 选题推荐算法

### 3.1 向量检索流程

```
PDF 文件 → pypdf.PdfReader 逐页提取文本
         → 头尾分块: 取前 1500 + 后 1500 字符 (短文本不分块)
         → UTF-8 清洗 (非法字符替换)
         → NVIDIA nv-embed-v1 API → 4096 维浮点向量
         → L2 归一化 → FAISS IndexFlatIP 索引 (内积 = 余弦相似度)
         → 缓存为 dataset/cache/{name}_chunk_vectors.npy
```

首次启动批量调用 API 向量化全部 PDF 并缓存。后续启动仅在 chunk 数量变化时重建。

### 3.2 混合检索架构

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

默认配置: HyDE=False, Rerank=False (速度优先)
选题分析阶段可启用: use_hyde=True, use_rerank=True
```

### 3.3 评分公式

`rag.py:topic_coverage_score()`:

```python
score = Σ(相似度 × 10) + Σ(相似度 × 15) + Σ(相似度 × 5)
      (问题匹配)          (论文匹配)          (参考文献匹配)
```

- 每个匹配结果按实际相似度 (0.35~1.0) 加权
- 低于阈值 0.35 的结果不计入
- 返回值包含 `has_coverage` 标志位，供 Prompt 降级使用

### 3.4 元数据支持

自动从文件路径提取年份 (正则 `\d{4}`) 和题型 (A/B/C)，支持 `search_filtered()` 按条件筛选。

### 3.5 多源知识库

索引源从 3 路扩展到 5 路：

| 目录 | 加载时机 | 用途 |
|------|----------|------|
| `problems/` | 启动时 | 历年赛题 |
| `papers/` | 启动时 | 获奖论文 |
| `references/` (旧) | 启动时 | 参考文献(存量) |
| `knowledge/` | 启动时 | 领域知识库(新增) |
| `reference/` | 选题确认后 | 动态推荐文献(新增) |

`retrieve_with_knowledge()` 方法统一查询所有已加载的索引，返回结构化结果。

## 4. Skill 清单

### 4.1 统一调用层

所有 Skill 通过 `skills_runner.py` 统一调度，在调用前自动读取对应 `SKILL.md` 确保按规范使用。

| 函数 | 调用 Skill | 用途 |
|------|-----------|------|
| `run_pressure_test()` | pressure-test + star-up | 方案可行性报告 |
| `run_grill_me()` | grill-me | PRD 需求对齐 |
| `run_code_check()` | think + check + tdd | 代码三重审查 |
| `read_skill()` | 任意 | 读取 SKILL.md |

### 4.2 Skill 路径映射

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

### 4.3 Skill 详细列表

#### Skill 1: codex-startup-pressure-test-skill — 压力测试

| 项目 | 内容 |
|---|---|
| 仓库 | `skills/codex-startup-pressure-test-skill/` |
| 入口 | `startup-pressure-test/SKILL.md` |
| 对应阶段 | 阶段 3b「建模方案中内嵌」 |
| 集成方式 | `skills_runner.run_pressure_test()` 统一调用 |
| 工作流程 | 取建模方案 → 3 维度(技术可行性/时间可行性/数据可行性) → 通过/有风险/不建议 |

#### Skill 2: mattpocock/skills — grill-me (需求对齐)

| 项目 | 内容 |
|---|---|
| 仓库 | `skills/skills/` |
| 入口 | `productivity/grill-me/SKILL.md` |
| 对应阶段 | 阶段 3d「PRD 对齐循环」 |
| 集成方式 | `skills_runner.run_grill_me()` 统一调用 |
| 工作流程 | 用户反馈 → AI 追问挑战 → 找出模糊点 → 修订建议 |

#### Skill 3: mattpocock/skills — tdd (测试驱动)

| 项目 | 内容 |
|---|---|
| 仓库 | `skills/skills/` |
| 入口 | `engineering/tdd/SKILL.md` |
| 对应阶段 | 阶段 4「代码三重审查」 |
| 集成方式 | `skills_runner.run_code_check()` 中 think+check+tdd 联合调用 |

#### Skill 4/5/6: waza — think / check / hunt

| Skill | 入口 | 调用方式 |
|-------|------|----------|
| think | `waza/skills/think/SKILL.md` | `skills_runner.run_code_check()` |
| check | `waza/skills/check/SKILL.md` | `skills_runner.run_code_check()` |
| hunt | `waza/skills/hunt/SKILL.md` | 对话触发, CLAUDE.md 内置 Bug 排查协议 |

#### Skill 7: scipilot-figure-skill (科学图表)

| 项目 | 内容 |
|---|---|
| 仓库 | `skills/scipilot-figure-skill/` |
| 入口 | `scripts/profile_data.py`, `scripts/setup_style.py`, `scripts/export_figure.py`, `scripts/check_figure.py` |
| 对应阶段 | 阶段 5「图表生成」 |
| 集成方式 | Python 直接调用 (`skills_bridge.py` → `from profile_data import profile_data`) |
| 核心函数 | `profile_data()` — 数据探索; `setup_style(journal)` — Nature/Science/IEEE 风格; `export_figure()` — 多格式导出; `check_figure()` — 合规审查 |

#### Skill 8: gpt_academic (论文润色)

| 项目 | 内容 |
|---|---|
| 仓库 | `skills/gpt_academic/` |
| 入口 | `main.py` + `crazy_functions/` (71 插件) |
| 对应阶段 | 阶段 7「论文润色」 |
| 集成方式 | 当前通过 LLM Prompt 模板; `skills_bridge.py` 预留 `gpt_academic_polish()` 子进程调用 |

### 4.4 调度表

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

## 5. API 架构

### 5.1 Chat 层

```
chat_client (OpenAI SDK)
  ├── Base URL: https://api.deepseek.com
  ├── Model: deepseek-chat (可配置)
  ├── API Key: sk-f245...
  └── 函数: chat(), gpt_analysis(), gpt_with_retry()
```

### 5.2 Embedding 层

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

### 5.3 Rerank 层

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

`query()` 默认 `use_rerank=False`，启用后检索结果经 `rerank()` 精排。

## 6. 数据流

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

## 7. 模块详解

### 7.1 main.py

**功能**: Streamlit UI + 工作流状态机。

**核心设计**:
- `@st.cache_resource` 装饰 `init_rag()` 确保 RAG 引擎只初始化一次
- `st.session_state` 管理全部状态
- 全局侧边栏: 进度追踪 + 额度监控 + Skills 说明 + 随时提问
- 每个 `elif st.session_state.phase == "xxx":` 块渲染一个阶段的 UI

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

### 7.2 rag.py

**类**: `RAG`

**索引方式**: FAISS IndexFlatIP (内积 = 余弦相似度)，L2 归一化，阈值过滤 (默认 0.35)

**检索管线**: 双路召回 (FAISS 向量 + BM25 关键词) → 合并加权 → 阈值过滤 → [可选] HyDE 双路增强 → [可选] Rerank 精排

**分块策略**: 头尾分块 (前 1500 + 后 1500 字符)，短文本 (<2000 字符) 不分块

**多源索引**: 启动时加载 `problems/`、`papers/`、`references/`、`knowledge/`，选题确认后动态加载 `reference/`

| 方法 | 用途 |
|---|---|
| `__init__` | 加载 PDF → 头尾分块 → 批量向量化 → IndexFlatIP → BM25 |
| `_build_index` | 批量向量化 + FAISS IndexFlatIP + .npy 缓存 |
| `_build_index_for_dir` | 为指定目录构建 FAISS 索引 (新增) |
| `_search_dual` | HyDE 增强检索 (原题 + 假设文档 双路) |
| `search` | 简单向量检索，供 retrieve_with_knowledge 使用 (新增) |
| `_hyde_query` | LLM 生成假设性建模思路 |
| `query` | 三索引并行检索，支持 use_hyde/use_rerank 开关 |
| `topic_coverage_score` | 相似度加权评分 + has_coverage 标志位 |
| `search_filtered` | 按年份/题型条件过滤检索 |
| `load_references` | 选题确认后动态加载 reference/ 目录 (新增) |
| `retrieve_with_knowledge` | 综合检索所有已加载索引 (新增) |
| `_extract_metadata` | 自动从文件路径提取年份和题型标签 |

### 7.3 model.py

**核心函数**:

| 函数 | 签名 | 用途 |
|---|---|---|
| `get_embedding` | `(text, max_chars=1500) → list[float]` | NVIDIA API 单条向量化 |
| `get_embeddings_batch` | `(texts, max_chars=1500) → list[list[float]]` | NVIDIA API 批量向量化 (10条/批) |
| `chat` | `(messages, model, max_tokens, temp, stream) → str` | OpenAI 兼容聊天 |
| `gpt_analysis` | `(prompt, max_tokens, temp) → str` | 单轮对话封装 |
| `gpt_with_retry` | `(prompt, max_tokens, retries=3) → str` | 指数退避重试 |
| `rerank` | `(query, docs, top_n, provider) → list[dict]` | 多 Provider 重排 |
| `_rerank_qwen` | `(query, docs, top_n) → list[dict]` | Qwen 余弦相似度重排 |

### 7.4 prompts.py

全部 8 个 Prompt 模板函数，无类，纯函数设计：

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

### 7.5 skills_runner.py (新增)

**功能**: 所有 Skill 的统一调用入口，避免各处散乱调用。

| 函数 | 用途 |
|---|---|
| `read_skill(skill_name)` | 读取指定 Skill 的 SKILL.md |
| `run_skill(skill_name, context, ...)` | 通用 Skill 执行器（先读文档，再按规范执行） |
| `run_pressure_test(question, plan)` | 压力测试 + star-up 启动分析 |
| `run_grill_me(prd_draft, feedback)` | grill-me 需求对齐 |
| `run_code_check(code, stage)` | think + check + tdd 三重代码审查 |
| `get_skill_comparison()` | 项目 Skills vs Claude Code 内置 Skills 对比 |

### 7.6 prd_generator.py (新增)

**功能**: 根据建模方案和对齐结果生成 PRD 和 CLAUDE.md。

| 函数 | 用途 |
|---|---|
| `generate_prd(question, plan, report, context, id)` | 生成结构化 PRD Markdown |
| `generate_claude_md(prd, plan, path, id)` | 生成 Claude Code 操作手册 |
| `export_prd_file(prd, path, id)` | 保存 PRD.md 到 workspace |

PRD 结构: 问题重述 → 核心建模方法 → 技术方案(数学模型/求解器/数据处理) → 执行计划 → 风险 → 论文结构规划 → 待确认决策

CLAUDE.md 包含: 执行规范(think/tdd/check/hunt)、文件结构、完成每个文件后的行动、Skills 对比说明

### 7.7 quota_monitor.py (新增)

**类**: `QuotaMonitor`

**功能**: 追踪 token 使用量，额度耗尽前提醒并生成多平台任务交接文档。

| 方法 | 用途 |
|---|---|
| `record(stage, tokens)` | 记录一次 LLM 调用的 token 消耗 |
| `estimate_tokens(text)` | 粗估 token 数（字符数/2） |
| `usage_ratio` | 当前使用率 (0.0~1.0) |
| `remaining_tokens` | 剩余 token 数 |
| `should_alert()` | 检查是否触发 70%/90% 预警 |
| `get_status_text()` | 生成用量进度条字符串 |
| `generate_handoff_doc(...)` | 生成多平台任务交接文档 |
| `save_log(path)` | 保存 token 使用日志 JSON |

支持的切换平台: ChatGPT 网页版 / Cursor / Codex (OpenAI) / Claude Code (新会话)

### 7.8 utils.py

| 函数 | 用途 |
|---|---|
| `load_texts(folder)` | 递归遍历文件夹，pypdf 提取所有 PDF 文本 |
| `chunk_text(text, max_tokens)` | 按段落分块 (非滑动窗口，无重叠) |
| `load_config()` | 读取 .env 文件返回 dict |
| `file_hash(path)` | SHA-256 文件哈希 |
| `save_json / load_json` | JSON 读写 |

### 7.9 skills_bridge.py

**模块级路径变量**:
- `SKILLS_DIR` = `agent/skills/`
- `SCIPILOT_DIR` = `skills/scipilot-figure-skill/scripts/`
- `GPT_ACADEMIC_DIR` = `skills/gpt_academic/`

**桥接函数**:
| 函数 | 对应 Skill |
|---|---|
| `profile_data()` | scipilot-figure 数据探索 |
| `setup_style()` | scipilot-figure 期刊风格 |
| `export_figure()` | scipilot-figure 图表导出 |
| `check_figure()` | scipilot-figure 合规审查 |
| `gpt_academic_polish()` | gpt_academic 论文润色 |

### 7.10 workflow_logger.py

**类**: `WorkflowLogger`

每次会话生成 `logs/session_{timestamp}.json` + `logs/session_{timestamp}.md`。
每个阶段操作调用对应的 `log_xxx()` 方法记录。
内容截断: 日志条目中模型输出截断到 500 字符，Markdown 截断到 2000 字符。

## 8. Prompt 模板

### 8.1 选题分析 (`get_topic_selection_prompt`)

```
你是APMCM数学建模竞赛特等奖教练,精通选题策略。
从获奖难度/完成可行性/数据与文献支撑 3 维度分析并推荐排名。
```

### 8.2 建模方案 (`get_modeling_prompt`)

```
你是APMCM数学建模竞赛教练,擅长数学建模方案设计。
输出: 问题分析/符号说明/模型假设/3种方案对比/推荐方案推导/创新点
```

### 8.3 压力测试 (`get_pressure_test_prompt`)

```
你是数学建模评审专家,请对以下建模方案进行压力测试。
评估维度: 可行性/创新性/完整性/可操作性/数学严谨性
每个维度: 评分(1-10) + 优点 + 潜在漏洞 + 改进建议
```

### 8.4 用户对齐 (`get_grill_me_prompt`)

```
你是数学建模项目评估专家。
从目标对齐度/方法匹配度/预期产出/差距分析/调整建议 5 角度评估。
明确判断: "符合预期可以继续" 或 "需要调整"
```

### 8.5 代码生成 (`get_coding_prompt`)

```
你是APMCM数学建模编程教练,擅长将数学模型转化为高效Python代码。
代码结构: 数据处理/模型实现(Pyomo/Scipy/GEKKO)/求解/敏感性分析
```

### 8.6 图表生成 (`get_figure_prompt`)

```
你是科学可视化专家,为数学建模论文设计专业图表。
图表清单: 类型/目的/数据源/配色/Nature 期刊风格
```

### 8.7 论文初稿 (`get_paper_writing_prompt`)

```
你是APMCM数学建模论文写作教练。
论文结构: 摘要→问题重述→模型建立→求解→检验→评价→参考文献
```

### 8.8 论文润色 (`get_polish_prompt`)

```
你是学术论文编辑。
润色类型: 润色/翻译为英文/学术语法修正/逻辑优化
```

## 9. PRD + CLAUDE.md 生成流程

```
建模方案 + 压力测试报告
       ↓
  generate_prd()
       ↓
   PRD.md (7 章节结构化文档)
       ↓
  grill-me 循环 (用户反馈 → AI 追问 → 修订)
       ↓
  generate_claude_md()
       ↓
  CLAUDE.md (Claude Code 操作手册)
```

CLAUDE.md 核心内容:
- 执行规范: 编码前(think) → 编码中(tdd) → 编码后(check) → 遇Bug(hunt)
- 文件结构: solution/ → data_processing.py / model.py / solver.py / sensitivity.py / figures.py
- 完成信号: DONE.md 报告
- Skills 对比说明: 项目 Skills vs Claude Code 内置 Skills

## 10. 扩展指南

### 新增 Skill
1. clone 仓库到 `skills/`
2. 在 `skills_runner.py` 的 `SKILL_PATHS` 中注册路径
3. 添加 `run_xxx()` 封装函数
4. 如 Prompt 级别集成，在 `prompts.py` 添加模板

### 切换 LLM
修改 `.env` 中的 `MODEL_NAME`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_API_KEY`，
任何 OpenAI 兼容 API 均可用。

### 新增工作流阶段
1. `main.py` 添加 `elif phase == "new_phase":`
2. 侧边栏 `all_stages` 列表添加阶段名
3. `prompts.py` 添加 Prompt 模板
4. `workflow_logger.py` 添加 log 方法

## 11. 更新日志

| 日期 | 内容 | 详情 |
|---|---|---|
| 2026-06-10 | 初始架构 | 项目搭建、RAG 引擎、9 阶段工作流、6 个 Skill 集成 |
| 2026-06-11 | Reranker 多 Provider | Jina + Qwen + Cohere 三通道降级链 |
| 2026-06-11 | RAG 7 方向改进 | 阈值过滤、Prompt 降级、头尾分块、BM25 混合检索、HyDE、Rerank 集成、元数据过滤 |
| 2026-06-12 | 架构重构 v2 | skills_runner 统一调用层、PRD+CLAUDE.md 自动生成、QuotaMonitor 额度监控、knowledge/+reference/ 多源索引、全局仪表盘侧边栏 |

详见 `update/` 目录。
