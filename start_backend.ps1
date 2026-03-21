# Run backend in production mode (no reload, bound to all interfaces)
# Note: This will automatically load your .env file
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
