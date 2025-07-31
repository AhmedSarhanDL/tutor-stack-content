from typing import Dict, List, Optional
import json
import os
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
from typing import Annotated

from tutor_stack_auth.main import fastapi_users
from tutor_stack_auth.models import User
from tutor_stack_auth.schemas import UserRead
from .gcs_curriculum import GCSCurriculumFetcher

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

current_active_user = fastapi_users.current_user(active=True)

app = FastAPI(
    title="Content Service",
    description="Content management service for the Tutor Stack platform",
    version="1.0.0",
    debug=True,
)

gcs_fetcher = GCSCurriculumFetcher()

# --- Pydantic Models for Curriculum Data ---

class SubConcept(BaseModel):
    name: str
    description: str
    examples: Optional[List[str]] = []
    exercises: Optional[List[dict]] = []

class Concept(BaseModel):
    name: str
    description: str
    examples: Optional[List[str]] = []
    sub_concepts: Optional[List[SubConcept]] = []
    exercises: Optional[List[dict]] = []

class SubjectConceptsResponse(BaseModel):
    grade: str
    term: str
    subject: str
    concepts: List[Concept]

# Path to the curriculum JSON files (fallback)
CURRICULUM_BASE_PATH = Path(__file__).parent.parent
P5_CURRICULUM_PATH = CURRICULUM_BASE_PATH / "P5.json"
P6_CURRICULUM_PATH = CURRICULUM_BASE_PATH / "P6.json"

def get_curriculum_path_for_user(user: User) -> Path:
    if user.grade == "6":
        return P6_CURRICULUM_PATH
    return P5_CURRICULUM_PATH


@app.get("/health")
async def health_check() -> Dict[str, str]:
    logger.info("Health check endpoint was called.")
    return {"status": "healthy"}


@app.get("/curriculum/grades")
async def get_available_grades() -> Dict[str, List[str]]:
    """Get list of available grades from GCS."""
    logger.info("Request received for available grades.")
    try:
        grades = gcs_fetcher.get_available_grades()
        logger.info(f"Returning {len(grades)} grades.")
        return {"grades": grades}
    except Exception as e:
        logger.error(f"Failed to get available grades: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get available grades: {str(e)}"
        )


@app.get("/curriculum/structure/{grade}")
async def get_grade_structure(grade: str) -> Dict:
    """Get the structure of a specific grade."""
    logger.info(f"Request received for grade structure: {grade}")
    try:
        structure = gcs_fetcher.get_grade_structure(grade)
        logger.info(f"Returning structure for grade: {grade}")
        return structure
    except Exception as e:
        logger.error(f"Failed to get structure for grade {grade}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get structure for grade {grade}: {str(e)}"
        )


@app.get("/curriculum/{grade}/{term}/{subject}", response_model=SubjectConceptsResponse)
async def get_subject_concepts(
    grade: str, term: str, subject: str
) -> SubjectConceptsResponse:
    """Get concepts for a specific subject, generating them if they don't exist."""
    logger.info(f"Request received for concepts: {grade}/{term}/{subject}")
    try:
        concepts_data = gcs_fetcher.get_subject_concepts(grade, term, subject)
        logger.info(f"Loaded {len(concepts_data)} concepts for {grade}/{term}/{subject}")

        response_payload = {
            "grade": grade,
            "term": term,
            "subject": subject,
            "concepts": concepts_data,
        }
        
        # Manually validate before returning to FastAPI for clearer error logging
        validated_data = SubjectConceptsResponse.model_validate(response_payload)
        logger.info(f"Successfully validated concepts for {grade}/{term}/{subject}")
        return validated_data

    except ValidationError as e:
        logger.error(f"Data validation error for {grade}/{term}/{subject}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Curriculum data is malformed. Details: {e}",
        )
    except Exception as e:
        logger.error(f"Failed to get concepts for {grade}/{term}/{subject}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while fetching concepts for {grade}/{term}/{subject}: {str(e)}",
        )


@app.get("/curriculum/user")
async def get_user_curriculum_structure(
    user: User = Depends(current_active_user),
) -> Dict:
    """Get curriculum structure for the current user's grade."""
    logger.info(f"Request received for user curriculum structure: user_id={user.id}, grade={user.grade}")
    grade_mapping = {
        "5": "P5", "6": "P6", "7": "G7", "8": "G8",
        "9": "G9", "10": "G10", "11": "G11", "12": "G12",
    }
    gcs_grade = grade_mapping.get(user.grade, "P5")
    
    try:
        structure = gcs_fetcher.get_grade_structure(gcs_grade)
        logger.info(f"Returning curriculum structure for user_id={user.id}, grade={gcs_grade}")
        return {
            "grade": gcs_grade,
            "structure": structure,
            "user_grade": user.grade,
        }
    except Exception as e:
        logger.error(f"GCS fetch failed for user_id={user.id}, grade={gcs_grade}: {e}", exc_info=True)
        # Fallback to local files if GCS fails
        try:
            logger.info(f"Falling back to local curriculum files for user_id={user.id}")
            curriculum_path = get_curriculum_path_for_user(user)
            if not curriculum_path.exists():
                logger.error(f"Fallback curriculum file not found: {curriculum_path.name}")
                raise HTTPException(status_code=404, detail=f"Curriculum file not found: {curriculum_path.name}")
            with open(curriculum_path, 'r', encoding='utf-8') as f:
                curriculum_data = json.load(f)
            
            # This is a mock structure for the fallback
            fallback_structure = {
                "grade": gcs_grade,
                "structure": {
                    "grade": gcs_grade,
                    "terms": {
                        "Term1": ["mathematics", "science"],
                        "Term2": ["mathematics", "science"],
                    }
                },
                "concepts": curriculum_data.get("concepts", []),
                "user_grade": user.grade,
                "source": "local_fallback"
            }
            logger.info(f"Successfully loaded fallback curriculum for user_id={user.id}")
            return fallback_structure
        except Exception as fallback_error:
            logger.error(f"Failed to load fallback curriculum: {fallback_error}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to load curriculum: {fallback_error}")


@app.get("/curriculum")
async def get_curriculum(user: User = Depends(current_active_user)) -> Dict:
    """Legacy endpoint for user curriculum. Now returns structure only."""
    logger.info(f"Legacy curriculum request for user_id={user.id}")
    return await get_user_curriculum_structure(user)
