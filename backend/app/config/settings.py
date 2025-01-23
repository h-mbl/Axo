# backend/app/config/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DEBUG = True
    MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB
    OUTPUT_DIR = Path("output")
    IMAGES_DIR = OUTPUT_DIR / "images"
    CORS_ORIGINS = ["http://localhost:5173"]
    API_HOST = "0.0.0.0"
    API_PORT = 8001
    WORKERS = 1
    TIMEOUT_KEEP_ALIVE = 65