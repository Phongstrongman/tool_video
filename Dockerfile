# DouyinVoice Pro Server Dockerfile
# For deployment on Railway.app or any container platform

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy server requirements first (for better caching)
COPY server/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy server application code
COPY server/ .

# Create directory for database
RUN mkdir -p /app/data

# Expose port (Railway will override with $PORT)
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/app/data/licenses.db

# Run the server - Railway uses startCommand from railway.toml
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
