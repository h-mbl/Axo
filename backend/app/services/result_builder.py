# backend/app/services/result_builder.py
from pathlib import Path
import asyncio
import logging
from typing import Dict, List

class ResultBuilder:
    def __init__(self, html_exporter):
        self.html_exporter = html_exporter
        self.logger = logging.getLogger("ResultBuilder")

    async def build_final_result(self,
                                extraction_result: Dict,
                                translated_text: str,
                                page_number: int,
                                source_lang: str,
                                target_lang: str) -> Dict:
        """Construit le résultat final avec organisation en sections."""
        try:
            # Préparation des éléments
            translated_text_parts = translated_text.split('\n')
            text_blocks = extraction_result['text_blocks']

            # Organisation des sections
            from content_organizer import ContentOrganizer
            content_organizer = ContentOrganizer()
            sections = content_organizer.organize_blocks_into_sections(
                text_blocks,
                translated_text_parts,
                extraction_result['images']
            )

            # Génération du HTML
            output_dir = Path("output")
            html_path = output_dir / f"page_{page_number}_translated.html"
            await asyncio.to_thread(
                self.html_exporter.export,
                sections,
                extraction_result['images'],
                str(html_path)
            )

            # Construction du résultat
            result = {
                "success": True,
                "translated_text": translated_text,
                "images": extraction_result['images'],
                "html_path": str(html_path),
                "blocks": [block for section in sections for block in section],
                "page_dimensions": extraction_result['page_dimensions'],
                "metadata": {
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "page_number": page_number,
                    "total_sections": len(sections),
                    "total_blocks": sum(len(section) for section in sections),
                    "scale_factor": 1.0
                },
                "message": "Traduction réussie avec organisation en sections"
            }

            return result
        except Exception as e:
            self.logger.error(f"Erreur lors de la construction du résultat: {str(e)}")
            raise