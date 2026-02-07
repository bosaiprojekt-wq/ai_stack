import json
from typing import Dict, Any, List
from .qdrant_service import qdrant_service, load_all_cases
from .config import KNOWLEDGE_BASE_PATH, SPECIAL_CASES_PATH, KNOWLEDGE_BASE_CATEGORIES, ALL_CATEGORIES_KEY

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
        knowledge_results = qdrant_service.search(query, collection="knowledge_base", limit=100)  # Reasonable limit for all
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
    
    # Show category distribution
    if formatted_results:
        from collections import Counter
        category_counts = Counter([r["category"] for r in formatted_results])
        print(f"DEBUG: Category distribution: {dict(category_counts)}")
        
        # Show confidence range
        confidences = [r["confidence"] for r in formatted_results]
        if confidences:
            print(f"DEBUG: Confidence range: {min(confidences)}% - {max(confidences)}%")
        
        # Show top 5 results
        print(f"DEBUG: Top 5 results by relevance:")
        for i, r in enumerate(formatted_results[:5]):
            marker = "★" if r["category"] == category else " "
            print(f"{marker} {i+1}. {r['filename']}")
            print(f"    Category: {r['category']}, Confidence: {r['confidence']}%")
            if r['confidence'] > 50:  # Show snippet for decent matches
                snippet = r['content'][:100]
                print(f"    Preview: {snippet}...")
    
    return formatted_results  # Return ALL results, no limit

def search_similar_case(query: str) -> Dict[str, Any]:
    """
    Enhanced search with RAG - searches ALL documents in selected category
    """
    try:
        # 1. Use LLM to classify query category
        category = classify_query_category(query)
        print(f"\n=== RAG SEARCH ===")
        print(f"Query: '{query}'")
        print(f"LLM Category: {category}")
        
        # DEBUG: Check what's in this category
        print(f"\n=== DEBUG: Checking category '{category}' ===")
        qdrant_service.debug_category_search(category)
        
        # 2. Search ALL documents in this category (no limit)
        search_results = search_by_category(query, category=category)
        
        # 3. If no results in target category, try all categories
        target_category_results = [r for r in search_results if r["category"] == category]
        if not target_category_results and category != ALL_CATEGORIES_KEY:
            print(f"\nNo results in category '{category}', trying ALL categories...")
            search_results = search_by_category(query, category=ALL_CATEGORIES_KEY)
        
        # 4. Build prompt with ALL found results
        prompt = build_enhanced_prompt(query, search_results, category)
        
        # 5. Generate response
        response = llm_service.generate_response(prompt)
        
        # 6. Parse response
        result = parse_rag_response(response, search_results)
        
        # Add metadata
        result["query"] = query
        result["category"] = category
        result["total_results"] = len(search_results)
        result["target_category_results"] = len([r for r in search_results if r["category"] == category])
        
        # Detailed summary
        print(f"\n=== FINAL SEARCH SUMMARY ===")
        print(f"Query: '{query}'")
        print(f"Selected category: {category}")
        print(f"Total documents retrieved: {len(search_results)}")
        print(f"Documents in target category: {result['target_category_results']}")
        
        if search_results:
            # Group by category
            from collections import Counter
            cat_counts = Counter([r["category"] for r in search_results])
            print(f"\nCategory breakdown:")
            for cat, count in cat_counts.items():
                marker = "→ " if cat == category else "  "
                print(f"  {marker}{cat}: {count} documents")
            
            # Show top results from target category
            target_results = [r for r in search_results if r["category"] == category]
            if target_results:
                print(f"\nTop results from target category '{category}':")
                for i, r in enumerate(target_results[:10]):
                    print(f"  {i+1}. {r['filename']} - {r['confidence']}%")
                    if r['confidence'] > 50:
                        print(f"      {r['content'][:80]}...")
            else:
                print(f"\n No results found in target category '{category}'")
                print("Showing top results from all categories:")
                for i, r in enumerate(search_results[:10]):
                    print(f"  {i+1}. {r['filename']} ({r['category']}) - {r['confidence']}%")
        
        return result
        
    except Exception as e:
        print(f"ERROR in search_similar_case: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "found": False,
            "cases_found": False,
            "message": f"System error: {str(e)}",
            "query": query
        }

def build_enhanced_prompt(query: str, search_results: List[Dict[str, Any]], category: str = None) -> str:
    """
    Build prompt with clear document type differentiation
    """
    # Load all cases for context
    cases = load_all_cases()
    
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
def search_similar_case(query: str) -> Dict[str, Any]:
    """
    Enhanced search with RAG
    """
    try:
        # 1. Use LLM to classify query category
        category = classify_query_category(query)
        print(f"\n=== RAG SEARCH ===")
        print(f"Query: '{query}'")
        print(f"LLM Category: {category}")
        
        # 2. Search ALL documents in this category
        search_results = search_by_category(query, category=category)
        
        # 3. Filter low confidence results (<20%)
        filtered_results = [r for r in search_results if r.get("confidence", 0) >= 20]
        
        if not filtered_results:
            print(f"No results with confidence >=20%, using all results")
            filtered_results = search_results
        
        print(f"Results after confidence filter: {len(filtered_results)}/{len(search_results)}")
        
        # 4. Build prompt
        prompt = build_enhanced_prompt(query, filtered_results, category)
        
        # 5. Generate response
        response = llm_service.generate_response(prompt)
        
        # 6. Parse response
        result = parse_rag_response(response, filtered_results)
        
        # Add metadata (BEZ 'cases_found' jeśli go nie ma!)
        result["query"] = query
        result["category"] = category
        result["total_results"] = len(filtered_results)
        result["high_confidence_results"] = len([r for r in filtered_results if r.get("confidence", 0) >= 40])
        
        # Debug information
        print(f"\n Search Summary:")
        print(f"   Query: '{query}'")
        print(f"   Category: {category}")
        print(f"   Total results: {len(filtered_results)}")
        print(f"   High confidence (≥40%): {result['high_confidence_results']}")
        print(f"   Response type: {result.get('response_type', 'unknown')}")
        
        # Show confidence distribution
        if filtered_results:
            confidences = [r.get("confidence", 0) for r in filtered_results]
            print(f"   Confidence stats: min={min(confidences)}%, max={max(confidences)}%, avg={sum(confidences)/len(confidences):.1f}%")
            
            # Show top 3
            print(f"\nTop 3 results:")
            for i, r in enumerate(filtered_results[:3]):
                source_type = "CASE" if r.get("collection") == "special_cases" else "DOC"
                print(f"   {i+1}. {r['filename']} ({source_type}) - {r['confidence']}%")
        
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