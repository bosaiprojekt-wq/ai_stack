
1) Agent fiels

agent4_bos/
├─ app.py                               # FastAPI service: exposes /run and /special_case; creates DOCX files, generates embeddings, and upserts vectors + metadata into Qdrant
├─ ingest.py                            # Batch ingestion script: walks documents/ and special_cases/, loads files, chunks text, embeds content, and upserts into Qdrant
├─ loaders/
│  ├─ pdf_loader.py                     # PDF loader: extracts text page-by-page from PDF files
│  ├─ txt_loader.py                     # TXT loader: splits plain text files into logical pages/chunks
│  └─ docx_loader.py                    # DOCX loader: extracts paragraphs/text from Word documents
├─ utils/
│  ├─ embeddings.py                     # Embedding helper: calls Ollama embedding API and returns vector representations
│  ├─ qdrant_client.py                  # Qdrant client setup: initializes client, ensures collections exist, handles upsert/search helpers
│  └─ chunking.py                       # Text chunking utility: splits text into overlapping chunks for embedding
├─ requirements.txt                     # Python dependencies for agent4_bos (FastAPI, qdrant-client, langchain, loaders, etc.)
├─ Dockerfile                           # Container build definition for agent4_bos service
├─ docker-compose.yml                   # Runtime configuration: service definition, volumes, network, user/permissions
└─ README.md                            # Documentation placeholder for agent4_bos architecture and usage


2) Datafiles

qdrant_data/
├─ storage/                # Qdrant internal DB (indexes, WAL, segments)
│
├─ documents/              # User-provided documents
│   ├─ *.pdf
│   ├─ *.txt
│   └─ *.docx
│
└─ special_cases/          # Generated DOCX from /special_case form
    └─ *.docx


3) Sequence: special case file

User / Browser / Node-RED
        |
        | POST /special_case
        | (form fields + file metadata)
        v
agent4_bos (FastAPI – app.py)
        |
        | 1. Validate request data
        |
        | 2. Create DOCX file
        |    → /special_cases/<uuid>.docx
        |
        | 3. Extract text from DOCX
        |
        | 4. Generate embeddings
        |    → utils.embeddings.embed(text)
        v
Ollama (Embedding model)
        |
        | 5. Return vector (e.g. 768 floats)
        v
agent4_bos
        |
        | 6. Upsert to Qdrant
        |    → utils.qdrant_client.client.upsert(
        |         id,
        |         vector,
        |         payload (metadata)
        |      )
        v
Qdrant (special_cases collection)
        |
        | 7. Persist vector + payload
        v
agent4_bos
        |
        | 8. HTTP 200 / error response
        v
Client


4) Sequence: run endpoint

User / API / Node-RED
        |
        | POST /run
        | (prompt / input text)
        v
agent4_bos (FastAPI – app.py)
        |
        | 1. Build prompt
        |
        | 2. Call ChatOllama
        v
Ollama (LLM – llama3)
        |
        | 3. Generate response
        v
agent4_bos
        |
        | 4. Return text response
        v
Client



5) useful endpoints
     http://localhost:6333/dashboard
    http://localhost:8004/docs#

