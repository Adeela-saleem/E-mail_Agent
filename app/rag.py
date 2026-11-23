"""RAG: data/docs ki files ko Chroma mein index karo aur mail ke hisaab se relevant info dhundo."""
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "data" / "docs"
DB_DIR = ROOT / "chroma_db"
COLLECTION_NAME = "knowledge"
EMBED_MODEL = "all-MiniLM-L6-v2"  # free, local, CPU par chalta hai


def _embedding_fn():
    return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)


def _client():
    return chromadb.PersistentClient(path=str(DB_DIR))


def _chunk(text: str, max_chars: int = 500) -> list[str]:
    """Text ko paragraphs mein todo, chhote paragraphs ko jod kar ~500 chars ke chunks banao."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, current = [], ""
    for p in paragraphs:
        if current and len(current) + len(p) > max_chars:
            chunks.append(current)
            current = p
        else:
            current = f"{current}\n\n{p}" if current else p
    if current:
        chunks.append(current)
    return chunks


def build_index() -> int:
    """data/docs ki saari .txt/.md files padho, chunk karo aur Chroma mein daalo. Chunks ki ginti return karta hai."""
    client = _client()
    try:
        client.delete_collection(COLLECTION_NAME)  # purana index hata do, naya banao
    except Exception:
        pass
    collection = client.create_collection(COLLECTION_NAME, embedding_function=_embedding_fn())

    ids, docs, metas = [], [], []
    for path in sorted(DOCS_DIR.glob("*")):
        if path.suffix.lower() not in {".txt", ".md"}:
            continue
        text = path.read_text(encoding="utf-8")
        for i, chunk in enumerate(_chunk(text)):
            ids.append(f"{path.stem}-{i}")
            docs.append(chunk)
            metas.append({"source": path.name})

    if docs:
        collection.add(ids=ids, documents=docs, metadatas=metas)
    return len(docs)


def retrieve(query: str, k: int = 3) -> list[str]:
    """Query se sabse milte-julte k chunks return karo (index na ho to khali list)."""
    try:
        collection = _client().get_collection(COLLECTION_NAME, embedding_function=_embedding_fn())
    except Exception:
        return []
    count = collection.count()
    if count == 0:
        return []
    result = collection.query(query_texts=[query], n_results=min(k, count))
    return result["documents"][0]
