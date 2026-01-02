# Multi-stage build for optimized Railway deployment
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY requirements.txt .
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Final stage - minimal runtime image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY init.sql .
COPY start.sh .

# Make startup script executable
RUN chmod +x start.sh

# Expose port (Railway will override with PORT env var)
EXPOSE 8000

# Note: Running as root for now to debug Railway deployment issues
# TODO: Add non-root user back after deployment works

# Note: Railway has its own healthcheck system, so we don't need a Docker HEALTHCHECK
# The Docker HEALTHCHECK uses hardcoded port which conflicts with Railway's dynamic PORT

# Temporary: Skip start.sh to test if the issue is the script
# Run migrations and start uvicorn directly
CMD ["sh", "-c", "echo 'Container started!' && alembic upgrade head && uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

