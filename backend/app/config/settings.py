import os
from pathlib import Path


class Settings:
    DEBUG = True
    MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB

    # Chemins importants
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    OUTPUT_DIR = BASE_DIR / "output"
    IMAGES_DIR = OUTPUT_DIR / "images"
    MODELS_DIR = BASE_DIR / "models"
    FONTS_DIR = BASE_DIR / "fonts"

    # Chemins spécifiques aux modèles et fonts
    MASKRCNN_MODEL_PATH = MODELS_DIR / "model_196000.pth"
    JAPANESE_FONT_PATH = FONTS_DIR / "Source Han Serif CN Light.otf"
    VIETNAMESE_FONT_PATH = FONTS_DIR / "AlegreyaSans-Regular.otf"

    # Configuration API
    CORS_ORIGINS = ["http://localhost:3000", "http://localhost:5173"]
    API_HOST = "0.0.0.0"
    API_PORT = 8001
    WORKERS = 1
    TIMEOUT_KEEP_ALIVE = 65

    # Configuration traduction
    SUPPORTED_LANGUAGES = {
        "en": "English",
        "fr": "French",
        "ja": "Japanese",
        "vi": "Vietnamese"
    }

    # Clés API pour les services externes
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

    # Créer les dossiers nécessaires au démarrage
    @classmethod
    def initialize(cls):
        cls.OUTPUT_DIR.mkdir(exist_ok=True)
        cls.IMAGES_DIR.mkdir(exist_ok=True)