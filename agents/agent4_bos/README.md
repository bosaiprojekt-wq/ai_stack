


HOW TO RUN THE PROJECT

run other containers BEFORE agent


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


PROJECT STRUCTURE

├── agents/
│   └── agent4_bos/                           # Contains agent files
│       ├── app.py                             # Entry point for the application
│       ├── docker-compose.yml                  # Configuration for Docker services
│       ├── Dockerfile                          # Instructions for building the Docker image
│       ├── main.py                             # Main logic for the application
│       ├── README.md                           # Documentation for the project
│       ├── requirements-batch-1.txt            # List of Python dependencies for batch 1
│       ├── requirements-batch-2.txt            # List of Python dependencies for batch 2
│       ├── requirements-batch-3.txt            # List of Python dependencies for batch 3
│       ├── api/                                # Contains API-related files
│       │   ├── __init__.py                      # Initializes the API package
│       │   └── api.py                           # Defines the API endpoints and logic
│       ├── core/                               # Contains core functionalities of the application
│       │   ├── __init__.py                      # Initializes the core package
│       │   ├── config.py                        # Configuration settings for the application
│       │   ├── document_generator.py            # Logic for generating documents
│       │   ├── document_ingestor.py             # Logic for ingesting documents
│       │   ├── document_processor.py            # Logic for processing documents
│       │   ├── llm_service.py                   # Service for interacting with the language model
│       │   ├── qdrant_service.py                # Service for interacting with Qdrant
│       │   └── support_agent.py                 # Logic for the support agent
│       └── web/                                # Contains web-related files
│           ├── __init__.py                      # Initializes the web package
│           ├── forms.py                         # Defines web forms
│           ├── run_interface.py                 # Logic for running the web interface
│           └── templates/                       # Contains HTML templates
│               ├── dashboard.html                # Dashboard template
│               └── run_page.html                 # Run page template
│
├── nodered/
│   ├── docker-compose.yml                      # Configuration for Node-RED services
│   └── Procesy/                                # Contains Node-RED flow files
│       ├── Agent4_BOS_Frontdesk.json           # Flow for the front desk agent
│       ├── flows.json                           # General flows for Node-RED
│       └── node-red_agent4-bos.json             # Specific Node-RED configuration for Agent 4 BOS
│
├── ollama/
│   └── docker-compose.yml                      # Configuration for Ollama services
│
├── qdrant/
│   └── docker-compose.yml                      # Configuration for Qdrant services
│
├── qdrant_data/
│   ├── knowledge_base/                         # Contains knowledge base documents
│   │   ├── dane_osobowe/                        # Personal data documents
│   │   ├── egzaminy/                            # Examination documents
│   │   ├── rekrutacja/                          # Recruitment documents
│   │   ├── stypendia/                           # Scholarship documents
│   │   └── urlopy_zwolnienia/                   # Leave and exemption documents
│   ├── special_cases/                          # Contains files for special cases
│   └── storage/                                # Storage for application data