FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y procps curl

# Copy requirements files
COPY requirements*.txt ./

# Install dependencies
RUN pip install -r requirements.txt && \
    if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi

# Copy application code
COPY app /app
COPY tests /app/tests

# Command to run the application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 