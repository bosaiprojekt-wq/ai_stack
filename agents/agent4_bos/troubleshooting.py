import os
from pathlib import Path
import uuid
import requests
import time

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

# ===== DEBUGGING =====
def debug_system():
    """Debug the entire system"""
    print("\n" + "="*50)
    print("🔧 SYSTEM DEBUG INFO")
    print("="*50)
    
    # Check environment
    print(f"OLLAMA_URL: {OLLAMA_URL}")
    print(f"EMBED_MODEL: {EMBED_MODEL}")
    
    # Test Ollama connection
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        print(f"✓ Ollama connection: OK (Status: {response.status_code})")
    except Exception as e:
        print(f"✗ Ollama connection failed: {e}")
    
    # Test Qdrant connection
    try:
        collections = client.get_collections()
        print(f"✓ Qdrant connection: OK")
        print(f"  Available collections: {[c.name for c in collections.collections]}")
    except Exception as e:
        print(f"✗ Qdrant connection failed: {e}")
    
    # Check folders
    print(f"\n📁 Folder check:")
    for path, name in [(DOCS_PATH, "DOCS_PATH"), (SPECIAL_PATH, "SPECIAL_PATH")]:
        p = Path(path)
        if p.exists():
            files = list(p.glob("*"))
            print(f"  {name}: {len(files)} files in {path}")
        else:
            print(f"  {name}: DOES NOT EXIST at {path}")

# ===== CORE FUNCTIONS =====
def embed(text):
    """Generate embedding using Ollama"""
    if isinstance(text, str):
        inputs = [text]
    else:
        inputs = text

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embed",
            json={"model": EMBED_MODEL, "input": inputs},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        embeddings = data.get("embeddings")
        if not embeddings:
            raise ValueError("No embeddings in response")
        return embeddings[0] if isinstance(embeddings, list) else embeddings
    except Exception as e:
        print(f"❌ Embedding failed: {e}")
        raise

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
                        "vector": {"default": vector},
                        "payload": {
                            "file_name": file_path.name,
                            "page": page_num,
                            "chunk_index": chunk_idx,
                            "text": chunk
                        }
                    }]
                )
                total_chunks += 1
                
                # Print progress every 10 chunks
                if total_chunks % 10 == 0:
                    print(f"  Processed {total_chunks} chunks...")
                
            except Exception as e:
                print(f"❌ Error in chunk {chunk_idx}: {str(e)}")
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
    
    for file_idx, file_path in enumerate(files, 1):
        print(f"\n[{file_idx}/{len(files)}] Processing: {file_path.name}")
        chunks = ingest_single_file(file_path, collection)
        if chunks > 0:
            total_files += 1
            total_chunks += chunks
    
    print(f"\n📊 Ingested {total_files} files, {total_chunks} chunks from {folder_path}")
    return total_files

def test_single_chunk(file_path: Path, collection: str):
    """Test ingest with a single chunk first"""
    print(f"\n🧪 Testing with file: {file_path.name}")
    
    # Load just first page
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        pages = load_pdf(file_path)
    elif suffix == ".txt":
        pages = load_txt(file_path)
    elif suffix == ".docx":
        pages = load_docx(file_path)
    else:
        print(f"  Unsupported file type: {suffix}")
        return 0
    
    if not pages:
        print("  No content found")
        return 0
    
    # Use first chunk only for testing
    chunks = chunk_text(pages[0])
    if not chunks:
        print("  No chunks generated")
        return 0
    
    test_chunk = chunks[0][:500]  # First 500 chars
    print(f"  Test chunk preview: {test_chunk[:100]}...")
    
    try:
        # Generate embedding
        print("  Generating embedding...")
        vector = embed(test_chunk)
        print(f"  Vector generated, length: {len(vector)}")
        
        # Try named vector format
        test_id = str(uuid.uuid4())
        
        print("  Uploading to Qdrant...")
        point = {
            "id": test_id,
            "vector": {"default": vector},
            "payload": {
                "file_name": file_path.name,
                "text": test_chunk,
                "test": True
            }
        }
        
        result = client.upsert(
            collection_name=collection,
            points=[point],
            wait=True
        )
        print(f"  ✓ Test upload succeeded!")
        
        # Verify the point was added
        time.sleep(1)
        collection_info = client.get_collection(collection)
        print(f"  Collection now has: {collection_info.points_count} points")
        
        return 1
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        # Try to get more details about the error
        try:
            # Check collection configuration
            coll_info = client.get_collection(collection)
            print(f"  Collection config: {coll_info.config.params.vectors}")
        except:
            pass
        return 0

# ===== MAIN EXECUTION =====
if __name__ == "__main__":
    print("🚀 Starting ingest process...")
    
    # First, debug the system
    debug_system()
    
    # Test with a single file first
    print("\n" + "="*50)
    print("🧪 Running test ingestion...")
    
    # Find any file to test with
    test_folder = Path(DOCS_PATH)
    test_passed = False
    
    if test_folder.exists():
        test_files = list(test_folder.glob("*"))
        if test_files:
            test_file = test_files[0]
            print(f"Testing with: {test_file.name}")
            test_result = test_single_chunk(test_file, DOCS_COLLECTION)
            
            if test_result > 0:
                print("\n✅ Test successful! Proceeding with full ingestion...")
                test_passed = True
            else:
                print("\n❌ Test failed. Cannot proceed with full ingestion.")
                print("Please check the errors above and fix them first.")
        else:
            print(f"No files found in {DOCS_PATH} to test with")
    else:
        print(f"Test folder not found: {DOCS_PATH}")
    
    # Only proceed if test passed
    if test_passed:
        print("\n" + "="*50)
        print("📚 Ingesting official documents...")
        docs_count = ingest_folder(DOCS_PATH, DOCS_COLLECTION)
        
        print("\n" + "="*50)
        print("⭐ Ingesting special cases...")
        special_count = ingest_folder(SPECIAL_PATH, SPECIAL_COLLECTION)
        
        # Summary
        print("\n" + "="*50)
        print("📊 INGEST SUMMARY:")
        print(f"  Documents: {docs_count} files")
        print(f"  Special cases: {special_count} files")
        
        # Verify final counts
        try:
            docs_info = client.get_collection(DOCS_COLLECTION)
            special_info = client.get_collection(SPECIAL_COLLECTION)
            print(f"\n📈 Qdrant stats:")
            print(f"  {DOCS_COLLECTION}: {docs_info.points_count} points")
            print(f"  {SPECIAL_COLLECTION}: {special_info.points_count} points")
        except Exception as e:
            print(f"⚠️ Could not verify final counts: {e}")
        
        print("✅ Ingest complete!")
    else:
        print("\n🚫 Ingest process stopped due to test failure.")
        print("Please fix the issues shown above and try again.")