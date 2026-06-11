# 更新日志

## 2026-06-11: RAG 7 方向全面改进

### 变更摘要
对 `rag.py` 实施全部 7 个改进方向。

### 方向一：相似度阈值过滤
- `rag.py`: IndexFlatL2 → IndexFlatIP (余弦相似度索引)
- L2 归一化向量，默认阈值 0.35
- `_search` 返回带 score 的 dict

### 方向二：Prompt 降级处理
- `prompts.py`: 新增 `_render_sim_block()` 条件渲染
- 低相似度时告知 LLM「无参考资料，请依据数学原理作答」
- `topic_coverage_score` 添加 `has_coverage` 标志位
- 评分改为相似度加权

### 方向三：分块策略改进
- `rag.py`: 头尾分块 (前 1500 + 后 1500 字符)
- 短文本 (<2000 字符) 不分块
- 同文件多 chunk 去重

### 方向四：BM25 混合检索
- `rag.py`: 新增 BM25 检索器 (rank_bm25, 字级别分词)
- 双路合并: 向量 60% + BM25 40%
- `requirements.txt` 隐含依赖 rank_bm25

### 方向五：HyDE 查询增强
- `rag.py`: `_hyde_query()` LLM 生成假设性建模思路
- `_search_dual()` 原题 + HyDE 双路检索
- HyDE 结果加权 1.2 倍
- 默认关闭 (`use_hyde=False`)

### 方向六：Rerank 接入检索管线
- `rag.py`: `query()` 集成 `rerank()` 精排
- 默认关闭 (`use_rerank=False`)
- 选题分析阶段可启用

### 方向七：元数据过滤
- `rag.py`: `_extract_metadata()` 自动提取年份/题型
- `search_filtered()` 按年份/题型筛选

### 其他
- `model.py`: 新增 `get_embeddings_batch()` 批量向量化 API

### 涉及文件
| 文件 | 变更行数 |
|---|---|
| `app/rag.py` | 99 → ~260 行 (+160) |
| `app/prompts.py` | 244 → ~300 行 (+60) |
| `app/model.py` | +15 行 (get_embeddings_batch) |
