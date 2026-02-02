from typing import List, Dict, Any
import datetime
from .qdrant_service import qdrant_service

def load_all_cases() -> List[Dict[str, Any]]:
    """Load all cases from Qdrant"""
    return qdrant_service.get_all_cases()

def save_case(title: str, author: str, description: str, solution: str, notes: str = "") -> Dict[str, Any]:
    """Save a new case to Qdrant"""
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
    
    # Save to Qdrant
    saved_case_id = qdrant_service.save_case(data)
    
    return {
        "status": "success",
        "case_id": saved_case_id,
        "data": data,
        "storage": "qdrant"
        # NO file_path here!
    }

def list_cases_summary() -> List[Dict[str, Any]]:
    """List all cases with summary info"""
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
    """Get number of cases in database"""
    return qdrant_service.get_case_count()

def get_database_info() -> Dict[str, Any]:
    """Get database information"""
    from .config import QDRANT_HOST, QDRANT_PORT, COLLECTION_NAME
    
    return {
        "storage": "qdrant",
        "collection": COLLECTION_NAME,
        "case_count": get_case_count(),
        "qdrant_host": QDRANT_HOST,
        "qdrant_port": QDRANT_PORT,
        "note": "JSON folder is ignored, using Qdrant only"
    }

# Remove or keep these for compatibility (they'll return Qdrant data)
def list_json_files() -> List[Dict[str, Any]]:
    """For compatibility - returns Qdrant cases as 'files'"""
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