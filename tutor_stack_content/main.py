from typing import Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="Content Service",
    description="Content management service for the Tutor Stack platform",
    version="1.0.0",
)

# Naive in-memory storage (in production, use a proper database)
texts: List[str] = []


class Document(BaseModel):
    text: str = Field(..., description="The text content to be stored")


class SearchQuery(BaseModel):
    text: str = Field(..., description="The search query text")


class SearchResponse(BaseModel):
    chunks: List[str] = Field(..., description="List of matching text chunks")


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint to verify service status"""
    return {"status": "healthy"}


@app.post("/ingest")
async def ingest(doc: Document) -> Dict[str, int]:
    """
    Ingest new content into the system

    This endpoint stores the provided text content and returns a unique identifier
    """
    try:
        texts.append(doc.text)
        return {"id": len(texts) - 1}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", response_model=SearchResponse)
async def search(q: SearchQuery, k: int = 3) -> SearchResponse:
    """
    Search for content matching the query

    This endpoint performs a simple substring search and returns up to k matching chunks
    """
    try:
        # Simple substring search for now
        # In production, use a proper search engine like Elasticsearch
        matches = [t for t in texts if q.text.lower() in t.lower()]
        return SearchResponse(chunks=matches[:k])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
