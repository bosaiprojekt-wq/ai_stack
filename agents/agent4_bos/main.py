# main.py - Launcher file
import uvicorn
from app import app

if __name__ == "__main__":
    print("=" * 60)
    print("Starting Agent4 BOS Application...")
    print("=" * 60)
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )