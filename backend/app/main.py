import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

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
class TextBlock:
    content: str
    bbox: list
    font_size: float
    font_name: str
    font_weight: str
    text_alignment: str
    line_height: float
    rotation: float
    color: str
    page_number: int

@dataclass
class TranslationResult:
    original_text: str
    translated_text: str
    images: list
    html_path: str
    success: bool
    message: str
    page_dimensions: dict
    blocks: list
    metadata: dict

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
        self.logger = logging.getLogger("PDFTranslationService")
        self.html_exporter = HTMLExporter()

        # Création des répertoires nécessaires
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        images_dir = output_dir / "images"
        images_dir.mkdir(exist_ok=True)

        # Initialisation des extracteurs
        self.image_extractor = EnhancedPDFImageExtractor(
            output_dir=str(images_dir)
        )
        self.text_extractor = EnhancedTextExtractor()

        # Initialisation des traducteurs
        self.translators = {
            "groq": GroqTranslator(api_key=os.getenv("GROQ_API_KEY")),
           # "huggingface": HuggingFaceTranslator()
        }

        self.logger.info("Service de traduction initialisé avec succès")

    async def process_file(self, file: UploadFile, page_number: int,
                           source_lang: str, target_lang: str,
                           translator_type: str = "groq") -> dict:
        """
        Traite un fichier PDF pour l'extraction, la traduction et la mise en forme.
        Cette version améliorée supporte le calque superposé avec des métadonnées enrichies.
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
            text_blocks, page_dimensions  = self.text_extractor.extract_text_with_layout(temp_file, page_number)
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
                    translated_blocks.append({
                        'type': 'text',
                        'content': translated_text_parts[i],
                        'bbox': block.bbox,
                        'style': {
                            'fontSize': f"{block.font_size}px",
                            'fontFamily': block.font_name,
                            'fontWeight': block.font_weight,
                            'textAlign': block.text_alignment,
                            'lineHeight': f"{block.line_height}px",
                            'transform': f"rotate({block.rotation}deg)",
                            'color': block.color
                        }
                    })

            # Ajout des images aux blocs
            image_info = [{
                'type': 'image',
                'path': str(img.path),
                'bbox': [
                    img.x0 if hasattr(img, 'x0') else 0,
                    img.y0 if hasattr(img, 'y0') else 0,
                    img.x1 if hasattr(img, 'x1') else 100,
                    img.y1 if hasattr(img, 'y1') else 100
                ],
                'width': img.width if hasattr(img, 'width') else None,
                'height': img.height if hasattr(img, 'height') else None
            } for img in images]

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
                "page_dimensions": page_dimensions,
                "blocks": [
                    {
                        "type": "text",
                        "content": translated_text_parts[i],
                        "bbox": block.bbox,
                        "style": {
                            "fontSize": f"{block.font_size}px",
                            "fontFamily": block.font_name,
                            "fontWeight": block.font_weight,
                            "textAlign": block.text_alignment,
                            "lineHeight": f"{block.line_height}px",
                            "transform": f"rotate({block.rotation}deg)",
                            "color": block.color
                        }
                    }
                    for i, block in enumerate(text_blocks)
                    if i < len(translated_text_parts)
                ]
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

app.mount("/output", StaticFiles(directory="output"), name="output")

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