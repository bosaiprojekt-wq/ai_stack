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


# def search_by_category(query: str, category: str = None) -> List[Dict[str, Any]]:
#     """
#     Search ALL documents in a specific category (no limit)
#     Returns ALL results sorted by relevance
#     """
#     if not category or category == ALL_CATEGORIES_KEY:
#         # No category filter - search all (with reasonable limit)
#         print(f"Searching ALL categories for: '{query}'")
#         knowledge_results = qdrant_service.search(query, collection="knowledge_base", limit=100)
#     else:
#         # Search ALL documents in this category
#         print(f"Searching ALL documents in category '{category}' for: '{query}'")
#         knowledge_results = qdrant_service.search_all_in_category(
#             query=query,
#             category=category,
#             collection="knowledge_base"
#         )
    
#     # Always search special_cases (with limit)
#     case_results = qdrant_service.search(query, collection="special_cases", limit=50)
    
#     # Combine all results
#     all_results = knowledge_results + case_results
    
#     print(f"DEBUG: Found {len(knowledge_results)} from knowledge_base, {len(case_results)} from special_cases")
    
#     # Format all results
#     formatted_results = []
#     for i, result in enumerate(all_results):
#         # Format for LLM
#         metadata = result.get("metadata", {})
#         if not metadata and "payload" in result:
#             metadata = result["payload"].get("metadata", {})
        
#         # Calculate confidence
#         confidence = round(result.get("score", 0) * 100, 1)
        
#         formatted_result = {
#             "rank": i + 1,
#             "score": result.get("score", 0),
#             "content": result.get("text", ""),
#             "source": metadata.get("source_file", "Unknown"),
#             "filename": metadata.get("filename", "Unknown"),
#             "type": "Form Response" if result.get("collection") == "special_cases" else "Document",
#             "category": metadata.get("category", "General"),
#             "confidence": confidence,
#             "collection": result.get("collection", "unknown")
#         }
#         formatted_results.append(formatted_result)
    
#     # Sort by score (most relevant first)
#     formatted_results.sort(key=lambda x: x["score"], reverse=True)
    
#     print(f"DEBUG: Total formatted results: {len(formatted_results)}")
    
#     return formatted_results

def search_by_category(query: str, category: str = None) -> List[Dict[str, Any]]:
    """
    Search documents in category, group chunks by file, return full documents
    """
    if not category or category == ALL_CATEGORIES_KEY:
        knowledge_results = qdrant_service.search(query, collection="knowledge_base", limit=100)
    else:
        knowledge_results = qdrant_service.search_all_in_category(
            query=query,
            category=category,
            collection="knowledge_base"
        )
    
    case_results = qdrant_service.search(query, collection="special_cases", limit=50)
    
    # GROUP chunks by source_file
    documents = {}
    
    for result in knowledge_results:
        metadata = result.get("metadata", {})
        source_file = metadata.get("source_file", "Unknown")
        
        if source_file not in documents:
            documents[source_file] = {
                "filename": metadata.get("filename", "Unknown"),
                "source": source_file,
                "category": metadata.get("category", "General"),
                "chunks": [],
                "confidences": [],
                "all_content": [],
                "total_chunks": metadata.get("total_chunks", 1)
            }
        
        # Add this chunk
        confidence = round(result.get("score", 0) * 100, 1)
        documents[source_file]["chunks"].append({
            "index": metadata.get("chunk_index", 0),
            "confidence": confidence,
            "text": result.get("text", "")
        })
        documents[source_file]["confidences"].append(confidence)
        documents[source_file]["all_content"].append(result.get("text", ""))
    
    # Calculate document scores and combine content
    knowledge_docs = []
    for source_file, doc in documents.items():
        # Sort chunks by index to maintain order
        doc["chunks"].sort(key=lambda x: x["index"])
        doc["all_content"] = [c["text"] for c in doc["chunks"]]  # Already in order
        
        knowledge_docs.append({
            "filename": doc["filename"],
            "source": doc["source"],
            "category": doc["category"],
            "confidence": max(doc["confidences"]),  # Best chunk score
            "avg_confidence": round(sum(doc["confidences"]) / len(doc["confidences"]), 1),
            "content": "\n\n".join(doc["all_content"]),  # Complete document
            "chunk_count": len(doc["chunks"]),
            "total_chunks": doc["total_chunks"],
            "collection": "knowledge_base"
        })
    
    # Format special cases
    special_cases = []
    for result in case_results:
        metadata = result.get("metadata", {})
        special_cases.append({
            "filename": f"Case: {metadata.get('title', 'Unknown')}",
            "source": "special_cases",
            "category": "Special Case",
            "confidence": round(result.get("score", 0) * 100, 1),
            "content": f"{metadata.get('description', '')}\n\n{metadata.get('solution', '')}",
            "collection": "special_cases",
            "case_id": metadata.get("case_id", "unknown"),
            "title": metadata.get("title", "Unknown"),
            "author": metadata.get("author", "Unknown")
        })
    
    # Combine and sort
    all_docs = knowledge_docs + special_cases
    all_docs.sort(key=lambda x: x["confidence"], reverse=True)
    
    # SHOW TOP 3 RESULTS
    print(f"\nTOP 3 DOCUMENTS (full content):")
    print("=" * 60)
    for i, doc in enumerate(all_docs[:3], 1):
        if doc["collection"] == "knowledge_base":
            print(f"\n{i}. {doc['filename']}")
            print(f"   Category: {doc['category']}")
            print(f"   Confidence: {doc['confidence']}% (best chunk)")
            print(f"   Chunks: {doc['chunk_count']}/{doc['total_chunks']}")
            print(f"   Preview: {doc['content'][:200].replace(chr(10), ' ')}...")
        else:
            print(f"\n{i}.{doc['filename']}")
            print(f"   Confidence: {doc['confidence']}%")
            print(f"   Preview: {doc['content'][:200].replace(chr(10), ' ')}...")
    print("\n" + "=" * 60)
    
    return all_docs


