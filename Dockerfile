FROM python:3.11-slim

# Install git for pip git dependencies
RUN apt-get update && \
    apt-get install -y git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
COPY requirements-dev.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY tutor_stack_content/ ./tutor_stack_content/

# Expose the port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "uvicorn", "tutor_stack_content.main:app", "--host", "0.0.0.0", "--port", "8000"] 