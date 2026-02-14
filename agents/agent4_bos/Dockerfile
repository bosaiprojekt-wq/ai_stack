FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

RUN pip install --no-cache-dir numpy

#IMPORTANT NOTE: We split requirements into batches to optimize layer caching in Docker. When we had everyting in one file, the building got stuck or was throwning errors mainly on torch, sentence-transformers and lanchain.
RUN pip install --no-cache-dir -r requirements-batch-1.txt

COPY requirements-batch-2.txt .
RUN pip install --no-cache-dir torch==2.1.0 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir transformers==4.35.2 huggingface-hub==0.22.2 sentence-transformers==2.5.0
COPY requirements-batch-3.txt .
RUN pip install --no-cache-dir -r requirements-batch-3.txt

# Create directories
RUN mkdir -p /app/qdrant_data/knowledge_base \
    /app/qdrant_data/special_cases \
    /app/qdrant_data/storage \
    /app/web/templates

COPY . .

CMD ["python", "main.py"]