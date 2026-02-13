from fastapi import FastAPI, Body, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles  # ADDED
import os

# Import components
from web.forms import form_app
from web.run_interface import run_app
from core.qdrant_service import get_case_count, list_cases_summary, get_database_info
from core.config import KNOWLEDGE_BASE_COLLECTION, SPECIAL_CASES_COLLECTION, BASE_DATA_PATH 
from api.api import handle_support_request
from core.document_ingestor import document_ingestor
from core.config import KNOWLEDGE_BASE_PATH, SPECIAL_CASES_PATH

app = FastAPI(
    title="Agent4 BOS Support",
    description="Main application launcher with AI agent capabilities",
    version="1.0.0"
)

# Initialize templates
current_dir = os.path.dirname(os.path.abspath(__file__))  # /app
templates_dir = os.path.join(current_dir, "web", "templates")  # /app/web/templates

print(f"Main app templates directory: {templates_dir}")  # Debug

templates = Jinja2Templates(directory=templates_dir)
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount data directory for generated files download
# Maps http://host/data/... to local /app/qdrant_data/...
if os.path.exists(BASE_DATA_PATH):
    app.mount("/data", StaticFiles(directory=BASE_DATA_PATH), name="data")
    print(f"Mounted /data to {BASE_DATA_PATH}")

# Mount sub-applications
app.mount("/form", form_app)
app.mount("/run_page", run_app)



@app.get("/", response_class=HTMLResponse)
# Render the main dashboard page with links and case count
async def read_root(request: Request):
    """Main landing page with links to all services"""
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "json_folder_path": f"qdrant://{SPECIAL_CASES_COLLECTION}",
            "case_count": get_case_count()
        }
    )

@app.get("/health")
# Perform health checks for DB and LLM service and return status
async def health_check():
    """Minimal but informative health check"""
    import datetime
    from core.llm_service import llm_service
    
    # Test database
    db_ok = False
    try:
        db_info = get_database_info()
        case_count = get_case_count()
        # Check Qdrant 
        db_ok = db_info.get("storage") == "qdrant" and case_count >= 0
    except:
        db_ok = False
    
    # Test LLM
    llm_ok = False
    try:
        import requests
        response = requests.get(f"{llm_service.llm.base_url}/api/tags", timeout=3)
        llm_ok = response.ok
    except:
        llm_ok = False
    
    # Overall status
    if db_ok and llm_ok:
        status = "healthy"
    elif not db_ok and not llm_ok:
        status = "unhealthy"
    else:
        status = "degraded"
    
    return {
        "status": status,
        "timestamp": datetime.datetime.now().isoformat(),
        "checks": {
            "database": {
                "healthy": db_ok,
                "cases": get_case_count() if db_ok else 0,
                "path": f"qdrant://{SPECIAL_CASES_COLLECTION}" if db_ok else "unknown",  # CHANGED
                "storage": db_info.get("storage", "unknown") if db_ok else "unknown"
            },
            "llm_service": {
                "healthy": llm_ok,
                "model": llm_service.model_name if llm_ok else "unknown",
                "base_url": llm_service.llm.base_url if llm_ok else "unknown"
            }
        },
        "applications": [
            {"name": "form", "mounted": True, "path": "/form"},
            {"name": "run_page", "mounted": True, "path": "/run_page"}
        ]
    }
#main agent endpoint
@app.post("/support")
# Handle support search requests and return similar cases/results
async def support(query: str = Body(..., embed=True)):
    """Search for similar cases in knowledge base - uses API service"""
    return await handle_support_request(query)


#all cases endpoint
@app.get("/cases")
# Return a summary list of cases from the database
async def list_cases():
    """List all cases in database - uses qdrant helpers"""
    cases = list_cases_summary()
    return {
        "cases": cases,
        "count": len(cases),
        "database_path": f"qdrant://{SPECIAL_CASES_COLLECTION}" 
    }

#db info endpoint
@app.get("/info")
# Return basic database information and collection counts
async def get_database_info_endpoint():
    """Get database information"""
    return get_database_info()

@app.post("/ingest/knowledge-base")
# Trigger ingestion of the knowledge base folder into Qdrant
async def ingest_knowledge_base(force: bool = False):
    """Ingest all documents from knowledge_base folder"""
    result = document_ingestor.ingest_knowledge_base(force_reingest=force)
    return result

@app.post("/ingest/special-cases")
# Trigger ingestion of special cases into Qdrant
async def ingest_special_cases(force: bool = False):
    """Ingest all documents from special_cases folder"""
    result = document_ingestor.ingest_special_cases(force_reingest=force)
    return result

@app.post("/ingest/all")
# Run ingestion for both knowledge base and special cases
async def ingest_all(force: bool = False):
    """Ingest all documents from both folders"""
    kb_result = document_ingestor.ingest_knowledge_base(force_reingest=force)
    sc_result = document_ingestor.ingest_special_cases(force_reingest=force)
    
    return {
        "knowledge_base": kb_result,
        "special_cases": sc_result
    }

@app.get("/collections/info")
# Return detailed information about all Qdrant collections
async def get_collections_info():
    """Get information about all collections"""
    from core.qdrant_service import qdrant_service
    return qdrant_service.get_database_info()

@app.get("/files/paths")
# Return configured file paths and existence flags
async def get_file_paths():
    """Get configured file paths"""
    return {
        "knowledge_base_path": KNOWLEDGE_BASE_PATH,
        "special_cases_path": SPECIAL_CASES_PATH,
        "exists": {
            "knowledge_base": os.path.exists(KNOWLEDGE_BASE_PATH),
            "special_cases": os.path.exists(SPECIAL_CASES_PATH)
        }
    }
    

print("=" * 60)
print("Agent4 BOS Main Application Initialized")
print(f"Form app mounted at: http://localhost:8004/form/")
print(f"Chat app mounted at: http://localhost:8004/run_page/")
print(f"Storage: Qdrant special case collection '{SPECIAL_CASES_COLLECTION}'") 
print(f"Storage: Qdrant knowledge base collection '{KNOWLEDGE_BASE_COLLECTION}'")  
print("=" * 60)