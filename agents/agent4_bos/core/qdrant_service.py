from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid  # ADD THIS
import json
from typing import List, Dict, Any, Optional
from .config import COLLECTION_NAME

class QdrantService:
    def __init__(self, host="qdrant", port=6333):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = COLLECTION_NAME or "agent4_bos_cases"
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
                print(f"Created collection: {self.collection_name}")
            else:
                # Check if collection needs to be recreated
                collection_info = self.client.get_collection(self.collection_name)
                # If it has named vectors, recreate it
                vectors_config = collection_info.config.params.vectors
                if hasattr(vectors_config, 'vector'):  # Named vectors detected
                    print(f"Recreating collection {self.collection_name} with plain vectors...")
                    self.client.delete_collection(collection_name=self.collection_name)
                    self.client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                    )
                    print(f"Recreated collection: {self.collection_name}")
                    
        except Exception as e:
            print(f"Error ensuring collection: {e}")
            # If collection exists with wrong config, try to recreate
            try:
                self.client.delete_collection(collection_name=self.collection_name)
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
                print(f"Recreated collection after error: {self.collection_name}")
            except Exception as e2:
                print(f"Failed to recreate collection: {e2}")
                pass
    
    def save_case(self, case_data: Dict[str, Any], point_id: Optional[str] = None) -> str:
        """Save a case to Qdrant"""
        # Generate UUID if not provided
        if point_id is None:
            point_id = str(uuid.uuid4())
        
        # Store as JSON in payload
        point = PointStruct(
            id=point_id,  # Must be UUID or integer
            vector=[0.0] * 384,  # Dummy vector
            payload=case_data
        )
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
        
        return point_id
    
    def get_all_cases(self) -> List[Dict[str, Any]]:
        """Get all cases from Qdrant"""
        try:
            points = self.client.scroll(
                collection_name=self.collection_name,
                limit=10000,
                with_payload=True
            )[0]
            
            cases = []
            for point in points:
                if point.payload:
                    cases.append(dict(point.payload))
            return cases
        except Exception as e:
            print(f"Error getting cases: {e}")
            return []
    
    
    def get_case_count(self) -> int:
        """Get total number of cases"""
        try:
            count = self.client.count(
                collection_name=self.collection_name
            ).count
            return count
        except:
            return 0
    
    def search_cases(self, query: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        """Search cases (simple metadata search for now)"""
        all_cases = self.get_all_cases()
        
        if not query:
            return all_cases[:limit]
        
        # Simple text search in title and description
        query_lower = query.lower()
        results = []
        for case in all_cases:
            title = case.get("title", "").lower()
            description = case.get("description", "").lower()
            
            if (query_lower in title) or (query_lower in description):
                results.append(case)
        
        return results[:limit]
    
    def delete_case(self, case_id: str) -> bool:
        """Delete a case by ID"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[case_id]
            )
            return True
        except:
            return False

# --- Module-level helper functions (migrated from file_utils.py) ---

def load_all_cases() -> List[Dict[str, Any]]:
    """Load all cases from Qdrant (compat wrapper)."""
    return qdrant_service.get_all_cases()


def save_case(title: str, author: str, description: str, solution: str, notes: str = "") -> Dict[str, Any]:
    """Save a new case to Qdrant (compat wrapper moved from file_utils)."""
    import datetime
    # Generate human-readable case_id
    case_id = f"SP-{int(datetime.datetime.now().timestamp())}"

    data = {
        "case_id": case_id,
        "title": title,
        "author": author,
        "description": description,
        "solution": solution,
        "additional_notes": notes,
        "created_at": datetime.datetime.now().isoformat()
    }

    try:
        saved_case_id = qdrant_service.save_case(data)
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to save case to Qdrant",
            "details": str(e)
        }

    return {
        "status": "success",
        "case_id": saved_case_id,
        "data": data,
        "storage": "qdrant"
    }


def list_cases_summary() -> List[Dict[str, Any]]:
    """List all cases with summary info (compat wrapper)."""
    cases = []
    for case in qdrant_service.get_all_cases():
        cases.append({
            "case_id": case.get("case_id"),
            "title": case.get("title"),
            "author": case.get("author"),
            "created_at": case.get("created_at")
        })
    return cases


def get_case_count() -> int:
    """Get number of cases in database (compat wrapper)."""
    return qdrant_service.get_case_count()


def get_database_info() -> Dict[str, Any]:
    """Get database information (compat wrapper)."""
    from .config import QDRANT_HOST, QDRANT_PORT, COLLECTION_NAME

    return {
        "storage": "qdrant",
        "collection": COLLECTION_NAME,
        "case_count": get_case_count(),
        "qdrant_host": QDRANT_HOST,
        "qdrant_port": QDRANT_PORT,
        "note": "JSON folder is ignored, using Qdrant only"
    }


def list_json_files() -> List[Dict[str, Any]]:
    """For compatibility - returns Qdrant cases as 'files'"""
    import datetime
    cases = []
    for case in qdrant_service.get_all_cases():
        case_id = case.get('case_id', 'unknown')
        cases.append({
            "filename": f"{case_id}.json",
            "size": len(str(case).encode('utf-8')),
            "modified": datetime.datetime.now().timestamp(),
            "path": f"qdrant://{qdrant_service.collection_name}/{case_id}",
            "storage": "qdrant"
        })
    return cases


def get_first_file() -> Dict[str, Any]:
    """For compatibility - returns first Qdrant case"""
    cases = qdrant_service.get_all_cases()
    if not cases:
        raise FileNotFoundError("No cases found in Qdrant")
    first_case = cases[0]
    return {
        "filename": f"{first_case.get('case_id', 'unknown')}.json",
        "content": first_case,
        "storage": "qdrant"
    }


# Singleton instance
qdrant_service = QdrantService()