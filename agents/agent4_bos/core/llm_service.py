import time
from typing import Dict, Any
from langchain_community.chat_models import ChatOllama


class LLMService:
    def __init__(self, model="llama3", base_url="http://ollama:11434"):
        self.llm = ChatOllama(model=model, base_url=base_url,temperature=0.1,top_p=0.1)
        self.model_name = model
    
    def generate_response(self, prompt: str, max_retries: int = 3) -> str:
        """Generate LLM response with retry logic"""
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
    
    def get_info(self) -> Dict[str, Any]:
        """Get LLM service information"""
        return {
            "model": self.model_name,
            "base_url": self.llm.base_url,
            "service": "ChatOllama"
        }


# Singleton instance
llm_service = LLMService()