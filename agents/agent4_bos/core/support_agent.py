import json
from typing import Dict, Any, List
from .qdrant_service import qdrant_service, load_all_cases
from .config import KNOWLEDGE_BASE_PATH, SPECIAL_CASES_PATH, KNOWLEDGE_BASE_CATEGORIES, ALL_CATEGORIES_KEY
from .llm_service import llm_service
from .document_generator import document_generator 

# GLOBAL CONTEXT to remember the last failed query for generation flow
LAST_SEARCH_CONTEXT = {"query": None, "category": None}

def classify_query_category(query: str) -> str:
    """
    Use LLM to classify query into ONE knowledge base category
    Returns category name or 'all' if uncertain
    """
    categories_text = "\n".join([f"- {cat}" for cat in KNOWLEDGE_BASE_CATEGORIES])
    
    prompt = f"""Jesteś klasyfikatorem zapytań w systemie uczelnianym. 
Twoim zadaniem jest określenie, której kategorii dotyczy zapytanie.

DOSTĘPNE KATEGORIE (musisz wybrać tylko jedną):
{categories_text}

ZAPYTANIE: "{query}"

INSTRUKCJE:
1. Przeanalizuj zapytanie i wybierz JEDNĄ kategorię, która najlepiej pasuje.
2. Odpowiedz TYLKO nazwą wybranej kategorii (np. "urlopy_zwolnienia").
3. Jeśli zapytanie jest ogólne lub dotyczy wielu kategorii, odpowiedz "all".
4. Jeśli nie jesteś pewny, odpowiedz "all".

PRZYKŁADY:
- "Jak złożyć wniosek o urlop dziekański?" → urlopy_zwolnienia
- "Kiedy jest sesja zimowa?" → egzaminy  
- "Jakie dokumenty są potrzebne do rekrutacji?" → rekrutacja
- "Czy przysługuje mi stypendium socjalne?" → stypendia
- "Kto ma dostęp do moich danych osobowych?" → dane_osobowe
- "Informacje o uczelni" → all
- "Dzień dobry, mam pytanie" → all

Twoja odpowiedź (TYLKO nazwa kategorii lub "all"):"""

    try:
        response = llm_service.generate_response(
            prompt, 
            temperature=0.1,
            max_tokens=50
        )
        
        category = response.strip().lower()
        
        # Validate response
        if category in KNOWLEDGE_BASE_CATEGORIES:
            print(f"LLM classified: '{query}' → {category}")
            return category
        elif category == ALL_CATEGORIES_KEY:
            print(f"LLM returned 'all' for: '{query}'")
            return ALL_CATEGORIES_KEY
        else:
            print(f"LLM returned unexpected category: '{category}' for: '{query}' → using 'all'")
            return ALL_CATEGORIES_KEY
            
    except Exception as e:
        print(f"Error in LLM classification: {e}")
        return ALL_CATEGORIES_KEY


def search_by_category(query: str, category: str = None) -> List[Dict[str, Any]]:
    """
    Search ALL documents in a specific category (no limit)
    Returns ALL results sorted by relevance
    """
    if not category or category == ALL_CATEGORIES_KEY:
        # No category filter - search all (with reasonable limit)
        print(f"Searching ALL categories for: '{query}'")
        knowledge_results = qdrant_service.search(query, collection="knowledge_base", limit=100)
    else:
        # Search ALL documents in this category
        print(f"Searching ALL documents in category '{category}' for: '{query}'")
        knowledge_results = qdrant_service.search_all_in_category(
            query=query,
            category=category,
            collection="knowledge_base"
        )
    
    # Always search special_cases (with limit)
    case_results = qdrant_service.search(query, collection="special_cases", limit=50)
    
    # Combine all results
    all_results = knowledge_results + case_results
    
    print(f"DEBUG: Found {len(knowledge_results)} from knowledge_base, {len(case_results)} from special_cases")
    
    # Format all results
    formatted_results = []
    for i, result in enumerate(all_results):
        # Format for LLM
        metadata = result.get("metadata", {})
        if not metadata and "payload" in result:
            metadata = result["payload"].get("metadata", {})
        
        # Calculate confidence
        confidence = round(result.get("score", 0) * 100, 1)
        
        formatted_result = {
            "rank": i + 1,
            "score": result.get("score", 0),
            "content": result.get("text", ""),
            "source": metadata.get("source_file", "Unknown"),
            "filename": metadata.get("filename", "Unknown"),
            "type": "Form Response" if result.get("collection") == "special_cases" else "Document",
            "category": metadata.get("category", "General"),
            "confidence": confidence,
            "collection": result.get("collection", "unknown")
        }
        formatted_results.append(formatted_result)
    
    # Sort by score (most relevant first)
    formatted_results.sort(key=lambda x: x["score"], reverse=True)
    
    print(f"DEBUG: Total formatted results: {len(formatted_results)}")
    
    return formatted_results


def detect_generation_intent(query: str) -> bool:
    """Check if the user explicitly wants to generate a document"""
    keywords = ["wygeneruj", "stwórz", "napisz", "przygotuj", "sporządź"]
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in keywords)


def search_similar_case(query: str) -> Dict[str, Any]:
    """
    Enhanced search with RAG and Generation Capability
    """
    global LAST_SEARCH_CONTEXT
    
    try:
        # 0. Check for explicit generation intent FIRST
        is_generation = detect_generation_intent(query)
        category = classify_query_category(query)
        
        # Handle "Confirmation" of generation (e.g. "Tak, wygeneruj")
        topic_to_generate = query
        
        if is_generation:
            clean_query = query.lower().strip()
            # If query is short (e.g. "tak wygeneruj") and we have context, use context
            if len(clean_query.split()) < 6 and LAST_SEARCH_CONTEXT["query"]:
                print(f"DEBUG: Detected confirmation for previous topic: {LAST_SEARCH_CONTEXT['query']}")
                topic_to_generate = LAST_SEARCH_CONTEXT["query"]
                if LAST_SEARCH_CONTEXT["category"] != ALL_CATEGORIES_KEY:
                    category = LAST_SEARCH_CONTEXT["category"]
        
        if is_generation:
            print(f"\n=== GENERATION REQUEST DETECTED ===")
            print(f"Query: {query}")
            print(f"Topic used for generation: {topic_to_generate}")
            print(f"Category: {category}")
            
            # Generate the document using the proper topic
            file_info = document_generator.generate_document(topic_to_generate, category)
            
            if file_info.get("success"):
                # POPRAWKA: Dodanie linku i nazwy pliku bezpośrednio do treści wiadomości
                download_url = file_info.get("download_url", "")
                filename = file_info.get("name", "dokument.docx")
                
                response_msg = (
                    f"Zgodnie z Twoją prośbą wygenerowałem dokument na temat: '{topic_to_generate}'.\n"
                    f"Został on zapisany w kategorii '{category}'.\n\n"
                    f"📄 **Nazwa pliku:** {filename}\n"
                    f"🔗 **Link do pobrania:** {download_url}"
                )
                
                # Clear context after successful generation
                LAST_SEARCH_CONTEXT = {"query": None, "category": None}
                
                return {
                    "found": True,
                    "generated_file": file_info,
                    "message": response_msg,
                    "query": query,
                    "category": category,
                    "response_type": "generated_document"
                }
            else:
                return {
                    "found": False,
                    "message": f"Wystąpił błąd podczas generowania dokumentu: {file_info.get('error')}",
                    "query": query
                }

        # 1. Standard RAG Search
        print(f"\n=== RAG SEARCH ===")
        print(f"Query: '{query}'")
        print(f"LLM Category: {category}")
        
        # 2. Search ALL documents in this category
        search_results = search_by_category(query, category=category)
        
        # 3. Filter low confidence results (<20%)
        filtered_results = [r for r in search_results if r.get("confidence", 0) >= 20]
        
        # NEW LOGIC: Handling "Not Found" with generation proposal
        # Check if we have any high confidence matches (>45%)
        high_confidence_matches = [r for r in filtered_results if r.get("confidence", 0) >= 45]
        
        if not high_confidence_matches:
            print(f"No high confidence results found. Proposing generation.")
            
            # SAVE CONTEXT for potential generation next turn
            LAST_SEARCH_CONTEXT["query"] = query
            LAST_SEARCH_CONTEXT["category"] = category
            
            # Use LLM to formulate a polite refusal with suggestion
            prompt = f"""Użytkownik pyta o: "{query}".
Przeszukałeś bazę wiedzy i nie znalazłeś satysfakcjonujących dokumentów (wyniki są słabe).
Twoim zadaniem jest:
1. Poinformować użytkownika, że nie znalazłeś takiego dokumentu w obecnej bazie.
2. Zapytać użytkownika, czy chce, abyś wygenerował (stworzył) ten dokument teraz.
3. Poinstruować go, że jeśli się zgadza, wystarczy że napisze: "Tak, wygeneruj".

Odpowiedz krótko i konkretnie w języku polskim."""
            
            suggestion_response = llm_service.generate_response(prompt, temperature=0.3)
            
            return {
                "found": False,
                "message": suggestion_response,
                "query": query,
                "category": category,
                "total_results": len(filtered_results),
                "response_type": "not_found_suggestion"
            }
        
        # If we have good results, proceed with standard RAG response
        print(f"Results after confidence filter: {len(filtered_results)}/{len(search_results)}")
        
        # 4. Build prompt
        prompt = build_enhanced_prompt(query, filtered_results, category)
        
        # 5. Generate response
        response = llm_service.generate_response(prompt)
        
        # 6. Parse response
        result = parse_rag_response(response, filtered_results)
        
        # Add metadata
        result["query"] = query
        result["category"] = category
        result["total_results"] = len(filtered_results)
        result["high_confidence_results"] = len(high_confidence_matches)
        
        return result
        
    except Exception as e:
        print(f"ERROR in search_similar_case: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "found": False,
            "message": f"System error: {str(e)}",
            "query": query
        }

