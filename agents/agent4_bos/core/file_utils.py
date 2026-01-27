import json
from typing import List, Dict, Any
from .config import JSON_FOLDER, JSON_FOLDER_PATH

def load_all_cases() -> List[Dict[str, Any]]:
    """Load all JSON cases from the folder."""
    cases = []
    for file_path in JSON_FOLDER.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                cases.append(json.load(f))
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load {file_path.name}: {e}")
    return cases

def list_json_files() -> List[Dict[str, Any]]:
    """List all JSON files with metadata."""
    files = []
    for file_path in JSON_FOLDER.glob("*.json"):
        files.append({
            "filename": file_path.name,
            "size": file_path.stat().st_size,
            "modified": file_path.stat().st_mtime,
            "path": str(file_path.absolute())
        })
    return files

def get_first_file() -> Dict[str, Any]:
    """Get the first JSON file alphabetically."""
    json_files = sorted(JSON_FOLDER.glob("*.json"))
    if not json_files:
        raise FileNotFoundError("No JSON files found")
    
    first_file = json_files[0]
    with open(first_file, "r", encoding="utf-8") as f:
        return {
            "filename": first_file.name,
            "content": json.load(f)
        }

def save_case(title: str, author: str, description: str, solution: str, notes: str = "") -> Dict[str, Any]:
    """Save a new case to the database"""
    import datetime
    
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
    
    file_path = JSON_FOLDER / f"{case_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return {
        "status": "success",
        "case_id": case_id,
        "data": data,
        "file_path": str(file_path)
    }

def list_cases_summary() -> List[Dict[str, Any]]:
    """List all cases with summary info"""
    cases = []
    for file_path in JSON_FOLDER.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                case_data = json.load(f)
                cases.append({
                    "case_id": case_data.get("case_id"),
                    "title": case_data.get("title"),
                    "author": case_data.get("author"),
                    "created_at": case_data.get("created_at")
                })
        except Exception:
            continue
    return cases

def get_case_count() -> int:
    """Get number of cases in database"""
    return len(list(JSON_FOLDER.glob("*.json")))

def get_database_info() -> Dict[str, Any]:
    """Get database information"""
    return {
        "folder_path": JSON_FOLDER_PATH,
        "case_count": get_case_count(),
        "exists": JSON_FOLDER.exists(),
        "is_dir": JSON_FOLDER.is_dir()
    }