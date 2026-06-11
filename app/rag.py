import os
import json
import numpy as np
import faiss
from model import get_embedding, get_embeddings_batch, gpt_with_retry, rerank
from utils import load_texts, chunk_text
from rank_bm25 import BM25Okapi
from pathlib import Path

THRESHOLD = 0.35
HYBRID_ALPHA = 0.6


class RAG:
    def __init__(self, problems_dir="dataset/problems", papers_dir="dataset/papers",
                 references_dir="dataset/references", cache_dir="dataset/cache",
                 threshold=THRESHOLD):
        self.problems_dir = problems_dir
        self.papers_dir = papers_dir
        self.references_dir = references_dir
        self.cache_dir = cache_dir
        self.threshold = threshold

        os.makedirs(cache_dir, exist_ok=True)
        self.dataset_dir = Path("dataset")

        self.problems_texts, self.problems_files = load_texts(problems_dir)
        self.papers_texts, self.papers_files = load_texts(papers_dir)
        self.refs_texts, self.refs_files = load_texts(references_dir)

        self.problem_chunks = []
        self.problem_chunk_files = []
        self.paper_chunks = []
        self.paper_chunk_files = []
        self.ref_chunks = []
        self.ref_chunk_files = []

        self.problem_index = None
        self.paper_index = None
        self.ref_index = None

        self._build_indices()

        # knowledge/ 目录索引（数学建模领域知识库，独立索引）
        self.knowledge_dir  = self.dataset_dir / "knowledge"
        self.knowledge_index = None
        self.knowledge_texts = []
        if self.knowledge_dir.exists() and list(self.knowledge_dir.rglob("*.pdf")):
            self.knowledge_index, self.knowledge_texts = self._build_index_for_dir(self.knowledge_dir)

        # reference/ 目录索引（选题确认后动态添加，初始为空）
        self.reference_dir   = self.dataset_dir / "reference"
        self.reference_index = None
        self.reference_texts = []
        # reference/ 在选题确认前不索引，调用 load_references() 后才生效

    @staticmethod
    def _normalize(vec):
        return vec / (np.linalg.norm(vec) + 1e-9)

    @staticmethod
    def _chunk_for_indexing(text):
        """取头部+尾部，避免丢失论文后半段"""
        text = text.strip()
        if len(text) <= 2000:
            return [text]
        chunks = [text[:1500]]
        tail = text[-1500:]
        if tail not in chunks:
            chunks.append(tail)
        return chunks

    def _load_cache(self, name):
        path = os.path.join(self.cache_dir, f"{name}_chunk_vectors.npy")
        if os.path.exists(path):
            return np.load(path)
        return None

    def _save_cache(self, name, vectors):
        path = os.path.join(self.cache_dir, f"{name}_chunk_vectors.npy")
        np.save(path, vectors)

    def _build_index(self, texts, files, name):
        if not texts:
            return None

        cached = self._load_cache(name)
        if cached is not None and len(cached) == sum(1 for t in texts for _ in self._chunk_for_indexing(t)):
            vectors = cached
        else:
            all_chunks = []
            for t in texts:
                all_chunks.extend(self._chunk_for_indexing(t))
            if not all_chunks:
                return None
            vectors_list = []
            batch_size = 10
            for i in range(0, len(all_chunks), batch_size):
                batch = all_chunks[i:i + batch_size]
                vectors_list.extend(get_embeddings_batch(batch))
            vectors = np.array(vectors_list).astype("float32")
            self._save_cache(name, vectors)

        faiss.normalize_L2(vectors)
        dim = vectors.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(vectors)
        return index

    def _chunk_texts(self, texts, files):
        chunks, chunk_files, metadata = [], [], []
        for t, f in zip(texts, files):
            for c in self._chunk_for_indexing(t):
                chunks.append(c)
                chunk_files.append(f)
                meta = self._extract_metadata(f)
                metadata.append(meta)
        return chunks, chunk_files, metadata

    @staticmethod
    def _extract_metadata(filename):
        import re
        meta = {"source": filename}
        year_match = re.search(r'(\d{4})', filename)
        if year_match:
            meta["year"] = int(year_match.group(1))
        if "A" in filename or "A题" in filename:
            meta["topic"] = "A"
        elif "B" in filename or "B题" in filename:
            meta["topic"] = "B"
        elif "C" in filename or "C题" in filename:
            meta["topic"] = "C"
        return meta

    def _build_indices(self):
        self.problem_chunks, self.problem_chunk_files, self.problem_metadata = self._chunk_texts(
            self.problems_texts, self.problems_files)
        self.paper_chunks, self.paper_chunk_files, self.paper_metadata = self._chunk_texts(
            self.papers_texts, self.papers_files)
        self.ref_chunks, self.ref_chunk_files, self.ref_metadata = self._chunk_texts(
            self.refs_texts, self.refs_files)

        self.problem_index = self._build_index(
            self.problems_texts, self.problems_files, "problems")
        self.paper_index = self._build_index(
            self.papers_texts, self.papers_files, "papers")
        self.ref_index = self._build_index(
            self.refs_texts, self.refs_files, "refs")

        self.bm25_problems = BM25Okapi([list(t) for t in self.problem_chunks]) if self.problem_chunks else None
        self.bm25_papers = BM25Okapi([list(t) for t in self.paper_chunks]) if self.paper_chunks else None
        self.bm25_refs = BM25Okapi([list(t) for t in self.ref_chunks]) if self.ref_chunks else None

    def _build_index_for_dir(self, dir_path):
        """为指定目录构建 FAISS 索引，返回 (index, chunk_texts)"""
        texts, files = load_texts(str(dir_path))
        if not texts:
            return None, []
        name = dir_path.name
        index = self._build_index(texts, files, name)
        chunks, _, _ = self._chunk_texts(texts, files)
        return index, chunks

    def search(self, query, index, texts, topk=3):
        """简单向量检索，返回 [{"text":..., "score":...}]"""
        if index is None or not texts:
            return []
        q_vec = np.array([get_embedding(query)]).astype("float32")
        self._normalize(q_vec)
        scores, indices = index.search(q_vec, topk)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if 0 <= idx < len(texts) and score >= self.threshold:
                results.append({"text": texts[idx][:2000], "score": round(float(score), 4)})
        return results

    def _hyde_query(self, question):
        try:
            prompt = f"""请用2-3句话概括解决以下数学建模问题可能用到的核心方法和思路，
不需要完整解答，只需要方法关键词和技术路线：

题目：{question[:500]}

输出格式：方法名称 + 一句话说明适用理由"""
            return gpt_with_retry(prompt, max_tokens=200)
        except Exception:
            return None

    def _search_dual(self, index, texts, files, query, hyde_doc,
                     topk=5, threshold=None, bm25=None, alpha=HYBRID_ALPHA):
        results = self._search(index, texts, files, query, topk * 2, threshold, bm25, alpha)
        if hyde_doc:
            hyde_results = self._search(index, texts, files, hyde_doc, topk * 2, threshold, bm25, alpha)
            seen = {r["index"]: r for r in results}
            for r in hyde_results:
                boosted_score = r["score"] * 1.2
                if r["index"] not in seen or seen[r["index"]]["score"] < boosted_score:
                    seen[r["index"]] = r
                    r["score"] = boosted_score
            results = sorted(seen.values(), key=lambda x: x["score"], reverse=True)[:topk]
        return results[:topk]
        if index is None:
            return []
        th = threshold if threshold is not None else self.threshold

        combined = {}
        seen_files = set()

        q_vec = np.array([get_embedding(query)]).astype("float32")
        self._normalize(q_vec)
        scores, indices = index.search(q_vec, topk * 2)
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(texts) and score >= th:
                fname = files[idx] if idx < len(files) else ""
                if fname and fname in seen_files:
                    continue
                seen_files.add(fname)
                combined[idx] = combined.get(idx, 0) + alpha * score

        if bm25 is not None:
            bm25_scores = bm25.get_scores(list(query))
            bm25_max = max(bm25_scores.max(), 1)
            for i, s in enumerate(bm25_scores):
                if s > 0:
                    combined[i] = combined.get(i, 0) + (1 - alpha) * (s / bm25_max)

        sorted_items = sorted(combined.items(), key=lambda x: x[1], reverse=True)[:topk]
        results = []
        for idx, score in sorted_items:
            results.append({
                "text": texts[idx][:3000],
                "file": files[idx] if idx < len(files) else "",
                "score": round(float(score), 4),
                "index": int(idx)
            })
        return results

    def query(self, question, topk=5, threshold=None, use_hyde=False, use_rerank=False):
        if use_hyde:
            hyde_doc = self._hyde_query(question)
        else:
            hyde_doc = None

        sim_problems = self._search_dual(
            self.problem_index, self.problem_chunks, self.problem_chunk_files,
            question, hyde_doc, topk, threshold, self.bm25_problems
        )
        sim_papers = self._search_dual(
            self.paper_index, self.paper_chunks, self.paper_chunk_files,
            question, hyde_doc, topk, threshold, self.bm25_papers
        )
        sim_refs = self._search_dual(
            self.ref_index, self.ref_chunks, self.ref_chunk_files,
            question, hyde_doc, topk, threshold, self.bm25_refs
        )

        if use_rerank:
            if sim_problems:
                texts = [r["text"] for r in sim_problems]
                reranked = rerank(question, texts, top_n=min(topk, len(texts)))
                sim_problems = [sim_problems[r["index"]] for r in reranked if r["index"] < len(sim_problems)]
            if sim_papers:
                texts = [r["text"] for r in sim_papers]
                reranked = rerank(question, texts, top_n=min(topk, len(texts)))
                sim_papers = [sim_papers[r["index"]] for r in reranked if r["index"] < len(sim_papers)]

        return {
            "sim_questions": [r["text"] for r in sim_problems],
            "sim_question_files": [r["file"] for r in sim_problems],
            "sim_question_scores": [r["score"] for r in sim_problems],
            "sim_papers": [r["text"] for r in sim_papers],
            "sim_paper_files": [r["file"] for r in sim_papers],
            "sim_paper_scores": [r["score"] for r in sim_papers],
            "sim_refs": [r["text"] for r in sim_refs],
            "sim_ref_files": [r["file"] for r in sim_refs],
            "sim_ref_scores": [r["score"] for r in sim_refs],
            "_raw_problems": sim_problems,
            "_raw_papers": sim_papers,
            "_raw_refs": sim_refs,
        }

    def search_filtered(self, chunks, files, metadata, index, query,
                        topk=5, year=None, topic=None):
        if index is None:
            return []
        valid = [
            i for i, m in enumerate(metadata)
            if (year is None or m.get("year") == year)
            and (topic is None or m.get("topic") == topic)
        ]
        if not valid:
            return []

        q_vec = np.array([get_embedding(query)]).astype("float32")
        self._normalize(q_vec)
        scores, indices = index.search(q_vec, len(valid) + topk)
        results = []
        valid_set = set(valid)
        seen = set()
        for score, idx in zip(scores[0], indices[0]):
            if idx in valid_set and score >= self.threshold:
                fname = files[idx] if idx < len(files) else ""
                if fname not in seen:
                    seen.add(fname)
                    results.append({
                        "text": chunks[idx][:3000],
                        "file": fname,
                        "score": round(float(score), 4),
                        "meta": metadata[idx]
                    })
        return results[:topk]

    def topic_coverage_score(self, question, topk=10, threshold=None,
                              use_hyde=False, use_rerank=False):
        sims = self.query(question, topk=topk, threshold=threshold,
                         use_hyde=use_hyde, use_rerank=use_rerank)
        raw_q = sims["_raw_problems"]
        raw_p = sims["_raw_papers"]
        raw_r = sims["_raw_refs"]

        q_score = sum(r["score"] for r in raw_q) * 10
        p_score = sum(r["score"] for r in raw_p) * 15
        r_score = sum(r["score"] for r in raw_r) * 5
        total = round(q_score + p_score + r_score, 2)

        has_coverage = len(raw_q) + len(raw_p) > 0

        return total, {
            "sim_questions": [r["text"] for r in raw_q],
            "sim_question_files": [r["file"] for r in raw_q],
            "sim_papers": [r["text"] for r in raw_p],
            "sim_paper_files": [r["file"] for r in raw_p],
            "sim_refs": [r["text"] for r in raw_r],
            "sim_ref_files": [r["file"] for r in raw_r],
            "has_coverage": has_coverage,
        }

    def load_references(self):
        """
        选题确认后调用，将 reference/ 目录索引进来。
        这个目录由大模型推荐的参考文献 PDF 填充。
        """
        if self.reference_dir.exists() and list(self.reference_dir.rglob("*.pdf")):
            self.reference_index, self.reference_texts = self._build_index_for_dir(self.reference_dir)
            return True
        return False

    def retrieve_with_knowledge(self, query: str, topk: int = 3) -> dict:
        """
        综合检索：同时查询 problems/ + papers/ + knowledge/（+ reference/ 如已加载）。
        返回各来源的检索结果，供大模型决策时参考。
        """
        results = {
            "similar_problems": self.search(query, self.problems_index, self.problems_texts, topk) if self.problems_index else [],
            "similar_papers":   self.search(query, self.papers_index,   self.papers_texts,   topk) if self.papers_index   else [],
            "knowledge":        self.search(query, self.knowledge_index, self.knowledge_texts, topk) if self.knowledge_index else [],
            "references":       self.search(query, self.reference_index, self.reference_texts, topk) if self.reference_index else [],
        }
        return results