def detect_generation_intent(query: str) -> bool:
    """Check if the user explicitly wants to generate a document"""
    keywords = ["wygeneruj", "stwórz", "napisz", "przygotuj", "sporządź"]
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in keywords)

def search_similar_case(query: str) -> Dict[str, Any]:
    """
    Enhanced search with RAG and Generation Capability
    Groups chunks by source file, returns full documents
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
            
            file_info = document_generator.generate_document(topic_to_generate, category)
            
            if file_info.get("success"):
                download_url = file_info.get("download_url", "")
                filename = file_info.get("name", "dokument.docx")
                
                response_msg = (
                    f"Zgodnie z Twoją prośbą wygenerowałem dokument na temat: '{topic_to_generate}'.\n"
                    f"Został on zapisany w kategorii '{category}'.\n\n"
                    f"📄 **Nazwa pliku:** {filename}\n"
                    f"🔗 **Link do pobrania:** {download_url}"
                )
                
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
        print(f"\n{'='*60}")
        print("RAG SEARCH")
        print('='*60)
        print(f"Query: '{query}'")
        print(f"LLM Category: {category}")
        print('='*60)
        
        # 2. Search with category filter
        if not category or category == ALL_CATEGORIES_KEY:
            print(f"Searching ALL categories for: '{query}'")
            knowledge_results = qdrant_service.search(query, collection="knowledge_base", limit=200)
        else:
            print(f"Searching ALL documents in category '{category}' for: '{query}'")
            knowledge_results = qdrant_service.search_all_in_category(
                query=query,
                category=category,
                collection="knowledge_base"
            )
        
        # Search special cases
        case_results = qdrant_service.search(query, collection="special_cases", limit=50)
        
        print(f"Raw results: {len(knowledge_results)} knowledge chunks, {len(case_results)} special cases")
        
        # 3. GROUP knowledge chunks by source_file
        documents = {}
        
        for result in knowledge_results:
            metadata = result.get("metadata", {})
            if not metadata and "payload" in result:
                metadata = result["payload"].get("metadata", {})
            
            source_file = metadata.get("source_file", "Unknown")
            filename = metadata.get("filename", "Unknown")
            
            if source_file not in documents:
                documents[source_file] = {
                    "filename": filename,
                    "source": source_file,
                    "category": metadata.get("category", "General"),
                    "chunks": [],
                    "confidences": [],
                    "all_content": [],
                    "total_chunks": metadata.get("total_chunks", 1),
                    "collection": "knowledge_base"
                }
            
            # Add this chunk
            confidence = round(result.get("score", 0) * 100, 1)
            chunk_index = metadata.get("chunk_index", 0)
            
            documents[source_file]["chunks"].append({
                "index": chunk_index,
                "confidence": confidence,
                "score": result.get("score", 0),
                "text": result.get("text", "")
            })
            documents[source_file]["confidences"].append(confidence)
            documents[source_file]["all_content"].append({
                "index": chunk_index,
                "text": result.get("text", "")
            })
        
        # Build complete documents with chunks in correct order
        knowledge_docs = []
        for source_file, doc in documents.items():
            # Sort chunks by index
            doc["chunks"].sort(key=lambda x: x["index"])
            doc["all_content"].sort(key=lambda x: x["index"])
            
            # Combine all text in order
            full_content = "\n\n".join([c["text"] for c in doc["all_content"]])
            
            # Calculate document confidence (max chunk confidence)
            max_confidence = max(doc["confidences"]) if doc["confidences"] else 0
            avg_confidence = round(sum(doc["confidences"]) / len(doc["confidences"]), 1) if doc["confidences"] else 0
            
            knowledge_docs.append({
                "filename": doc["filename"],
                "source": doc["source"],
                "category": doc["category"],
                "confidence": max_confidence,
                "avg_confidence": avg_confidence,
                "content": full_content,
                "chunk_count": len(doc["chunks"]),
                "total_chunks": doc["total_chunks"],
                "collection": "knowledge_base",
                "type": "Document"
            })
        
        # 4. Format special cases
        special_cases = []
        for result in case_results:
            metadata = result.get("metadata", {})
            if not metadata and "payload" in result:
                metadata = result["payload"].get("metadata", {})
            
            confidence = round(result.get("score", 0) * 100, 1)
            
            special_cases.append({
                "filename": f"Sprawa: {metadata.get('title', 'Unknown')}",
                "source": "special_cases",
                "category": "Przypadek specjalny",
                "confidence": confidence,
                "content": f"Tytuł: {metadata.get('title', '')}\nOpis: {metadata.get('description', '')}\nRozwiązanie: {metadata.get('solution', '')}\nUwagi: {metadata.get('notes', '')}",
                "collection": "special_cases",
                "type": "Form Response",
                "case_id": metadata.get("case_id", "unknown"),
                "title": metadata.get("title", "Unknown"),
                "author": metadata.get("author", "Unknown"),
                "created_at": metadata.get("created_at", "")
            })
        
        # 5. Combine all documents
        all_docs = knowledge_docs + special_cases
        all_docs.sort(key=lambda x: x["confidence"], reverse=True)
        
        # 6. DISPLAY TOP 3 RESULTS
        print(f"\n{'='*60}")
        print("TOP 3 MOST RELEVANT DOCUMENTS")
        print('='*60)
        
        if not all_docs:
            print("\nNo documents found.")
        else:
            for i, doc in enumerate(all_docs[:3], 1):
                if doc["collection"] == "knowledge_base":
                    print(f"\n{i}. 📄 {doc['filename']}")
                    print(f"   Kategoria: {doc['category']}")
                    print(f"   Dopasowanie: {doc['confidence']}% (maks), {doc.get('avg_confidence', 0)}% (średnia)")
                    print(f"   Chunków: {doc['chunk_count']}/{doc['total_chunks']}")
                    # Show preview of first 200 chars
                    preview = doc['content'][:200].replace('\n', ' ').strip()
                    print(f"   Podgląd: {preview}...")
                else:
                    print(f"\n{i}. 📋 {doc['filename']}")
                    print(f"   Autor: {doc.get('author', 'Nieznany')}")
                    print(f"   Dopasowanie: {doc['confidence']}%")
                    preview = doc['content'][:200].replace('\n', ' ').strip()
                    print(f"   Podgląd: {preview}...")
        
        print(f"\n{'='*60}")
        print(f"Znaleziono {len(all_docs)} unikalnych dokumentów")
        print(f"{'='*60}")
        
        # 7. Check if we have good matches
        good_matches = [doc for doc in all_docs if doc["confidence"] >= 35]
        
        if not good_matches:
            print(f"\nBrak dokumentów z dobrym dopasowaniem (najlepsze: {all_docs[0]['confidence'] if all_docs else 0}%)")
            
            # SAVE CONTEXT for potential generation
            LAST_SEARCH_CONTEXT["query"] = query
            LAST_SEARCH_CONTEXT["category"] = category
            
            # Prepare information about what WAS found
            found_info = ""
            if all_docs:
                found_info = f"Znalazłem {len(all_docs)} dokumentów, ale najlepsze dopasowanie to tylko {all_docs[0]['confidence']}%."
            
            prompt = f"""Użytkownik pyta o: "{query}".
{found_info}
Przeszukałeś bazę wiedzy w kategorii '{category}' i nie znalazłeś dokumentów z wystarczająco wysokim dopasowaniem (potrzebne >=35%).
Twoim zadaniem jest:
1. Poinformować użytkownika, że nie znalazłeś dobrze dopasowanego dokumentu w obecnej bazie.
2. Zapytać użytkownika, czy chce, abyś wygenerował (stworzył) ten dokument teraz.
3. Poinstruować go, że jeśli się zgadza, wystarczy że napisze: "Tak, wygeneruj".

