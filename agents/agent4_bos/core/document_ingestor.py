#imports
import os
import time
from pathlib import Path
from typing import List, Dict, Any
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

#dependency imports
from .config import KNOWLEDGE_BASE_PATH, SPECIAL_CASES_PATH
from .document_processor import document_processor
from .qdrant_service import qdrant_service


#class: DocumentIngestor - handles document ingestion from folders, processing, and saving to Qdrant
class DocumentIngestor:
    def __init__(self):
        self.processed_files = {}
    
    #method: ingest knowledge base documents
    def ingest_knowledge_base(self, force_reingest: bool = False) -> Dict[str, Any]:
        """Ingest all documents from knowledge_base folder"""
        return self._ingest_folder(KNOWLEDGE_BASE_PATH, "knowledge_base", force_reingest)
    
    #method: ingest special cases documents
    def ingest_special_cases(self, force_reingest: bool = False) -> Dict[str, Any]:
        """Ingest all documents from special_cases folder (form responses)"""
        return self._ingest_folder(SPECIAL_CASES_PATH, "special_cases", force_reingest)
    
    #method: ingest all documents from both folders
    def ingest_all(self, force_reingest: bool = False) -> Dict[str, Any]:
        """Ingest from both folders"""
        kb_result = self.ingest_knowledge_base(force_reingest)
        sc_result = self.ingest_special_cases(force_reingest)
        
        return {
            "knowledge_base": kb_result,
            "special_cases": sc_result,
            "total": {
                "files": kb_result["stats"]["processed_files"] + sc_result["stats"]["processed_files"],
                "chunks": kb_result["stats"]["total_chunks"] + sc_result["stats"]["total_chunks"]
            }
        }
    
    #method: ingest all documents from a folder
    def _ingest_folder(self, folder_path: str, collection: str, force_reingest: bool = False) -> Dict[str, Any]:
        """Ingest all documents from a folder"""
        folder = Path(folder_path)
        
        if not folder.exists():
            return {
                "status": "error",
                "message": f"Folder does not exist: {folder_path}",
                "stats": {
                    "total_files": 0,
                    "processed_files": 0,
                    "skipped_files": 0,
                    "total_chunks": 0,
                    "errors": []
                }
            }
        
        stats = {
            "total_files": 0,
            "processed_files": 0,
            "skipped_files": 0,
            "total_chunks": 0,
            "errors": []
        }
        
        # Supported file extensions
        extensions = {'.docx', '.pdf', '.txt'}
        
        print(f"  Scanning {folder_path}...")
        
        for file_path in folder.rglob('*'):
            if file_path.suffix.lower() in extensions and file_path.is_file():
                stats["total_files"] += 1
                
                try:
                    # Check if file needs processing
                    if not force_reingest and self._should_skip(file_path):
                        stats["skipped_files"] += 1
                        continue
                    
                    # Process file
                    print(f"    Processing: {file_path.name}")
                    chunks = document_processor.process_file(str(file_path))
                    
                    # Save each chunk to Qdrant
                    for chunk in chunks:
                        qdrant_service.save_document_chunk(chunk, collection)
                        stats["total_chunks"] += 1
                    
                    # Mark as processed
                    self.processed_files[str(file_path)] = {
                        "last_modified": file_path.stat().st_mtime,
                        "file_hash": chunk["metadata"]["file_hash"] if chunks else "unknown",
                        "chunks": len(chunks),
                        "ingestion_time": time.time()
                    }
                    
                    stats["processed_files"] += 1
                    
                except Exception as e:
                    error_msg = f"Error processing {file_path.name}: {str(e)}"
                    stats["errors"].append(error_msg)
                    print(f"    ✗ {error_msg}")
        
        return {
            "status": "success",
            "collection": collection,
            "folder": str(folder),
            "stats": stats
        }
    
    #method: check if file should be skipped (already processed and not modified)
    def _should_skip(self, file_path: Path) -> bool:
        """Check if file should be skipped (already processed and not modified)"""
        file_str = str(file_path)
        
        if file_str not in self.processed_files:
            return False
        
        file_info = self.processed_files[file_str]
        current_mtime = file_path.stat().st_mtime
        
        # Check if file was modified since last ingestion
        return current_mtime <= file_info["last_modified"]


#class: FileWatcher - watches folders for new or modified files and triggers ingestion
class FileWatcher(FileSystemEventHandler):
    def __init__(self, ingestor: DocumentIngestor):
        self.ingestor = ingestor
    
    #method: handle file creation event
    def on_created(self, event):
        if not event.is_directory:
            self._process_file(event.src_path)
    
    #method: handle file modification event
    def on_modified(self, event):
        if not event.is_directory:
            self._process_file(event.src_path)
    
    #method: process a single file when created or modified
    def _process_file(self, file_path: str):
        """Process a single file when created or modified"""
        file_path_obj = Path(file_path)
        
        # Determine collection based on path
        if str(KNOWLEDGE_BASE_PATH) in file_path:
            collection = "knowledge_base"
            folder_name = "knowledge_base"
        elif str(SPECIAL_CASES_PATH) in file_path:
            collection = "special_cases"
            folder_name = "special_cases"
        else:
            return
        
        # Check file extension
        if file_path_obj.suffix.lower() not in {'.docx', '.pdf', '.txt'}:
            return
        
        try:
            print(f"\nAuto-detected new/modified file in {folder_name}:")
            print(f"   File: {file_path_obj.name}")
            
            chunks = document_processor.process_file(file_path)
            
            for chunk in chunks:
                qdrant_service.save_document_chunk(chunk, collection)
            
            print(f"Auto-ingested: {len(chunks)} chunks")
            
        except Exception as e:
            print(f"Auto-ingestion failed: {e}")

#function: start file watcher to monitor folders for changes
def start_file_watcher():
    # Launch a filesystem observer
    """Start watching folders for changes"""
    ingestor = DocumentIngestor()
    event_handler = FileWatcher(ingestor)
    observer = Observer()
    
    # Watch both folders
    folders_to_watch = []
    for folder, name in [(KNOWLEDGE_BASE_PATH, "knowledge_base"), (SPECIAL_CASES_PATH, "special_cases")]:
        if os.path.exists(folder):
            observer.schedule(event_handler, folder, recursive=True)
            folders_to_watch.append(name)
            print(f"   Watching: {folder}")
    
    if not folders_to_watch:
        print("   No folders to watch!")
        return
    
    observer.start()
    print(f"   ✓ File watcher started for: {', '.join(folders_to_watch)}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()

# Singleton instance
document_ingestor = DocumentIngestor()