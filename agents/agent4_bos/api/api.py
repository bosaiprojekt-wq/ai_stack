from fastapi import Body, HTTPException
from core.support_agent import search_similar_case
from core.qdrant_service import load_all_cases, get_case_count

# API wrapper: handle incoming support queries and dispatch to core agent
async def handle_support_request(query: str) -> dict:
    query = query.strip()
    if not query:
        raise HTTPException(400, "Empty query")

    cases = load_all_cases()

    # Note: Even if database is empty, we might want to generate documents, 
    # so we proceed instead of returning early if cases is empty

    if not cases and get_case_count() == 0:
        # Try to proceed anyway as we might generate documents
        pass

    try:
        result = search_similar_case(query)
        
        response = {
            "message": result.get("response") or result.get("message", "Brak odpowiedzi"),
            "found": result.get("found", False),
            "search_query": query,
            "database_path": f"qdrant://agent4_bos_cases",
            "source": "core_support_agent"
        }
        
        # Pass generated file info if present
        if result.get("generated_file"):
            response["generated_file"] = result.get("generated_file")
            
        return response

    except Exception as e:
        return {
            "message": "Wystąpił błąd podczas generowania odpowiedzi.",
            "error": str(e),
            "cases_count": len(cases) if cases else 0
        }