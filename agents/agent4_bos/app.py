from fastapi import FastAPI, Body, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
import os

# Import components
from web.forms import form_app
from web.run_interface import run_app
from api.support_api import handle_support_request
from core.file_utils import get_case_count
from core.config import JSON_FOLDER_PATH

# =========================
# MAIN APP CONFIGURATION
# =========================

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

# Mount sub-applications
app.mount("/form", form_app)
app.mount("/run_page", run_app)

# =========================
# MAIN APP ROUTES
# =========================

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):  # <-- Add request parameter
    """Main landing page with links to all services"""
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "json_folder_path": JSON_FOLDER_PATH,
            "case_count": get_case_count()
        }
    )

@app.get("/health")
async def health_check():
    """Minimal but informative health check"""
    import datetime
    from core.file_utils import get_database_info, get_case_count
    from core.llm_service import llm_service
    
    # Test database
    db_ok = False
    try:
        db_info = get_database_info()
        case_count = get_case_count()
        db_ok = db_info["exists"] and db_info["is_dir"]
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
                "path": db_info.get("folder_path", "unknown") if db_ok else "unknown"
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
async def support(query: str = Body(..., embed=True)):
    """Search for similar cases in knowledge base - uses API service"""
    return await handle_support_request(query)


#files testing endpoints
@app.get("/test/files")
async def test_files():
    """Test endpoint to list JSON files"""
    from core.file_utils import list_json_files, get_database_info
    files = list_json_files()
    db_info = get_database_info()
    
    return {
        "folder": db_info.get("folder_path", JSON_FOLDER_PATH),
        "file_count": len(files),
        "database_info": db_info,
        "files": files
    }
@app.get("/test/first-file")
async def test_first_file():
    """Test endpoint to read first JSON file"""
    from core.file_utils import get_first_file
    try:
        return get_first_file()
    except FileNotFoundError:
        return {"error": "No JSON files found"}
    
# =========================
# STARTUP DEBUG INFO
# =========================

print("=" * 60)
print("Agent4 BOS Main Application Initialized...")
print(f"Form app mounted at: /form")
print(f"Run page app mounted at: /run_page")
print(f"Database cases: {get_case_count()}")
print("=" * 60)