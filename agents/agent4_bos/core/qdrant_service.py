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
        except Exception as e:
            print(f"Error ensuring collection: {e}")
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

# Singleton instance
qdrant_service = QdrantService()