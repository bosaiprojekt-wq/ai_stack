import os
from pathlib import Path
from typing import Dict, List
from utils.embeddings import embed
from utils.qdrant_client import client
from langchain_community.chat_models import ChatOllama

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
llm = ChatOllama(model="llama3", base_url=OLLAMA_URL, temperature=0.1)

# === SIMPLE QDRANT SEARCHER ===
def search_qdrant_naturally(question: str, collection: str) -> List[Dict]:
    """Search Qdrant using the question's natural meaning."""
    vector = embed(question)
    
    try:
        response = client.query_points(
            collection_name=collection,
            query=vector,
            using="default",
            limit=3,
            with_payload=True,
            score_threshold=0.5
        )
        
        results = []
        
        # Check different response formats
        if hasattr(response, 'points'):
            # Newer Qdrant format
            for point in response.points:
                # Access attributes properly
                payload = {}
                if hasattr(point, 'payload'):
                    # Convert payload object to dict if needed
                    if hasattr(point.payload, '__dict__'):
                        payload = point.payload.__dict__
                    else:
                        payload = point.payload
                
                # Get file_name with fallbacks
                file_name = payload.get('file_name', 
                                      payload.get('tytul', 
                                                'Unknown Document'))
                
                # Get content with fallbacks
                content = payload.get('text', 
                                    payload.get('opis', 
                                              payload.get('content', '')))
                
                results.append({
                    "file_name": file_name,
                    "content": content,
                    "score": point.score,
                    "source": "qdrant"
                })
                
        elif hasattr(response, 'hits'):
            # Older Qdrant format
            for hit in response.hits:
                results.append({
                    "file_name": hit.payload.get('file_name', 
                                               hit.payload.get('tytul', 'Unknown Document')),
                    "content": hit.payload.get('text', 
                                             hit.payload.get('opis', '')),
                    "score": hit.score,
                    "source": "qdrant"
                })
        
        print(f"🔍 Found {len(results)} results from {collection}")
        return results
        
    except Exception as e:
        print(f"❌ Qdrant search error in '{collection}': {e}")
        return []

# === SIMPLE FILE SEARCHER ===
def search_files_naturally(question: str) -> List[Dict]:
    """
    Natural file search: LLM suggests which files to check based on the question.
    This mimics how a human would think about finding files.
    """
    print(f"🔍 Natural file search for: '{question}'")
    
    # 1. Get list of files
    docs_path = Path("/qdrant_data/documents")
    if not docs_path.exists():
        print(f"⚠️ Documents path not found: {docs_path}")
        return []
    
    files = list(docs_path.iterdir())
    if not files:
        print("⚠️ No files found in documents directory")
        return []
    
    file_list = "\n".join([f"{i+1}. {f.name}" for i, f in enumerate(files[:10])])  # First 10 files
    
    # 2. Ask LLM which files might be relevant
    prompt = f"""Based on this question, suggest which files in the 'documents' folder might contain relevant information.

QUESTION: "{question}"

Available files:
{file_list}

Which file(s) should I check first? List them in order of relevance.
Respond with ONLY file names separated by commas, or 'none' if no files seem relevant.

Example responses:
- "sample1.docx, TXT test file Purpose.txt"
- "sample1.docx"
- "none"
"""
    
    try:
        response = llm.invoke(prompt).content.strip()
        print(f"🤖 LLM suggests checking: {response}")
        
        if response.lower() == "none":
            return []
        
        # 3. Check suggested files
        suggested_files = [f.strip() for f in response.split(",")]
        results = []
        
        for filename in suggested_files:
            file_path = docs_path / filename
            
            if not file_path.exists():
                print(f"⚠️ File not found: {filename}")
                continue
            
            # Read file content
            try:
                if filename.endswith('.docx'):
                    from docx import Document
                    doc = Document(file_path)
                    content = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
                elif filename.endswith('.txt'):
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                else:
                    print(f"⚠️ Skipping unsupported file type: {filename}")
                    continue
                
                # Simple relevance check
                question_keywords = set(question.lower().split())
                content_lower = content.lower()
                
                relevance_score = 0
                for keyword in question_keywords:
                    if len(keyword) > 3 and keyword in content_lower:
                        relevance_score += 1
                
                results.append({
                    "file_name": filename,
                    "content": content[:500],  # First 500 chars
                    "relevance": relevance_score,
                    "full_content": len(content)
                })
                
                print(f"✅ Found {filename} (relevance: {relevance_score})")
                
            except Exception as e:
                print(f"❌ Error reading {filename}: {e}")
        
        # Sort by relevance
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results
        
    except Exception as e:
        print(f"❌ File search error: {e}")
        return []

