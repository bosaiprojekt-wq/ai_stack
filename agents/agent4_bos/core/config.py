from pathlib import Path
import os


# Qdrant configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = os.getenv("COLLECTION", "agent4_bos_cases")

# # Get absolute path to json_folder relative to project root
# BASE_DIR = Path(__file__).parent.parent  # Goes up from core to project root
# JSON_FOLDER = BASE_DIR / "json_folder"

# # Ensure folder exists
# JSON_FOLDER.mkdir(exist_ok=True)

# # Optional: Make it configurable via environment
# JSON_FOLDER = Path(os.getenv("JSON_FOLDER_PATH", str(JSON_FOLDER)))

# # Export the path as a string for easier use
# JSON_FOLDER_PATH = str(JSON_FOLDER)