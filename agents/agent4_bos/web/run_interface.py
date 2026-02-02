from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os

# Create sub-app
run_app = FastAPI(title="AI Interface", description="Web interface for AI response generation")

# Initialize templates
current_dir = os.path.dirname(os.path.abspath(__file__))  # /app/web
templates_dir = os.path.join(current_dir, "templates")    # /app/web/templates

templates = Jinja2Templates(directory=templates_dir)

# Add CORS
run_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@run_app.get("/")
async def get_run_page(request: Request):
    """Serve the AI response generation HTML page"""
    return templates.TemplateResponse("run_page.html", {"request": request})

# Note: Test endpoint removed from run_app
    import datetime
    return {
        "status": "ok",
        "message": "Run page app is working",
        "timestamp": datetime.datetime.now().isoformat()
    }