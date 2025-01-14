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

# Import de nos classes personnalisées
from extractors.image_extractor import EnhancedPDFImageExtractor
from extractors.text_extractor import EnhancedTextExtractor
from translator.translator_base import TranslatorBase
from translator.groq_translator import GroqTranslator
from translator.huggingface_translator import  HuggingFaceTranslator
from exporters.html_exporter import HTMLExporter


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
    """Service principal de traduction de PDF."""

    def __init__(self, output_dir: str = "output"):
        """
        Initialise le service de traduction avec tous les composants nécessaires.

        Args:
            output_dir: Répertoire pour les fichiers de sortie
        """
        # Configuration des chemins
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Configuration du logging
        self.logger = logging.getLogger(__name__)

        # Initialisation des composants
        self.image_extractor = EnhancedPDFImageExtractor(
            output_dir=str(self.output_dir / "images")
        )
        self.text_extractor = EnhancedTextExtractor()

        # Initialisation des traducteurs
        self.translators = {
            "groq": GroqTranslator(api_key=os.getenv("GROQ_API_KEY")),
            "huggingface": HuggingFaceTranslator()
        }

        self.exporter = HTMLExporter()

    async def process_page(
            self,
            pdf_path: str,
            page_number: int,
            source_lang: str,
            target_lang: str,
            translator_type: str = "groq"
    ) -> TranslationResult:
        """
        Traite une page de PDF de manière asynchrone.

        Args:
            pdf_path: Chemin vers le fichier PDF
            page_number: Numéro de la page à traduire
            source_lang: Langue source
            target_lang: Langue cible
            translator_type: Type de traducteur à utiliser
        """
        try:
            # Extraction des images
            self.logger.info(f"Extraction des images de la page {page_number}")
            images = self.image_extractor.extract_images(pdf_path, page_number)

            # Extraction du texte
            self.logger.info("Extraction du texte")
            text_blocks = self.text_extractor.extract_text_with_layout(pdf_path, page_number)

            # Préparation du texte pour la traduction
            original_text = ""
            for block in text_blocks:
                if block.is_title:
                    original_text += f"\n## {block.content}\n"
                else:
                    original_text += f"\n{block.content}\n"

            # Traduction
            translator = self.translators.get(translator_type)
            if not translator:
                raise ValueError(f"Traducteur non supporté: {translator_type}")

            self.logger.info("Traduction du texte")
            translated_text = await asyncio.to_thread(
                translator.translate,
                original_text,
                source_lang,
                target_lang
            )

            # Génération du fichier HTML
            output_path = self.output_dir / f"page_{page_number}.html"
            self.exporter.export(
                translated_text,
                images,
                str(output_path)
            )

            return TranslationResult(
                original_text=original_text,
                translated_text=translated_text,
                images=[img.path for img in images],
                html_path=str(output_path),
                success=True,
                message="Traduction réussie"
            )

        except Exception as e:
            self.logger.error(f"Erreur lors du traitement: {str(e)}")
            return TranslationResult(
                original_text="",
                translated_text="",
                images=[],
                html_path="",
                success=False,
                message=str(e)
            )


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
    """
    Point de terminaison pour la traduction de PDF.

    Args:
        file: Fichier PDF à traduire
        page_number: Numéro de la page à traduire
        source_language: Langue source
        target_language: Langue cible
        translator_type: Type de traducteur à utiliser
    """
    try:
        # Création d'un fichier temporaire pour le PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_path = temp_file.name

            # Sauvegarde du fichier uploadé
            async with aiofiles.open(temp_path, 'wb') as out_file:
                content = await file.read()
                await out_file.write(content)

            # Traitement de la page
            result = await translation_service.process_page(
                temp_path,
                page_number,
                source_language,
                target_language,
                translator_type
            )

            # Nettoyage
            os.unlink(temp_path)

            if result.success:
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "message": result.message,
                        "translated_text": result.translated_text,
                        "html_path": result.html_path,
                        "images": result.images
                    }
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=result.message
                )

    except Exception as e:
        logging.error(f"Erreur lors de la traduction: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/health")
async def health_check():
    """Point de terminaison pour vérifier l'état du service."""
    return {"status": "healthy"}


if __name__ == "__main__":
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
        reload=True,
        workers=1,
        timeout_keep_alive=65,
        limit_concurrency=20,
        limit_max_requests=100,
        backlog=100
    )