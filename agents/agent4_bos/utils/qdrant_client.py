from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
import os

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION = os.getenv("COLLECTION", "acollection_documents")

client = QdrantClient(url=QDRANT_URL)

def create_collection_if_missing():
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION not in collections:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE)
        )
