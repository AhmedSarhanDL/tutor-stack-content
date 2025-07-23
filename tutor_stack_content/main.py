from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
texts = []  # naive in‑mem storage

class Doc(BaseModel): text: str

@app.post("/ingest")
async def ingest(doc: Doc):
    texts.append(doc.text)
    return {"id": len(texts)-1}

@app.post("/search")
async def search(q: Doc, k: int = 3):
    # Simple substring search for now
    matches = [t for t in texts if q.text.lower() in t.lower()]
    return {"chunks": matches[:k]} 