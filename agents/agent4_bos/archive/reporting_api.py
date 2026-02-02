# api/protocol_api.py
from fastapi import HTTPException, Body
from core.reporting_agent import generate_protocol_response
from core.reporting_service import university_service

async def handle_protocol_request(query: str) -> dict:
    """Handle /protocols endpoint request"""
    query = query.strip()
    if not query:
        raise HTTPException(400, "Empty query")
    
    try:
        # Generate response using protocol agent
        result = generate_protocol_response(query)
        
        # Add statistics for context
        stats = {
            "open_protocols": university_service.get_open_protocols_count(),
            "pending_protocols": university_service.get_pending_protocols_count(),
            "closed_protocols": university_service.get_closed_protocols_count(),
            "total_protocols": university_service.get_open_protocols_count() + 
                              university_service.get_pending_protocols_count() + 
                              university_service.get_closed_protocols_count()
        }
        
        if result["success"]:
            return {
                "message": result["response"],
                "success": True,
                "query": query,
                "statistics": stats,
                "source": "university_protocol_agent"
            }
        else:
            return {
                "message": result["response"],
                "success": False,
                "query": query,
                "statistics": stats,
                "source": "university_protocol_agent"
            }
            
    except Exception as e:
        return {
            "message": f"Błąd systemu protokołów: {str(e)}",
            "success": False,
            "query": query,
            "error": str(e)
        }