Odpowiedz krótko i konkretnie w języku polskim."""
            
            suggestion_response = llm_service.generate_response(prompt, temperature=0.3)
            
            return {
                "found": False,
                "message": suggestion_response,
                "query": query,
                "category": category,
                "total_documents": len(all_docs),
                "best_confidence": all_docs[0]["confidence"] if all_docs else 0,
                "response_type": "not_found_suggestion"
            }
        
        # 8. Use the best document for response
        best_doc = good_matches[0]
        
        print(f"\n✅ Wybrano dokument do odpowiedzi:")
        print(f"   Tytuł: {best_doc['filename']}")
        print(f"   Dopasowanie: {best_doc['confidence']}%")
        print(f"   Długość treści: {len(best_doc['content'])} znaków")
        print(f"{'='*60}\n")
        
        # 9. Build prompt with complete document
        prompt = build_document_prompt(query, best_doc, category)
        
        # 10. Generate response
        response = llm_service.generate_response(prompt)
        
        # 11. Parse response
        result = parse_rag_response(response, [best_doc])
        
        # 12. Add metadata
        result["query"] = query
        result["category"] = category
        result["total_documents"] = len(all_docs)
        result["good_matches"] = len(good_matches)
        result["document_used"] = {
            "filename": best_doc["filename"],
            "confidence": best_doc["confidence"],
            "source": best_doc.get("source", "").replace("/app/qdrant_data/", "data/")
        }
        
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


def build_document_prompt(query: str, document: Dict[str, Any], category: str = None) -> str:
    """
    Build prompt with single complete document
    """
    file_path = document.get("source", "").replace("/app/qdrant_data/", "data/")
    
    prompt = f"""Jesteś asystentem Biura Obsługi Studenta w systemie uczelnianym i współpracujesz z jego pracownikami. Otrzymujesz pytanie i pełny dokument źródłowy.

