import os
from pathlib import Path
import uuid
import requests

from loaders.pdf_loader import load_pdf
from loaders.txt_loader import load_txt
from loaders.docx_loader import load_docx
from utils.chunking import chunk_text
from utils.qdrant_client import client

# Environment / collections
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
COLLECTION_DOCS = os.getenv("COLLECTION", "collection_documents")
SPECIAL_COLLECTION = os.getenv("SPECIAL_COLLECTION", "special_cases")

# Folders
DOCS_PATH = "/qdrant_data/documents"
SPECIAL_PATH = "/qdrant_data/special_cases"

def embed(text):
    """Generate embedding vector using Ollama embedding model"""
    if isinstance(text, str):
        inputs = [text]
    else:
        inputs = text

    r = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBED_MODEL, "input": inputs}
    )
    data = r.json()
    return data["embeddings"][0]

def ingest_folder(path: str, collection: str):
    """Ingest all files in a folder into Qdrant collection"""
    for file in Path(path).iterdir():
        if not file.is_file():
            continue

        pages = []
        suffix = file.suffix.lower()

        if suffix == ".pdf":
            pages = load_pdf(file)
        elif suffix == ".txt":
            pages = load_txt(file)
        elif suffix == ".docx":
            pages = load_docx(file)
        else:
            print(f"Skipping unsupported file: {file.name}")
            continue

        for page_num, page_text in enumerate(pages):
            chunks = chunk_text(page_text)
            for chunk_idx, chunk in enumerate(chunks):
                vector = embed(chunk)
                point_id = str(uuid.uuid4())
                client.upsert(
                    collection_name=collection,
                    points=[{
                        "id": point_id,
                        "vector": vector,
                        "payload": {
                            "file_name": file.name,
                            "page": page_num,
                            "chunk_index": chunk_idx,
                            "text": chunk
                        }
                    }]
                )
                print(f"Ingested {file.name} page {page_num} chunk {chunk_idx} -> {point_id}")

if __name__ == "__main__":
    print("=== Ingesting documents folder ===")
    ingest_folder(DOCS_PATH, COLLECTION_DOCS)

    print("=== Ingesting special cases folder ===")
    ingest_folder(SPECIAL_PATH, SPECIAL_COLLECTION)
