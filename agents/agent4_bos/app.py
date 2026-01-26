from fastapi import FastAPI
from langchain_community.chat_models import ChatOllama
from agent_logic.support_router import get_support_router

# FastAPI app
app = FastAPI()

#llm innitialization
llm = ChatOllama(
    model="llama3",
    base_url="http://localhost:11434"
)

COLLECTION = "agent4_bos"

#routers
app.include_router(get_support_router(llm, COLLECTION))

# Debug – list all endpoints
print("Registered routes:")
for r in app.routes:
    print(r.path)