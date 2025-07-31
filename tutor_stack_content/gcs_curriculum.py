import json
import logging
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Dict, List, Optional

from google.auth.exceptions import DefaultCredentialsError
from google.cloud import storage
from google.api_core.exceptions import NotFound

from .generate_concepts import generate_for_subject

# Configure detailed logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GCSCurriculumFetcher:
    """
    Fetches curriculum data from Google Cloud Storage, with on-demand generation.
    """

    def __init__(self, bucket_name: str = "thoth-concepts"):
        self.bucket_name = bucket_name
        self.client = None
        self.bucket = None

    def _initialize_client(self):
        """Initialize the GCS client."""
        if self.client:
            return
        try:
            self.client = storage.Client()
            self.bucket = self.client.bucket(self.bucket_name)
            logger.info(f"Successfully connected to GCS bucket: {self.bucket_name}")
        except DefaultCredentialsError:
            logger.error(
                "Failed to authenticate with Google Cloud. Please set up credentials."
            )
            raise
        except Exception as e:
            logger.error(f"Failed to initialize GCS client: {e}", exc_info=True)
            raise

    def _run_concept_generation(self, subject_path: str):
        """
        Downloads required files, runs generation script, and uploads the result.
        """
        logger.info(f"Starting concept generation for: {subject_path}")
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            logger.info(f"Using temporary directory: {temp_path}")
            
            prefix = f"concepts/content/{subject_path}/"
            blobs = self.client.list_blobs(self.bucket_name, prefix=prefix)

            # Download all files for the subject
            try:
                for blob in blobs:
                    if blob.name.endswith((".pdf", "_descriptor.json")):
                        destination_path = temp_path / Path(blob.name).name
                        logger.info(f"Downloading {blob.name} to {destination_path}")
                        blob.download_to_filename(destination_path)
            except Exception as e:
                logger.error(f"Failed to download files for {subject_path}: {e}", exc_info=True)
                return

            # Run the generation script
            try:
                logger.info(f"Running concept generation script for {temp_path}")
                generate_for_subject(str(temp_path))
                logger.info(f"Concept generation script finished for {temp_path}")

                # Upload the generated file
                generated_file = temp_path / "concepts" / "unified_curriculum.json"
                if generated_file.exists():
                    blob_name = f"{prefix}concepts/unified_curriculum.json"
                    blob = self.bucket.blob(blob_name)
                    logger.info(f"Uploading generated concepts to {blob_name}")
                    blob.upload_from_filename(str(generated_file))
                    logger.info(f"Successfully uploaded generated concepts to {blob_name}")
                else:
                    logger.error(f"Concept generation script did not produce a file in {generated_file}")
            except Exception as e:
                logger.error(f"Failed to generate or upload concepts for {subject_path}: {e}", exc_info=True)

    def get_available_grades(self) -> List[str]:
        """Get list of available grades from GCS."""
        self._initialize_client()
        try:
            iterator = self.client.list_blobs(
                self.bucket_name, prefix="concepts/content/", delimiter="/"
            )
            prefixes = set()
            for page in iterator.pages:
                prefixes.update(page.prefixes)
            
            grades = [
                prefix.split("/")[-2]
                for prefix in prefixes
                if prefix.endswith("/")
            ]
            return sorted([grade for grade in grades if grade.startswith(("G", "P", "KG"))])

        except Exception as e:
            logger.error(f"Failed to get available grades: {e}", exc_info=True)
            raise

    def get_grade_structure(self, grade: str) -> Dict:
        """Get the term and subject structure of a specific grade."""
        self._initialize_client()
        structure = {"grade": grade, "terms": {}}
        try:
            prefix = f"concepts/content/{grade}/"
            term_iterator = self.client.list_blobs(self.bucket_name, prefix=prefix, delimiter="/")
            
            term_prefixes = set()
            for page in term_iterator.pages:
                term_prefixes.update(page.prefixes)

            for term_prefix in term_prefixes:
                term = term_prefix.split('/')[-2]
                if term.startswith('Term'):
                    structure["terms"][term] = []
                    subject_iterator = self.client.list_blobs(self.bucket_name, prefix=term_prefix, delimiter="/")
                    
                    subject_prefixes = set()
                    for page in subject_iterator.pages:
                        subject_prefixes.update(page.prefixes)

                    for subject_prefix in subject_prefixes:
                        subject = subject_prefix.split('/')[-2]
                        if subject != 'concepts':
                            structure["terms"][term].append(subject)
            return structure
        except Exception as e:
            logger.error(f"Failed to get grade structure for {grade}: {e}", exc_info=True)
            raise

    def get_subject_concepts(self, grade: str, term: str, subject: str) -> List[Dict]:
        """
        Get concepts for a subject, generating them if they don't exist.
        """
        self._initialize_client()
        concept_file_path = (
            f"concepts/content/{grade}/{term}/{subject}/concepts/unified_curriculum.json"
        )
        blob = self.bucket.blob(concept_file_path)

        try:
            logger.info(f"Attempting to download existing concept file: {concept_file_path}")
            content = blob.download_as_text(encoding="utf-8")
            logger.info(f"Successfully downloaded concept file: {concept_file_path}")
            return json.loads(content).get("concepts", [])
        
        except NotFound:
            logger.info(f"Concept file not found at {concept_file_path}. Starting generation in background.")
            generation_thread = threading.Thread(
                target=self._run_concept_generation,
                args=(f"{grade}/{term}/{subject}",),
            )
            generation_thread.start()
            return [{"name": "Generating Concepts", "description": "The curriculum for this subject is being generated. Please check back in a few minutes."}]

        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in {concept_file_path}: {e}", exc_info=True)
            return [{"name": "Error", "description": f"The curriculum file is corrupted: {e}"}]

        except Exception as e:
            logger.error(f"Failed to download or process concept file {concept_file_path}: {e}", exc_info=True)
            raise IOError(f"Failed to access curriculum file. Please check GCS permissions and file integrity. Error: {e}")


    def get_grade_curriculum(self, grade: str) -> Dict:
        """
        Get the structure for a grade. Concepts are fetched on demand.
        """
        self._initialize_client()
        try:
            structure = self.get_grade_structure(grade)
            return {
                "grade": grade,
                "structure": structure,
            }
        except Exception as e:
            logger.error(f"Failed to get curriculum for grade {grade}: {e}", exc_info=True)
            raise
