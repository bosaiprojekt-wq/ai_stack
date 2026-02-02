import os
from pathlib import Path
import uuid
import requests

from loaders.pdf_loader import load_pdf
from loaders.txt_loader import load_txt
from loaders.docx_loader import load_docx
from utils.chunking import chunk_text
from utils.qdrant_client import client

# ===== CONFIGURATION =====
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

# Collection names
DOCS_COLLECTION = "collection_documents"
SPECIAL_COLLECTION = "special_cases"

# Folder paths
DOCS_PATH = "/qdrant_data/documents"
SPECIAL_PATH = "/qdrant_data/special_cases"

# ===== CORE FUNCTIONS =====
def embed(text):
    """Generate embedding using Ollama"""
    if isinstance(text, str):
        inputs = [text]
    else:
        inputs = text

    response = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBED_MODEL, "input": inputs},
        timeout=30
    )
    return response.json()["embeddings"][0]

def ingest_single_file(file_path: Path, collection: str):
    """Ingest one file into Qdrant"""
    suffix = file_path.suffix.lower()
    
    # Load file based on type
    if suffix == ".pdf":
        pages = load_pdf(file_path)
    elif suffix == ".txt":
        pages = load_txt(file_path)
    elif suffix == ".docx":
        pages = load_docx(file_path)
    else:
        print(f"⚠️ Skipping unsupported: {file_path.name}")
        return 0
    
    total_chunks = 0
    
    for page_num, page_text in enumerate(pages):
        chunks = chunk_text(page_text)
        
        for chunk_idx, chunk in enumerate(chunks):
            try:
                # Generate embedding
                vector = embed(chunk)
                
                # Insert with NAMED VECTOR format
                client.upsert(
                    collection_name=collection,
                    points=[{
                        "id": str(uuid.uuid4()),
                        "vector": {"default": vector},  # ← NAMED VECTOR
                        "payload": {
                            "file_name": file_path.name,
                            "page": page_num,
                            "chunk_index": chunk_idx,
                            "text": chunk
                        }
                    }]
                )
                total_chunks += 1
                
            except Exception as e:
                print(f"❌ Error chunk {chunk_idx}: {e}")
                continue
    
    if total_chunks > 0:
        print(f"✅ {file_path.name}: {total_chunks} chunks")
    return total_chunks

def ingest_folder(folder_path: str, collection: str):
    """Ingest all files in a folder"""
    folder = Path(folder_path)
    
    if not folder.exists():
        print(f"❌ Folder not found: {folder_path}")
        return 0
    
    files = [f for f in folder.iterdir() if f.is_file()]
    print(f"📁 Found {len(files)} files in {folder_path}")
    
    total_files = 0
    total_chunks = 0
    
    for file_path in files:
        chunks = ingest_single_file(file_path, collection)
        if chunks > 0:
            total_files += 1
            total_chunks += chunks
    
    print(f"📊 Ingested {total_files} files, {total_chunks} chunks")
    return total_files

# ===== MAIN EXECUTION =====
if __name__ == "__main__":
    print("🚀 Starting ingest process...")
    
    # Ingest documents
    print("\n" + "="*50)
    print("📚 Ingesting official documents...")
    docs_count = ingest_folder(DOCS_PATH, DOCS_COLLECTION)
    
    # Ingest special cases
    print("\n" + "="*50)
    print("⭐ Ingesting special cases...")
    special_count = ingest_folder(SPECIAL_PATH, SPECIAL_COLLECTION)
    
    # Summary
    print("\n" + "="*50)
    print("📊 INGEST SUMMARY:")
    print(f"  Documents: {docs_count} files")
    print(f"  Special cases: {special_count} files")
    print("✅ Ingest complete!")
    
    # Verify
    try:
        docs_info = client.get_collection(DOCS_COLLECTION)
        special_info = client.get_collection(SPECIAL_COLLECTION)
        print(f"\n📈 Qdrant stats:")
        print(f"  {DOCS_COLLECTION}: {docs_info.points_count} points")
        print(f"  {SPECIAL_COLLECTION}: {special_info.points_count} points")
    except Exception as e:
        print(f"⚠️ Could not verify: {e}")

def ingest_form_submission(file_path: Path, metadata: dict):
    """Ingest a form submission DOCX file with metadata."""
    print(f"📄 Processing form submission: {file_path.name}")
    
    try:
        # Check if file already exists in Qdrant
        from utils.qdrant_client import client
        
        # Simple check: search for this file name
        search_result = client.scroll(
            collection_name=SPECIAL_COLLECTION,
            scroll_filter={
                "must": [
                    {"key": "file_name", "match": {"value": file_path.name}}
                ]
            },
            limit=1
        )
        
        if search_result[0]:  # File already exists
            print(f"⚠️ File {file_path.name} already in Qdrant, skipping")
            return {"status": "skipped", "reason": "already_exists"}
        
        # Ingest the file
        chunks = ingest_single_file(file_path, SPECIAL_COLLECTION)
        
        if chunks > 0:
            # Update the first chunk with form metadata
            search_result = client.scroll(
                collection_name=SPECIAL_COLLECTION,
                scroll_filter={
                    "must": [
                        {"key": "file_name", "match": {"value": file_path.name}}
                    ]
                },
                limit=1,
                with_payload=True
            )
            
            if search_result[0]:
                point = search_result[0][0]
                # Update payload with form metadata
                updated_payload = point.payload.copy()
                updated_payload.update(metadata)
                
                client.upsert(
                    collection_name=SPECIAL_COLLECTION,
                    points=[{
                        "id": point.id,
                        "vector": point.vector,
                        "payload": updated_payload
                    }]
                )
            
            print(f"✅ Form submission ingested: {chunks} chunks")
            return {"status": "ingested", "chunks": chunks}
        else:
            print(f"❌ Failed to ingest form submission")
            return {"status": "failed", "reason": "no_chunks"}
            
    except Exception as e:
        print(f"❌ Error ingesting form submission: {e}")
        return {"status": "error", "reason": str(e)}
    

    