# core/llm_service.py - LLM service wrapper
from langchain_community.chat_models import ChatOllama
import time

class LLMService:
    def __init__(self, model="llama3", base_url="http://ollama:11434"):
        self.llm = ChatOllama(model=model, base_url=base_url)
    
    def generate_response(self, prompt: str, max_retries: int = 3) -> str:
        """Generate response with retry logic"""
        for attempt in range(max_retries):
            try:
                response = self.llm.invoke(prompt)
                return response.content
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"LLM attempt {attempt + 1} failed: {str(e)}")
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise Exception(f"Failed after {max_retries} attempts: {str(e)}")
    
    def generate_draft(self, task: str) -> str:
        """Generate draft response for a task"""
        prompt = f"Generate draft response or summary for this: {task}"
        return self.generate_response(prompt)

# Singleton instance
llm_service = LLMService()