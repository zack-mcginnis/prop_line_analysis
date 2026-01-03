#!/bin/sh
set -e

# Enable verbose mode for debugging
set -x

echo "=========================================="
echo "Starting Prop Line Analysis API"
echo "=========================================="
echo "DEBUG: Script is running"
echo "DEBUG: Current directory: $(pwd)"
echo "DEBUG: Files present:"
ls -la

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL environment variable is not set!"
    echo "Please set DATABASE_URL in Railway dashboard"
    exit 1
fi

echo "✓ DATABASE_URL is set"

# Check if PORT is set (Railway sets this)
PORT=${PORT:-8000}
echo "✓ Using PORT: $PORT"

# Wait for database to be ready
echo ""
echo "Waiting for database to be ready..."
max_retries=30
retry_count=0
until pg_isready -d "$DATABASE_URL" 2>/dev/null || [ $retry_count -eq $max_retries ]; do
    retry_count=$((retry_count + 1))
    echo "Waiting for database... ($retry_count/$max_retries)"
    sleep 2
done

if [ $retry_count -eq $max_retries ]; then
    echo "⚠ Warning: Could not verify database connection, but continuing anyway..."
else
    echo "✓ Database is ready"
fi

# Run database migrations
echo ""
echo "Running database migrations..."
if uv run alembic upgrade head; then
    echo "✓ Migrations completed successfully"
else
    echo "ERROR: Database migrations failed!"
    echo "This usually means:"
    echo "  1. Database is not accessible"
    echo "  2. DATABASE_URL is incorrect"
    echo "  3. Database doesn't exist yet"
    exit 1
fi

# Start the application
echo ""
echo "Starting uvicorn server..."
echo "Listening on 0.0.0.0:$PORT"
echo "=========================================="

exec uv run uvicorn src.api.main:app --host 0.0.0.0 --port $PORT

