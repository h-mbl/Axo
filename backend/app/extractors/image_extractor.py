import fitz
from PIL import Image
import io
import os
import torch
from transformers import pipeline
import hashlib
from pathlib import Path
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ExtractedImage:
    """Classe pour stocker les informations d'une image extraite."""
    path: str  # Chemin de l'image sauvegardée
    caption: str  # Légende générée par BLIP
    bbox: tuple  # Position dans le PDF (x0, y0, x1, y1)
    page_number: int  # Numéro de la page
    context_text: str  # Texte environnant l'image
    marker: str  # Marqueur unique pour référencer l'image dans le texte
    size: tuple  # Dimensions de l'image (largeur, hauteur)


class EnhancedPDFImageExtractor:
    """Extracteur d'images PDF amélioré avec génération de légendes et analyse contextuelle."""

    def __init__(self, output_dir: str = "output/images", min_size: int = 100):
        """
        Initialise l'extracteur d'images PDF.

        Args:
            output_dir: Répertoire de sortie pour les images
            min_size: Taille minimale (en pixels) pour considérer une image valide
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.min_size = min_size
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.image_captioner = None
        self.logger = logging.getLogger(__name__)

        # Configuration du logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def _ensure_image_captioner(self) -> bool:
        """Initialise le modèle de génération de légendes si nécessaire."""
        if self.image_captioner is None:
            try:
                self.logger.info("Chargement du modèle BLIP...")
                self.image_captioner = pipeline(
                    "image-to-text",
                    model="Salesforce/blip-image-captioning-base",
                    device=self.device
                )
                self.logger.info("Modèle BLIP chargé avec succès")
                return True
            except Exception as e:
                self.logger.error(f"Erreur lors du chargement du modèle BLIP: {str(e)}")
                return False
        return True

    def _get_surrounding_text(self, page: fitz.Page, bbox: tuple, context_size: int = 200) -> str:
        """
        Extrait le texte autour d'une zone spécifique dans la page.

        Args:
            page: Page du PDF
            bbox: Coordonnées de la zone (x0, y0, x1, y1)
            context_size: Nombre de caractères à extraire avant et après
        """
        try:
            # Élargir légèrement la zone de recherche
            x0, y0, x1, y1 = bbox
            margin = 20  # pixels
            search_area = (x0 - margin, y0 - margin, x1 + margin, y1 + margin)

            # Extraire le texte de la zone élargie
            text_dict = page.get_text("dict", clip=search_area)

            # Rassembler tout le texte trouvé
            text_parts = []
            for block in text_dict.get("blocks", []):
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text_parts.append(span.get("text", ""))

            full_text = " ".join(text_parts)

            # Limiter la longueur du contexte
            if len(full_text) > context_size * 2:
                start = max(0, len(full_text) // 2 - context_size)
                end = min(len(full_text), len(full_text) // 2 + context_size)
                full_text = full_text[start:end]

            return full_text.strip()

        except Exception as e:
            self.logger.warning(f"Erreur lors de l'extraction du contexte: {str(e)}")
            return ""

    def _extract_image(self, doc: fitz.Document, xref: int) -> Optional[Image.Image]:
        """
        Extrait une image à partir de sa référence dans le PDF.

        Args:
            doc: Document PDF
            xref: Référence de l'image
        """
        try:
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            return Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            self.logger.error(f"Erreur lors de l'extraction de l'image {xref}: {str(e)}")
            return None

    def _generate_caption(self, image: Image.Image) -> str:
        """
        Génère une légende pour une image en utilisant BLIP.

        Args:
            image: Image PIL à décrire
        """
        if not self._ensure_image_captioner():
            return "Image description not available"

        try:
            result = self.image_captioner(image)
            return result[0]['generated_text']
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération de la légende: {str(e)}")
            return "Image description not available"

    def extract_images(self, pdf_path: str, page_number: int) -> List[ExtractedImage]:
        """
        Extrait toutes les images d'une page spécifique d'un PDF
        """
        extracted_images = []

        try:
            doc = fitz.open(pdf_path)
            page = doc[page_number - 1]  # Les pages commencent à 0

            # Obtenir la liste des images de la page
            image_list = page.get_images()  # Notez la différence : pas de paramètre full=True

            for img_index, img in enumerate(image_list):
                try:
                    # Extraction directe de l'image avec xref
                    xref = img[0]  # Obtenir la référence de l'image
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]

                    # Conversion en image PIL
                    image = Image.open(io.BytesIO(image_bytes))

                    # Vérification de la taille minimale
                    if image.width < self.min_size or image.height < self.min_size:
                        continue

                    # Génération du nom de fichier unique
                    image_hash = hashlib.md5(image_bytes).hexdigest()[:8]
                    image_filename = f"page_{page_number}_img_{img_index}_{image_hash}.png"
                    image_path = str(self.output_dir / image_filename)

                    # Sauvegarde de l'image
                    image.save(image_path, "PNG")

                    # Obtention de la zone de l'image (bbox)
                    bbox = page.get_image_bbox(xref)

                    # Extraction du contexte et génération de la légende
                    context = self._get_surrounding_text(page, bbox)
                    caption = self._generate_caption(image)

                    # Création de l'objet ExtractedImage
                    extracted_image = ExtractedImage(
                        path=image_path,
                        caption=caption,
                        bbox=bbox,
                        page_number=page_number,
                        context_text=context,
                        marker=f"[IMAGE{img_index}]",
                        size=(image.width, image.height)
                    )

                    extracted_images.append(extracted_image)
                    self.logger.info(f"Image extraite avec succès: {image_filename}")

                except Exception as e:
                    self.logger.error(f"Erreur lors du traitement de l'image {img_index}: {str(e)}")
                    continue

            doc.close()
            return extracted_images

        except Exception as e:
            self.logger.error(f"Erreur lors de l'ouverture du PDF: {str(e)}")
            return []

    def get_image_statistics(self, extracted_images: List[ExtractedImage]) -> Dict:
        """
        Génère des statistiques sur les images extraites.

        Args:
            extracted_images: Liste des images extraites
        """
        return {
            "total_images": len(extracted_images),
            "average_width": sum(img.size[0] for img in extracted_images) / len(
                extracted_images) if extracted_images else 0,
            "average_height": sum(img.size[1] for img in extracted_images) / len(
                extracted_images) if extracted_images else 0,
            "images_with_context": sum(1 for img in extracted_images if img.context_text.strip()),
            "images_with_caption": sum(
                1 for img in extracted_images if img.caption != "Image description not available")
        }