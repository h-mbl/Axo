# backend/app/services/result_builder.py
from pathlib import Path
import asyncio
import logging
from typing import Dict, List, Tuple, Optional

from backend.app.services.content_organizer import ContentOrganizer


class ResultBuilder:
    def __init__(self, html_exporter):
        self.html_exporter = html_exporter
        self.logger = logging.getLogger("ResultBuilder")
        self.content_organizer = ContentOrganizer()

    def _validate_and_normalize_block(self, block: Dict) -> Dict:
        """
        Valide et normalise un bloc de données en s'assurant que tous les champs requis sont présents
        et correctement formatés. Cette fonction est essentielle pour éviter les erreurs de type
        et assurer la cohérence des données.

        Args:
            block: Le bloc à valider et normaliser

        Returns:
            Dict: Le bloc normalisé avec tous les champs requis
        """
        normalized_block = block.copy()

        # Définition des valeurs par défaut pour les champs essentiels
        default_values = {
            'type': 'text',  # Par défaut, on considère que c'est du texte
            'content': '',
            'bbox': [0, 0, 0, 0],
            'style': {
                'fontSize': '12px',
                'fontFamily': 'Arial',
                'fontWeight': 'normal',
                'textAlign': 'left',
                'lineHeight': '14.4px',
                'transform': None,
                'color': 'rgb(0, 0, 0)'
            }
        }

        # Vérification et normalisation du type
        if 'type' not in normalized_block:
            # Si le bloc a un chemin d'image, c'est probablement une image
            if 'path' in normalized_block:
                normalized_block['type'] = 'image'
            else:
                normalized_block['type'] = default_values['type']

        # Normalisation en fonction du type
        if normalized_block['type'] == 'image':
            # Validation des champs requis pour une image
            if 'path' not in normalized_block:
                self.logger.warning("Bloc image sans chemin détecté")
                return None

            # S'assurer que bbox est présent pour les images
            if 'bbox' not in normalized_block:
                normalized_block['bbox'] = default_values['bbox']

        else:  # Type texte
            # Valider et normaliser le contenu
            if 'content' not in normalized_block:
                normalized_block['content'] = default_values['content']

            # Valider et normaliser le style
            if 'style' not in normalized_block:
                normalized_block['style'] = default_values['style']
            else:
                for key, value in default_values['style'].items():
                    if key not in normalized_block['style']:
                        normalized_block['style'][key] = value

            # Valider bbox
            if 'bbox' not in normalized_block:
                normalized_block['bbox'] = default_values['bbox']

        return normalized_block

    async def build_final_result(self,
                                 extraction_result: Dict,
                                 translated_text: str,
                                 page_number: int,
                                 source_lang: str,
                                 target_lang: str) -> Dict:
        """
        Construit le résultat final avec une validation complète des données.
        """
        try:
            # Validation des données d'entrée
            if not extraction_result:
                raise ValueError("Résultat d'extraction vide")

            if 'text_blocks' not in extraction_result:
                self.logger.warning("Aucun bloc de texte trouvé dans le résultat d'extraction")
                extraction_result['text_blocks'] = []

            # Normalisation de tous les blocs
            text_blocks = []
            for block in extraction_result['text_blocks']:
                normalized_block = self._validate_and_normalize_block(block)
                if normalized_block is not None:
                    text_blocks.append(normalized_block)

            # Organisation de la traduction
            translated_parts = translated_text.split('\n')

            # Application des traductions aux blocs normalisés
            for i, block in enumerate(text_blocks):
                if block['type'] == 'text' and i < len(translated_parts):
                    block['content'] = translated_parts[i]

            # Organisation en sections
            sections = self.content_organizer.organize_blocks_into_sections(
                text_blocks,
                translated_parts,
                extraction_result.get('images', [])
            )

            # Génération du HTML
            output_dir = Path("output")
            html_path = output_dir / f"page_{page_number}_translated.html"

            await asyncio.to_thread(
                self.html_exporter.export,
                sections,
                extraction_result.get('images', []),
                str(html_path)
            )

            # Construction du résultat final
            result = {
                "success": True,
                "translated_text": translated_text,
                "images": [
                    self.content_organizer.convert_extracted_image_to_dict(img)
                    for img in extraction_result.get('images', [])
                ],
                "html_path": str(html_path),
                "blocks": [block for section in sections for block in section],
                "page_dimensions": extraction_result.get('page_dimensions', {
                    "width": 612.0,
                    "height": 792.0,
                    "rotation": 0
                }),
                "metadata": {
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "page_number": page_number,
                    "total_sections": len(sections),
                    "total_blocks": sum(len(section) for section in sections),
                    "scale_factor": 1.0
                },
                "message": "Traduction réussie avec validation complète des données"
            }

            return result

        except Exception as e:
            self.logger.error(f"Erreur lors de la construction du résultat: {str(e)}")
            self.logger.debug("État des données au moment de l'erreur:", exc_info=True)
            # Log détaillé pour le débogage
            if 'text_blocks' in locals():
                self.logger.debug(f"Nombre de blocs de texte: {len(text_blocks)}")
                if text_blocks:
                    self.logger.debug(f"Premier bloc: {text_blocks[0]}")
            raise