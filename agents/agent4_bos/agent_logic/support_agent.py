import json
from .config import JSON_FOLDER 

#build prompt for LLM
def build_support_prompt(query: str) -> str:
    """
    Buduje prompt dla LLM - tylko szukanie w bazie, bez sugerowania.
    """
    cases = []

    for file_path in JSON_FOLDER.glob("*.json"):
        with open(file_path, "r", encoding="utf-8") as f:
            case_data = json.load(f)
            #add filename
            case_data["_filename"] = file_path.name
            cases.append(case_data)


    prompt = f"""
Jesteś asystentem wsparcia technicznego. Masz bazę przypadków w formacie JSON.

BAZA PRZYPADKÓW:
{json.dumps(cases, ensure_ascii=False, indent=2)}

PRACOWNIK ZGŁASZA PROBLEM:
"{query}"

INSTRUKCJE:
1. Znajdź JEDEN najbardziej podobny przypadek
2. Jeśli NIE MA podobnego przypadku: odpowiedz "NIE_ZNALEZIONO"
3. Jeśli JEST podobny przypadek: odpowiedz W TYM FORMACIE:
'''
Przypadek nr: [case_id]
Data: [created_at w formacie DD.MM.YYYY]
Tytuł: [Tytuł]
Autor: [Autor]
Opis: [Opis]
Rozwiązanie: [Rozwiązanie]
Uwagi: [Dodatkowe uwagi]
'''
Ograniczenia:
- NIE sugeruj żadnych rozwiązań jeśli nie ma przypadku
- NIE doradzaj co zrobić
- Zwróć tylko to co jest proszone
- Pisz tylko po Polsku


Przykład odpowiedzi: "Plik: sp_010.json | Tytuł: Brak dostępu do ocen w systemie"
"""
    return prompt

#response parsing
def parse_support_response(raw: str) -> dict:
    """
    Uproszczone parsowanie - zwraca tylko czysty tekst odpowiedzi.
    """
    raw = raw.strip()
    #if response include "Przypadek nr:"
    if "Przypadek nr:" in raw:
        start_idx = raw.find("Przypadek nr:")
        if start_idx != -1:
            clean_response = raw[start_idx:].strip()
            return {
                "found": True,
                "response": clean_response
            }
    
    # if not found
    if "NIE_ZNALEZIONO" in raw.upper():
        return {
            "found": False,
            "response": "Nie znaleziono podobnego przypadku w bazie wiedzy."
        }
    
    return {
        "found": False,
        "response": f"Nie udało się przetworzyć odpowiedzi LLM. Otrzymano: {raw[:100]}..."
    }