PYTANIE: "{query}"

DOKUMENT ŹRÓDŁOWY:
Plik: {document['filename']}
Ścieżka: {file_path}
Kategoria: {document.get('category', 'unknown')}
Dopasowanie: {document['confidence']}%

TREŚĆ DOKUMENTU:
{document['content']}

INSTRUKCJE:
1. Odpowiedz na pytanie WYŁĄCZNIE na podstawie treści dokumentu.
2. Odpowiadaj WYŁĄCZNIE po polsku.
3. Nie dodawaj informacji, których nie ma w dokumencie.
4. Na końcu odpowiedzi podaj link do dokumentu i procent dopasowania w formacie:
   [ścieżka/do/pliku] [dopasowanie%]

PRZYKŁAD:
Procedura składania wniosku o urlop dziekański:
1. Złóż wniosek z uzasadnieniem.
2. Dołącz wymagane dokumenty.
3. Złóż w dziekanacie.

data/urlopy/Urlop dziekański_Dean's leave.docx 85%

ODPOWIEDŹ:"""
    
    return prompt


def parse_rag_response(raw_response: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Parse response with single document
    """
    raw_response = raw_response.strip()
    
    # Check if no information found
    found = True
    if "nie posiadam informacji" in raw_response.lower() or "brak informacji" in raw_response.lower():
        found = False
    
    # Extract sources
    sources = []
    file_paths = []
    similarity = 0
    
    if documents:
        doc = documents[0]
        source_path = doc.get("source", "")
        user_path = source_path.replace("/app/qdrant_data/", "data/")
        
        sources.append({
            "type": "document",
            "filename": doc.get("filename", "Unknown"),
            "path": user_path,
            "confidence": doc.get("confidence", 0)
        })
        
        file_paths.append(user_path)
        similarity = doc.get("confidence", 0)
    
    return {
        "found": found,
        "response": raw_response,
        "sources": sources,
        "file_paths": file_paths,
        "results_count": len(documents),
        "similarity": similarity,
        "response_type": "knowledge_doc"
    }


