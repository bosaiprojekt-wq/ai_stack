# core/protocol_agent.py
import json
from typing import Dict, Any
from .llm_service import llm_service
from .reporting_service import university_service

def build_protocol_prompt(query: str) -> str:
    """Build prompt for protocol-related queries"""
    
    # Gather all university data
    data = {
        "statistics": {
            "open_protocols": university_service.get_open_protocols_count(),
            "pending_protocols": university_service.get_pending_protocols_count(),
            "closed_protocols": university_service.get_closed_protocols_count(),
            "total_protocols": university_service.get_open_protocols_count() + 
                              university_service.get_pending_protocols_count() + 
                              university_service.get_closed_protocols_count()
        },
        "professors_with_open_protocols": university_service.get_professors_with_open_protocols(),
        "all_professors": university_service.get_professors(),
        "all_groups": university_service.get_groups(),
        "protocols_by_status": {
            "open": university_service.get_protocols(status="open"),
            "pending": university_service.get_protocols(status="pending"),
            "closed": university_service.get_protocols(status="closed")
        }
    }
    
    prompt = f"""Jesteś asystentem do monitorowania protokołów uczelnianych.
Odpowiadasz na pytania dotyczące protokołów, ocen, studentów i profesorów.
Użyj poniższych danych, aby odpowiedzieć na pytanie.

DANE SYSTEMU:
{json.dumps(data, ensure_ascii=False, indent=2)}

PYTANIE: "{query}"

INSTRUKCJE:
1. Odpowiedz KONKRETNIE na pytanie, używając dostępnych danych
2. Bądź zwięzły - maksymalnie 3-4 zdania
3. Jeśli pytanie dotyczy liczb, podaj dokładne liczby
4. Jeśli pytanie dotyczy listy, przedstaw ją w uporządkowany sposób
5. Używaj tylko danych z systemu - nie wymyślaj
6. Odpowiadaj po polsku
7. Temperatura odpowiedzi: bardzo niska (0.1) - bądź faktualny

ODPOWIEDŹ:
"""
    return prompt

def generate_protocol_response(query: str) -> Dict[str, Any]:
    """Generate response for protocol-related queries"""
    try:
        prompt = build_protocol_prompt(query)
        
        # Use lower temperature for factual responses
        original_temperature = llm_service.llm.temperature
        original_top_p = llm_service.llm.top_p
        
        # Set very low temperature for factual answers
        llm_service.llm.temperature = 0.1
        llm_service.llm.top_p = 0.1
        
        response = llm_service.generate_response(prompt)
        
        # Restore original settings
        llm_service.llm.temperature = original_temperature
        llm_service.llm.top_p = original_top_p
        
        return {
            "success": True,
            "response": response.strip(),
            "query": query,
            "data_used": {
                "open_protocols": university_service.get_open_protocols_count(),
                "pending_protocols": university_service.get_pending_protocols_count(),
                "closed_protocols": university_service.get_closed_protocols_count()
            }
        }
        
    except Exception as e:
        print(f"Error in protocol agent: {e}")
        return {
            "success": False,
            "response": f"Błąd podczas generowania odpowiedzi: {str(e)}",
            "query": query
        }

# Example usage functions
def get_protocol_summary():
    """Get summary of protocols"""
    return generate_protocol_response("Podaj podsumowanie protokołów: ile jest otwartych, w trakcie i zamkniętych?")

def get_professors_with_missing_protocols():
    """Get professors with open protocols"""
    return generate_protocol_response("Którzy profesorowie nie zamknęli jeszcze protokołów? Podaj listę z przedmiotami i grupami.")