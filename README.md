# Content Service

Content management and semantic search service for the Tutor Stack.

## Features

- Content ingestion
- Semantic search using substring matching
- **Dynamic curriculum fetching from Google Cloud Storage**
- RESTful API with FastAPI

## New: GCS Curriculum Integration

The content service now supports dynamic curriculum fetching from Google Cloud Storage. This allows for:

- **Dynamic Grade Selection**: Access curriculum for any grade (KG1, P1-P6, G7-G12)
- **Term-based Organization**: Browse concepts by Term1 and Term2
- **Subject Filtering**: Filter concepts by subject (mathematics, science, english, etc.)
- **Real-time Updates**: Curriculum updates in GCS are immediately available
- **Fallback Support**: Falls back to local JSON files if GCS is unavailable

### Quick Start with GCS

1. **Set up GCS authentication**:
   ```bash
   # For development
   gcloud auth application-default login
   
   # For production (set service account key)
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
   ```

2. **Access curriculum data**:
   ```bash
   # Get available grades
   curl http://localhost:8000/content/curriculum/grades
   
   # Get curriculum for a specific grade
   curl http://localhost:8000/content/curriculum/G10
   
   # Get concepts for a specific subject
   curl http://localhost:8000/content/curriculum/G10/Term1/mathematics
   ```

For detailed documentation, see [GCS_INTEGRATION.md](GCS_INTEGRATION.md).

## Development

### Prerequisites

- Python 3.11+
- Docker (optional)
- Google Cloud SDK (for GCS integration)

### Local Setup

1. Create and activate virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   ```

2. Install dependencies:
   ```bash
   pip install -e .
   ```

3. Set up GCS authentication (optional):
   ```bash
   gcloud auth application-default login
   ```

4. Run the service:
   ```bash
   uvicorn tutor_stack_content.main:app --reload
   ```

### Using Docker

```bash
docker build -t content-service .
docker run -p 8000:8000 content-service
```

### Testing

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=tutor_stack_content --cov-report=term-missing
```

### Code Quality

```bash
# Format code
black tutor_stack_content/ tests/
isort tutor_stack_content/ tests/

# Run linters
flake8 tutor_stack_content/ tests/
mypy tutor_stack_content/ tests/
```

## API Documentation

When running, visit:
- OpenAPI UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Environment Variables

- `GOOGLE_APPLICATION_CREDENTIALS`: Path to GCS service account key (optional)
- `GCS_BUCKET_NAME`: GCS bucket name (defaults to "thoth-concepts")

## CI/CD

GitHub Actions workflows handle:
- Running tests
- Code quality checks
- Building Docker image
- (Optional) Deployment to chosen platform 