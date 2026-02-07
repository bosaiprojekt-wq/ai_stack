
agent4_bos/
├── app.py                          # Main FastAPI app - mounts sub-apps, defines main endpoints
├── main.py                         # Application launcher - starts uvicorn server
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Docker build configuration
├── docker-compose.yml              # Docker orchestration (with Qdrant)

│
├── api/                            # API layer - endpoint handlers
│   ├── __init__.py
│   ├── support_api.py              # Handles /support endpoint - searches cases in knowledge base
│   └── protocol_api.py             # Handles /protocols endpoint - university protocols queries
│
├── core/                           # Core business logic
│   ├── __init__.py
│   ├── config.py                   # Configuration (Qdrant, collections, paths)
│   ├── qdrant_service.py          # Qdrant client + DB helpers (merged from file_utils)
│   ├── llm_service.py              # LLM client (ChatOllama) with retry logic
│   ├── support_agent.py            # AI agent for case similarity search
│   ├── qdrant_service.py           # Qdrant client for cases collection
│
└── web/                            # Web interface layer
    ├── __init__.py
    ├── forms.py                    # Form sub-app (/form) - HTML form for adding cases
    ├── run_interface.py            # Run page sub-app (/run_page) - AI response interface
    └── templates/                  # HTML templates
        ├── dashboard.html          # Main dashboard with links to all services
        ├── run_page.html           # AI response generation interface


Endponts:
    POST /support -Wyszukiwanie w bazie cases
    GET /run_page - Interfejs webowy dla /support
    GET /cases - Lista przypadków (cases)
    GET /health - Status serwisu
    GET /form - Formularz HTML
    POST /form/submit - Zapis formularza




HOW TO RUN THE PROJECT

run ollama and qdrant containers BEFORE agent


each agent change needs those comments to work:
    sudo docker-compose down
    sudo docker-compose build --no-cache
    sudo docker-compose up

if you made pull from git, it's best to do this for all containers:
    sudo docker-compose down
    sudo docker-compose build --no-cache
    sudo docker-compose up


in web search for:
dashboard: http://localhost:8004/
Qdrant: http://localhost:6333/dashboard#/collections
endpoint docs: http://localhost:8004/docs#/
Node-RED:http://localhost:1880/ (files for inport in the nodered/Procesy folder)


