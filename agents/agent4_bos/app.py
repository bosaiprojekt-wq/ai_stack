from fastapi import FastAPI
from langchain_community.chat_models import ChatOllama

from form.form import get_form_router

# FastAPI app
app = FastAPI()

# JEDYNE miejsce inicjalizacji LLM
llm = ChatOllama(
    model="llama3",
    base_url="http://localhost:11434"
)

COLLECTION = "agent4_bos"

# Routers
app.include_router(get_form_router())

# Debug – lista endpointów
print("Registered routes:")
for r in app.routes:
    print(r.path)
