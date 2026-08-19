import sys
from pathlib import Path

# Add backend directory to sys.path for Vercel Python runtime execution
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app

# Export FastAPI app instance for Vercel Serverless Function entrypoint
app_handler = app