def build_enhanced_prompt(query: str, search_results: List[Dict[str, Any]], category: str = None) -> str:
    """
    Build prompt with clear document type differentiation
    """
    # Separate special_cases from knowledge_base documents
    special_cases_results = []
    knowledge_docs_results = []
    
    for result in search_results:
        if result.get("type") == "Form Response" or result.get("collection") == "special_cases":
            special_cases_results.append(result)
        else:
            knowledge_docs_results.append(result)
    
    # Take top results
    top_special_cases = special_cases_results[:3]  # Max 3 special cases
    top_knowledge_docs = knowledge_docs_results[:3]  # Max 3 knowledge docs
    
    # Prepare context text
    context_text = ""
    
    # Add special cases if any
    if top_special_cases:
        context_text += "### HISTORYCZNE PRZYPADKI (SPECIAL CASES):\n\n"
        for i, case in enumerate(top_special_cases):
            metadata = case.get("metadata", {})
            context_text += f"[Przypadek {i+1}]\n"
            context_text += f"ID: {metadata.get('case_id', 'unknown')}\n"
            context_text += f"Tytuł: {metadata.get('title', 'unknown')}\n"
            context_text += f"Autor: {metadata.get('author', 'unknown')}\n"
            context_text += f"Opis: {metadata.get('description', '')}\n"
            context_text += f"Rozwiązanie: {metadata.get('solution', '')}\n"
            context_text += f"Uwagi: {metadata.get('notes', '')}\n"
            context_text += f"Podobieństwo wyszukiwania: {case.get('confidence', 0)}%\n\n"
    
    # Add knowledge documents if any
    if top_knowledge_docs:
        context_text += "### DOKUMENTY (KNOWLEDGE BASE):\n\n"
        for i, doc in enumerate(top_knowledge_docs):
            file_path = doc.get("source", "").replace("/app/qdrant_data/", "data/")
            context_text += f"[Dokument {i+1}]\n"
            context_text += f"Plik: {doc.get('filename', 'unknown')}\n"
            context_text += f"Ścieżka: {file_path}\n"
            context_text += f"Kategoria: {doc.get('category', 'unknown')}\n"
            
            # Content preview (truncated)
            content = doc.get('content', '')
            if len(content) > 400:
                content = content[:397] + "..."
            
            context_text += f"Zawartość: {content}\n"
            context_text += f"Podobieństwo wyszukiwania: {doc.get('confidence', 0)}%\n\n"
    
    if not context_text:
        context_text = "BRAK DOPASOWANYCH MATERIAŁÓW."
    
    # Simple, clear prompt
    prompt = f"""Jesteś asystentem Biura Obsługi Studenta w systemie uczelnianym i współpracujesz z jego pracownikami. Otrzymujesz pytanie i materiały źródłowe.

PYTANIE: "{query}"

MATERIAŁY ŹRÓDŁOWE:
{context_text}

INSTRUKCJE:

1. ANALIZUJ materiały i odpowiadaj WYŁĄCZNIE na ich podstawie.
2. Odpowiadaj WYŁĄCZNIE po polsku.
3. Nie wymyślaj informacji.

FORMAT ODPOWIEDZI:

JEŚLI MASZ DOPASOWANE DOKUMENTY Z KNOWLEDGE_BASE:
[Odpowiedź na pytanie w formie krótkiej instrukcji/procedury po polsku]

[link do dokumentu] [dopasowanie%]

PRZYKŁAD:
Procedura składania wniosku o urlop dziekańskiego:

1. Złóż wniosek z szczegółowym uzasadnieniem.
2. Dołącz wymagane dokumenty (zaświadczenia lekarskie, opinie).
3. Zanieś komplet dokumentów do dziekanatu.
4. Oczekuj na decyzję dziekana.

data/urlopy/wniosek_urlop_dziekanski.docx 85%

JEŚLI MASZ DOPASOWANE PRZYPADKI Z SPECIAL_CASES:
---
Przypadek nr: [case_id]
Podobieństwo: [80-100]%
Uzasadnienie dopasowania: [dlaczego pasuje]
Data: [DD.MM.YYYY]
Tytuł: [tytuł]
Autor: [autor]
Opis: [opis]
Rozwiązanie: [rozwiązanie]
Uwagi: [uwagi]
---

JEŚLI NIE MASZ INFORMACJI:
Nie posiadam informacji na ten temat w aktualnej bazie wiedzy.

Rozpocznij odpowiedź:
"""
    
    return prompt

