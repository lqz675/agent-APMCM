import os
import time
import requests
from openai import OpenAI
from utils import load_config

_config = load_config()

BASE_URL = _config.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
API_KEY = _config.get("DEEPSEEK_API_KEY", os.getenv("DEEPSEEK_API_KEY", ""))
MODEL_NAME = _config.get("MODEL_NAME", "deepseek-chat")

NVIDIA_BASE_URL = _config.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_API_KEY = _config.get("NVIDIA_API_KEY", os.getenv("NVIDIA_API_KEY", ""))
NVIDIA_EMBED_MODEL = _config.get("NVIDIA_EMBED_MODEL", "nvidia/nv-embed-v1")

JINA_API_KEY = _config.get("JINA_API_KEY", os.getenv("JINA_API_KEY", ""))
JINA_RERANK_MODEL = _config.get("JINA_RERANK_MODEL", "jina-reranker-v2-base-multilingual")

QWEN_API_KEY = _config.get("QWEN_API_KEY", os.getenv("QWEN_API_KEY", ""))
QWEN_BASE_URL = _config.get("QWEN_BASE_URL", "https://dashscope-us.aliyuncs.com/compatible-mode/v1")
QWEN_RERANK_MODEL = _config.get("QWEN_RERANK_MODEL", "Qwen3-Reranker-8B")

COHERE_API_KEY = _config.get("COHERE_API_KEY", os.getenv("COHERE_API_KEY", ""))
COHERE_RERANK_MODEL = _config.get("COHERE_RERANK_MODEL", "rerank-multilingual-v3.0")

chat_client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
embed_client = OpenAI(api_key=NVIDIA_API_KEY, base_url=NVIDIA_BASE_URL)


_qwen_client = None


def _get_qwen_client():
    global _qwen_client
    if _qwen_client is None and QWEN_API_KEY:
        _qwen_client = OpenAI(api_key=QWEN_API_KEY, base_url=QWEN_BASE_URL)
    return _qwen_client


def rerank(query, documents, top_n=5, provider="jina"):
    """对检索结果重排序。provider: "jina"(默认) / "qwen" / "cohere"。失败时自动降级。"""
    if not documents:
        return []

    if provider == "qwen":
        result = _rerank_qwen(query, documents, top_n)
        if result:
            return result

    if provider == "cohere" and COHERE_API_KEY:
        try:
            resp = requests.post(
                "https://api.cohere.ai/v2/rerank",
                headers={"Authorization": f"Bearer {COHERE_API_KEY}", "Content-Type": "application/json"},
                json={"model": COHERE_RERANK_MODEL, "query": query, "documents": documents, "top_n": top_n},
                timeout=15
            )
            data = resp.json()
            return [{"index": r["index"], "text": documents[r["index"]], "relevance_score": r["relevance_score"]}
                    for r in data.get("results", [])]
        except Exception as e:
            print(f"Cohere rerank failed: {e}")

    if JINA_API_KEY and provider != "qwen":
        try:
            resp = requests.post(
                "https://api.jina.ai/v1/rerank",
                headers={"Authorization": f"Bearer {JINA_API_KEY}", "Content-Type": "application/json"},
                json={"model": JINA_RERANK_MODEL, "query": query, "documents": documents, "top_n": top_n},
                timeout=15
            )
            data = resp.json()
            return [{"index": r["index"], "text": documents[r["index"]], "relevance_score": r["relevance_score"]}
                    for r in data.get("results", [])]
        except Exception as e:
            print(f"Jina rerank failed: {e}")

    # Jina 失败，自动降级到 Qwen
    result = _rerank_qwen(query, documents, top_n)
    return result


def _rerank_qwen(query, documents, top_n):
    client = _get_qwen_client()
    if not client:
        return []
    try:
        q_emb = client.embeddings.create(
            model=QWEN_RERANK_MODEL, input=[query[:1500]]
        ).data[0].embedding
        scores = []
        for i, doc in enumerate(documents):
            d_emb = client.embeddings.create(
                model=QWEN_RERANK_MODEL, input=[doc[:1500]]
            ).data[0].embedding
            dot = sum(a * b for a, b in zip(q_emb, d_emb))
            norm_q = sum(a * a for a in q_emb) ** 0.5
            norm_d = sum(a * a for a in d_emb) ** 0.5
            sim = dot / (norm_q * norm_d + 1e-9)
            scores.append((i, sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        return [{"index": i, "text": documents[i], "relevance_score": round(s, 4)}
                for i, s in scores[:top_n]]
    except Exception as e:
        print(f"Qwen rerank failed: {e}")
        return []


def get_embeddings_batch(texts, max_chars=1500):
    clean = []
    for t in texts:
        t = t.replace("\n", " ")
        t = t.encode("utf-8", errors="replace").decode("utf-8")
        clean.append(t[:max_chars])
    resp = embed_client.embeddings.create(
        model=NVIDIA_EMBED_MODEL,
        input=clean,
        encoding_format="float"
    )
    return [d.embedding for d in resp.data]


def get_embedding(text, max_chars=1500):
    text = text.replace("\n", " ")
    text = text.encode("utf-8", errors="replace").decode("utf-8")
    text = text[:max_chars]
    resp = embed_client.embeddings.create(
        model=NVIDIA_EMBED_MODEL,
        input=[text],
        encoding_format="float"
    )
    return resp.data[0].embedding


def chat(messages, model=None, max_tokens=4096, temperature=0.7, stream=False):
    m = model or MODEL_NAME
    resp = chat_client.chat.completions.create(
        model=m,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=stream
    )
    if stream:
        return resp
    return resp.choices[0].message.content


def gpt_analysis(prompt, max_tokens=4096, temperature=0.7):
    return chat(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature
    )


def gpt_with_retry(prompt, max_tokens=4096, retries=3):
    for i in range(retries):
        try:
            return gpt_analysis(prompt, max_tokens=max_tokens)
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(2 ** i)
