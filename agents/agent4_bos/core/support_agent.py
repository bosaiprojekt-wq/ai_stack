#imports
import json
from typing import Dict, Any, List
from .qdrant_service import qdrant_service, load_all_cases
from .config import KNOWLEDGE_BASE_PATH, SPECIAL_CASES_PATH, KNOWLEDGE_BASE_CATEGORIES, ALL_CATEGORIES_KEY
from .llm_service import llm_service
from .document_generator import document_generator 

LAST_SEARCH_CONTEXT = {"query": None, "category": None}

#CLASSIFICATION OF QUERY
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
            temperature=0.5,
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

#SEARCH FUNCTION WITH CATEGORY FILTER
#CHUNK GROUPING FOR BETTER CONFIDENCE ASSESSMENT
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
        
        # Add chunk to documens{}
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
        doc["all_content"] = [c["text"] for c in doc["chunks"]] 
        
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
        payload = result.get("payload", {})
        special_cases.append({
            "filename": f"Case: {payload.get('title', 'Unknown')}",
            "source": "special_cases",
            "category": "Special Case",
            "confidence": round(result.get("score", 0) * 100, 1),
            "content": f"{payload.get('description', '')}\n\n{payload.get('solution', '')}",
            "collection": "special_cases",
            "case_id": payload.get("case_id", "unknown"),
            "title": payload.get("title", "Unknown"),
            "author": payload.get("author", "Unknown")
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
        else:
            print(f"\n{i}.{doc['filename']}")
            print(f"   Confidence: {doc['confidence']}%")
    print("\n" + "=" * 60)
    
   
    return all_docs

#GENERATION INTENT DETECTION - avoid generating documents without user confirmation
def detect_generation_intent(query: str) -> bool:
    """Check if the user explicitly wants to generate a document"""
    keywords = ["wygeneruj", "stwórz", "napisz", "przygotuj", "sporządź"]
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in keywords)

#MAIN SEARCH FUNCTION WITH RAG
def search_similar_case(query: str) -> Dict[str, Any]:
    """
    Enhanced search with RAG and Generation Capability
    Groups chunks by source file, returns full documents
    """
    global LAST_SEARCH_CONTEXT
    
    try:
        # Check for explicit generation intent
        is_generation = detect_generation_intent(query)
        category = classify_query_category(query)
        
        # Handle "Confirmation" of generation
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
                    f"Nazwa pliku: {filename}\n"
                    f"Link do pobrania: {download_url}"
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

        # CONSOLE DEBUG - show query and category
        print("RAG SEARCH")
        print(f"Query: '{query}'")
        print(f"LLM Category: {category}")
        
        # Search knowledge_base with category filter
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
        
        # Search special_cases
        print(f"Searching special cases for: '{query}'")
        case_results = qdrant_service.search(query, collection="special_cases", limit=50)
                
        print(f"Raw results: {len(knowledge_results)} knowledge chunks, {len(case_results)} special cases")
        
        # group knowledge chunks by source_file
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
            
            # Add chunk
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
            
            # Calculate document confidence
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
        
        # Format special cases
        special_cases = []
        for result in case_results:
            
            payload = result.get("payload", {})
            
            confidence = round(result.get("score", 0) * 100, 1)
            
            
            special_cases.append({
                "filename": f"Sprawa: {payload.get('title', 'Unknown')}",
                "source": "special_cases",
                "category": "Przypadek specjalny",
                "confidence": confidence,
                "content": f"Tytuł: {payload.get('title', '')}\nOpis: {payload.get('description', '')}\nRozwiązanie: {payload.get('solution', '')}\nUwagi: {payload.get('additional_notes', '')}",
                "collection": "special_cases",
                "type": "Form Response",
                "case_id": payload.get("case_id", "unknown"),
                "title": payload.get("title", "Unknown"),
                "author": payload.get("author", "Nieznany"),
                "created_at": payload.get("created_at", ""),
                "description": payload.get("description", ""),
                "solution": payload.get("solution", ""),
                "notes": payload.get("additional_notes", "")
            })
        
        # Combine all documents
        all_docs = knowledge_docs + special_cases
        all_docs.sort(key=lambda x: x["confidence"], reverse=True)
        
        # DISPLAY TOP 3 RESULTS
    
        print("TOP 3 MOST RELEVANT DOCUMENTS")
        
        if not all_docs:
            print("\nNo documents found.")
        else:
            for i, doc in enumerate(all_docs[:3], 1):
                if doc["collection"] == "knowledge_base":
                    print(f"\n{i}. {doc['filename']}")
                    print(f"   Kategoria: {doc['category']}")
                    print(f"   Dopasowanie: {doc['confidence']}% (maks), {doc.get('avg_confidence', 0)}% (średnia)")
                    print(f"   Chunków: {doc['chunk_count']}/{doc['total_chunks']}")
                    # Show preview of first 200 chars
                    #preview = doc['content'][:200].replace('\n', ' ').strip()
                    #print(f"   Podgląd: {preview}...")
                else:
                    print(f"\n{i}. {doc['filename']}")
                    #print(f"   Autor: {doc.get('author', 'Nieznany')}")
                    print(f"   Dopasowanie: {doc['confidence']}%")
                    #preview = doc['content'][:200].replace('\n', ' ').strip()
                    #print(f"   Podgląd: {preview}...")
        
        print(f"Znaleziono {len(all_docs)} dokumentów")
        
        # Check if we have good matches
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
        
        # Use the best document for response
        best_doc = good_matches[0]
        
        print(f"\nWybrano dokument do odpowiedzi:")
        print(f"   Tytuł: {best_doc['filename']}")
        print(f"   Dopasowanie: {best_doc['confidence']}%")
        print(f"   Długość treści: {len(best_doc['content'])} znaków")
        print(f"{'='*60}\n")
        
        # Build prompt with complete document
        prompt = build_document_prompt(query, best_doc, category)
        
        # Generate response
        response = llm_service.generate_response(prompt)
        
        # Parse response
        result = parse_rag_response(response, [best_doc])
        
        # Add metadata
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

#PROMPT BUILDING b(ased on document type - knowledge_base, special_cases, no info)
def build_document_prompt(query: str, document: Dict[str, Any], category: str = None) -> str:
    """
    Build prompt with single complete document
    Trzy przypadki: knowledge_base, special_cases, brak informacji
    """
    file_path = document.get("source", "").replace("/app/qdrant_data/", "data/")
    doc_type = document.get("collection", "knowledge_base")
    
    #KNOWLEDGE_BASE
    if doc_type == "knowledge_base":
        return f"""Jesteś asystentem Biura Obsługi Studenta. Pomagasz pracownikom dziekanatu.

PYTANIE: "{query}"

DOKUMENT ŹRÓDŁOWY:
Plik: {document['filename']}
Ścieżka: {file_path}
Kategoria: {document.get('category', 'unknown')}
Dopasowanie: {document['confidence']}%

TREŚĆ DOKUMENTU:
{document['content']}

INSTRUKCJE:
1. Odpowiedz na pytanie WYŁĄCZNIE na podstawie tego dokumentu.
2. Odpowiadaj po polsku.
3. NIE cytuj dosłownie formularza (nie wypisuj pól).
4. Jeśli to formularz/wniosek - wyjaśnij do czego służy i gdzie go złożyć.
5. Na końcu podaj link i dopasowanie.

ODPOWIEDŹ:"""
    
    # SPECIAL_CASES
    elif doc_type == "special_cases":
        # Formatuj datę na DD.MM.YYYY
        created_date = document.get('created_at', '')
        if created_date and len(created_date) >= 10:
            date_parts = created_date[:10].split('-')
            created_date = f"{date_parts[2]}.{date_parts[1]}.{date_parts[0]}"
        else:
            created_date = "brak daty"
        
        return f"""Jesteś asystentem Biura Obsługi Studenta. Pomagasz pracownikom dziekanatu.

PYTANIE: "{query}"

ZNALEZIONY PRZYPADEK HISTORYCZNY:
Tytuł: {document.get('title', 'unknown')}
Opis: {document.get('description', 'Brak opisu')}
Rozwiązanie: {document.get('solution', 'Brak rozwiązania')}
Dopasowanie: {document['confidence']}%

INSTRUKCJE:
1. To jest historyczny przypadek rozwiązania podobnego problemu.
2. Wyjaśnij dlaczego ten przypadek pasuje do pytania.
3. Opisz jak rozwiązano ten przypadek.
4. Odpowiadaj po polsku.
5. Użyj formatu z poniższego przykładu.

ODPOWIEDŹ:
---
Przypadek nr: {document.get('case_id', 'unknown')}
Podobieństwo: {document['confidence']}%
Uzasadnienie dopasowania: [napisz 1-2 zdania dlaczego ten przypadek pasuje]
Data: {created_date}
Tytuł: {document.get('title', 'unknown')}
Autor: {document.get('author', 'Nieznany')}
Opis: {document.get('description', 'Brak opisu')}
Rozwiązanie: {document.get('solution', 'Brak rozwiązania')}
Uwagi: {document.get('notes', document.get('additional_notes', 'Brak uwag'))}
---"""
    
    # PRZYPADEK 3: BRAK INFORMACJI (gdy dokument jest None lub nieznany typ)
    else:
        return f"""Jesteś asystentem Biura Obsługi Studenta.

PYTANIE: "{query}"

Nie znaleziono odpowiednich dokumentów w bazie wiedzy.

INSTRUKCJE:
1. Poinformuj użytkownika, że nie znaleziono informacji.
2. Zaproponuj wygenerowanie nowego dokumentu.
3. Odpowiadaj po polsku.

ODPOWIEDŹ:
Nie posiadam informacji na ten temat w aktualnej bazie wiedzy.

Czy chcesz, abym wygenerował dokument z procedurą?"""

#RAG RESPONSE PARSING - extract sources, confidence, check if info found
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


