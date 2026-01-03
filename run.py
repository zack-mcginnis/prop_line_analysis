#!/usr/bin/env python3
"""
Simple runner script for Railway deployment.
This ensures we can see output and debug startup issues.
"""
import os
import sys
import subprocess

print("=" * 60, flush=True)
print("STARTING RAILWAY DEPLOYMENT", flush=True)
print("=" * 60, flush=True)

# Print environment info
port = os.getenv("PORT", "8000")
db_url = os.getenv("DATABASE_URL", "NOT SET")
print(f"PORT: {port}", flush=True)
print(f"DATABASE_URL: {'SET' if db_url != 'NOT SET' else 'NOT SET'}", flush=True)
print(f"Python: {sys.version}", flush=True)
print("=" * 60, flush=True)

# Run database migrations
print("\nRunning database migrations...", flush=True)
try:
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        check=True,
        capture_output=True,
        text=True
    )
    print(result.stdout, flush=True)
    print("✓ Migrations completed successfully", flush=True)
except subprocess.CalledProcessError as e:
    print(f"ERROR: Migration failed!", flush=True)
    print(f"stdout: {e.stdout}", flush=True)
    print(f"stderr: {e.stderr}", flush=True)
    print("Exiting...", flush=True)
    sys.exit(1)
except FileNotFoundError:
    print("WARNING: alembic command not found, skipping migrations", flush=True)

print("=" * 60, flush=True)

# Start uvicorn
print("Starting uvicorn...", flush=True)
import uvicorn

uvicorn.run(
    "src.api.main:app",
    host="0.0.0.0",
    port=int(port),
    log_level="info",
)

