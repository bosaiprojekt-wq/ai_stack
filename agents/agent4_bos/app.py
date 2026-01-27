# app.py - Main FastAPI application (updated)
from fastapi import FastAPI, Body, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# Import components
from web.forms import form_app
from web.run_interface import run_app
from api.run_api import handle_run_request
from api.support_api import handle_support_request
from core.database import db

# =========================
# MAIN APP CONFIGURATION
# =========================

app = FastAPI(
    title="Agent4 BOS Support",
    description="Main application launcher with AI agent capabilities",
    version="1.0.0"
)

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
async def read_root():
    """Main landing page with links to all services"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Agent4 BOS - Main Dashboard</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 1000px; 
                margin: 40px auto; 
                padding: 20px; 
            }
            .header { 
                text-align: center; 
                margin-bottom: 40px; 
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 10px;
            }
            .dashboard {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-top: 30px;
            }
            .card {
                background: white;
                border-radius: 8px;
                padding: 25px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                transition: transform 0.2s;
                border: 1px solid #e0e0e0;
            }
            .card:hover {
                transform: translateY(-5px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }
            .card h3 {
                color: #2c3e50;
                margin-top: 0;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .card p {
                color: #7f8c8d;
                line-height: 1.6;
            }
            .btn {
                display: inline-block;
                padding: 10px 20px;
                background: #3498db;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                margin-top: 15px;
                transition: background 0.3s;
            }
            .btn:hover {
                background: #2980b9;
            }
            .api-info {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                margin-top: 30px;
            }
            .icon {
                font-size: 24px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🤖 Agent4 BOS - Dashboard</h1>
            <p>System wsparcia administracyjnego z bazą wiedzy i agentem AI</p>
        </div>
        
        <div class="dashboard">
            <div class="card">
                <h3><span class="icon">📝</span> Formularz przypadków</h3>
                <p>Dodawanie nowych przypadków do bazy wiedzy poprzez formularz HTML</p>
                <a href="/form" class="btn">Otwórz formularz</a>
            </div>
            
            <div class="card">
                <h3><span class="icon">🤖</span> Interfejs AI</h3>
                <p>Interfejs webowy do generowania odpowiedzi przez AI</p>
                <a href="/run_page" class="btn">Uruchom AI</a>
            </div>
            
            <div class="card">
                <h3><span class="icon">🔍</span> Wyszukiwanie w bazie</h3>
                <p>Przeszukaj istniejące przypadki w bazie wiedzy</p>
                <a href="/docs#/default/support_support_post" class="btn">Użyj API</a>
            </div>
            
            <div class="card">
                <h3><span class="icon">📚</span> Dokumentacja API</h3>
                <p>Pełna dokumentacja wszystkich endpointów API</p>
                <a href="/docs" class="btn">Otwórz dokumentację</a>
            </div>
            
            <div class="card">
                <h3><span class="icon">📋</span> Lista przypadków</h3>
                <p>Przeglądaj wszystkie przypadki w bazie danych</p>
                <a href="/form/cases" class="btn">Zobacz przypadki</a>
            </div>
            
            <div class="card">
                <h3><span class="icon">🩺</span> Health Check</h3>
                <p>Sprawdź stan serwisu i połączenia z AI</p>
                <a href="/health" class="btn">Sprawdź zdrowie</a>
            </div>
        </div>
        
        <div class="api-info">
            <h3>📡 Endpointy API:</h3>
            <ul>
                <li><strong>POST /run</strong> - Generowanie odpowiedzi AI</li>
                <li><strong>POST /support</strong> - Wyszukiwanie w bazie wiedzy</li>
                <li><strong>GET /health</strong> - Status serwisu</li>
                <li><strong>GET /form</strong> - Formularz HTML</li>
                <li><strong>POST /form/submit</strong> - Zapis formularza</li>
                <li><strong>GET /form/cases</strong> - Lista przypadków</li>
                <li><strong>GET /run_page</strong> - Interfejs webowy AI</li>
            </ul>
        </div>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    import datetime
    return {
        "status": "healthy",
        "service": "agent4_bos_main",
        "timestamp": datetime.datetime.now().isoformat(),
        "form_app_mounted": True,
        "run_app_mounted": True,
        "database_cases": db.get_case_count(),
        "endpoints": [
            {"path": "/", "method": "GET", "description": "Main dashboard"},
            {"path": "/form", "method": "GET", "description": "Form sub-application"},
            {"path": "/run_page", "method": "GET", "description": "AI interface"},
            {"path": "/run", "method": "POST", "description": "AI response generation"},
            {"path": "/support", "method": "POST", "description": "Knowledge base search"},
            {"path": "/health", "method": "GET", "description": "Health check"}
        ]
    }

@app.post("/run")
async def run(payload: dict):
    """Legacy endpoint for generating draft responses - uses API service"""
    return await handle_run_request(payload)

@app.post("/support")
async def support(query: str = Body(..., embed=True)):
    """Search for similar cases in knowledge base - uses API service"""
    return await handle_support_request(query)

# =========================
# STARTUP DEBUG INFO
# =========================

print("=" * 60)
print("Agent4 BOS Main Application Initialized...")
print(f"Form app mounted at: /form")
print(f"Run page app mounted at: /run_page")
print(f"Database cases: {db.get_case_count()}")
print("=" * 60)