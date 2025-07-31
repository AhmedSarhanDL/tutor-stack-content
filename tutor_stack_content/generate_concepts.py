import argparse
import json
import os
import pathlib
import time
import io
import math
from dotenv import load_dotenv
import google.generativeai as genai
import fitz  # PyMuPDF

# Load environment variables from .env file
load_dotenv()

def find_files(directory: str) -> (list[pathlib.Path], list[pathlib.Path]):
    """
    Finds and categorizes PDF files in a directory based on their descriptor files.
    """
    curriculum_pdfs = []
    exercise_pdfs = []
    base_path = pathlib.Path(directory)
    for descriptor_path in base_path.glob('*_descriptor.json'):
        with open(descriptor_path, 'r', encoding='utf-8') as f:
            descriptor = json.load(f)
        book_type = descriptor.get("book_type")
        pdf_filename = descriptor_path.stem.replace('_descriptor', '') + '.pdf'
        pdf_path = base_path / pdf_filename
        if pdf_path.exists():
            if book_type == "curriculum":
                curriculum_pdfs.append(pdf_path)
            elif book_type == "exercise":
                exercise_pdfs.append(pdf_path)
    return curriculum_pdfs, exercise_pdfs

def process_curriculum_chunk(pdf_chunk_path: pathlib.Path, model: genai.GenerativeModel, original_filename: str) -> dict:
    """
    Processes a single curriculum PDF chunk to extract concepts.
    """
    print(f"Uploading curriculum chunk from: {original_filename}")
    display_name = f"chunk_{time.time()}_{original_filename}"
    pdf_file = genai.upload_file(path=pdf_chunk_path, display_name=display_name, mime_type="application/pdf")
    print(f"Completed uploading chunk: {pdf_file.name}")

    prompt = """
    Based on the content of the provided curriculum PDF chunk, generate a JSON object that outlines the concepts and sub-concepts.
    For each concept and sub-concept, provide a detailed description and at least one relevant example.
    The JSON structure should be:
    {
      "concepts": [
        {
          "name": "Concept Name",
          "description": "Detailed description of the concept.",
          "examples": ["Example 1", "Example 2"],
          "sub_concepts": [
            {
              "name": "Sub-concept Name",
              "description": "Detailed description of the sub-concept.",
              "examples": ["Example 1", "Example 2"]
            }
          ]
        }
      ]
    }
    """
    try:
        response = model.generate_content([prompt, pdf_file])
        json_string = response.text.strip().replace('```json', '').replace('```', '').strip()
        return json.loads(json_string)
    except Exception as e:
        print(f"An error occurred while processing chunk from {original_filename}: {e}")
        return {"concepts": []}
    finally:
        genai.delete_file(pdf_file.name)
        print(f"Deleted uploaded file: {pdf_file.name}")

def process_curriculum_file_in_chunks(pdf_path: pathlib.Path, model: genai.GenerativeModel, num_chunks: int = 4) -> list:
    """
    Splits a PDF into chunks and processes each one for curriculum data.
    """
    print(f"Processing curriculum file in {num_chunks} chunks: {pdf_path.name}")
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    pages_per_chunk = math.ceil(total_pages / num_chunks)
    all_chunk_concepts = []
    temp_dir = pdf_path.parent

    for i in range(num_chunks):
        start_page = i * pages_per_chunk
        end_page = min((i + 1) * pages_per_chunk, total_pages)
        if start_page >= total_pages:
            break

        print(f"Processing chunk {i+1}/{num_chunks} (pages {start_page}-{end_page-1}) of {pdf_path.name}")
        chunk_doc = fitz.open()
        chunk_doc.insert_pdf(doc, from_page=start_page, to_page=end_page - 1)
        pdf_chunk_bytes = chunk_doc.write()
        chunk_doc.close()

        chunk_pdf_path = temp_dir / f"chunk_{i}_{pdf_path.name}"
        try:
            with open(chunk_pdf_path, "wb") as f:
                f.write(pdf_chunk_bytes)

            chunk_concepts = process_curriculum_chunk(chunk_pdf_path, model, pdf_path.name)
            if chunk_concepts and "concepts" in chunk_concepts:
                all_chunk_concepts.extend(chunk_concepts["concepts"])
        finally:
            if chunk_pdf_path.exists():
                os.remove(chunk_pdf_path)
            
    doc.close()
    return all_chunk_concepts

def unify_concepts(concepts_list: list[dict]) -> dict:
    """
    Unifies a list of concepts, merging duplicates.
    """
    unified = {}
    for concept in concepts_list:
        name = concept.get("name")
        if not name:
            continue
        if name not in unified:
            unified[name] = concept
            unified[name]["sub_concepts"] = {sub.get("name"): sub for sub in concept.get("sub_concepts", []) if sub.get("name")}
        else:
            unified[name]["description"] = concept.get("description", unified[name].get("description"))
            unified[name].setdefault("examples", []).extend(concept.get("examples", []))
            for sub_concept in concept.get("sub_concepts", []):
                sub_name = sub_concept.get("name")
                if sub_name and sub_name not in unified[name]["sub_concepts"]:
                    unified[name]["sub_concepts"][sub_name] = sub_concept

    final_concepts = list(unified.values())
    for concept in final_concepts:
        concept["sub_concepts"] = list(concept["sub_concepts"].values())
    return {"concepts": final_concepts}

