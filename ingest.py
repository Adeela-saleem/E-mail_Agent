"""data/docs ki files ko Chroma mein index karo. Docs badlein to dobara chalao."""
from app.rag import build_index

if __name__ == "__main__":
    n = build_index()
    print(f"Index ban gaya: {n} chunks.")
