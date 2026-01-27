import json
from typing import Dict, Any
from .llm_service import llm_service  # Import from pure service
from .file_utils import load_all_cases

def build_support_prompt(query: str) -> str:
    cases = load_all_cases()

    prompt = f"""Twoje zadanie: porównać zapytanie z bazą przypadków i zwrócić najbardziej podobny przypadek.

BAZA PRZYPADKÓW:
{json.dumps(cases, ensure_ascii=False, indent=2)}

ZAPYTANIE: "{query}"

ODPOWIEDŹ MUSI BYĆ TYLKO W TYM FORMACIE, NIC WIĘCEJ:

***
Najbardziej podobny przypadek w bazie:

Podobieństwo: [0-100]%
Przypadek nr: [case_id]
Data: [DD.MM.YYYY]
Tytuł: [tytuł]
Autor: [autor]
Opis: [opis]
Rozwiązanie: [rozwiązanie]
Uwagi: [uwagi]
***

LUB JEŚLI NIE MA DOPASOWANIA (podobieństwo < 80%):

***
NIE_ZNALEZIONO
***

Wymogi:
- NIE PISZ ŻADNEGO TEKSTU POZA TYM FORMATEM.
- NIE ANALIZUJ NA GŁOS.
- NIE PISZ KOMENTARZY.
- NIGDY nie wymyślaj wartości pól
- wpisuj tylko wartość pul z pliku json przypadku
- ZWRÓĆ JAKO ODPOWIEDŹ JEDYNIE TO CO POMIĘDZY ZNAKAMI *** ***
"""
    return prompt


def parse_support_response(raw: str) -> dict:
    raw = raw.strip()
    
    # Check for NIE_ZNALEZIONO first
    if "NIE_ZNALEZIONO" in raw.upper():
        # Try to extract similarity score
        similarity = 0
        import re
        match = re.search(r'podobieństwo:\s*(\d+)%', raw, re.IGNORECASE)
        if match:
            similarity = int(match.group(1))
        
        return {
            "found": False,
            "response": "Nie znaleziono podobnego przypadku w bazie wiedzy.",
            "similarity": similarity
        }
    
    # Check if it's a valid case response
    if "Przypadek nr:" in raw and "Podobieństwo:" in raw:
        # Extract similarity
        similarity = 0
        import re
        match = re.search(r'Podobieństwo:\s*(\d+)%', raw)
        if match:
            similarity = int(match.group(1))
        
        # Only return if similarity >= 80 (as per prompt)
        if similarity >= 80:
            # Clean up the response (remove brackets if present)
            clean_response = raw.replace('[', '').replace(']', '').strip()
            return {
                "found": True,
                "response": clean_response,
                "similarity": similarity
            }
        else:
            # Even if LLM returned case but similarity < 80, treat as not found
            return {
                "found": False,
                "response": "Nie znaleziono podobnego przypadku w bazie wiedzy.",
                "similarity": similarity
            }
    
    # If response doesn't match expected format at all
    return {
        "found": False,
        "response":  "Odpowiedź AI w złym formacie",
        "similarity": 0,
        "raw_response": raw[:200]
    }

def search_similar_case(query: str) -> Dict[str, Any]:
    """
    Search for similar cases using LLM
    """
    try:
        prompt = build_support_prompt(query)
        response = llm_service.generate_response(prompt)
        
        # Debug log
        print(f"\n=== DEBUG SEARCH ===")
        print(f"Query: {query}")
        print(f"Response preview: {response[:300]}...")
        
        result = parse_support_response(response)
        
        result["query"] = query
        return result
        
    except Exception as e:
        print(f"ERROR in search_similar_case: {str(e)}")
        return {
            "found": False,
            "message": f"Błąd systemu: {str(e)}",
            "query": query,
            "similarity": 0
        }