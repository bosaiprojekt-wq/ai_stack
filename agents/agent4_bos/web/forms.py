
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse

# Import from core modules
from core.file_utils import save_case
from core.config import JSON_FOLDER_PATH

# Create sub-app
form_app = FastAPI(title="Form Application", description="HTML form for adding cases")
# Import database service


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
    """Handle form submission - uses file_utils service"""
    try:
        result = save_case(Tytul, Autor, Opis, Rozwiazanie, Uwagi)
        return JSONResponse({
            "status": "success",
            "message": "Przypadek zapisany pomyślnie",
            "case_id": result["case_id"],
            "file": result["file_path"],
            "data": result["data"]
        })
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": f"Błąd podczas zapisywania: {str(e)}"
        }, status_code=500)

# @form_app.get("/cases")
# async def list_cases():
#     """List all cases in database - uses file_utils service"""
#     cases = list_cases_summary()
#     return {
#         "cases": cases,
#         "count": len(cases),
#         "database_path": JSON_FOLDER_PATH
#     }

# @form_app.get("/info")
# async def get_database_info():
#     """Get database information"""
#     from core.file_utils import get_database_info
#     return get_database_info()