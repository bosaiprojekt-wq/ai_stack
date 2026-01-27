# api/support_api.py - /support endpoint logic
from fastapi import HTTPException
from core.llm_service import llm_service
from core.database import db
import json

async def handle_support_request(query: str) -> dict:
    """Handle /support endpoint request"""
    query = query.strip()
    if not query:
        raise HTTPException(400, "Empty query")
    
    # Get cases from database
    cases = db.get_all_cases()
    
    if not cases:
        return {
            "message": "Baza przypadków jest pusta. Dodaj przypadki przez formularz.",
            "cases_count": 0,
            "form_url": "/form"
        }
    
    # Create prompt for LLM
    prompt = f"""
Jesteś agentem wsparcia administracyjnego.

BAZA PRZYPADKÓW (JSON):
{json.dumps(cases, ensure_ascii=False, indent=2)}

ZGŁOSZENIE PRACOWNIKA:
"{query}"

ZADANIE:
1. Oceń, czy w bazie istnieje podobny przypadek.
2. Jeśli TAK - zwróć JSON z case_id, title, description, solution, confidence (0-100)
3. Jeśli NIE - zwróć JSON: {{ "message": "W bazie nie ma takiego przypadku" }}

Zwróć WYŁĄCZNIE poprawny JSON.
"""
    
    try:
        response = llm_service.generate_response(prompt)
        content = response.strip()
        
        try:
            result = json.loads(content)
            return {
                **result,
                "search_query": query,
                "cases_searched": len(cases),
                "source": "main_app_support"
            }
        except json.JSONDecodeError:
            return {
                "message": "LLM returned invalid JSON",
                "raw_response": content[:500],
                "cases_count": len(cases),
                "search_query": query
            }
    except Exception as e:
        return {
            "message": "Error processing request",
            "error": str(e),
            "cases_count": len(cases)
        }