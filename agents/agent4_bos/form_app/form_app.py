import json
import datetime
from pathlib import Path
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse

# Create sub-app
form_app = FastAPI(title="Form Application", description="HTML form for adding cases")

# Setup templates
templates = Jinja2Templates(directory="form_app/form_templates")

# Configuration
JSON_FOLDER = Path("../json_database_handling/json_folder")

# Create JSON folder if it doesn't exist
if not JSON_FOLDER.exists():
    JSON_FOLDER.mkdir(parents=True, exist_ok=True)

# HTML Form Template
FORM_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Agent4 BOS - Formularz przypadku</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            max-width: 800px; 
            margin: 40px auto; 
            padding: 20px; 
        }
        .container { 
            border: 1px solid #ccc; 
            padding: 30px; 
            border-radius: 8px; 
            background: #f9f9f9; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 { 
            color: #2c3e50; 
            text-align: center; 
            margin-bottom: 30px;
        }
        label { 
            display: block; 
            margin-top: 15px; 
            font-weight: bold; 
            color: #34495e;
        }
        input[type="text"], textarea { 
            width: 100%; 
            padding: 10px; 
            margin-top: 5px; 
            border: 1px solid #ddd; 
            border-radius: 4px;
            font-size: 14px;
        }
        textarea { 
            height: 120px; 
            resize: vertical; 
        }
        .submit-btn { 
            margin-top: 25px; 
            padding: 12px 30px; 
            background: #3498db; 
            color: white; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer; 
            font-size: 16px;
            display: block;
            width: 100%;
        }
        .submit-btn:hover { 
            background: #2980b9; 
        }
        .message {
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
            display: none;
        }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .info {
            background: #e8f4fd;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
            border-left: 4px solid #3498db;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📝 Formularz przypadku</h1>
        
        <div class="info">
            <strong>Informacja:</strong> Wypełnij formularz aby dodać nowy przypadek do bazy wiedzy.
            Po zapisaniu, przypadek będzie dostępny dla agenta AI.
        </div>
        
        <div id="message" class="message"></div>
        
        <form id="caseForm">
            <label>Tytuł przypadku:</label>
            <input type="text" name="Tytul" placeholder="Np. Urlop dziekański - procedura" required>
            
            <label>Autor (osoba dodająca):</label>
            <input type="text" name="Autor" placeholder="Twoje imię/nazwa" required>
            
            <label>Opis przypadku:</label>
            <textarea name="Opis" placeholder="Szczegółowy opis sytuacji, problemu..." required></textarea>
            
            <label>Rozwiązanie/procedura:</label>
            <textarea name="Rozwiazanie" placeholder="Proponowane rozwiązanie, kroki postępowania..." required></textarea>
            
            <label>Uwagi dodatkowe (opcjonalne):</label>
            <textarea name="Uwagi" placeholder="Dodatkowe informacje, komentarze..."></textarea>
            
            <button type="submit" class="submit-btn">💾 Zapisz przypadek</button>
        </form>
        
        <div style="margin-top: 20px; text-align: center;">
            <a href="/" style="color: #3498db; text-decoration: none;">← Powrót do głównej strony</a>
        </div>
    </div>

    <script>
        document.getElementById('caseForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            
            // Show loading
            submitBtn.textContent = 'Zapisywanie...';
            submitBtn.disabled = true;
            
            try {
                const response = await fetch('/form/submit', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.status === 'success') {
                    showMessage('success', '✅ Przypadek został pomyślnie zapisany! ID: ' + result.case_id);
                    // Clear form
                    this.reset();
                } else {
                    showMessage('error', '❌ Błąd: ' + (result.message || 'Nie udało się zapisać przypadku'));
                }
            } catch (error) {
                showMessage('error', '❌ Błąd połączenia: ' + error.message);
            } finally {
                // Restore button
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
            }
        });
        
        function showMessage(type, text) {
            const msgDiv = document.getElementById('message');
            msgDiv.className = 'message ' + type;
            msgDiv.textContent = text;
            msgDiv.style.display = 'block';
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                msgDiv.style.display = 'none';
            }, 5000);
        }
    </script>
