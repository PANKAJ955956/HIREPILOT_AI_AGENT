from pathlib import Path
import chromadb
from app.config import settings

_client = None

def client():
    global _client
    if _client is None:
        Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return _client

def index_document(document_id: str, text: str, metadata: dict):
    # Chroma's built-in embedding function is used so the app can index without another API key.
    collection = client().get_or_create_collection("hirepilot_documents", metadata={"hnsw:space": "cosine"})
    chunks = [text[i:i+900] for i in range(0, min(len(text), 30000), 700)]
    if not chunks: return 0
    ids = [f"{document_id}-{i}" for i in range(len(chunks))]
    metas = [{**metadata, "chunk": i} for i in range(len(chunks))]
    collection.upsert(ids=ids, documents=chunks, metadatas=metas)
    return len(chunks)

def search_documents(query: str, limit: int = 4):
    collection = client().get_or_create_collection("hirepilot_documents", metadata={"hnsw:space": "cosine"})
    if collection.count() == 0: return []
    result = collection.query(query_texts=[query], n_results=min(limit, collection.count()))
    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]
    return [{"text": d, "metadata": m} for d, m in zip(docs, metas)]
