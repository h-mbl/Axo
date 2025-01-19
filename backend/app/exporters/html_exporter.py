import os
from pathlib import Path
from typing import List, Dict, Union
from dataclasses import dataclass


@dataclass
class ImageInfo:
    """Classe pour stocker les informations d'une image de manière structurée."""
    path: str
    bbox: List[float]
    width: Union[float, None]
    height: Union[float, None]


class HTMLExporter:
    """
    Classe responsable de l'exportation des documents traduits en format HTML.
    Gère la mise en page et le positionnement précis des éléments textuels et images.
    """

    def __init__(self, base_path: str = "output"):
        """
        Initialise l'exportateur HTML avec un chemin de base pour les fichiers.

        Args:
            base_path (str): Le répertoire racine pour tous les fichiers générés
        """
        self.base_path = Path(base_path)
        # Création des répertoires nécessaires
        self.base_path.mkdir(exist_ok=True)
        (self.base_path / "images").mkdir(exist_ok=True)

    def _get_relative_image_path(self, image_path: str, html_path: str) -> str:
        """
        Calcule le chemin relatif correct pour une image par rapport au fichier HTML.

        Args:
            image_path (str): Chemin absolu ou relatif de l'image
            html_path (str): Chemin du fichier HTML de sortie

        Returns:
            str: Chemin relatif correct pour accéder à l'image depuis le HTML
        """
        # Convertir les chemins en objets Path pour une manipulation plus facile
        image_absolute = self.base_path / "images" / os.path.basename(image_path)
        html_absolute = Path(html_path)

        # Calculer le chemin relatif
        return os.path.relpath(image_absolute, html_absolute.parent)

    def _generate_css(self) -> str:
        """
        Génère les styles CSS nécessaires pour le document.

        Returns:
            str: Les règles CSS formatées
        """
        return """
            <style>
                .page-content {
                    position: relative;
                    width: 100%;
                    min-height: 1000px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 20px;
                }
                .text-block {
                    position: absolute;
                    font-family: Arial, sans-serif;
                    line-height: 1.5;
                    margin: 0;
                    padding: 0;
                    overflow-wrap: break-word;
                }
                .image-block {
                    position: absolute;
                    max-width: 100%;
                    height: auto;
                    object-fit: contain;
                }
            </style>
        """

    def export(self, translated_blocks: List[Dict], images: List[Dict], output_path: str) -> None:
        """
        Exporte le contenu traduit en fichier HTML avec la mise en page préservée.

        Args:
            translated_blocks (List[Dict]): Liste des blocs de texte traduits avec leur position
            images (List[Dict]): Liste des informations sur les images
            output_path (str): Chemin où sauvegarder le fichier HTML
        """
        # Début du document HTML
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

        # Trier les blocs par position verticale pour une lecture naturelle
        sorted_blocks = sorted(translated_blocks, key=lambda x: x['bbox'][1])

        # Traiter chaque bloc (texte ou image)
        for block in sorted_blocks:
            if block['type'] == 'text' and block['content'].strip():
                # Calcul des dimensions pour le texte
                left = f"{block['bbox'][0]}px"
                top = f"{block['bbox'][1]}px"
                width = f"{block['bbox'][2] - block['bbox'][0]}px"

                html_content += f"""
                <div class="text-block" style="
                    left: {left};
                    top: {top};
                    width: {width};
                    ">
                    {block['content']}
                </div>
                """
            elif block['type'] == 'image':
                # Traitement des images avec chemins relatifs corrects
                left = f"{block['bbox'][0]}px"
                top = f"{block['bbox'][1]}px"
                width = f"{block['bbox'][2] - block['bbox'][0]}px"

                # Calculer le chemin relatif correct pour l'image
                image_path = self._get_relative_image_path(block['path'], output_path)

                html_content += f"""
                <img class="image-block" 
                    src="{image_path}"
                    alt="Image extraite du PDF"
                    style="
                        left: {left};
                        top: {top};
                        width: {width};
                    "
                >
                """

        # Fermeture du document HTML
        html_content += """
        </div>
        </body>
        </html>
        """

        # Créer le répertoire de sortie si nécessaire
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Écrire le fichier HTML
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)