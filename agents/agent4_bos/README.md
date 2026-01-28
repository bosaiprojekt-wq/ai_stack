What does the files do?

agent4_bos/
├── app.py                          # Main FastAPI app - mounts sub-apps, defines main endpoints
├── main.py                         # Application launcher - starts uvicorn server
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Docker build configuration
├── docker-compose.yml              # Docker orchestration (with Qdrant)
├── create_university_db.py         # (Optional) Script to create university protocols database
├── test_protocols.py               # (Optional) Test script for protocol agent
│
├── api/                            # API layer - endpoint handlers
│   ├── __init__.py
│   ├── support_api.py              # Handles /support endpoint - searches cases in knowledge base
│   └── protocol_api.py             # Handles /protocols endpoint - university protocols queries
│
├── core/                           # Core business logic
│   ├── __init__.py
│   ├── config.py                   # Configuration (Qdrant, collections, paths)
│   ├── file_utils.py               # CRUD operations for cases (now using Qdrant)
│   ├── llm_service.py              # LLM client (ChatOllama) with retry logic
│   ├── support_agent.py            # AI agent for case similarity search
│   ├── qdrant_service.py           # Qdrant client for cases collection
│   ├── university_service.py       # Qdrant client for university_protocols collection
│   └── protocol_agent.py           # AI agent for protocol-related queries
│
└── web/                            # Web interface layer
    ├── __init__.py
    ├── forms.py                    # Form sub-app (/form) - HTML form for adding cases
    ├── run_interface.py            # Run page sub-app (/run_page) - AI response interface
    ├── protocol_interface.py       # Protocol page sub-app (/reporting_page) - protocol monitoring
    └── templates/                  # HTML templates
        ├── dashboard.html          # Main dashboard with links to all services
        ├── run_page.html           # AI response generation interface
        └── reporting_page.html     # University protocols monitoring interface


Endponts:
    POST /support -Wyszukiwanie w bazie cases
    POST /protocols -Wyszukiwanie w bazie protokołów
    GET /run_page - Interfejs webowy dla /support
    GET /reporting_page - Interfejs webowy dla /protocols
    GET /cases - Lista przypadków (cases)
    GET /health - Status serwisu
    GET /form - Formularz HTML
    POST /form/submit - Zapis formularza




HOW TO RUN THE PROJECT

run ollama and qdrant containers BEFORE agent container


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