def process_exercise_chunk(pdf_chunk_path: pathlib.Path, unified_concepts: dict, model: genai.GenerativeModel, original_filename: str) -> list:
    """
    Processes a single exercise PDF chunk to link exercises to concepts.
    """
    print(f"Uploading exercise chunk from: {original_filename}")
    display_name = f"chunk_{time.time()}_{original_filename}"
    pdf_file = genai.upload_file(path=pdf_chunk_path, display_name=display_name, mime_type="application/pdf")
    print(f"Completed uploading chunk: {pdf_file.name}")
    
    concept_names = [c['name'] for c in unified_concepts.get('concepts', [])]
    prompt = f"""
    Based on the unified concepts provided and the content of the uploaded exercise book PDF chunk, identify exercises and link each to the most relevant concept and sub-concept.
    Return a JSON object with an "exercises" list.
    JSON Structure: {{ "exercises": [ {{ "question": "...", "answer": "...", "concept_name": "...", "sub_concept_name": "..." }} ] }}
    Unified Concepts: {json.dumps(concept_names)}
    """
    try:
        response = model.generate_content([prompt, pdf_file])
        json_string = response.text.strip().replace('```json', '').replace('```', '').strip()
        return json.loads(json_string).get("exercises", [])
    except Exception as e:
        print(f"An error occurred while processing chunk from {original_filename}: {e}")
        return []
    finally:
        genai.delete_file(pdf_file.name)
        print(f"Deleted uploaded file: {pdf_file.name}")

def process_exercise_file_in_chunks(pdf_path: pathlib.Path, unified_concepts: dict, model: genai.GenerativeModel, num_chunks: int = 4) -> list:
    """
    Splits an exercise PDF into chunks and processes each one.
    """
    print(f"Processing exercise file in {num_chunks} chunks: {pdf_path.name}")
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    pages_per_chunk = math.ceil(total_pages / num_chunks)
    all_chunk_exercises = []
    temp_dir = pdf_path.parent

    for i in range(num_chunks):
        start_page = i * pages_per_chunk
        end_page = min((i + 1) * pages_per_chunk, total_pages)
        if start_page >= total_pages:
            break

        print(f"Processing chunk {i+1}/{num_chunks} (pages {start_page}-{end_page-1}) of {pdf_path.name}")
        chunk_doc = fitz.open()
        chunk_doc.insert_pdf(doc, from_page=start_page, to_page=end_page - 1)
        pdf_chunk_bytes = chunk_doc.write()
        chunk_doc.close()

        chunk_pdf_path = temp_dir / f"chunk_{i}_{pdf_path.name}"
        try:
            with open(chunk_pdf_path, "wb") as f:
                f.write(pdf_chunk_bytes)

            exercises = process_exercise_chunk(chunk_pdf_path, unified_concepts, model, pdf_path.name)
            all_chunk_exercises.extend(exercises)
        finally:
            if chunk_pdf_path.exists():
                os.remove(chunk_pdf_path)
    
    doc.close()
    return all_chunk_exercises

def generate_for_subject(subject_folder: str):
    """
    Generates concepts for a given subject folder.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    print(f"Processing folder: {subject_folder}")
    curriculum_files, exercise_files = find_files(subject_folder)
    print(f"Found {len(curriculum_files)} curriculum books and {len(exercise_files)} exercise books.")

    all_concepts = []
    for pdf in curriculum_files:
        concepts_from_chunks = process_curriculum_file_in_chunks(pdf, model)
        all_concepts.extend(concepts_from_chunks)

    unified_data = unify_concepts(all_concepts)
    print(f"Unified {len(unified_data.get('concepts', []))} concepts.")

    all_exercises = []
    for pdf in exercise_files:
        exercises = process_exercise_file_in_chunks(pdf, unified_data, model)
        all_exercises.extend(exercises)

    for exercise in all_exercises:
        concept_name = exercise.get("concept_name")
        sub_concept_name = exercise.get("sub_concept_name")
        for concept in unified_data.get("concepts", []):
            if concept.get("name") == concept_name:
                concept.setdefault("exercises", []).append(exercise)
                for sub_concept in concept.get("sub_concepts", []):
                    if sub_concept.get("name") == sub_concept_name:
                        sub_concept.setdefault("exercises", []).append(exercise)
                        break

    output_dir = pathlib.Path(subject_folder) / "concepts"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "unified_curriculum.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(unified_data, f, ensure_ascii=False, indent=4)

    print(f"Successfully generated and saved the unified curriculum to {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Process curriculum and exercise books to generate a unified concepts JSON.")
    parser.add_argument("subject_folder", type=str, help="Path to the subject folder in 'content'.")
    args = parser.parse_args()
    generate_for_subject(args.subject_folder)

if __name__ == "__main__":
    main()
