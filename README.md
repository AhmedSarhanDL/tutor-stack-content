# Content Service

Content management and semantic search service for the Tutor Stack.

## Features

- Content ingestion
- Semantic search using substring matching
- RESTful API with FastAPI

## Development

### Prerequisites

- Python 3.11+
- Docker (optional)

### Local Setup

1. Create and activate virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # for development
   ```

3. Run the service:
   ```bash
   uvicorn app.main:app --reload
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
pytest --cov=app --cov-report=term-missing
```

### Code Quality

```bash
# Format code
black app/ tests/
isort app/ tests/

# Run linters
flake8 app/ tests/
mypy app/ tests/
```

## API Documentation

When running, visit:
- OpenAPI UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Environment Variables

None required for basic operation.

## CI/CD

GitHub Actions workflows handle:
- Running tests
- Code quality checks
- Building Docker image
- (Optional) Deployment to chosen platform 