# def search_similar_case(query: str) -> Dict[str, Any]:
#     """
#     Enhanced search with RAG and Generation Capability
#     """
#     global LAST_SEARCH_CONTEXT
    
#     try:
#         # 0. Check for explicit generation intent FIRST
#         is_generation = detect_generation_intent(query)
#         category = classify_query_category(query)
        
#         # Handle "Confirmation" of generation (e.g. "Tak, wygeneruj")
#         topic_to_generate = query
        
#         if is_generation:
#             clean_query = query.lower().strip()
#             # If query is short (e.g. "tak wygeneruj") and we have context, use context
#             if len(clean_query.split()) < 6 and LAST_SEARCH_CONTEXT["query"]:
#                 print(f"DEBUG: Detected confirmation for previous topic: {LAST_SEARCH_CONTEXT['query']}")
#                 topic_to_generate = LAST_SEARCH_CONTEXT["query"]
#                 if LAST_SEARCH_CONTEXT["category"] != ALL_CATEGORIES_KEY:
#                     category = LAST_SEARCH_CONTEXT["category"]
        
#         if is_generation:
#             print(f"\n=== GENERATION REQUEST DETECTED ===")
#             print(f"Query: {query}")
#             print(f"Topic used for generation: {topic_to_generate}")
#             print(f"Category: {category}")
            
#             # Generate the document using the proper topic
#             file_info = document_generator.generate_document(topic_to_generate, category)
            
#             if file_info.get("success"):
#                 download_url = file_info.get("download_url", "")
#                 filename = file_info.get("name", "dokument.docx")
                
#                 response_msg = (
#                     f"Zgodnie z Twoją prośbą wygenerowałem dokument na temat: '{topic_to_generate}'.\n"
#                     f"Został on zapisany w kategorii '{category}'.\n\n"
#                     f"📄 **Nazwa pliku:** {filename}\n"
#                     f"🔗 **Link do pobrania:** {download_url}"
#                 )
                
#                 # Clear context after successful generation
#                 LAST_SEARCH_CONTEXT = {"query": None, "category": None}
                
#                 return {
#                     "found": True,
#                     "generated_file": file_info,
#                     "message": response_msg,
#                     "query": query,
#                     "category": category,
#                     "response_type": "generated_document"
#                 }
#             else:
#                 return {
#                     "found": False,
#                     "message": f"Wystąpił błąd podczas generowania dokumentu: {file_info.get('error')}",
#                     "query": query
#                 }

#         # 1. Standard RAG Search
#         print(f"\n{'='*60}")
#         print(f"🔍 RAG SEARCH")
#         print(f"{'='*60}")
#         print(f"Query: '{query}'")
#         print(f"LLM Category: {category}")
#         print(f"{'='*60}")
        
#         # 2. Search ALL documents in this category
#         search_results = search_by_category(query, category=category)
        
#         # 3. DEBUG: Print all raw results with their confidence scores
#         print(f"\n RAW SEARCH RESULTS ({len(search_results)} total):")
#         print(f"{'-'*60}")
        
#         # Group by collection type for better visibility
#         knowledge_results = [r for r in search_results if r.get("collection") == "knowledge_base"]
#         special_results = [r for r in search_results if r.get("collection") == "special_cases"]
        
#         print(f"\n📚 KNOWLEDGE BASE RESULTS ({len(knowledge_results)}):")
#         if knowledge_results:
#             for i, r in enumerate(knowledge_results, 1):
#                 confidence = r.get("confidence", 0)
#                 filename = r.get("filename", "Unknown")
#                 category = r.get("category", "Unknown")
#                 score = r.get("score", 0)
                
#                 # Highlight high confidence results
#                 if confidence >= 45:
#                     marker = "HIGH CONFIDENCE"
#                 elif confidence >= 20:
#                     marker = "MEDIUM CONFIDENCE"
#                 else:
#                     marker = "LOW CONFIDENCE"
                
#                 print(f"\n  [{i}] {marker}")
#                 print(f"      File: {filename}")
#                 print(f"      Category: {category}")
#                 print(f"      Confidence: {confidence}%")
#                 print(f"      Raw score: {score:.4f}")
                
