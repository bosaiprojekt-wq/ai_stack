from fastapi import APIRouter, HTTPException
from .support_agent import build_support_prompt, parse_support_response
from .file_utils import list_json_files, get_first_file

#support agent router
def get_support_router(llm, collection_name):
    router = APIRouter()

    @router.post("/support")
    async def support_request(query: str):
        """
        Endpoint do znajdowania podobnych przypadków.
        Przyjmuje plain text jako query.
        """
        query = query.strip()

        if not query:
            raise HTTPException(status_code=400, detail="Puste zapytanie")

        try:
            prompt = build_support_prompt(query)
            response = llm.invoke(prompt)
            result = parse_support_response(response.content)
            
            # Dodajemy oryginalne zapytanie do odpowiedzi
            result["query"] = query
            
            return result
            
        except Exception as e:
            return {
                "found": False,
                "message": f"Błąd systemu: {str(e)}",
                "query": query
            }

    #routers for files listing and contents = testing purposes
    @router.get("/list-files")
    async def get_list_files():
        """List all JSON files in the json_folder"""
        try:
            files = list_json_files()
            return {
                "folder_path": str(files[0]["path"]) if files else "",
                "file_count": len(files),
                "files": files
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")

    @router.get("/get-first-file")
    async def get_first_json_file():
        """Get the contents of the first JSON file in the folder"""
        try:
            return get_first_file()
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

    return router