import json
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

from backend.app.translator.translatorCache import TranslationCache
# Import de nos classes personnalisées
from extractors.image_extractor import EnhancedPDFImageExtractor
from extractors.text_extractor import EnhancedTextExtractor
from translator.groq_translator import GroqTranslator
from translator.huggingface_translator import HuggingFaceTranslator
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
        self.translation_cache = TranslationCache()
        self.logger = logging.getLogger("main")
        self.html_exporter = HTMLExporter()

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
        """
        Traite un fichier PDF pour extraire, traduire et formater son contenu.
        Cette fonction gère la mise en cache des traductions pour optimiser les performances.

        Args:
            file (UploadFile): Le fichier PDF à traiter
            page_number (int): Le numéro de la page à traduire
            source_lang (str): La langue source du document
            target_lang (str): La langue cible pour la traduction
            translator_type (str): Le type de traducteur à utiliser (défaut: "groq")

        Returns:
            dict: Un dictionnaire contenant le résultat du traitement avec les clés :
                - success (bool): État de la traduction
                - translated_text (str): Le texte traduit
                - images (list): Liste des chemins d'images
                - html_path (str): Chemin vers le fichier HTML généré
                - message (str): Message de statut
        """
        temp_file = None
        try:
            # Étape 1 : Sauvegarde temporaire du fichier PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                temp_file = tmp.name
                self.logger.info(f"Création du fichier temporaire : {temp_file}")
                async with aiofiles.open(temp_file, 'wb') as out_file:
                    while chunk := await file.read(8192):
                        await out_file.write(chunk)

            # Étape 2 : Extraction des images et du texte
            self.logger.info(f"Extraction des images de la page {page_number}")
            images = self.image_extractor.extract_images(temp_file, page_number)

            self.logger.info("Extraction du texte avec mise en page")
            text_blocks = self.text_extractor.extract_text_with_layout(temp_file, page_number)
            text_to_translate = "\n".join(block.content for block in text_blocks)

            # Étape 3 : Vérification du cache
            self.logger.info("Vérification du cache de traduction")
            cached_result = self.translation_cache.get_cached_translation(
                text_to_translate, source_lang, target_lang
            )

            if cached_result:
                self.logger.info("Résultat trouvé dans le cache")
                print("Résultat en cache utilisé:",
                      json.dumps(cached_result, indent=2, ensure_ascii=False))
                return cached_result

            # Étape 4 : Traduction si pas en cache
            self.logger.info(f"Traduction avec {translator_type}")
            translator = self.translators.get(translator_type)
            if not translator:
                raise ValueError(f"Traducteur non supporté: {translator_type}")

            translated_text = await asyncio.to_thread(
                translator.translate,
                text_to_translate,
                source_lang,
                target_lang
            )

            # Étape 5 : Construction des blocs traduits
            self.logger.info("Construction des blocs traduits")
            translated_blocks = []
            translated_text_parts = translated_text.split('\n')

            for i, block in enumerate(text_blocks):
                if i < len(translated_text_parts):
                    # Utilisation des attributs de position du bloc
                    bbox = [
                        block.bbox[0] if hasattr(block, 'bbox') else 0,
                        block.bbox[1] if hasattr(block, 'bbox') else 0,
                        block.bbox[2] if hasattr(block, 'bbox') else 100,
                        block.bbox[3] if hasattr(block, 'bbox') else 100
                    ]
                    translated_blocks.append({
                        'type': 'text',
                        'content': translated_text_parts[i],
                        'bbox': bbox
                    })

            # Ajout des images aux blocs
            for image in images:
                translated_blocks.append({
                    'type': 'image',
                    'path': str(image.path),
                    'bbox': [
                        image.bbox[0] if hasattr(image, 'bbox') else 0,
                        image.bbox[1] if hasattr(image, 'bbox') else 0,
                        image.bbox[2] if hasattr(image, 'bbox') else 100,
                        image.bbox[3] if hasattr(image, 'bbox') else 100
                    ]
                })

            # Étape 6 : Génération du fichier HTML
            self.logger.info("Génération du fichier HTML")
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            html_output_path = output_dir / f"page_{page_number}_translated.html"

            self.html_exporter.export(translated_blocks, images, str(html_output_path))

            # Étape 7 : Construction du résultat final
            result = {
                "success": True,
                "translated_text": translated_text,
                "images": [str(img.path) for img in images],
                "html_path": str(html_output_path),
                "blocks": translated_blocks,  # Ajout des blocs pour référence
                "message": "Traduction réussie"
            }

            # Étape 8 : Sauvegarde dans le cache
            self.logger.info("Sauvegarde du résultat dans le cache")
            self.translation_cache.save_translation(
                text_to_translate, source_lang, target_lang, result
            )

            # Affichage du résultat pour débogage
            print("Nouveau résultat de traduction:",
                  json.dumps(result, indent=2, ensure_ascii=False))

            return result

        except Exception as e:
            self.logger.error(f"Erreur lors du traitement: {str(e)}")
            print(f"Erreur détaillée: {str(e)}")
            raise

        finally:
            # Nettoyage du fichier temporaire
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                    self.logger.debug("Fichier temporaire supprimé avec succès")
                except Exception as e:
                    self.logger.warning(
                        f"Erreur lors de la suppression du fichier temporaire: {str(e)}")

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