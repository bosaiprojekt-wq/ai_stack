from fastapi import HTTPException
from core.support_agent import search_similar_case
from core.file_utils import load_all_cases, get_case_count
from core.config import JSON_FOLDER_PATH

async def handle_support_request(query: str) -> dict:
    """Handle /support endpoint request"""
    query = query.strip()
    if not query:
        raise HTTPException(400, "Empty query")
    
    # Get cases from database
    cases = load_all_cases()
    
    if not cases:
        return {
            "message": "Baza przypadków jest pusta. Dodaj przypadki przez formularz.",
            "cases_count": 0,
            "form_url": "/form",
            "database_path": JSON_FOLDER_PATH
        }
    

    try:
        result = search_similar_case(query)
        
        # Format response to match existing API structure
        if result.get("found"):
            return {
                "message": result.get("response", ""),
                "found": True,
                "confidence": 95,
                "search_query": query,
                "cases_searched": len(cases),
                "database_path": JSON_FOLDER_PATH,
                "source": "core_support_agent"
            }
        else:
            return {
                "message": result.get("response", "Nie znaleziono podobnego przypadku"),
                "found": False,
                "search_query": query,
                "cases_searched": len(cases),
                "database_path": JSON_FOLDER_PATH,
                "source": "core_support_agent"
            }
            
    except Exception as e:
        return {
            "message": "Wystąpił błąd podczas generowania odpowiedzi.",
            "error": str(e),
            "cases_count": len(cases),
            "database_path": JSON_FOLDER_PATH
        }