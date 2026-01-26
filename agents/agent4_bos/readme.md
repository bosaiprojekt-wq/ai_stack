User → Query "Studenci nie widzą ocen"

app.py → Receives request, passes to router

support_router.py → Calls /support endpoint

support_agent.py → Builds prompt with cases from file_utils.py

file_utils.py → Loads cases from json_folder/

LLM (Ollama) → Finds similar case, responds

support_agent.py → Parses and formats response

support_router.py → Returns to use