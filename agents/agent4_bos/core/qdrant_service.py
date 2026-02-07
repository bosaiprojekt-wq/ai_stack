# core/qdrant_service.py - UPDATED
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
from .config import (
    QDRANT_HOST, QDRANT_PORT, 
    SPECIAL_CASES_COLLECTION, 
    KNOWLEDGE_BASE_COLLECTION,
    COLLECTION_NAME
)

class QdrantService:
    def __init__(self, host=QDRANT_HOST, port=QDRANT_PORT):
        self.client = QdrantClient(host=host, port=port)
        #self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedder = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        # self.embedder = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
        # Collections
        self.collections = {
            "special_cases": SPECIAL_CASES_COLLECTION,
            "knowledge_base": KNOWLEDGE_BASE_COLLECTION
        }
        
        self._ensure_collections()
    
    def _ensure_collections(self):
        """Create collections if they don't exist"""
        for collection_name in self.collections.values():
            try:
                collections = self.client.get_collections().collections
                collection_names = [c.name for c in collections]
                
                if collection_name not in collection_names:
                    self.client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                    )
                    print(f"Created collection: {collection_name}")
            except Exception as e:
                print(f"Error ensuring collection {collection_name}: {e}")
    
    def clear_all_collections(self, delete_structure: bool = False):
        """
        Clear collections.
        
        Args:
            delete_structure: If True, deletes and recreates collections
                             If False (default), only clears content
        """
        print("=" * 60)
        if delete_structure:
            print("DELETING AND RECREATING COLLECTIONS")
        else:
            print("CLEARING COLLECTION CONTENTS (keeping structure)")
        print("=" * 60)
        
        for collection_key, collection_name in self.collections.items():
            try:
                if delete_structure:
                    # Delete and recreate collections
                    self.client.delete_collection(collection_name)
                    self.client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                    )
                    print(f"  Recreated: {collection_name}")
                else:
                    # Only clear content
                    self.client.delete(
                        collection_name=collection_name,
                        points_selector=Filter(must=[])  # empty filter = everything
                    )
                    print(f"Cleared: {collection_name} (structure kept)")
                    
            except Exception as e:
                print(f"  Error with {collection_name}: {e}")
        
        print("Operation completed")
    
    def clear_collection_contents(self, collection: str):
        """Clear only contents of a collection (keep structure)"""
        collection_name = self.collections.get(collection)
        if not collection_name:
            print(f"Collection {collection} not found")
            return False
        
        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=Filter(must=[])
            )
            print(f"Cleared contents of {collection_name} (structure preserved)")
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def search_all_in_category(self, query: str, category: str, collection: str = "knowledge_base") -> List[Dict[str, Any]]:
        """
        Search ALL documents in a specific category (no limit)
        """
        from qdrant_client.models import FieldCondition, MatchValue
        
        # Generate query embedding
        query_embedding = self.embedder.encode(query).tolist()
        
        collection_name = self.collections.get(collection)
        if not collection_name:
            return []
        
        # Build filter for category
        search_filter = Filter(
            must=[
                FieldCondition(
                    key="metadata.category",
                    match=MatchValue(value=category)
                )
            ]
        )
        
        try:
            # First, get count to know how many to retrieve
            count_result = self.client.count(
                collection_name=collection_name,
                count_filter=search_filter
            )
            
            total_in_category = count_result.count
            print(f"DEBUG: Found {total_in_category} documents in category '{category}'")
            
            if total_in_category == 0:
                return []
            
            # Get ALL documents from this category
            search_results = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=total_in_category  # Get ALL documents in category
            )
            
            # Format results
            results = []
            for result in search_results:
                result_data = {
                    "score": result.score,
                    "text": result.payload.get("text", ""),
                    "metadata": result.payload.get("metadata", {}),
                    "collection": collection,
                    "source": collection_name,
                    "payload": result.payload
                }
                results.append(result_data)
            
            print(f"DEBUG: Retrieved {len(results)} documents after search")
            return results
            
        except Exception as e:
            print(f"Error searching all in category {category}: {e}")
            return []
    
    def save_case(self, case_data: Dict[str, Any], collection: str = "special_cases") -> Dict[str, Any]:
        """Save a case to Qdrant with duplicate prevention"""
        try:
            collection_name = self.collections.get(collection, SPECIAL_CASES_COLLECTION)
            
            # Generate unique content hash
            import hashlib
            content_to_hash = f"{case_data.get('title', '')}_{case_data.get('description', '')}_{case_data.get('solution', '')}"
            content_hash = hashlib.md5(content_to_hash.encode()).hexdigest()
            
            print(f"🔍 Checking for duplicates (hash: {content_hash[:8]})...")
            
            # Check if similar case already exists
            try:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                
                # Search for cases with similar content
                similar_cases = self.client.search(
                    collection_name=collection_name,
                    query_vector=self.embedder.encode(content_to_hash).tolist(),
                    limit=3,
                    query_filter=Filter(
                        should=[
                            FieldCondition(
                                key="title",
                                match=MatchValue(value=case_data.get('title', ''))
                            )
                        ]
                    )
                )
                
                if similar_cases:
                    best_match = similar_cases[0]
                    similarity = best_match.score * 100
                    
                    if similarity > 85:  # High similarity threshold
                        print(f"⏭️ Similar case already exists: {best_match.payload.get('title', 'unknown')} ({similarity:.1f}% match)")
                        return {
                            "status": "duplicate",
                            "case_id": best_match.payload.get('case_id', 'unknown'),
                            "similarity": similarity,
                            "message": f"Podobny przypadek już istnieje (podobieństwo: {similarity:.1f}%)"
                        }
                        
            except Exception as e:
                print(f"⚠️ Duplicate check failed: {e}")
            
            # Generate text for embedding
            text_for_embedding = f"{case_data.get('title', '')} {case_data.get('description', '')} {case_data.get('solution', '')}"
            
            # Generate embedding
            embedding = self.embedder.encode(text_for_embedding).tolist()
            
            # Generate ID
            import uuid
            point_id = str(uuid.uuid4())
            
            # Create case ID
            import datetime
            case_id = f"CASE-{datetime.datetime.now().strftime('%Y%m%d')}-{point_id[:8]}"
            
            # Prepare payload
            payload = {
                "case_id": case_id,
                "title": case_data.get('title', ''),
                "author": case_data.get('author', ''),
                "description": case_data.get('description', ''),
                "solution": case_data.get('solution', ''),
                "additional_notes": case_data.get('notes', ''),
                "created_at": datetime.datetime.now().isoformat(),
                "content_hash": content_hash,
                "type": "special_case",
                "source": "web_form",
                "collection": collection
            }
            
            # Create point
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload
            )
            
            # Save to Qdrant
            self.client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            
            print(f"✅ Case saved to Qdrant: {case_id}")
            print(f"   Title: {case_data.get('title', '')[:50]}...")
            print(f"   Content hash: {content_hash[:8]}")
            
            return {
                "status": "success",
                "case_id": case_id,
                "point_id": point_id,
                "content_hash": content_hash,
                "message": "Przypadek zapisany w Qdrant"
            }
            
        except Exception as e:
            print(f"❌ Error saving case to Qdrant: {e}")
            return {
                "status": "error",
                "message": f"Błąd zapisu do Qdrant: {str(e)}"
            }
        
    def save_document_chunk(self, chunk_data: Dict[str, Any], collection: str = "knowledge_base"):
        """Save a document chunk to Qdrant"""
        collection_name = self.collections.get(collection, KNOWLEDGE_BASE_COLLECTION)
        
        # Ensure ID is a string (UUIDs are already strings)
        point_id = str(chunk_data["id"])
        
        # Generate embedding
        embedding = self.embedder.encode(chunk_data["text"]).tolist()
        
        # Create point
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload=chunk_data
        )
        
        # Save to Qdrant
        self.client.upsert(
            collection_name=collection_name,
            points=[point]
        )
        
        return point_id
    
    def search(self, query: str, collection: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search across one or all collections
        If collection is None, searches both collections
        """
        # Generate query embedding
        query_embedding = self.embedder.encode(query).tolist()
        
        results = []
        
        if collection is None:
            # Search both collections
            collections_to_search = list(self.collections.values())
        else:
            # Search specific collection
            collections_to_search = [self.collections.get(collection)]
        
        for collection_name in collections_to_search:
            try:
                search_results = self.client.search(
                    collection_name=collection_name,
                    query_vector=query_embedding,
                    limit=limit
                )
                
                for result in search_results:
                    result_data = {
                        "score": result.score,
                        "text": result.payload.get("text", ""),
                        "metadata": result.payload.get("metadata", {}),
                        "collection": collection,
                        "source": collection_name,
                        "payload": result.payload
                    }
                    results.append(result_data)
            except Exception as e:
                print(f"Error searching collection {collection_name}: {e}")
        
        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
    
    def search_with_filter(self, query: str, category: str = None, collection: str = "knowledge_base", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search with category filter
        """
        from qdrant_client.models import FieldCondition, MatchValue
        
        # Generate query embedding
        query_embedding = self.embedder.encode(query).tolist()
        
        collection_name = self.collections.get(collection)
        if not collection_name:
            return []
        
        # Build filter if category is provided
        search_filter = None
        if category and category != "all":
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="metadata.category",  # Path to category in metadata
                        match=MatchValue(value=category)
                    )
                ]
            )
        
        try:
            # Search WITH filter
            search_results = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                query_filter=search_filter,  # THIS IS THE KEY - add filter here
                limit=limit * 2  # Get more results for confidence filtering
            )
            
            # Format results
            results = []
            for result in search_results:
                result_data = {
                    "score": result.score,
                    "text": result.payload.get("text", ""),
                    "metadata": result.payload.get("metadata", {}),
                    "collection": collection,
                    "source": collection_name,
                    "payload": result.payload
                }
                results.append(result_data)
            
            return results
            
        except Exception as e:
            print(f"Error searching collection {collection_name} with filter: {e}")
            return []
    
    def get_all_cases(self) -> List[Dict[str, Any]]:
        """Get all cases from special_cases collection (for backward compatibility)"""
        return self._get_all_from_collection("special_cases")
    
    def _get_all_from_collection(self, collection: str) -> List[Dict[str, Any]]:
        """Get all documents from a collection"""
        collection_name = self.collections.get(collection)
        if not collection_name:
            return []
        
        try:
            points = self.client.scroll(
                collection_name=collection_name,
                limit=10000,
                with_payload=True
            )[0]
            
            documents = []
            for point in points:
                if point.payload:
                    documents.append(dict(point.payload))
            return documents
        except Exception as e:
            print(f"Error getting documents from {collection_name}: {e}")
            return []
    
    def get_case_count(self) -> int:
        """Get total number of cases in special_cases (for backward compatibility)"""
        return self._get_collection_count("special_cases")
    
    def _get_collection_count(self, collection: str) -> int:
        """Get document count in a collection"""
        collection_name = self.collections.get(collection)
        if not collection_name:
            return 0
        
        try:
            count = self.client.count(
                collection_name=collection_name
            ).count
            return count
        except:
            return 0
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get comprehensive database information"""
        return {
            "storage": "qdrant",
            "collections": {
                "special_cases": {
                    "name": SPECIAL_CASES_COLLECTION,
                    "count": self._get_collection_count("special_cases")
                },
                "knowledge_base": {
                    "name": KNOWLEDGE_BASE_COLLECTION,
                    "count": self._get_collection_count("knowledge_base")
                }
            },
            "qdrant_host": QDRANT_HOST,
            "qdrant_port": QDRANT_PORT
        }

# Update the compatibility functions to use the new service

# Singleton instance
qdrant_service = QdrantService()

# Compatibility functions (keep for backward compatibility)
def load_all_cases() -> List[Dict[str, Any]]:
    return qdrant_service.get_all_cases()

def save_case(title: str, author: str, description: str, solution: str, notes: str = "") -> Dict[str, Any]:
    import datetime
    
    case_id = f"SP-{int(datetime.datetime.now().timestamp())}"
    
    data = {
        "case_id": case_id,
        "title": title,
        "author": author,
        "description": description,
        "solution": solution,
        "additional_notes": notes,
        "created_at": datetime.datetime.now().isoformat(),
        "type": "special_case"
    }

    try:
        saved_case_id = qdrant_service.save_case(data, collection="special_cases")
        return {
            "status": "success",
            "case_id": saved_case_id,
            "data": data,
            "storage": "qdrant"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to save case to Qdrant",
            "details": str(e)
        }

def list_cases_summary() -> List[Dict[str, Any]]:
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
    return qdrant_service.get_case_count()

def get_database_info() -> Dict[str, Any]:
    return qdrant_service.get_database_info()

# Remove or update these functions as they're no longer needed for JSON files
def list_json_files() -> List[Dict[str, Any]]:
    """For compatibility - returns empty list"""
    return []

def get_first_file() -> Dict[str, Any]:
    """For compatibility - returns first case"""
    cases = qdrant_service.get_all_cases()
    if not cases:
        raise FileNotFoundError("No cases found in Qdrant")
    first_case = cases[0]
    return {
        "filename": f"{first_case.get('case_id', 'unknown')}.json",
        "content": first_case,
        "storage": "qdrant"
    }