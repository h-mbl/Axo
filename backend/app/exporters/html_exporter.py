# backend/app/exporters/html_exporter.py
import os
from pathlib import Path
from typing import List, Dict, Union
from dataclasses import dataclass


@dataclass
class ImageInfo:
    """Classe pour stocker les informations d'une image de manière structurée."""
    path: str
    bbox: tuple
    width: Union[float, None]
    height: Union[float, None]


class HTMLExporter:
    """
    Classe responsable de l'exportation des documents traduits en format HTML.
    Gère la mise en page et le positionnement précis des éléments par sections.
    """

    def __init__(self, base_path: str = "output"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        (self.base_path / "images").mkdir(exist_ok=True)

    @staticmethod
    def _generate_css() -> str:
        """
        Génère des styles CSS améliorés avec support des sections et meilleure gestion
        des espacements.
        """
        return """
            <style>
                /* Style de base pour le conteneur de page */
                .page-content {
                    position: relative;
                    width: 100%;
                    min-height: 1000px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 20px;
                }

                /* Style pour les sections logiques */
                .document-section {
                    position: relative;
                    margin-bottom: 2em;
                    clear: both; /* Évite les problèmes de flottement */
                }

                /* Style pour les blocs de texte avec positionnement amélioré */
                .text-block {
                    position: absolute;
                    font-family: Arial, sans-serif;
                    line-height: 1.5;
                    margin: 0;
                    padding: 0;
                    overflow-wrap: break-word;
                    z-index: 1; /* Place le texte au-dessus des images par défaut */
                }

                /* Style pour les titres de section */
                .section-title {
                    font-weight: bold;
                    margin-bottom: 1em;
                }

                /* Style pour les images avec gestion de position */
                .image-block {
                    position: absolute;
                    max-width: 100%;
                    height: auto;
                    object-fit: contain;
                    z-index: 0; /* Place les images en arrière-plan par défaut */
                }

                /* Style pour la zone de contenu d'une section */
                .section-content {
                    position: relative;
                    width: 100%;
                }
            </style>
        """

    @staticmethod
    def _calculate_section_boundaries(section_blocks: List[Dict]) -> Dict:
        """
        Calcule les limites d'une section pour assurer un bon positionnement.
        """
        if not section_blocks:
            return {"top": 0, "bottom": 0, "left": 0, "right": 0}

        boundaries = {
            "top": float('inf'),
            "bottom": float('-inf'),
            "left": float('inf'),
            "right": float('-inf')
        }

        for block in section_blocks:
            bbox = block['bbox']
            boundaries["top"] = min(boundaries["top"], bbox[1])
            boundaries["bottom"] = max(boundaries["bottom"], bbox[3])
            boundaries["left"] = min(boundaries["left"], bbox[0])
            boundaries["right"] = max(boundaries["right"], bbox[2])

        return boundaries

    def _get_relative_image_path(self, image_path: str, html_path: str) -> str:
        """Calcule le chemin relatif des images."""
        image_absolute = self.base_path / "images" / os.path.basename(image_path)
        html_absolute = Path(html_path)
        return os.path.relpath(image_absolute, html_absolute.parent)

    def export(self, sections: List[List[Dict]], images: List[Dict], output_path: str) -> None:
        """
        Exporte le contenu traduit en HTML en respectant la structure des sections.

        Args:
            sections: Liste des sections, chaque section contenant ses blocs
            images: Liste des informations sur les images
            output_path: Chemin de sortie du fichier HTML
        """
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            {self._generate_css()}
        </head>
        <body>
        <div class="page-content">
        """

        current_y_offset = 0

        # Traitement section par section
        for section_index, section_blocks in enumerate(sections):
            # Calcul des limites de la section
            boundaries = self._calculate_section_boundaries(section_blocks)
            section_height = boundaries["bottom"] - boundaries["top"]

            html_content += f'<div class="document-section" style="min-height: {section_height}px;">'

            # Traitement des blocs de la section
            for block in section_blocks:
                # Ajustement des positions relatives à la section
                relative_top = block['bbox'][1] - boundaries["top"]

                if block['type'] == 'text':
                    # Positionnement du texte avec z-index pour éviter les chevauchements
                    html_content += f"""
                    <div class="text-block" style="
                        left: {block['bbox'][0]}px;
                        top: {relative_top + current_y_offset}px;
                        width: {block['bbox'][2] - block['bbox'][0]}px;
                        {'; '.join(f'{k}: {v}' for k, v in block['style'].items() if v is not None)};
                        z-index: {2 if block.get('is_title') else 1};
                    ">
                        {block['content']}
                    </div>
                    """
                elif block['type'] == 'image':
                    # Gestion des images avec positionnement relatif à la section
                    image_path = self._get_relative_image_path(block['path'], output_path)
                    html_content += f"""
                    <img class="image-block" 
                        src="{image_path}"
                        alt="Image extraite du PDF"
                        style="
                            left: {block['bbox'][0]}px;
                            top: {relative_top + current_y_offset}px;
                            width: {block['bbox'][2] - block['bbox'][0]}px;
                            height: {block['bbox'][3] - block['bbox'][1]}px;
                        "
                    >
                    """

            html_content += '</div>'
            current_y_offset += section_height + 20  # Ajoute un espacement entre les sections

        html_content += """
        </div>
        </body>
        </html>
        """

        # Création du répertoire de sortie si nécessaire
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Écriture du fichier HTML
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)