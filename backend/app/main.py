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

from PIL import Image
import io

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
    """Classe enrichie pour stocker les résultats de traduction avec métadonnées."""
    original_text: str
    translated_text: str
    images: list
    html_path: str
    success: bool
    message: str
    page_dimensions: Dict
    blocks: list[Dict]
    metadata: Dict

load_dotenv()

class PDFTranslationService:
    _instance = None
    _initialized = False

    def __new__(cls):
        """Implémentation du pattern Singleton pour garantir une seule instance du service."""
        if cls._instance is None:
            cls._instance = super(PDFTranslationService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialise les composants du service si ce n'est pas déjà fait."""
        if not self._initialized:
            self.initialize_components()
            self.__class__._initialized = True

    def initialize_components(self):
        """Configure tous les composants nécessaires au service de traduction."""
        # Initialisation du cache et du logger
        self.translation_cache = TranslationCache()
        self.logger = logging.getLogger("PDFTranslationService")
        self.html_exporter = HTMLExporter()

        # Création des répertoires de sortie
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        images_dir = output_dir / "images"
        images_dir.mkdir(exist_ok=True)

        # Initialisation des composants principaux
        self.image_extractor = EnhancedPDFImageExtractor(
            output_dir=str(images_dir)
        )
        self.text_extractor = EnhancedTextExtractor()

        # Configuration des traducteurs disponibles
        self.translators = {
            "groq": GroqTranslator(api_key=os.getenv("GROQ_API_KEY")),
        }

        self.logger.info("Service de traduction PDF initialisé avec succès")

    async def process_file(self,
                           file: UploadFile,
                           page_number: int,
                           source_lang: str,
                           target_lang: str,
                           translator_type: str = "groq") -> Dict:
        """
        Traite un fichier PDF pour l'extraction, la traduction et la mise en forme.
        Cette version améliorée supporte le calque superposé avec des métadonnées enrichies.
        """
        temp_file = None
        try:
            # Création et écriture du fichier temporaire
            temp_file = await self._save_temp_file(file)
            self.logger.info(f"Fichier temporaire créé : {temp_file}")

            # Extraction des composants du PDF
            extraction_result = await self._extract_pdf_components(
                temp_file,
                page_number
            )


            cached_result = self.translation_cache.get_cached_translation(extraction_result['text_to_translate'],
                source_lang,
                target_lang)
            if cached_result:
                self.logger.info("Utilisation du résultat en cache")
                return cached_result

            # Traduction du contenu
            translation_result = await self._translate_content(
                extraction_result['text_to_translate'],
                source_lang,
                target_lang,
                translator_type
            )

            # Construction du résultat final
            result = await self._build_final_result(
                extraction_result,
                translation_result,
                page_number,
                source_lang,
                target_lang
            )

            # Mise en cache du résultat
            self.translation_cache.save_translation(extraction_result['text_to_translate'],
                source_lang,
                target_lang, result)

            return result

        except Exception as e:
            self.logger.error(f"Erreur lors du traitement : {str(e)}")
            raise
        finally:
            await self._cleanup_temp_file(temp_file)

    async def _save_temp_file(self, file: UploadFile) -> str:
        """Sauvegarde le fichier uploadé en fichier temporaire."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf').name
        async with aiofiles.open(temp_file, 'wb') as out_file:
            while chunk := await file.read(8192):
                await out_file.write(chunk)
        return temp_file

    async def _extract_pdf_components(self, pdf_path: str, page_number: int) -> Dict:
        """Extrait tous les composants nécessaires du PDF."""
        # Extraction des images
        images = await asyncio.to_thread(
            self.image_extractor.extract_images,
            pdf_path,
            page_number
        )

        # Extraction du texte avec mise en page
        text_blocks, page_dimensions = await asyncio.to_thread(
            self.text_extractor.extract_text_with_layout,
            pdf_path,
            page_number
        )

        # Construction du texte à traduire
        text_to_translate = "\n".join(block.content for block in text_blocks)

        return {
            'images': images,
            'text_blocks': text_blocks,
            'page_dimensions': page_dimensions,
            'text_to_translate': text_to_translate
        }

    async def _translate_content(self,
                                 text: str,
                                 source_lang: str,
                                 target_lang: str,
                                 translator_type: str) -> str:
        """Traduit le contenu textuel."""
        translator = self.translators.get(translator_type)
        if not translator:
            raise ValueError(f"Traducteur non supporté : {translator_type}")

        return await asyncio.to_thread(
            translator.translate,
            text,
            source_lang,
            target_lang
        )



    async def _build_final_result(self,
                                  extraction_result: Dict,
                                  translated_text: str,
                                  page_number: int,
                                  source_lang: str,
                                  target_lang: str) -> Dict:
        """Construit le résultat final avec support du calque superposé et redimensionnement d'images."""

        def resize_image(img_path, max_size=800):
            """Redimensionne l'image tout en conservant son ratio."""
            try:
                with Image.open(img_path) as img:
                    # Calcul du ratio pour garder les proportions
                    ratio = min(max_size / max(img.size[0], img.size[1]), 1.0)
                    if ratio < 1.0:  # Redimensionner seulement si l'image est plus grande que max_size
                        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                        img = img.resize(new_size, Image.Resampling.LANCZOS)

                        # Créer un nouveau nom de fichier pour l'image redimensionnée
                        path = Path(img_path)
                        new_path = path.parent / f"resized_{path.name}"
                        img.save(new_path, quality=85, optimize=True)

                        return str(new_path), new_size
                return img_path, img.size
            except Exception as e:
                self.logger.error(f"Erreur lors du redimensionnement de l'image: {str(e)}")
                return img_path, None  # Retourner le chemin original en cas d'erreur

        # Préparation des blocs traduits
        translated_blocks = []
        translated_text_parts = translated_text.split('\n')
        text_blocks = extraction_result['text_blocks']

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

        # Préparation des informations d'images avec redimensionnement
        image_info = []
        for img in extraction_result['images']:
            # Redimensionner l'image
            new_path, new_size = resize_image(img.path)

            # Ajuster le bbox proportionnellement si l'image a été redimensionnée
            if new_size and new_size != img.size:
                scale_x = new_size[0] / img.size[0]
                scale_y = new_size[1] / img.size[1]
                original_bbox = list(img.bbox)
                new_bbox = [
                    original_bbox[0],  # Garder la position x
                    original_bbox[1],  # Garder la position y
                    int(original_bbox[2] * scale_x),  # Nouvelle largeur
                    int(original_bbox[3] * scale_y)  # Nouvelle hauteur
                ]
            else:
                new_bbox = list(img.bbox)

            image_info.append({
                'type': 'image',
                'path': new_path,
                'bbox': new_bbox,
                'width': new_size[0] if new_size else img.size[0],
                'height': new_size[1] if new_size else img.size[1],
            })

        # Génération du fichier HTML
        output_dir = Path("output")
        html_path = output_dir / f"page_{page_number}_translated.html"
        await asyncio.to_thread(
            self.html_exporter.export,
            translated_blocks,
            image_info,  # Utiliser les images redimensionnées
            str(html_path)
        )

        # Construction du résultat final
        result = {
            "success": True,
            "translated_text": translated_text,
            "images": image_info,
            "html_path": str(html_path),
            "blocks": translated_blocks + image_info,
            "page_dimensions": extraction_result['page_dimensions'],
            "metadata": {
                "source_language": source_lang,
                "target_language": target_lang,
                "page_number": page_number,
                "total_blocks": len(translated_blocks),
                "scale_factor": 1.0,
                "image_processing": {
                    "total_images": len(image_info),
                    "resized_images": sum(1 for img in image_info if "resized_" in img['path'])
                }
            },
            "message": "Traduction réussie avec redimensionnement des images"
        }

        return result

    async def _cleanup_temp_file(self, temp_file: Optional[str]):
        """Nettoie les fichiers temporaires."""
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
                self.logger.debug("Fichier temporaire supprimé avec succès")
            except Exception as e:
                self.logger.warning(
                    f"Erreur lors de la suppression du fichier temporaire: {str(e)}")

    def _generate_cache_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """Génère une clé de cache unique pour la traduction."""
        return f"{hash(text)}_{source_lang}_{target_lang}"
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
    source_language: str = "English",
    target_language: str = "French",
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