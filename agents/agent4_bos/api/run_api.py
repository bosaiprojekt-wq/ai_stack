# api/run_api.py - /run endpoint logic
from fastapi import HTTPException
from core.llm_service import llm_service
import datetime

async def handle_run_request(payload: dict) -> dict:
    """Handle /run endpoint request"""
    task = payload.get("input", "")
    if not task:
        raise HTTPException(400, "No input provided")
    
    try:
        response = llm_service.generate_draft(task)
        return {
            "draft": response,
            "collection": "agent4_bos",
            "model": "llama3",
            "timestamp": datetime.datetime.now().isoformat(),
            "source": "main_app"
        }
    except Exception as e:
        raise HTTPException(500, f"Error generating response: {str(e)}")