from typing import Dict, List, Optional
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="Content Service",
    description="Content management service for the Tutor Stack platform",
    version="1.0.0",
)

# Naive in-memory storage (in production, use a proper database)
texts: List[str] = []
uploaded_files: List[Dict] = []

# Path to the curriculum JSON file
CURRICULUM_PATH = Path(__file__).parent.parent / "unified_curriculum.json"


class Document(BaseModel):
    text: str = Field(..., description="The text content to be stored")


class SearchQuery(BaseModel):
    text: str = Field(..., description="The search query text")


class SearchResponse(BaseModel):
    chunks: List[str] = Field(..., description="List of matching text chunks")


class FileUploadResponse(BaseModel):
    filename: str = Field(..., description="Name of the uploaded file")
    file_id: str = Field(..., description="Unique identifier for the uploaded file")
    size: int = Field(..., description="Size of the uploaded file in bytes")
    content_type: str = Field(..., description="MIME type of the uploaded file")


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


@app.post("/upload-pdf", response_model=FileUploadResponse)
async def upload_pdf(
    file: UploadFile = File(..., description="PDF file to upload"),
    description: Optional[str] = Form(None, description="Optional description of the PDF content")
) -> FileUploadResponse:
    """
    Upload a PDF file to the content system
    
    This is a dummy implementation that simulates PDF upload without actually storing the file
    """
    try:
        # Validate file type
        if not file.content_type or file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Validate file size (max 10MB)
        if file.size and file.size > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size must be less than 10MB")
        
        # Generate a unique file ID (in production, use a proper ID generation)
        import uuid
        file_id = str(uuid.uuid4())
        
        # Simulate file processing (in production, you would save the file and extract text)
        file_info = {
            "id": file_id,
            "filename": file.filename,
            "size": file.size or 0,
            "content_type": file.content_type,
            "description": description,
            "uploaded_at": "2024-01-01T00:00:00Z",  # In production, use actual timestamp
            "status": "processed"
        }
        
        uploaded_files.append(file_info)
        
        return FileUploadResponse(
            filename=file.filename,
            file_id=file_id,
            size=file.size or 0,
            content_type=file.content_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@app.get("/uploaded-files")
async def list_uploaded_files() -> Dict[str, List[Dict]]:
    """
    List all uploaded files
    """
    try:
        return {"files": uploaded_files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/curriculum")
async def get_curriculum() -> Dict:
    """
    Get the unified curriculum JSON data
    """
    try:
        if not CURRICULUM_PATH.exists():
            raise HTTPException(status_code=404, detail="Curriculum file not found")
        
        with open(CURRICULUM_PATH, 'r', encoding='utf-8') as f:
            curriculum_data = json.load(f)
        
        return curriculum_data
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in curriculum file: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load curriculum: {str(e)}")


@app.get("/curriculum/concepts")
async def get_curriculum_concepts() -> Dict[str, List[Dict]]:
    """
    Get just the concepts from the curriculum
    """
    try:
        curriculum_data = await get_curriculum()
        return {"concepts": curriculum_data.get("concepts", [])}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/curriculum/concepts/{concept_name}")
async def get_concept_by_name(concept_name: str) -> Dict:
    """
    Get a specific concept by name
    """
    try:
        curriculum_data = await get_curriculum()
        concepts = curriculum_data.get("concepts", [])
        
        # Find concept by name (case-insensitive)
        for concept in concepts:
            if concept.get("name", "").lower() == concept_name.lower():
                return concept
        
        raise HTTPException(status_code=404, detail=f"Concept '{concept_name}' not found")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
