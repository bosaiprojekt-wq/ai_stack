import os
from pathlib import Path

# Qdrant configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

# Collection names for qdrant
SPECIAL_CASES_COLLECTION = os.getenv("SPECIAL_CASES_COLLECTION", "agent4_bos_cases")
KNOWLEDGE_BASE_COLLECTION = os.getenv("KNOWLEDGE_BASE_COLLECTION", "agent4_knowledge_base")
# Default collection (for backward compatibility, some files might still use this)
COLLECTION_NAME = SPECIAL_CASES_COLLECTION

# local data folder paths
BASE_DATA_PATH = os.getenv("BASE_DATA_PATH", "/app/qdrant_data")
KNOWLEDGE_BASE_PATH = os.path.join(BASE_DATA_PATH, "knowledge_base")
SPECIAL_CASES_PATH = os.path.join(BASE_DATA_PATH, "special_cases")

# Create directories on import
def ensure_directories():
    """Create necessary directories if they don't exist"""
    # Ensure local data folders exist for ingestion and special cases
    directories = [KNOWLEDGE_BASE_PATH, SPECIAL_CASES_PATH]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

# Run on import
ensure_directories()

# Knowledge Base Categories
KNOWLEDGE_BASE_CATEGORIES = [
    "dane_osobowe",
    "egzaminy", 
    "rekrutacja",
    "stypendia",
    "urlopy_zwolnienia"
]

# Special value - all categories
ALL_CATEGORIES_KEY = "all"