#                 # Show first 100 chars of content
#                 content = r.get("content", "")
#                 if content:
#                     print(f"      Preview: {content[:100].replace(chr(10), ' ')}...")
                
#                 # Group documents by source file
#                 source = r.get("source", "")
#                 if source:
#                     # Extract just the filename from path
#                     from pathlib import Path
#                     source_filename = Path(source).name
#                     print(f"      Source file: {source_filename}")
#         else:
#             print("  No results from knowledge_base")
        
#         print(f"\n📋 SPECIAL CASES RESULTS ({len(special_results)}):")
#         if special_results:
#             for i, r in enumerate(special_results, 1):
#                 confidence = r.get("confidence", 0)
#                 metadata = r.get("metadata", {})
#                 title = metadata.get("title", "Unknown")
                
#                 if confidence >= 45:
#                     marker = "✅ HIGH CONFIDENCE"
#                 elif confidence >= 20:
#                     marker = "⚠️ MEDIUM CONFIDENCE"
#                 else:
#                     marker = "❌ LOW CONFIDENCE"
                
#                 print(f"\n  [{i}] {marker}")
#                 print(f"      Title: {title}")
#                 print(f"      Confidence: {confidence}%")
#                 print(f"      Raw score: {r.get('score', 0):.4f}")
                
#                 if metadata.get('description'):
#                     print(f"      Description: {metadata['description'][:100]}...")
#         else:
#             print("  No results from special_cases")
        
#         # 4. Filter low confidence results (<20%)
#         filtered_results = [r for r in search_results if r.get("confidence", 0) >= 20]
        
#         print(f"\n🔍 FILTERING RESULTS:")
#         print(f"   Total results: {len(search_results)}")
#         print(f"   After 20% threshold: {len(filtered_results)}")
#         print(f"   Removed: {len(search_results) - len(filtered_results)} low confidence results")
        
#         # 5. Check for high confidence matches (>45%)
#         high_confidence_matches = [r for r in filtered_results if r.get("confidence", 0) >= 45]
        
#         # Group high confidence matches by source file to see unique documents
#         unique_documents = {}
#         for r in high_confidence_matches:
#             source = r.get("source", "unknown")
#             filename = r.get("filename", "Unknown")
#             if source not in unique_documents:
#                 unique_documents[source] = {
#                     "filename": filename,
#                     "confidence": r.get("confidence", 0),
#                     "category": r.get("category", "Unknown")
#                 }
        
#         print(f"\n🎯 HIGH CONFIDENCE MATCHES ({len(high_confidence_matches)} total chunks):")
#         if high_confidence_matches:
#             print(f"   Unique documents: {len(unique_documents)}")
#             for i, (source, info) in enumerate(unique_documents.items(), 1):
#                 print(f"\n   [{i}] {info['filename']}")
#                 print(f"       Category: {info['category']}")
#                 print(f"       Max confidence: {info['confidence']}%")
                
#                 # Show all chunks for this document
#                 doc_chunks = [r for r in high_confidence_matches if r.get("source") == source]
#                 if len(doc_chunks) > 1:
#                     print(f"       Chunks: {len(doc_chunks)} chunks (confidence range: {min(c.get('confidence',0) for c in doc_chunks)}-{max(c.get('confidence',0) for c in doc_chunks)}%)")
#         else:
#             print("   ❌ No high confidence matches found!")
            
#             # Additional debugging: check if documents exist in this category
#             print(f"\n📊 CATEGORY CONTENT DEBUG:")
#             try:
#                 # Check if any documents exist in this category at all
#                 collection_name = qdrant_service.collections.get("knowledge_base")
#                 if collection_name:
#                     from qdrant_client.models import Filter, FieldCondition, MatchValue
                    
#                     count_result = qdrant_service.client.count(
#                         collection_name=collection_name,
#                         count_filter=Filter(
#                             must=[
#                                 FieldCondition(
#                                     key="metadata.category",
#                                     match=MatchValue(value=category)
#                                 )
#                             ]
#                         )
#                     )
#                     print(f"   Category '{category}': {count_result.count} total chunks")
                    
#                     if count_result.count == 0:
#                         print(f"   ⚠️ No documents at all in category '{category}'!")
#                         print(f"   Available categories might be: {KNOWLEDGE_BASE_CATEGORIES}")
                        
#                         # Show sample of categories that do exist
#                         sample_points = qdrant_service.client.scroll(
#                             collection_name=collection_name,
#                             limit=10,
#                             with_payload=True
#                         )[0]
                        
#                         existing_categories = set()
#                         for point in sample_points:
#                             cat = point.payload.get("metadata", {}).get("category")
#                             if cat:
#                                 existing_categories.add(cat)
                        
#                         print(f"   Found categories in DB: {sorted(existing_categories)}")
#             except Exception as e:
#                 print(f"   Error checking category content: {e}")
        
#         if not high_confidence_matches:
#             print(f"\n💡 No high confidence results found. Proposing generation.")
            
#             # SAVE CONTEXT for potential generation next turn
#             LAST_SEARCH_CONTEXT["query"] = query
#             LAST_SEARCH_CONTEXT["category"] = category
            
#             # Use LLM to formulate a polite refusal with suggestion
#             prompt = f"""Użytkownik pyta o: "{query}".
# Przeszukałeś bazę wiedzy i znalazłeś {len(search_results)} dokumentów, ale wszystkie mają niskie dopasowanie (poniżej 45%).
# Najlepsze dopasowanie: {max([r.get('confidence',0) for r in search_results]) if search_results else 0}%

# Twoim zadaniem jest:
# 1. Poinformować użytkownika, że nie znalazłeś satysfakcjonujących dokumentów w obecnej bazie.
# 2. Zapytać użytkownika, czy chce, abyś wygenerował (stworzył) ten dokument teraz.
# 3. Poinstruować go, że jeśli się zgadza, wystarczy że napisze: "Tak, wygeneruj".

# Odpowiedz krótko i konkretnie w języku polskim."""
            
#             suggestion_response = llm_service.generate_response(prompt, temperature=0.3)
            
#             return {
#                 "found": False,
#                 "message": suggestion_response,
#                 "query": query,
#                 "category": category,
#                 "total_results": len(filtered_results),
#                 "response_type": "not_found_suggestion",
#                 "debug_info": {
#                     "total_chunks_retrieved": len(search_results),
#                     "knowledge_base_chunks": len(knowledge_results),
#                     "special_cases": len(special_results),
#                     "max_confidence": max([r.get('confidence',0) for r in search_results]) if search_results else 0,
#                     "category_content_count": count_result.count if 'count_result' in locals() else "unknown"
#                 }
#             }
        
#         # If we have good results, proceed with standard RAG response
#         print(f"\n✅ Found {len(high_confidence_matches)} high confidence chunks from {len(unique_documents)} documents")
#         print(f"\n📝 Generating response...")
        
#         # 4. Build prompt
#         prompt = build_enhanced_prompt(query, filtered_results, category)
        
#         # 5. Generate response
#         response = llm_service.generate_response(prompt)
        
#         # 6. Parse response
#         result = parse_rag_response(response, filtered_results)
        
#         # Add metadata
#         result["query"] = query
#         result["category"] = category
#         result["total_results"] = len(filtered_results)
#         result["high_confidence_results"] = len(high_confidence_matches)
#         result["unique_documents"] = len(unique_documents)
        
#         return result
        
#     except Exception as e:
#         print(f"ERROR in search_similar_case: {str(e)}")
#         import traceback
#         traceback.print_exc()
#         return {
#             "found": False,
#             "message": f"System error: {str(e)}",
#             "query": query
#         }

# def search_similar_case(query: str) -> Dict[str, Any]:
#     """
#     Enhanced search with RAG and Generation Capability
#     """
#     global LAST_SEARCH_CONTEXT
    
#     try:
#         # 0. Check for explicit generation intent FIRST
#         is_generation = detect_generation_intent(query)
#         category = classify_query_category(query)
        
#         # Handle "Confirmation" of generation (e.g. "Tak, wygeneruj")
#         topic_to_generate = query
        
#         if is_generation:
#             clean_query = query.lower().strip()
#             # If query is short (e.g. "tak wygeneruj") and we have context, use context
#             if len(clean_query.split()) < 6 and LAST_SEARCH_CONTEXT["query"]:
#                 print(f"DEBUG: Detected confirmation for previous topic: {LAST_SEARCH_CONTEXT['query']}")
#                 topic_to_generate = LAST_SEARCH_CONTEXT["query"]
#                 if LAST_SEARCH_CONTEXT["category"] != ALL_CATEGORIES_KEY:
#                     category = LAST_SEARCH_CONTEXT["category"]
        