</body>
</html>
"""

@form_app.get("/")
async def get_form(request: Request):
    """Serve the HTML form"""
    return HTMLResponse(FORM_HTML)

@form_app.post("/submit")
async def submit_case(
    Tytul: str = Form(...),
    Autor: str = Form(...),
    Opis: str = Form(...),
    Rozwiazanie: str = Form(...),
    Uwagi: str = Form("")
):
    """Handle form submission"""
    try:
        case_id = f"SP-{int(datetime.datetime.now().timestamp())}"
        
        data = {
            "case_id": case_id,
            "title": Tytul,
            "author": Autor,
            "description": Opis,
            "solution": Rozwiazanie,
            "additional_notes": Uwagi,
            "created_at": datetime.datetime.now().isoformat()
        }
        
        # Save to JSON file
        file_path = JSON_FOLDER / f"{case_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return JSONResponse({
            "status": "success",
            "message": "Przypadek zapisany pomyślnie",
            "case_id": case_id,
            "file": str(file_path),
            "data": data
        })
        
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": f"Błąd podczas zapisywania: {str(e)}"
        }, status_code=500)

@form_app.get("/cases")
async def list_cases():
    """List all cases in database"""
    cases = []
    try:
        for file in JSON_FOLDER.glob("*.json"):
            with open(file, "r", encoding="utf-8") as f:
                case_data = json.load(f)
                cases.append({
                    "case_id": case_data.get("case_id"),
                    "title": case_data.get("title"),
                    "author": case_data.get("author"),
                    "created_at": case_data.get("created_at")
                })
    except Exception as e:
        return {"error": str(e)}
    
    return {
        "cases": cases,
        "count": len(cases),
        "database_path": str(JSON_FOLDER)
    }
@form_app.get("/run")
async def run_page(request: Request):

    """Serve the AI response generation HTML page"""
    return HTMLResponse(RUN_HTML)

# Add this variable with the HTML content (add it near the FORM_HTML variable)
RUN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Agent4 BOS - Generowanie odpowiedzi AI</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            max-width: 800px; 
            margin: 40px auto; 
            padding: 20px; 
        }
        .container { 
            border: 1px solid #ccc; 
            padding: 30px; 
            border-radius: 8px; 
            background: #f9f9f9; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 { 
            color: #2c3e50; 
            text-align: center; 
            margin-bottom: 30px;
        }
        label { 
            display: block; 
            margin-top: 15px; 
            font-weight: bold; 
            color: #34495e;
        }
        textarea, input[type="text"] { 
            width: 100%; 
            padding: 10px; 
            margin-top: 5px; 
            border: 1px solid #ddd; 
            border-radius: 4px;
            font-size: 14px;
        }
        textarea { 
            height: 150px; 
            resize: vertical; 
        }
        .btn { 
            margin-top: 20px; 
            padding: 12px 30px; 
            background: #3498db; 
            color: white; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer; 
            font-size: 16px;
            display: inline-block;
        }
        .btn:hover { 
            background: #2980b9; 
        }
        .btn-danger { 
            background: #e74c3c; 
        }
        .btn-danger:hover { 
            background: #c0392b; 
        }
        .btn-success { 
            background: #2ecc71; 
        }
        .btn-success:hover { 
            background: #27ae60; 
        }
        .message {
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
            display: none;
        }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .info { background: #e8f4fd; color: #004085; border: 1px solid #b8daff; }
        .response-box {
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
            margin-top: 20px;
            max-height: 400px;
            overflow-y: auto;
            display: none;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }
        .loading-spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #3498db;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .nav-links {
            display: flex;
            justify-content: space-between;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }
        .nav-links a {
            color: #3498db;
            text-decoration: none;
        }
        .nav-links a:hover {
            text-decoration: underline;
        }
        .model-info {
            background: #fff3cd;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 20px;
            border: 1px solid #ffeaa7;
        }
        .example-queries {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            margin-top: 20px;
        }
        .example-queries h4 {
            margin-top: 0;
        }
        .example-item {
            cursor: pointer;
            padding: 8px;
            margin: 5px 0;
            border: 1px solid #ddd;
            border-radius: 4px;
            background: white;
        }
        .example-item:hover {
            background: #e8f4fd;
        }
        .stats {
            display: flex;
            justify-content: space-around;
            margin-top: 20px;
            padding: 10px;
            background: white;
            border-radius: 4px;
            border: 1px solid #ddd;
        }
        .stat-item {
            text-align: center;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #3498db;
        }
        .stat-label {
            font-size: 12px;
            color: #7f8c8d;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Generowanie odpowiedzi AI</h1>
        
        <div class="model-info">
            <strong>Model AI:</strong> Llama 3 | <strong>Endpoint:</strong> /run | 
            <strong>Typ:</strong> Generowanie szkiców odpowiedzi
        </div>
        
        <div id="message" class="message"></div>
        
        <form id="runForm">
            <label>Zadanie/pytanie do AI:</label>
            <textarea id="inputField" name="input" placeholder="Wpisz zadanie, np. 'Przygotuj odpowiedź dla studenta dotyczącą urlopu dziekańskiego'..." required></textarea>
            
            <label>Kontekst (opcjonalnie):</label>
            <input type="text" id="contextField" name="context" placeholder="Np. student choruje, potrzebuje dokumentów...">
            
            <div style="display: flex; gap: 10px; margin-top: 20px;">
                <button type="submit" class="btn btn-success">🚀 Generuj odpowiedź</button>
                <button type="button" onclick="clearForm()" class="btn btn-danger">🗑️ Wyczyść</button>
            </div>
        </form>
        
        <div class="loading" id="loading">
            <div class="loading-spinner"></div>
            <p>Generowanie odpowiedzi przez AI... Proszę czekać.</p>
        </div>
        
        <div class="response-box" id="responseBox">
            <h3 style="margin-top: 0;">🤖 Wygenerowana odpowiedź:</h3>
            <div id="responseContent"></div>
            <div style="margin-top: 20px; padding: 10px; background: #f8f9fa; border-radius: 4px;">
                <strong>Metadane:</strong>
                <div id="responseMeta"></div>
            </div>
            <button onclick="copyToClipboard()" class="btn" style="margin-top: 15px; width: 100%;">📋 Kopiuj odpowiedź</button>
        </div>
        
        <div class="example-queries">
            <h4>💡 Przykładowe zapytania:</h4>
            <div class="example-item" onclick="fillExample(0)">Przygotuj odpowiedź dla studenta dotyczącą urlopu dziekańskiego</div>
            <div class="example-item" onclick="fillExample(1)">Sformułuj pismo w sprawie zaległych opłat za akademik</div>
            <div class="example-item" onclick="fillExample(2)">Napisz streszczenie procedury składania skargi na wykładowcę</div>
            <div class="example-item" onclick="fillExample(3)">Przygotuj projekt odpowiedzi na pytanie o stypendium rektora</div>
        </div>
        
        <div class="stats" id="stats">
            <div class="stat-item">
                <div class="stat-value" id="responseTime">0s</div>
                <div class="stat-label">Czas odpowiedzi</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="charCount">0</div>
                <div class="stat-label">Znaków</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="wordCount">0</div>
                <div class="stat-label">Słów</div>
            </div>
        </div>
        
        <div class="nav-links">
            <a href="/">← Powrót do głównej strony</a>
            <a href="/form">📝 Formularz przypadków</a>
        </div>
    </div>

    <script>
        const examples = [
            "Przygotuj odpowiedź dla studenta dotyczącą urlopu dziekańskiego z przyczyn zdrowotnych. Wyjaśnij procedurę, wymagane dokumenty i terminy.",
            "Sformułuj oficjalne pismo do studenta w sprawie zaległych opłat za akademik. Uwzględnij informację o konsekwencjach prawnych i terminie płatności.",
            "Napisz streszczenie procedury składania skargi na wykładowcę. Opisz kroki formalne, wymagane dokumenty i terminy rozpatrzenia sprawy.",
            "Przygotuj projekt odpowiedzi na pytanie studenta o stypendium rektora dla najlepszych studentów. Wyjaśnij kryteria, wymagane dokumenty i terminy składania wniosków."
        ];
        
        const exampleContexts = [
            "Student choruje, potrzebuje urlopu dziekańskiego",
            "Zaległości w opłatach za mieszkanie w akademiku",
            "Problemy z prowadzącym zajęcia",
            "Dotyczy najlepszych studentów, średnia powyżej 4.5"
        ];
        
        let currentExample = 0;
        
        function fillExample(index) {
            document.getElementById('inputField').value = examples[index];
            document.getElementById('contextField').value = exampleContexts[index];
            currentExample = (index + 1) % examples.length;
        }
        
        function clearForm() {
            document.getElementById('runForm').reset();
            document.getElementById('responseBox').style.display = 'none';
            document.getElementById('stats').style.display = 'flex';
            showMessage('info', 'Formularz wyczyszczony. Możesz wprowadzić nowe zapytanie.');
        }
        
        function showMessage(type, text) {
            const msgDiv = document.getElementById('message');
            msgDiv.className = 'message ' + type;
            msgDiv.textContent = text;
            msgDiv.style.display = 'block';
            
            setTimeout(() => {
                msgDiv.style.display = 'none';
            }, 5000);
        }
        
        function updateStats(response, responseTime) {
            const responseText = response.draft || '';
            const charCount = responseText.length;
            const wordCount = responseText.split(/\s+/).filter(word => word.length > 0).length;
            
            document.getElementById('responseTime').textContent = responseTime + 's';
            document.getElementById('charCount').textContent = charCount;
            document.getElementById('wordCount').textContent = wordCount;
        }
        
        function copyToClipboard() {
            const responseText = document.getElementById('responseContent').innerText;
            navigator.clipboard.writeText(responseText).then(() => {
                showMessage('success', '✅ Odpowiedź skopiowana do schowka!');
            }).catch(err => {
                showMessage('error', '❌ Błąd kopiowania: ' + err);
            });
        }
        
        document.getElementById('runForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const input = document.getElementById('inputField').value;
            const context = document.getElementById('contextField').value;
            
            if (!input.trim()) {
                showMessage('error', '❌ Proszę wprowadzić zapytanie do AI');
                return;
            }
            
            let payload = { input: input };
            if (context.trim()) {
                payload.context = context;
            }
            
            document.getElementById('loading').style.display = 'block';
            document.getElementById('responseBox').style.display = 'none';
            document.getElementById('stats').style.display = 'none';
            
            const startTime = Date.now();
            
            try {
                const response = await fetch('/run', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(payload)
                });
                
                const endTime = Date.now();
                const responseTime = ((endTime - startTime) / 1000).toFixed(1);
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const result = await response.json();
                
                document.getElementById('loading').style.display = 'none';
                
                document.getElementById('responseContent').innerHTML = formatResponse(result.draft);
                document.getElementById('responseMeta').innerHTML = `
                    <div>Model: ${result.model || 'llama3'}</div>
                    <div>Kolekcja: ${result.collection || 'agent4_bos'}</div>
                    <div>Czas: ${result.timestamp || new Date().toLocaleString()}</div>
                `;
                
                document.getElementById('responseBox').style.display = 'block';
                document.getElementById('stats').style.display = 'flex';
                
                updateStats(result, responseTime);
                
                showMessage('success', '✅ Odpowiedź wygenerowana pomyślnie!');
                
            } catch (error) {
                document.getElementById('loading').style.display = 'none';
                showMessage('error', '❌ Błąd: ' + error.message);
            }
        });
        
        function formatResponse(text) {
            let html = text
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/^### (.*$)/gm, '<h3>$1</h3>')
                .replace(/^## (.*$)/gm, '<h2>$1</h2>')
                .replace(/^# (.*$)/gm, '<h1>$1</h1>')
                .replace(/^\d+\.\s+(.*$)/gm, '<li>$1</li>')
                .replace(/^-\s+(.*$)/gm, '<li>$1</li>')
                .replace(/\n/g, '<br>');
            
            html = html.replace(/(<li>.*?<\/li>)+/g, '<ul>$&</ul>');
            
            return html;
        }
        
        setInterval(() => {
            fillExample(currentExample);
            currentExample = (currentExample + 1) % examples.length;
        }, 10000);
    </script>
</body>
</html>
"""