def parse_rag_response(raw_response: str, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Parse response with clear document type differentiation
    """
    raw_response = raw_response.strip()
    
    # Check for special cases format
    has_special_case_format = "---\nPrzypadek nr:" in raw_response
    
    # Separate sources
    special_cases = [r for r in search_results if r.get("collection") == "special_cases"]
    knowledge_docs = [r for r in search_results if r.get("collection") == "knowledge_base"]
    
    # Find best matches
    best_special_case = sorted(special_cases, key=lambda x: x.get("confidence", 0), reverse=True)[0] if special_cases else None
    best_knowledge_doc = sorted(knowledge_docs, key=lambda x: x.get("confidence", 0), reverse=True)[0] if knowledge_docs else None
    
    # Extract sources and paths
    sources = []
    file_paths = []
    similarity = 0
    
    # Handle special case response
    if has_special_case_format:
        # Parse special case info from response
        import re
        
        # Extract case_id if present
        case_id_match = re.search(r'Przypadek nr:\s*([^\n]+)', raw_response)
        case_id = case_id_match.group(1).strip() if case_id_match else "unknown"
        
        # Extract similarity
        sim_match = re.search(r'Podobieństwo:\s*(\d+)%', raw_response)
        if sim_match:
            similarity = int(sim_match.group(1))
        
        if best_special_case:
            sources.append({
                "type": "special_case",
                "case_id": case_id,
                "title": best_special_case.get("metadata", {}).get("title", "unknown"),
                "similarity": similarity
            })
    
    # Handle knowledge document response
    else:
        # Look for document link in response
        import re
        
        # Extract document path and similarity from response
        link_pattern = r'(data/[^\s]+)\s+(\d+)%'
        matches = re.findall(link_pattern, raw_response)
        
        for link, sim in matches:
            file_paths.append(link)
            if int(sim) > similarity:
                similarity = int(sim)
        
        # Add knowledge document sources
        if best_knowledge_doc:
            source_path = best_knowledge_doc.get("source", "")
            user_path = source_path.replace("/app/qdrant_data/", "data/")
            
            sources.append({
                "type": "document",
                "filename": best_knowledge_doc.get("filename", "Unknown"),
                "path": user_path,
                "confidence": best_knowledge_doc.get("confidence", 0)
            })
            
            if not file_paths:  # If no link found in text, add from best doc
                file_paths.append(user_path)
                similarity = best_knowledge_doc.get("confidence", 0)
    
    # Check if no information found
    found = True
    if "nie posiadam informacji" in raw_response.lower() or "brak informacji" in raw_response.lower():
        found = False
    
    return {
        "found": found,
        "response": raw_response,
        "sources": sources,
        "file_paths": file_paths,
        "results_count": len(search_results),
        "similarity": similarity,
        "response_type": "special_case" if has_special_case_format else "knowledge_doc"
    }