# === NATURAL AGENT ===
def natural_agent_answer(question: str) -> Dict:
    """
    Simple, natural approach:
    1. Understand the question naturally (it's an LLM!)
    2. Look through files if that makes sense
    3. Search Qdrant if files don't have answer
    4. Be helpful like a human assistant
    """
    print(f"\n{'='*60}")
    print(f"🧠 Natural Agent processing: '{question}'")
    
    # Step 1: Determine intent
    intent_prompt = f"""Is the user asking about:
A) Files/folders (e.g., "ile plików", "co zawiera plik", file names)
B) University information (e.g., regulations, procedures, policies)
C) Greeting or general chat

QUESTION: "{question}"

Respond with ONLY A, B, or C."""
    
    try:
        intent = llm.invoke(intent_prompt).content.strip()
        print(f"🎯 Intent: {intent}")
    except Exception as e:
        print(f"❌ Intent detection failed: {e}")
        intent = "B"  # Default to document search
    
    # Step 2A: Handle file questions
    if intent == "A":
        print("📁 Searching files naturally...")
        file_results = search_files_naturally(question)
        
        if file_results:
            # Build answer from file contents
            context = "\n\n".join([
                f"Z pliku '{r['file_name']}':\n{r['content']}"
                for r in file_results[:2]  # Top 2 files
            ])
            
            answer_prompt = f"""Użytkownik zapytał: "{question}"

Odnaleziono te pliki:
{context}

Odpowiedz naturalnie na podstawie zawartości plików. Jeśli informacji nie ma, powiedz to.
Odpowiedz po polsku, zwięźle, jak prawdziwy asystent."""
            
            try:
                answer = llm.invoke(answer_prompt).content
            except Exception as e:
                answer = f"Przepraszam, wystąpił błąd podczas przetwarzania plików: {e}"
            
            return {
                "odpowiedz": answer,
                "pewnosc": "wysoka",
                "zrodla": [r["file_name"] for r in file_results],
                "kolekcja": "files",
                "draft": False
            }
        else:
            # No relevant files found
            return {
                "odpowiedz": f"Przejrzałem dostępne pliki, ale nie znalazłem informacji na temat '{question}'.\n\nMożesz spróbować:\n1. Sprawdzić oficjalną stronę uczelni\n2. Zapytać w dziekanacie\n3. Przeszukać dokumenty regulaminowe",
                "pewnosc": "niska",
                "zrodla": [],
                "kolekcja": "files_not_found",
                "draft": False
            }
    
    # Step 2B: Handle document questions (RAG)
    elif intent == "B":
        print("📚 Searching documents in Qdrant...")
        
        # Try official documents first
        doc_results = search_qdrant_naturally(question, "collection_documents")
        
        if not doc_results:
            # Try special cases
            print("🔍 Trying special cases...")
            doc_results = search_qdrant_naturally(question, "special_cases")
        
        if doc_results:
            # Build context
            context = "\n\n".join([
                f"Z dokumentu '{r['file_name']}':\n{r['content'][:400]}..."
                for r in doc_results[:2]
            ])
            
            answer_prompt = f"""Jesteś asystentem administracyjnym uczelni.
Odpowiedz na pytanie na podstawie poniższych dokumentów:

PYTANIE: {question}

DOKUMENTY:
{context}

Odpowiedz po polsku, zwięźle i pomocnie. Jeśli dokumenty nie zawierają odpowiedzi, przyznaj to."""
            
            try:
                answer = llm.invoke(answer_prompt).content
            except Exception as e:
                answer = f"Przepraszam, wystąpił błąd podczas generowania odpowiedzi: {e}"
            
            return {
                "odpowiedz": answer,
                "pewnosc": "wysoka",
                "zrodla": [r["file_name"] for r in doc_results],
                "kolekcja": "official" if doc_results[0].get("source") == "qdrant" else "special_cases",
                "draft": False
            }
        else:
            # No documents found
            return {
                "odpowiedz": f"Przeszukałem dokumenty uczelniane, ale nie znalazłem informacji na temat '{question}'.\n\nMoże to być:\n1. Nowa sytuacja wymagająca decyzji dziekanatu\n2. Informacja dostępna tylko w dziekanacie\n3. Temat nieobjęty dokumentacją",
                "pewnosc": "niska",
                "zrodla": [],
                "kolekcja": "no_documents",
                "draft": False
            }
    
    # Step 2C: Handle greetings/chat
    else:  # intent == "C" or default
        answer_prompt = f"""Jesteś przyjaznym asystentem administracyjnym uczelni.
Użytkownik powiedział: "{question}"

Odpowiedz naturalnie, po polsku, jak w normalnej rozmowie.
Możesz zapytać, w czym możesz pomóc."""
        
        try:
            answer = llm.invoke(answer_prompt).content
        except Exception as e:
            answer = f"Witaj! Przykro mi, ale wystąpił błąd: {e}"
        
        return {
            "odpowiedz": answer,
            "pewnosc": "wysoka",
            "zrodla": [],
            "kolekcja": "chat",
            "draft": False
        }