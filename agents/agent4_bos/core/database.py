# core/database.py - JSON database handler
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any

class JSONDatabase:
    def __init__(self, folder_path: str = "./json_database_handling/json_folder"):
        self.folder = Path(folder_path)
        if not self.folder.exists():
            self.folder.mkdir(parents=True, exist_ok=True)
    
    def save_case(self, title: str, author: str, description: str, 
                  solution: str, notes: str = "") -> Dict[str, Any]:
        """Save a new case to the database"""
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
        
        file_path = self.folder / f"{case_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return {
            "status": "success",
            "case_id": case_id,
            "data": data,
            "file_path": str(file_path)
        }
    
    def list_cases(self) -> List[Dict[str, Any]]:
        """List all cases in the database"""
        cases = []
        for file in self.folder.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
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
    
    def get_all_cases(self) -> List[Dict[str, Any]]:
        """Get all cases with full data"""
        cases = []
        for file in self.folder.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    cases.append(json.load(f))
            except Exception:
                continue
        return cases
    
    def get_case_count(self) -> int:
        """Get number of cases in database"""
        return len(list(self.folder.glob("*.json")))

# Singleton instance
db = JSONDatabase()