from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse
from pathlib import Path
import json
import datetime

# Folder na pliki JSON
JSON_FOLDER = Path(".json_folder")


def get_form_router():
    router = APIRouter()

    @router.get("/form")
    def form():
        return HTMLResponse("""
        <html>
        <head><title>Formularz lokalny</title></head>
        <body>
        <h2>Formularz przypadku specjalnego</h2>
        <form action="/submit" method="post">
          Tytuł: <input name="Tytul" required><br><br>
          Autor: <input name="Autor" required><br><br>
          Opis: <textarea name="Opis" rows="4" cols="50" required></textarea><br><br>
          Rozwiązanie: <textarea name="Rozwiazanie" rows="4" cols="50" required></textarea><br><br>
          Dodatkowe uwagi: <textarea name="Uwagi" rows="2" cols="50"></textarea><br><br>
          <input type="submit" value="Zapisz">
        </form>
        </body>
        </html>
        """)

    @router.post("/submit")
    def submit(
        Tytul: str = Form(...),
        Autor: str = Form(...),
        Opis: str = Form(...),
        Rozwiazanie: str = Form(...),
        Uwagi: str = Form("")
    ):
        case_id = f"SP-{int(datetime.datetime.now().timestamp())}"

        data = {
            "case_id": case_id,
            "created_at": datetime.datetime.now().isoformat(),
            "status": "processed",
            "Tytuł": Tytul,
            "Autor": Autor,
            "Opis": Opis,
            "Rozwiązanie": Rozwiazanie,
            "Dodatkowe uwagi": Uwagi
        }

        file_path = JSON_FOLDER / f"{case_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return {
            "status": "ok",
            "message": "Plik zapisany",
            "file": file_path.name
        }

    return router
