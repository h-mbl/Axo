# backend/app/services/extraction_service.py
import asyncio
from typing import Dict
import logging

from backend.app.extractors.text_extractor import EnhancedTextExtractor
from backend.app.extractors.image_extractor import EnhancedPDFImageExtractor


class ExtractionService:
    def __init__(self, text_extractor=None, image_extractor=None):
        self.text_extractor = text_extractor or EnhancedTextExtractor()
        self.image_extractor = image_extractor or EnhancedPDFImageExtractor()
        self.logger = logging.getLogger("ExtractionService")

    async def extract_pdf_components(self, pdf_path: str, page_number: int) -> Dict:
        """Extrait les composants avec analyse structurelle."""
        tmp = None
        try:
            # Extraction du texte avec mise en page
            text_blocks, page_dimensions = await asyncio.to_thread(
                self.text_extractor.extract_text_with_layout,
                pdf_path,
                page_number
            )
            tmp = text_blocks

            # Analyse des relations spatiales
            sections = self.text_extractor.analyze_spatial_relationships(text_blocks)

            # Extraction des images avec contexte
            images = await asyncio.to_thread(
                self.image_extractor.extract_images,
                pdf_path,
                page_number
            )
            text_to_translate = "\n".join(block['content'] for block in text_blocks)

            return {
                'sections': sections,
                'images': images,
                'text_blocks': text_blocks,
                'page_dimensions': page_dimensions,
                'text_to_translate': text_to_translate
            }
        except Exception as e:
            self.logger.error(f"Erreur lors de l'extraction des composants: {str(e)}")
            self.logger.debug(f"Structure des blocs de texte: {tmp[:1] if tmp else 'None'}")
            raise