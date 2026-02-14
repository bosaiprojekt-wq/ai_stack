import time
import requests
from typing import Dict, Any

#class: LLMService - handles interactions with the LLM using API 
class LLMService:
    def __init__(self, model="llama3", base_url="http://ollama:11434"):
        self.model_name = model
        self.base_url = base_url
    
    #method: generate response
    def generate_response(self, prompt: str, temperature: float = 0.1, max_tokens: int = 2000, max_retries: int = 3) -> str:
        """Generate LLM response with retry logic using direct Ollama API"""
        for attempt in range(max_retries):
            try:
                url = f"{self.base_url}/api/generate"
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                }
                
                response = requests.post(url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                return result.get("response", "")
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"LLM attempt {attempt + 1} failed: {str(e)}")
                    time.sleep(2 ** attempt)
                else:
                    print(f"Failed after {max_retries} attempts: {str(e)}")
                    return f"Błąd podczas generowania odpowiedzi: {str(e)}"
    
    #method: get LLM service information
    def get_info(self) -> Dict[str, Any]:
        """Get LLM service information"""
        return {
            "model": self.model_name,
            "base_url": self.base_url,
            "service": "Ollama Direct API"
        }


# Singleton instance
llm_service = LLMService()