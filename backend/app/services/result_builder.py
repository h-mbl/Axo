# app/services/result_builder.py
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

    def _merge_adjacent_blocks(self, text_blocks: List[Dict]) -> List[Dict]:
        """
        Fusionne les blocs de texte adjacents après les avoir normalisés.
        """
        normalized_blocks = []
        for block in text_blocks:
            normalized_block = self._validate_and_normalize_block(block)
            if normalized_block is not None:
                normalized_blocks.append(normalized_block)

        if not normalized_blocks:
            return []

        merged = []
        current_block = normalized_blocks[0]

        for next_block in normalized_blocks[1:]:
            if (self._are_blocks_similar(current_block, next_block) and
                    self._are_blocks_adjacent(current_block, next_block)):
                # Fusion des boîtes englobantes
                current_block['bbox'] = [
                    min(current_block['bbox'][0], next_block['bbox'][0]),
                    min(current_block['bbox'][1], next_block['bbox'][1]),
                    max(current_block['bbox'][2], next_block['bbox'][2]),
                    max(current_block['bbox'][3], next_block['bbox'][3])
                ]
            else:
                merged.append(current_block)
                current_block = next_block

        merged.append(current_block)
        return merged

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

    # app/services/result_builder.py

    def _are_blocks_similar(self, block1: Dict, block2: Dict) -> bool:
        """
        Détermine si deux blocs sont similaires en comparant leurs propriétés.
        Cette méthode utilise plusieurs critères pour établir la similarité :
        - Type de bloc (texte/image)
        - Propriétés de style (police, taille, etc.)
        - Attributs géométriques (alignement, rotation)

        Args:
            block1: Premier bloc à comparer
            block2: Second bloc à comparer

        Returns:
            bool: True si les blocs sont considérés comme similaires, False sinon
        """
        try:
            # Vérification préliminaire des types
            if block1.get('type') != block2.get('type'):
                return False

            # Pour les images, comparaison simple
            if block1.get('type') == 'image':
                return True  # Les images sont toujours considérées comme uniques

            # Pour les blocs de texte, comparaison approfondie
            style1 = block1.get('style', {})
            style2 = block2.get('style', {})

            # Liste des propriétés de style à comparer
            style_properties = [
                ('fontSize', self._normalize_font_size),
                ('fontFamily', str.lower),
                ('fontWeight', str.lower),
                ('textAlign', str.lower)
            ]

            # Comparaison des propriétés de style avec normalisation
            for prop, normalizer in style_properties:
                value1 = style1.get(prop)
                value2 = style2.get(prop)

                # Si l'une des valeurs est manquante, on continue
                if value1 is None or value2 is None:
                    continue

                # Normalisation et comparaison des valeurs
                if normalizer(value1) != normalizer(value2):
                    return False

            # Vérification de la rotation (avec tolérance)
            rotation1 = self._extract_rotation(style1.get('transform'))
            rotation2 = self._extract_rotation(style2.get('transform'))
            if not self._are_rotations_similar(rotation1, rotation2):
                return False

            return True

        except Exception as e:
            self.logger.warning(f"Erreur lors de la comparaison des blocs: {str(e)}")
            return False

    @staticmethod
    def _normalize_font_size(font_size: str) -> float:
        """
        Normalise la taille de police en flottant pour comparaison.
        Gère les différents formats possibles (px, pt, em, etc.).

        Args:
            font_size: Taille de police sous forme de chaîne (ex: "12px", "10pt")

        Returns:
            float: Taille normalisée en pixels
        """
        try:
            # Suppression des unités et conversion en float
            return float(''.join(c for c in font_size if c.isdigit() or c == '.'))
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _extract_rotation(transform: Optional[str]) -> float:
        """
        Extrait l'angle de rotation d'une transformation CSS.

        Args:
            transform: Chaîne de transformation CSS (ex: "rotate(45deg)")

        Returns:
            float: Angle de rotation en degrés
        """
        try:
            if not transform:
                return 0.0

            # Extraction de l'angle à partir de rotate(Xdeg)
            import re
            match = re.search(r'rotate\(([-\d.]+)deg\)', transform)
            if match:
                return float(match.group(1))
            return 0.0
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _are_rotations_similar(rotation1: float, rotation2: float) -> bool:
        """
        Compare deux angles de rotation avec une certaine tolérance.

        Args:
            rotation1: Premier angle de rotation en degrés
            rotation2: Second angle de rotation en degrés

        Returns:
            bool: True si les rotations sont similaires, False sinon
        """
        # Tolérance de 1 degré pour les rotations
        tolerance = 1.0
        return abs(rotation1 - rotation2) <= tolerance


    def _are_blocks_adjacent(self, block1: Dict, block2: Dict) -> bool:
        """
        Détermine si deux blocs sont adjacents dans le document en prenant en compte
        leur position relative et leur chevauchement.

        La méthode considère plusieurs facteurs :
        1. La distance verticale entre les blocs
        2. Le chevauchement horizontal
        3. L'alignement général des blocs

        Args:
            block1: Premier bloc à comparer (dictionnaire avec bbox)
            block2: Second bloc à comparer (dictionnaire avec bbox)

        Returns:
            bool: True si les blocs sont considérés comme adjacents, False sinon
        """
        try:
            # Extraction des coordonnées des boîtes englobantes
            x1_min, y1_min, x1_max, y1_max = block1['bbox']
            x2_min, y2_min, x2_max, y2_max = block2['bbox']

            # Définition des seuils de tolérance (ajustables selon vos besoins)
            VERTICAL_TOLERANCE = 15.0  # Distance verticale maximale (en points)
            OVERLAP_THRESHOLD = 0.3  # Pourcentage minimum de chevauchement horizontal

            # 1. Vérification de la distance verticale
            vertical_distance = abs(y2_min - y1_max)  # Distance entre le bas du bloc1 et le haut du bloc2
            if vertical_distance > VERTICAL_TOLERANCE:
                return False

            # 2. Calcul du chevauchement horizontal
            # Largeur de la zone de chevauchement
            overlap_width = min(x1_max, x2_max) - max(x1_min, x2_min)

            # Si pas de chevauchement, on vérifie quand même si les blocs sont proches horizontalement
            if overlap_width <= 0:
                horizontal_gap = max(x1_min, x2_min) - min(x1_max, x2_max)
                return horizontal_gap <= VERTICAL_TOLERANCE  # Utilise la même tolérance

            # Calcul du pourcentage de chevauchement par rapport au bloc le plus étroit
            block1_width = x1_max - x1_min
            block2_width = x2_max - x2_min
            min_width = min(block1_width, block2_width)

            overlap_ratio = overlap_width / min_width

            # 3. Vérification de l'alignement
            if overlap_ratio >= OVERLAP_THRESHOLD:
                # Les blocs ont un chevauchement significatif
                return True

            # 4. Vérification des styles si disponibles
            if self._have_compatible_styles(block1, block2):
                # On peut être plus tolérant avec les blocs de même style
                return overlap_ratio >= OVERLAP_THRESHOLD / 2

            return False

        except Exception as e:
            self.logger.warning(f"Erreur lors de la vérification d'adjacence: {str(e)}")
            return False

    def _have_compatible_styles(self, block1: Dict, block2: Dict) -> bool:
        """
        Vérifie si deux blocs ont des styles compatibles pour l'adjacence.
        Cette vérification est plus souple que _are_blocks_similar.

        Args:
            block1: Premier bloc avec propriétés de style
            block2: Second bloc avec propriétés de style

        Returns:
            bool: True si les styles sont compatibles, False sinon
        """
        try:
            style1 = block1.get('style', {})
            style2 = block2.get('style', {})

            # Vérifie uniquement les propriétés essentielles
            essential_properties = ['fontSize', 'fontFamily']

            for prop in essential_properties:
                if style1.get(prop) != style2.get(prop):
                    return False

            return True

        except Exception as e:
            self.logger.warning(f"Erreur lors de la comparaison des styles: {str(e)}")
            return False