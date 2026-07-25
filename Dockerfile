FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for building python packages & healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the API gateway port
EXPOSE 8008

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8008/api/udf/config || exit 1

# 4 workers: scheduler can block 1 worker without starving HTTP requests
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8008", "--workers", "4"]
