# web/protocol_interface.py
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os

# Create sub-app
protocol_app = FastAPI(title="Protocol Interface", description="Web interface for university protocols")

# Initialize templates
current_dir = os.path.dirname(os.path.abspath(__file__))  # /app/web
templates_dir = os.path.join(current_dir, "templates")    # /app/web/templates

templates = Jinja2Templates(directory=templates_dir)

# Add CORS
protocol_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@protocol_app.get("/")
async def get_protocol_page(request: Request):
    """Serve the protocol monitoring HTML page"""
    return templates.TemplateResponse("reporting_page.html", {"request": request})

@protocol_app.get("/test")
async def test_endpoint():
    """Test endpoint"""
    import datetime
    return {
        "status": "ok",
        "message": "Protocol page app is working",
        "timestamp": datetime.datetime.now().isoformat()
    }