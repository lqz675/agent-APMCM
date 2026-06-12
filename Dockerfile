FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs workspace/upload/1 workspace/upload/2 workspace/upload/3 \
    workspace/coding workspace/writing workspace/picture workspace/prepare_claude \
    workspace/rubbish dataset/cache \
    inbox/problems inbox/papers inbox/references inbox/knowledge inbox/web_ai inbox/data \
    memory

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app/main.py", "--server.headless", "true", \
            "--server.address", "0.0.0.0", "--server.port", "8501"]
