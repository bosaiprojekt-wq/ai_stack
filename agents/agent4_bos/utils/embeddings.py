import os
import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

def embed(text):
    """
    Returns embedding vector from Ollama embedding model.
    """
    if isinstance(text, str):
        inputs = [text]  # Ollama expects a list
    else:
        inputs = text

    r = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={
            "model": EMBED_MODEL,
            "input": inputs
        }
    )
    data = r.json()
    # data["embeddings"] is a list of vectors
    return data["embeddings"][0]  # return first embedding if single string