#         if is_generation:
#             print(f"\n=== GENERATION REQUEST DETECTED ===")
#             print(f"Query: {query}")
#             print(f"Topic used for generation: {topic_to_generate}")
#             print(f"Category: {category}")
            
#             # Generate the document using the proper topic
#             file_info = document_generator.generate_document(topic_to_generate, category)
            
#             if file_info.get("success"):
#                 # POPRAWKA: Dodanie linku i nazwy pliku bezpośrednio do treści wiadomości
#                 download_url = file_info.get("download_url", "")
#                 filename = file_info.get("name", "dokument.docx")
                
#                 response_msg = (
#                     f"Zgodnie z Twoją prośbą wygenerowałem dokument na temat: '{topic_to_generate}'.\n"
#                     f"Został on zapisany w kategorii '{category}'.\n\n"
#                     f"📄 **Nazwa pliku:** {filename}\n"
#                     f"🔗 **Link do pobrania:** {download_url}"
#                 )
                
#                 # Clear context after successful generation
#                 LAST_SEARCH_CONTEXT = {"query": None, "category": None}
                
#                 return {
#                     "found": True,
#                     "generated_file": file_info,
#                     "message": response_msg,
#                     "query": query,
#                     "category": category,
#                     "response_type": "generated_document"
#                 }
#             else:
#                 return {
#                     "found": False,
#                     "message": f"Wystąpił błąd podczas generowania dokumentu: {file_info.get('error')}",
#                     "query": query
#                 }

#         # 1. Standard RAG Search
#         print(f"\n=== RAG SEARCH ===")
#         print(f"Query: '{query}'")
#         print(f"LLM Category: {category}")
        
#         # 2. Search ALL documents in this category
#         search_results = search_by_category(query, category=category)
        
#         # 3. Filter low confidence results (<20%)
#         filtered_results = [r for r in search_results if r.get("confidence", 0) >= 20]
        
#         # NEW LOGIC: Handling "Not Found" with generation proposal
#         # Check if we have any high confidence matches (>45%)
#         high_confidence_matches = [r for r in filtered_results if r.get("confidence", 0) >= 45]
        
#         if not high_confidence_matches:
#             print(f"No high confidence results found. Proposing generation.")
            
#             # SAVE CONTEXT for potential generation next turn
#             LAST_SEARCH_CONTEXT["query"] = query
#             LAST_SEARCH_CONTEXT["category"] = category
            
#             # Use LLM to formulate a polite refusal with suggestion
#             prompt = f"""Użytkownik pyta o: "{query}".
# Przeszukałeś bazę wiedzy i nie znalazłeś satysfakcjonujących dokumentów (wyniki są słabe).
# Twoim zadaniem jest:
# 1. Poinformować użytkownika, że nie znalazłeś takiego dokumentu w obecnej bazie.
# 2. Zapytać użytkownika, czy chce, abyś wygenerował (stworzył) ten dokument teraz.
# 3. Poinstruować go, że jeśli się zgadza, wystarczy że napisze: "Tak, wygeneruj".

# Odpowiedz krótko i konkretnie w języku polskim."""
            
#             suggestion_response = llm_service.generate_response(prompt, temperature=0.3)
            
#             return {
#                 "found": False,
#                 "message": suggestion_response,
#                 "query": query,
#                 "category": category,
#                 "total_results": len(filtered_results),
#                 "response_type": "not_found_suggestion"
#             }
        
#         # If we have good results, proceed with standard RAG response
#         print(f"Results after confidence filter: {len(filtered_results)}/{len(search_results)}")
        
#         # 4. Build prompt
#         prompt = build_enhanced_prompt(query, filtered_results, category)
        
#         # 5. Generate response
#         response = llm_service.generate_response(prompt)
        
#         # 6. Parse response
#         result = parse_rag_response(response, filtered_results)
        
#         # Add metadata
#         result["query"] = query
#         result["category"] = category
#         result["total_results"] = len(filtered_results)
#         result["high_confidence_results"] = len(high_confidence_matches)
        
#         return result
        
#     except Exception as e:
#         print(f"ERROR in search_similar_case: {str(e)}")
#         import traceback
#         traceback.print_exc()
#         return {
#             "found": False,
#             "message": f"System error: {str(e)}",
#             "query": query
#         }

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