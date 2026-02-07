import uvicorn
from app import app
import threading
import time
import os

# Run the full ingestion pipeline once at startup (knowledge base + special cases)
def run_startup_ingestion():
    """Run ingestion of both knowledge base and special cases on startup"""
    try:
        print("=" * 60)
        print("STARTUP: CLEAN & FRESH INGESTION")
        print("=" * 60)
        
        # Import here to avoid circular imports
        from core.document_ingestor import document_ingestor
        from core.qdrant_service import qdrant_service
        
        # 1. Clear collection CONTENTS (keeping structure)
        print("\nStep 1: Clearing collection CONTENTS (keeping structure)...")
        qdrant_service.clear_all_collections(delete_structure=False)
        
        # 2. Check if folders exist
        from core.config import KNOWLEDGE_BASE_PATH, SPECIAL_CASES_PATH
        
        print(f"\nStep 2: Checking data paths...")
        print(f"Knowledge base: {KNOWLEDGE_BASE_PATH} - Exists: {os.path.exists(KNOWLEDGE_BASE_PATH)}")
        print(f"Special cases: {SPECIAL_CASES_PATH} - Exists: {os.path.exists(SPECIAL_CASES_PATH)}")
        
        # 3. Perform fresh ingestion
        print("\nStep 3: Fresh ingestion...")
        
        # Ingest knowledge base
        print("\n  1. Ingesting knowledge base...")
        kb_result = document_ingestor.ingest_knowledge_base()
        print(f"     Result: {kb_result['stats']['processed_files']} files, {kb_result['stats']['total_chunks']} chunks")
        
        # Ingest special cases
        print("\n  2. Ingesting special cases...")
        sc_result = document_ingestor.ingest_special_cases()
        print(f"     Result: {sc_result['stats']['processed_files']} files, {sc_result['stats']['total_chunks']} chunks")
        
        # 4. Summary
        print("\n" + "=" * 60)
        print("CLEAN & FRESH INGESTION COMPLETE")
        print("=" * 60)
        
        total_files = kb_result['stats']['processed_files'] + sc_result['stats']['processed_files']
        total_chunks = kb_result['stats']['total_chunks'] + sc_result['stats']['total_chunks']
        
        print(f"\nFinal stats:")
        print(f"  Total files: {total_files}")
        print(f"  Total chunks: {total_chunks}")
        print(f"  Knowledge base: {kb_result['stats']['total_chunks']} chunks")
        print(f"  Special cases: {sc_result['stats']['total_chunks']} chunks")
        
        # 5. Check Qdrant
        try:
            info = qdrant_service.get_database_info()
            print("\nQdrant Collections:")
            for col_name, col_info in info['collections'].items():
                print(f"  {col_name}: {col_info['count']} documents")
        except Exception as e:
            print(f"\nCould not check Qdrant: {e}")
        
        print("\nSystem ready! No duplicates guaranteed.")
        
    except Exception as e:
        print(f"\nERROR in startup ingestion: {e}")
        import traceback
        traceback.print_exc()

# Start a background thread that watches folders and triggers auto-ingestion
def start_background_watcher():
    """Start file watcher for auto-ingestion of new files"""
    try:
        print("\nStarting file watcher for auto-ingestion...")
        from core.document_ingestor import start_file_watcher
        watcher_thread = threading.Thread(target=start_file_watcher, daemon=True)
        watcher_thread.start()
        print("File watcher started")
        return watcher_thread
    except Exception as e:
        print(f"Could not start file watcher: {e}")
        return None

if __name__ == "__main__":
    print("=" * 60)
    print("Starting Agent4 BOS RAG System")
    print("=" * 60)
    
    # Run startup ingestion in background thread
    print("\n[1] Running startup ingestion...")
    ingestion_thread = threading.Thread(target=run_startup_ingestion, daemon=True)
    ingestion_thread.start()
    
    # Start file watcher for auto-ingestion
    print("[2] Starting file watcher...")
    watcher_thread = start_background_watcher()
    
    # Give ingestion a moment to start
    time.sleep(3)
    
    print("\n[3] Starting FastAPI server...")
    print(f"Server will be available at: http://0.0.0.0:8000")
    print("=" * 60)
    
    # Start FastAPI server
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
        access_log=True
    )