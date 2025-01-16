from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from pathlib import Path
import logging
import os
import tempfile
import asyncio
from dotenv import load_dotenv
from typing import Dict, Optional
from groq import Groq
from dataclasses import dataclass
import aiofiles
import multiprocessing
from multiprocessing import freeze_support

# Import de nos classes personnalisées
from extractors.image_extractor import EnhancedPDFImageExtractor
from extractors.text_extractor import EnhancedTextExtractor
from translator.groq_translator import GroqTranslator
from translator.huggingface_translator import HuggingFaceTranslator


@dataclass
class TranslationResult:
    """Classe pour stocker les résultats de traduction."""
    original_text: str
    translated_text: str
    images: list
    html_path: str
    success: bool
    message: str

load_dotenv()

class PDFTranslationService:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PDFTranslationService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.initialize_components()
            self.__class__._initialized = True

    def initialize_components(self):
        """Initialise tous les composants nécessaires"""
        self.logger = logging.getLogger("main")

        # Création des répertoires nécessaires
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        # Initialisation des extracteurs
        self.image_extractor = EnhancedPDFImageExtractor(
            output_dir=str(output_dir / "images")
        )
        self.text_extractor = EnhancedTextExtractor()

        # Initialisation des traducteurs
        self.translators = {
            "groq": GroqTranslator(api_key=os.getenv("GROQ_API_KEY")),
            "huggingface": HuggingFaceTranslator()
        }

        self.logger.info("Service de traduction initialisé avec succès")

    async def process_file(self, file: UploadFile, page_number: int,
                           source_lang: str, target_lang: str,
                           translator_type: str = "groq") -> dict:
        """Traite un fichier PDF"""
        temp_file = None
        try:
            # Créer un fichier temporaire avec un contexte
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                temp_file = tmp.name
                # Lire et écrire le fichier par morceaux
                async with aiofiles.open(temp_file, 'wb') as out_file:
                    while chunk := await file.read(8192):
                        await out_file.write(chunk)

            self.logger.info(f"Extraction des images de la page {page_number}")
            images = self.image_extractor.extract_images(temp_file, page_number)

            self.logger.info("Extraction du texte")
            text_blocks = self.text_extractor.extract_text_with_layout(temp_file, page_number)

            # Préparation du texte pour la traduction
            text_to_translate = "\n".join(block.content for block in text_blocks)

            # Traduction
            translator = self.translators.get(translator_type)
            if not translator:
                raise ValueError(f"Traducteur non supporté: {translator_type}")

            translated_text = await asyncio.to_thread(
                translator.translate,
                text_to_translate,
                source_lang,
                target_lang
            )

            return {
                "success": True,
                "translated_text": translated_text,
                "images": [str(img.path) for img in images],
                "message": "Traduction réussie"
            }

        except Exception as e:
            self.logger.error(f"Erreur lors du traitement: {str(e)}")
            raise

        finally:
            # Nettoyage du fichier temporaire
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except Exception as e:
                    self.logger.warning(f"Erreur lors de la suppression du fichier temporaire: {str(e)}")


# Configuration de FastAPI
app = FastAPI(title="PDF Translation API")

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration du service
translation_service = PDFTranslationService()

# Limites de taille de fichier
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB


@app.middleware("http")
async def size_limit_middleware(request, call_next):
    """Middleware pour vérifier la taille des fichiers."""
    content_length = request.headers.get('content-length')
    if content_length and int(content_length) > MAX_UPLOAD_SIZE:
        return JSONResponse(
            status_code=413,
            content={"detail": "Fichier trop volumineux"}
        )
    return await call_next(request)


@app.post("/translate")
async def translate_pdf_page(
    file: UploadFile = File(...),
    page_number: int = Form(...),
    source_language: str = Form(...),
    target_language: str = Form(...),
    translator_type: str = Form("groq")
):
    """Point de terminaison pour la traduction de PDF"""
    try:
        result = await translation_service.process_file(
            file,
            page_number,
            source_language,
            target_language,
            translator_type
        )
        return JSONResponse(content=result)

    except Exception as e:
        logging.error(f"Erreur lors de la traduction: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Point de terminaison pour vérifier l'état du service."""
    return {"status": "healthy"}


if __name__ == "__main__":
    # Nécessaire pour Windows
    freeze_support()
    multiprocessing.set_start_method('spawn', force=True)

    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('app.log')
        ]
    )

    # Configuration du serveur
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        workers=1,
        timeout_keep_alive=65,
    )