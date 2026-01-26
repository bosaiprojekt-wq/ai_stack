import json
from typing import List, Dict, Any
from .config import JSON_FOLDER

#case data loader - Loads all case files from the JSON folder into memory
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

#COLLECTOR: Gets information about all case files; get filename, zize, modification timestaWmp, full path; for testing purposes ("does it see the files at all?")
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

#get first alfabetical file - for testing file reading purposes ("Can it read the files' content?")
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