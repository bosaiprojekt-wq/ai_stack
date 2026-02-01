import os
from fastapi import FastAPI, Form
from pathlib import Path
from docx import Document
import uuid
import requests
from qdrant_client.models import VectorParams, Distance
from langchain_community.chat_models import ChatOllama
from utils.embeddings import embed
from utils.qdrant_client import client, COLLECTION  # COLLECTION is collection_documents

# Environment
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
COLLECTION_DOCS = os.getenv("COLLECTION", "collection_documents")
SPECIAL_COLLECTION = os.getenv("SPECIAL_COLLECTION", "special_cases")

# Paths
DOCS_PATH = "/qdrant_data/documents"
SPECIAL_CASES_PATH = "/qdrant_data/special_cases"

# FastAPI app
app = FastAPI()

# LLM
llm = ChatOllama(model="llama3", base_url=OLLAMA_URL)

def ensure_collection(name: str):
    if name not in client.get_collections().collections:
        client.recreate_collection(
            collection_name=name,
            vectors_config={
                "default": {
                    "size": 768,  # adjust to your embedding size
                    "distance": "Cosine"
                }
            }
        )


# Ensure collections exist at startup
ensure_collection(COLLECTION_DOCS)
ensure_collection(SPECIAL_COLLECTION)



@app.post("/run")
async def run(payload: dict):
    """
    Simple endpoint to query LLM with text, for testing or generating summaries.
    """
    task = payload.get("input", "")
    response = llm.invoke(f"Generate draft response or summary for this: {task}")
    return {"draft": response.content, "collection": COLLECTION_DOCS}


@app.post("/special_case")
async def add_special_case(
    tytul: str = Form(...),
    opis: str = Form(...),
    autor: str = Form(...),
    uwagi: str = Form("")
):
    """
    Submit a special case via form:
    - Saves DOCX in special_cases folder
    - Embeds text and upserts into special_cases Qdrant collection
    """
    # Generate file path
    file_id = str(uuid.uuid4())
    filename = f"{file_id}_{tytul[:30].replace(' ', '_')}.docx"
    filepath = Path(SPECIAL_CASES_PATH) / filename

    # Save DOCX
    doc = Document()
    doc.add_heading(tytul, level=1)
    doc.add_paragraph(f"Opis: {opis}")
    doc.add_paragraph(f"Autor: {autor}")
    doc.add_paragraph(f"Uwagi dodatkowe: {uwagi}")
    doc.save(filepath)
    # Ensure file is writable by all
    filepath.chmod(0o666)

    # Prepare text for embedding
    text = f"{tytul}\n{opis}\n{autor}\n{uwagi}"
    vector = embed(text)

    # Insert into Qdrant
    client.upsert(
        collection_name=SPECIAL_COLLECTION,
        points=[{
            "id": file_id,
            "vector": {
                "default": vector.tolist() if hasattr(vector, "tolist") else list(vector)
            },
            "payload": {
                "file_name": filename,
                "tytul": tytul,
                "opis": opis,
                "autor": autor,
                "uwagi": uwagi
            }
        }]
    )
        

    return {"status": "ok", "file": filename, "id": file_id}
