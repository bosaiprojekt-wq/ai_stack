
# Spis treści

1. **[Wprowadzenie](#wprowadzenie)**

2. **[Architektura projektu](#architektura-projektu)**

3. **[Struktura projektu](#struktura-projektu)**
   - [app.py](#appy)
   - [main.py](#mainpy)
   - [config.py](#configpy)
   - [qdrant_service.py](#qdrant_servicepy)
   - [document_processor.py](#document_processorpy)
   - [document_ingestor.py](#document_ingestorpy)
   - [llm_service.py](#llm_servicepy)
   - [document_generator.py](#document_generatorpy)
   - [support_agent.py](#support_agentpy)

4. **[Przepływ danych w systemie](#przepływ-danych-w-systemie)**

5. **[Technologie](#technologie)**

6. **[Przepływ działania systemu krok po kroku](#przepływ-działania-systemu-krok-po-kroku)**
   - [1. Uruchomienie projektu](#1-uruchomienie-projektu)
   - [2. Zadanie zapytania przez użytkownika](#2-zadanie-zapytania-przez-użytkownika)
   - [3. Poproszenie o wygenerowanie nowego pliku](#3-poproszenie-o-wygenerowanie-nowego-pliku)




# Agent4 BOS - Asystent Biura Obsługi Studenta

System asystenta AI wspomagający pracowników BOS w wyszukiwaniu informacji w bazie wiedzy oraz generowaniu dokumentów. Wykorzystuje Retrieval Augmented Generation (RAG) do łączenia wyszukiwania semantycznego z modelem językowym.

# Architektura projektu

```text
ai_stack/
├── Open_WebUI/
│   └── docker-compose.yml
├── agents/
│   └── agent4_bos/
│       ├── Dockerfile
│       ├── README.md
│       ├── app.py
│       ├── docker-compose.yml
│       ├── main.py
│       ├── requirements-batch-1.txt
│       ├── requirements-batch-2.txt
│       ├── requirements-batch-3.txt
│       ├── api/
│       │   ├── __init__.py
│       │   └── api.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── document_generator.py
│       │   ├── document_ingestor.py
│       │   ├── document_processor.py
│       │   ├── llm_service.py
│       │   ├── qdrant_service.py
│       │   └── support_agent.py
│       └── web/
│           ├── __init__.py
│           ├── forms.py
│           ├── run_interface.py
│           └── templates/
│               ├── dashboard.html
│               └── run_page.html
├── nodered/
│   ├── docker-compose.yml
│   └── Procesy/
│       └── flows.json
├── ollama/
│   └── docker-compose.yml
├── qdrant/
│   └── docker-compose.yml
├── qdrant_data/
│   ├── knowledge_base/
│   │   ├── dane_osobowe/
│   │   ├── egzaminy/
│   │   ├── rekrutacja/
│   │   ├── stypendia/
│   │   ├── urlopy_zwolnienia/
│   ├── special_cases/
│   └── storage/
└
```
## Struktura projektu

### **app.py**
Główna aplikacja FastAPI, punkt wejścia do systemu integrujący wszystkie komponenty i udostępniający interfejsy API.

**Endpointy główne:**
- `GET /` - Strona główna dashboard z linkami do usług
- `POST /support` - Główny endpoint agenta do zapytań
- `GET /health` - Sprawdzanie stanu systemu (baza danych i LLM)

**Endpointy zarządzania danymi:**
- `GET /cases` - Lista przypadków specjalnych
- `GET /info` - Informacje o bazie danych
- `GET /collections/info` - Szczegółowe informacje o kolekcjach Qdrant
- `GET /files/paths` - Skonfigurowane ścieżki plików

**Endpointy ingestii:**
- `POST /ingest/knowledge-base` - Indeksowanie bazy wiedzy
- `POST /ingest/special-cases` - Indeksowanie przypadków specjalnych
- `POST /ingest/all` - Indeksowanie wszystkich dokumentów

**Montowane podaplikacje:**
- `/form` - Aplikacja formularza
- `/run_page` - Interfejs czatu
- `/data` - Statyczne pliki do pobrania

---

### **main.py**
Plik uruchomieniowy odpowiedzialny za inicjalizację systemu, ingestię danych przy starcie i uruchomienie serwera.

**Funkcje:**
- `run_startup_ingestion()` - Czyszczenie kolekcji i ingestia wszystkich dokumentów z folderów knowledge_base i special_cases
- `start_background_watcher()` - Uruchomienie wątku monitorującego foldery pod kątem nowych plików

**Proces uruchomienia:**
1. Uruchomienie ingestii startowej w tle
2. Start obserwatora plików do automatycznej ingestii
3. Uruchomienie serwera FastAPI na porcie 8000

---

### **config.py**
Plik konfiguracyjny zawierający ustawienia środowiskowe, ścieżki i stałe.

**Konfiguracja Qdrant:**
- `QDRANT_HOST` - Host serwera Qdrant (domyślnie: "qdrant")
- `QDRANT_PORT` - Port serwera Qdrant (domyślnie: 6333)
- `SPECIAL_CASES_COLLECTION` - Kolekcja przypadków specjalnych (domyślnie: "agent4_bos_cases")
- `KNOWLEDGE_BASE_COLLECTION` - Kolekcja bazy wiedzy (domyślnie: "agent4_knowledge_base")

**Ścieżki folderów:**
- `BASE_DATA_PATH` - Główna ścieżka danych (domyślnie: "/app/qdrant_data")
- `KNOWLEDGE_BASE_PATH` - Folder bazy wiedzy
- `SPECIAL_CASES_PATH` - Folder przypadków specjalnych

**Kategorie bazy wiedzy:**
- `dane_osobowe` - Dokumenty dotyczące danych osobowych i RODO
- `egzaminy` - Regulaminy, terminy, procedury egzaminacyjne
- `rekrutacja` - Procedury rekrutacyjne, wymagane dokumenty
- `stypendia` - Zasady przyznawania stypendiów, wnioski
- `urlopy_zwolnienia` - Urlopy dziekańskie, zwolnienia lekarskie
- `ALL_CATEGORIES_KEY` - Stała "all" oznaczająca wszystkie kategorie

**Funkcje:**
- `ensure_directories()` - Tworzenie niezbędnych katalogów przy imporcie

---

### **qdrant_service.py**
Serwis do zarządzania bazą wektorową Qdrant, odpowiedzialny za przechowywanie i wyszukiwanie dokumentów z wykorzystaniem embeddingów.

**Klasa QdrantService:**

**Metody zarządzania kolekcjami:**
- `__init__()` - Inicjalizacja połączenia z Qdrant, załadowanie modelu embeddingów, utworzenie kolekcji
- `_ensure_collections()` - Sprawdzenie i utworzenie kolekcji jeśli nie istnieją
- `clear_all_collections()` - Czyszczenie zawartości lub odtworzenie kolekcji
- `clear_collection_contents()` - Czyszczenie tylko zawartości kolekcji

**Metody zapisu:**
- `save_case()` - Zapis przypadku specjalnego z zabezpieczeniem przed duplikatami (próg podobieństwa 85%)
- `save_document_chunk()` - Zapis fragmentu dokumentu do bazy wiedzy

**Metody wyszukiwania:**
- `search()` - Przeszukiwanie jednej lub wszystkich kolekcji
- `search_with_filter()` - Wyszukiwanie z filtrem kategorii
- `search_all_in_category()` - Wyszukiwanie wszystkich dokumentów w określonej kategorii

**Metody pomocnicze:**
- `get_all_cases()` - Pobranie wszystkich przypadków specjalnych
- `get_database_info()` - Informacje o bazie danych
- `_get_collection_count()` - Liczba dokumentów w kolekcji

**Model embeddingów:**
- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- Rozmiar wektora: 384
- Metryka podobieństwa: COSINE

**Funkcje pomocnicze (kompatybilność):**
- `load_all_cases()` - Wrapper dla get_all_cases()
- `list_cases_summary()` - Lista przypadków z podstawowymi danymi
- `get_case_count()` - Liczba przypadków w kolekcji special_cases
- `get_database_info()` - Informacje o bazie danych

**Globalne instancje:**
- `qdrant_service` - Singleton serwisu Qdrant

---

### **document_processor.py**
Moduł do przetwarzania dokumentów, odpowiedzialny za ekstrakcję tekstu z różnych formatów i dzielenie na fragmenty.

**Klasa DocumentProcessor:**

**Metody ekstrakcji tekstu:**
- `__init__()` - Inicjalizacja splittera tekstu z rozmiarem fragmentu 1000 znaków i nakładaniem 200 znaków
- `extract_text()` - Ekstrakcja tekstu z pliku w zależności od rozszerzenia (DOCX, PDF, TXT)
- `_extract_from_docx()` - Wyciąganie tekstu z plików DOCX (akapity i tabele)
- `_extract_from_pdf()` - Wyciąganie tekstu z plików PDF (wszystkie strony)

**Metody przetwarzania:**
- `process_file()` - Przetwarzanie pliku na fragmenty z metadanymi:
  - Unikalne ID (UUID)
  - Tekst fragmentu
  - Metadane: źródło, nazwa pliku, rozszerzenie, rozmiar, hash MD5, indeks fragmentu, liczba fragmentów, kategoria, czas ingestii, data modyfikacji
- `_determine_category()` - Określanie kategorii na podstawie ścieżki pliku
- `_calculate_file_hash()` - Generowanie hasha MD5 pliku do weryfikacji zmian

**Globalne instancje:**
- `document_processor` - Singleton procesora dokumentów

---

### **document_ingestor.py**
Moduł odpowiedzialny za automatyczne przetwarzanie i indeksowanie dokumentów do bazy wektorowej.

**Klasa DocumentIngestor:**

**Metody ingestii:**
- `__init__()` - Inicjalizacja słownika processed_files do śledzenia przetworzonych plików
- `ingest_knowledge_base()` - Przetwarzanie dokumentów z folderu bazy wiedzy
- `ingest_special_cases()` - Przetwarzanie dokumentów z folderu przypadków specjalnych
- `ingest_all()` - Przetwarzanie dokumentów z obu folderów
- `_ingest_folder()` - Główna metoda przetwarzania folderu:
  - Iteracja przez pliki .docx, .pdf, .txt
  - Sprawdzenie czy plik wymaga przetworzenia
  - Przetworzenie przez document_processor
  - Zapis fragmentów do Qdrant
  - Aktualizacja statystyk
- `_should_skip()` - Sprawdzenie czy plik może być pominięty (już przetworzony i niezmieniony)

**Klasa FileWatcher (dziedziczy po FileSystemEventHandler):**
- `__init__()` - Przechowanie referencji do ingestor
- `on_created()` - Handler tworzenia nowego pliku
- `on_modified()` - Handler modyfikacji pliku
- `_process_file()` - Przetwarzanie pojedynczego pliku wykrytego przez watcher

**Funkcje:**
- `start_file_watcher()` - Uruchomienie obserwatora systemu plików monitorującego foldery KNOWLEDGE_BASE_PATH i SPECIAL_CASES_PATH

**Globalne instancje:**
- `document_ingestor` - Singleton ingestor dokumentów

---

### **llm_service.py**
Serwis odpowiedzialny za komunikację z modelem językowym poprzez API Ollama.

**Klasa LLMService:**

**Metody:**
- `__init__()` - Inicjalizacja połączenia z modelem (domyślnie "llama3" na http://ollama:11434)
- `generate_response()` - Generowanie odpowiedzi z mechanizmem ponawiania prób:
  - Wysyłanie zapytania POST do endpointu `/api/generate`
  - Parametry: temperature, max_tokens
  - Do 3 prób z wykładniczym opóźnieniem (2^attempt sekund)
- `get_info()` - Informacje o serwisie (model, base_url, typ serwisu)

**Globalne instancje:**
- `llm_service` - Singleton serwisu LLM

---

### **document_generator.py**
Moduł odpowiedzialny za generowanie dokumentów na podstawie zapytań użytkownika.

**Klasa DocumentGenerator:**

**Metody:**
- `__init__()` - Inicjalizacja z folderem wyjściowym KNOWLEDGE_BASE_PATH
- `generate_document()` - Główna metoda generowania dokumentu:
  - Wywołanie `_generate_content_with_llm()` do utworzenia treści
  - Wywołanie `_create_docx_file()` do zapisu pliku
- `_generate_content_with_llm()` - Generowanie zawartości przez LLM w formacie:
  - NAZWA_PLIKU: [nazwa_z_podkresleniami_bez_polskich_znakow]
  - TYTUŁ: [oficjalny tytuł z prefiksem AI_GEN_]
  - TREŚĆ: [pełna treść dokumentu]
- `_create_docx_file()` - Tworzenie fizycznego pliku DOCX:
  - Dodanie nagłówka z tytułem
  - Dodanie metadanych (data, kategoria)
  - Dodanie treści
  - Określenie folderu docelowego na podstawie kategorii
  - Czyszczenie nazwy pliku (usuwanie niebezpiecznych znaków)
  - Dodanie timestamp i prefiksu "AI_GEN_"
  - Zapis pliku i zwrócenie URL do pobrania

**Format zapisu:**
- Ścieżka: `/data/knowledge_base/[kategoria]/AI_GEN_[nazwa]_[timestamp].docx`

**Globalne instancje:**
- `document_generator` - Singleton generatora dokumentów

---

### **support_agent.py**
Główny plik logiki agenta wsparcia implementujący wyszukiwanie semantyczne z RAG oraz generowanie dokumentów.

**Główne funkcje:**

**Klasyfikacja:**
- `classify_query_category()` - Wykorzystuje LLM do klasyfikacji zapytania do jednej z kategorii bazy wiedzy. Zwraca nazwę kategorii lub "all" gdy zapytanie jest ogólne lub niepewne.

**Wyszukiwanie:**
- `search_by_category()` - Przeszukuje dokumenty w określonej kategorii, grupuje fragmenty według plików źródłowych i zwraca kompletne dokumenty z obliczonym poziomem dopasowania.
- `search_similar_case()` - Główna funkcja wyszukiwania z RAG. Wykonuje klasyfikację kategorii, wyszukiwanie w bazie wiedzy i przypadkach specjalnych, grupuje wyniki oraz generuje odpowiedź. W przypadku wykrycia intencji generowania, uruchamia generator dokumentów.

**Detekcja:**
- `detect_generation_intent()` - Sprawdza czy zapytanie użytkownika zawiera intencję wygenerowania dokumentu (słowa kluczowe: "wygeneruj", "stwórz", "napisz").

**Budowanie promptów:**
- `build_document_prompt()` - Tworzy prompt dla LLM w zależności od typu dokumentu:
  - **Baza wiedzy** - odpowiedź wyłącznie na podstawie dokumentu, wyjaśnienie do czego służy formularz
  - **Przypadki specjalne** - prezentacja historycznego przypadku z uzasadnieniem dopasowania
  - **Brak informacji** - informacja o braku danych i propozycja wygenerowania dokumentu

**Parsowanie:**
- `parse_rag_response()` - Parsuje odpowiedź z LLM, ekstrahuje źródła i poziomy dopasowania, określa czy znaleziono informacje.

**Globalne zmienne:**
- `LAST_SEARCH_CONTEXT` - Przechowuje kontekst ostatniego wyszukiwania (zapytanie i kategoria) do wykorzystania przy potwierdzeniu generowania dokumentu.

---

## Przepływ danych w systemie

1. **Ingestia startowa** - Przy uruchomieniu systemu (main.py) czyszczone są kolekcje Qdrant i uruchamiana jest ingestia wszystkich dokumentów z folderów knowledge_base i special_cases.

2. **Monitorowanie plików** - FileWatcher (document_ingestor.py) obserwuje foldery pod kątem nowych lub zmodyfikowanych plików i automatycznie uruchamia ich przetwarzanie.

3. **Przetwarzanie dokumentów** - DocumentProcessor.py ekstrahuje tekst z plików, dzieli na fragmenty i dodaje metadane.

4. **Zapis do bazy wektorowej** - QdrantService.py generuje embeddingi dla każdego fragmentu i zapisuje w odpowiedniej kolekcji.

5. **Obsługa zapytania użytkownika**:
   - Zapytanie trafia do endpointu `/support` w app.py
   - support_agent.py klasyfikuje kategorię zapytania
   - QdrantService wyszukuje najbardziej podobne dokumenty
   - LLMService generuje odpowiedź na podstawie znalezionych dokumentów (RAG)

6. **Generowanie dokumentu**:
   - Jeśli wykryto intencję generowania, DocumentGenerator tworzy nowy dokument DOCX
   - Plik zapisywany jest w odpowiedniej kategorii w folderze knowledge_base
   - Użytkownik otrzymuje link do pobrania pliku

## Technologie

- **FastAPI** - REST API i serwowanie interfejsów
- **Qdrant** - Baza wektorowa do przechowywania embeddingów
- **Sentence Transformers** - Model do generowania embeddingów dla języka polskiego
- **Ollama** - Lokalny serwer LLM (domyślnie Llama 3)
- **python-docx, PyPDF2** - Ekstrakcja tekstu z dokumentów biurowych
- **LangChain** - Dzielenie tekstu na fragmenty (RecursiveCharacterTextSplitter)
- **Watchdog** - Monitorowanie systemu plików pod kątem zmian
- **Uvicorn** - Serwer ASGI do uruchomienia FastAPI

## Przepływ działania systemu krok po kroku

### 1. Uruchomienie projektu

**main.py** uruchamia:

1. **Ingestię startową** w tle:
   - `qdrant_service.clear_all_collections(delete_structure=False)` - czyszczenie kolekcji
   - `document_ingestor.ingest_knowledge_base()` - przetwarzanie plików z bazy wiedzy
   - `document_ingestor.ingest_special_cases()` - przetwarzanie przypadków specjalnych
   - Dla każdego pliku: `document_processor.process_file()` → ekstrakcja tekstu i podział na fragmenty
   - Dla każdego fragmentu: `qdrant_service.save_document_chunk()` → embedding i zapis do Qdrant

2. **Obserwator plików**:
   - `start_background_watcher()` → `start_file_watcher()`
   - `FileWatcher` monitoruje foldery pod kątem nowych plików

3. **Serwer FastAPI**:
   - `uvicorn.run("app:app")` - start serwera na porcie 8000
   - Inicjalizacja endpointów i zamontowanie podaplikacji

---

### 2. Zadanie zapytania przez użytkownika

Użytkownik wysyła POST `/support` z zapytaniem "Jak złożyć wniosek o urlop dziekański?"

1. **app.py** odbiera zapytanie → `handle_support_request()` → `search_similar_case()`

2. **Wykrycie intencji generowania**:
   - `detect_generation_intent(query)` → False (brak słów kluczowych)

3. **Klasyfikacja kategorii**:
   - `classify_query_category(query)` → prompt do LLM
   - `llm_service.generate_response()` → LLM zwraca "urlopy_zwolnienia"

4. **Wyszukiwanie w Qdrant**:
   - `qdrant_service.search_all_in_category(query, "urlopy_zwolnienia")` - wszystkie dokumenty z kategorii
   - `qdrant_service.search(query, collection="special_cases", limit=50)` - przypadki specjalne

5. **Grupowanie wyników**:
   - Grupowanie fragmentów według `source_file`
   - Sortowanie fragmentów według indeksu
   - Łączenie w pełne dokumenty
   - Obliczanie `max_confidence` i `avg_confidence`

6. **Filtrowanie**:
   - `good_matches = [doc for doc in all_docs if doc["confidence"] >= 35]`
   - Jeśli brak dobrych dopasowań → zapis do `LAST_SEARCH_CONTEXT` i sugestia generowania

7. **Generowanie odpowiedzi RAG**:
   - Wybranie najlepszego dokumentu
   - `build_document_prompt(query, best_doc, category)`
   - `llm_service.generate_response(prompt)`
   - `parse_rag_response()` - ekstrakcja źródeł i odpowiedzi

8. **Zwrócenie JSON** z odpowiedzią do użytkownika

---

### 3. Poproszenie o wygenerowanie nowego pliku

Użytkownik odpowiada "Tak, wygeneruj" lub wysyła "Wygeneruj dokument o urlopie dziekańskim"

1. **Wykrycie intencji generowania**:
   - `detect_generation_intent("Tak, wygeneruj")` → True
   - Zapytanie krótkie (< 6 słów) → użyj `LAST_SEARCH_CONTEXT["query"]` jako tematu

2. **Wywołanie generatora**:
   - `document_generator.generate_document(topic, category)`

3. **Generowanie treści przez LLM**:
   - `_generate_content_with_llm(topic)` → prompt z formatem:
     - NAZWA_PLIKU: [nazwa_z_podkresleniami]
     - TYTUŁ: [oficjalny tytuł z prefiksem AI_GEN_]
     - TREŚĆ: [pełna treść dokumentu]
   - `llm_service.generate_response(prompt, temperature=0.4, max_tokens=2500)`
   - Parsowanie odpowiedzi, ekstrakcja nazwy pliku, tytułu i treści

4. **Tworzenie pliku DOCX**:
   - `_create_docx_file(topic, content, category)`
   - `Document()` - nowy dokument
   - Dodanie nagłówka, daty, kategorii i treści
   - Określenie folderu docelowego na podstawie kategorii
   - Czyszczenie nazwy pliku (usunięcie niebezpiecznych znaków)
   - Dodanie timestamp i prefiksu "AI_GEN_"
   - Zapis pliku: `doc.save(filepath)`

5. **Generowanie URL do pobrania**:
   - `relative_path = f"/data/knowledge_base/{target_category}/{filename}"`

6. **Przygotowanie odpowiedzi**:
   - Sprawdzenie `file_info.get("success")`
   - Budowanie wiadomości z linkiem do pobrania
   - Reset `LAST_SEARCH_CONTEXT`
   - Zwrócenie `response_type: "generated_document"`

7. **Pobranie pliku**:
   - Użytkownik klika link `/data/knowledge_base/.../AI_GEN_*.docx`
   - `StaticFiles` zwraca plik z `BASE_DATA_PATH`