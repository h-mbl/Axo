import fitz  # PyMuPDF
import pdfplumber
from pdf2image import convert_from_path
import camelot
from pikepdf import Pdf
import os
from pathlib import Path
import logging
from PIL import Image
import io
import hashlib
import cv2
import numpy as np


class ComprehensivePDFExtractor:
    def __init__(self):
        # Configuration du logging pour suivre le processus d'extraction
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        self.extracted_images = set()  # Pour la déduplication
        self.image_hashes = set()  # Pour le suivi des images uniques

    def _get_image_hash(self, image_bytes):
        """Calcule un hash unique pour une image"""
        return hashlib.md5(image_bytes).hexdigest()

    def _is_duplicate(self, image_bytes):
        """Vérifie si une image est un doublon"""
        image_hash = self._get_image_hash(image_bytes)
        if image_hash in self.image_hashes:
            return True
        self.image_hashes.add(image_hash)
        return False

    def _extract_with_pymupdf(self, pdf_path, output_dir):
        """Extraction avec PyMuPDF - Efficace pour les images bitmap intégrées"""
        extracted = []
        self.logger.info("Starting PyMuPDF extraction")

        doc = fitz.open(pdf_path)
        for page_num in range(doc.page_count):
            page = doc[page_num]
            image_list = page.get_images()

            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]

                    if not self._is_duplicate(image_bytes):
                        image_path = output_dir / f"pymupdf_p{page_num + 1}_{img_index}.{base_image['ext']}"
                        with open(image_path, "wb") as f:
                            f.write(image_bytes)
                        extracted.append(image_path)

                except Exception as e:
                    self.logger.error(f"PyMuPDF extraction error: {e}")

        return extracted

    def _extract_with_pdfplumber(self, pdf_path, output_dir):
        """Extraction avec pdfplumber - Bon pour les images avec métadonnées"""
        extracted = []
        self.logger.info("Starting pdfplumber extraction")

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                images = page.images

                for img_index, img in enumerate(images):
                    try:
                        image_bytes = img['stream'].get_data()

                        if not self._is_duplicate(image_bytes):
                            image_path = output_dir / f"pdfplumber_p{page_num + 1}_{img_index}.png"
                            with open(image_path, "wb") as f:
                                f.write(image_bytes)
                            extracted.append(image_path)

                    except Exception as e:
                        self.logger.error(f"pdfplumber extraction error: {e}")

        return extracted

    def _extract_with_pikepdf(self, pdf_path, output_dir):
        """Extraction avec pikepdf - Accès bas niveau aux objets PDF"""
        extracted = []
        self.logger.info("Starting pikepdf extraction")

        try:
            pdf = Pdf.open(pdf_path)
            for page_num, page in enumerate(pdf.pages):
                try:
                    for img_index, (name, image) in enumerate(page.images.items()):
                        raw_bytes = image.read_bytes()

                        if not self._is_duplicate(raw_bytes):
                            image_path = output_dir / f"pikepdf_p{page_num + 1}_{img_index}.png"
                            with open(image_path, "wb") as f:
                                f.write(raw_bytes)
                            extracted.append(image_path)

                except Exception as e:
                    self.logger.error(f"pikepdf page extraction error: {e}")

        except Exception as e:
            self.logger.error(f"pikepdf general error: {e}")

        return extracted

    def _extract_with_camelot(self, pdf_path, output_dir):
        """Extraction avec Camelot - Spécialisé dans la détection de zones graphiques"""
        extracted = []
        self.logger.info("Starting Camelot extraction")

        try:
            # Utiliser le mode stream pour détecter les zones non textuelles
            tables = camelot.read_pdf(pdf_path, flavor='stream')

            for table_num, table in enumerate(tables):
                try:
                    # Analyser les zones non textuelles qui pourraient être des images
                    img = table.parsing_report.get('figure_bbox')
                    if img:
                        # Convertir la zone détectée en image
                        image_path = output_dir / f"camelot_region_{table_num}.png"
                        extracted.append(image_path)

                except Exception as e:
                    self.logger.error(f"Camelot table extraction error: {e}")

        except Exception as e:
            self.logger.error(f"Camelot general error: {e}")

        return extracted

    def _extract_with_pdf2image(self, pdf_path, output_dir):
        """Extraction avec pdf2image - Capture visuelle complète"""
        extracted = []
        self.logger.info("Starting pdf2image extraction")

        try:
            pages = convert_from_path(pdf_path)
            for i, page in enumerate(pages):
                page_path = output_dir / f"page_{i + 1}.png"
                page.save(str(page_path), "PNG")
                extracted.append(page_path)

                # Analyse supplémentaire pour détecter les zones d'images
                self._analyze_page_for_images(page, i, output_dir, extracted)

        except Exception as e:
            self.logger.error(f"pdf2image extraction error: {e}")

        return extracted

    def _analyze_page_for_images(self, page_image, page_num, output_dir, extracted):
        """Analyse avancée d'une page pour détecter les zones d'images"""
        try:
            # Convertir l'image PIL en format OpenCV
            opencv_image = cv2.cvtColor(np.array(page_image), cv2.COLOR_RGB2BGR)

            # Détecter les contours
            gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for i, contour in enumerate(contours):
                # Filtrer les contours pertinents
                area = cv2.contourArea(contour)
                if area > 1000:  # Ignorer les petites zones
                    x, y, w, h = cv2.boundingRect(contour)
                    region = opencv_image[y:y + h, x:x + w]

                    # Sauvegarder la région comme potentielle image
                    region_path = output_dir / f"region_p{page_num + 1}_{i}.png"
                    cv2.imwrite(str(region_path), region)
                    extracted.append(region_path)

        except Exception as e:
            self.logger.error(f"Page analysis error: {e}")

    def extract_all_images(self, pdf_path, output_dir="extracted_images"):
        """Méthode principale combinant toutes les approches d'extraction"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        self.logger.info(f"Starting comprehensive extraction from {pdf_path}")

        # Créer des sous-dossiers pour chaque méthode
        methods_dirs = {
            "pymupdf": output_path / "pymupdf",
            "pdfplumber": output_path / "pdfplumber",
            "pikepdf": output_path / "pikepdf",
            "camelot": output_path / "camelot",
            "pdf2image": output_path / "pdf2image"
        }

        for dir_path in methods_dirs.values():
            dir_path.mkdir(exist_ok=True)

        # Extraire avec chaque méthode
        results = {
            "pymupdf": self._extract_with_pymupdf(pdf_path, methods_dirs["pymupdf"]),
            "pdfplumber": self._extract_with_pdfplumber(pdf_path, methods_dirs["pdfplumber"]),
            "pikepdf": self._extract_with_pikepdf(pdf_path, methods_dirs["pikepdf"]),
            "camelot": self._extract_with_camelot(pdf_path, methods_dirs["camelot"]),
            "pdf2image": self._extract_with_pdf2image(pdf_path, methods_dirs["pdf2image"])
        }

        # Analyser et regrouper les résultats
        stats = {
            "total_unique_images": len(self.image_hashes),
            "images_by_method": {
                method: len(images) for method, images in results.items()
            },
            "total_images_found": sum(len(images) for images in results.values())
        }

        return results, stats


def main():
    extractor = ComprehensivePDFExtractor()
    pdf_path = "uploads/plannification_strategie.pdf"
    results, stats = extractor.extract_all_images(pdf_path)

    print("\nExtraction Results:")
    print(f"Total unique images found: {stats['total_unique_images']}")
    print(f"Total images extracted (including duplicates): {stats['total_images_found']}")
    print("\nImages found by each method:")

    for method, images in results.items():
        print(f"\n- {method}: {len(images)} images")
        for image_path in images:
            print(f"  - {image_path}")


if __name__ == "__main__":
    main()