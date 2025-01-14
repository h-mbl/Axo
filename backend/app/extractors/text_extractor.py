from pathlib import Path
import logging
from markitdown import MarkItDown
import fitz
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re


@dataclass
class TextBlock:
    """Classe pour représenter un bloc de texte extrait avec ses métadonnées."""
    content: str  # Le texte extrait
    position: tuple  # Position dans la page (x0, y0, x1, y1)
    style: Dict  # Informations de style (police, taille, etc.)
    level: int  # Niveau hiérarchique (pour les titres)
    is_title: bool  # Indique si c'est un titre
    page_number: int  # Numéro de la page


class EnhancedTextExtractor:
    """
    Extracteur de texte PDF amélioré utilisant MarkItDown et PyMuPDF.
    Combine les capacités de structuration de MarkItDown avec l'extraction
    précise de la mise en page de PyMuPDF.
    """

    def __init__(self):
        """
        Initialise l'extracteur avec MarkItDown et configure le logging.
        """
        # Initialisation de MarkItDown
        self.md = MarkItDown()

        # Configuration du logging
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def _analyze_text_style(self, block: Dict) -> Dict:
        """
        Analyse le style d'un bloc de texte (police, taille, etc.).

        Args:
            block: Bloc de texte extrait par PyMuPDF

        Returns:
            Dict contenant les informations de style
        """
        style_info = {}

        try:
            if "lines" in block:
                # Examiner le premier span du bloc pour les informations de style
                first_line = block["lines"][0]
                if first_line["spans"]:
                    first_span = first_line["spans"][0]
                    style_info = {
                        "font": first_span.get("font", ""),
                        "size": first_span.get("size", 0),
                        "flags": first_span.get("flags", 0),  # Contient des infos comme bold, italic
                        "color": first_span.get("color", 0),
                        "ascender": first_span.get("ascender", 0),
                        "descender": first_span.get("descender", 0)
                    }
        except Exception as e:
            self.logger.warning(f"Erreur lors de l'analyse du style: {str(e)}")

        return style_info

    def _is_title(self, block: Dict, style_info: Dict) -> Tuple[bool, int]:
        """
        Détermine si un bloc de texte est un titre et son niveau.

        Args:
            block: Bloc de texte
            style_info: Informations de style du bloc

        Returns:
            Tuple (is_title, level)
        """
        is_title = False
        level = 0

        try:
            # Critères pour identifier un titre
            text = " ".join(span["text"] for line in block["lines"]
                            for span in line["spans"]).strip()

            # Vérifier la taille de la police
            font_size = style_info.get("size", 0)

            # Vérifier si le texte correspond à un format de titre
            title_patterns = [
                (r"^(?:Chapter|Section)\s+\d+", 1),  # Chapitres et sections
                (r"^\d+\.\d+\s+[A-Z]", 2),  # Sous-sections (e.g., "1.2 Title")
                (r"^\d+\.\d+\.\d+\s+[A-Z]", 3)  # Sous-sous-sections
            ]

            for pattern, level_value in title_patterns:
                if re.match(pattern, text):
                    is_title = True
                    level = level_value
                    break

            # Si ce n'est pas déjà identifié comme titre par le motif
            if not is_title:
                # Vérifier la taille de la police et d'autres caractéristiques
                if font_size > 12:  # Taille arbitraire, à ajuster selon vos besoins
                    is_title = True
                    # Déterminer le niveau en fonction de la taille
                    if font_size >= 18:
                        level = 1
                    elif font_size >= 14:
                        level = 2
                    else:
                        level = 3

        except Exception as e:
            self.logger.warning(f"Erreur lors de l'analyse du titre: {str(e)}")

        return is_title, level

    def extract_text_with_layout(self, pdf_path: str, page_number: int) -> List[TextBlock]:
        """
        Extrait le texte d'une page avec sa mise en page et sa structure.
        Combine l'extraction de MarkItDown avec l'analyse de mise en page de PyMuPDF.

        Args:
            pdf_path: Chemin vers le fichier PDF
            page_number: Numéro de la page à extraire

        Returns:
            Liste de TextBlock contenant le texte structuré
        """
        try:
            # Utiliser MarkItDown pour l'extraction initiale
            md_result = self.md.convert(str(pdf_path))

            # Ouvrir le PDF avec PyMuPDF pour l'analyse détaillée
            doc = fitz.open(pdf_path)
            page = doc[page_number - 1]

            # Extraire les blocs avec PyMuPDF
            blocks = page.get_text("dict")["blocks"]

            text_blocks = []

            for block in blocks:
                if block["type"] == 0:  # Type 0 = bloc de texte
                    try:
                        # Analyser le style
                        style_info = self._analyze_text_style(block)

                        # Vérifier si c'est un titre
                        is_title, level = self._is_title(block, style_info)

                        # Extraire le texte du bloc
                        text_content = " ".join(
                            span["text"] for line in block["lines"]
                            for span in line["spans"]
                        ).strip()

                        # Créer le TextBlock
                        if text_content:  # Ignorer les blocs vides
                            text_block = TextBlock(
                                content=text_content,
                                position=block["bbox"],
                                style=style_info,
                                level=level,
                                is_title=is_title,
                                page_number=page_number
                            )
                            text_blocks.append(text_block)

                    except Exception as e:
                        self.logger.warning(f"Erreur lors du traitement d'un bloc: {str(e)}")
                        continue

            doc.close()
            return text_blocks

        except Exception as e:
            self.logger.error(f"Erreur lors de l'extraction du texte: {str(e)}")
            raise

    def get_document_structure(self, pdf_path: str) -> Dict:
        """
        Analyse la structure globale du document en utilisant MarkItDown.

        Args:
            pdf_path: Chemin vers le fichier PDF

        Returns:
            Dictionnaire contenant la structure du document
        """
        try:
            result = self.md.convert(str(pdf_path))

            # Extraire la structure du document
            structure = {
                "title": result.metadata.get("title", ""),
                "author": result.metadata.get("author", ""),
                "date": result.metadata.get("date", ""),
                "sections": self._extract_sections(result.text_content),
                "total_pages": len(result.pages) if hasattr(result, "pages") else 0
            }

            return structure

        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse de la structure: {str(e)}")
            return {}

    def _extract_sections(self, text_content: str) -> List[Dict]:
        """
        Extrait la structure des sections du texte.

        Args:
            text_content: Texte complet du document

        Returns:
            Liste de sections avec leur hiérarchie
        """
        sections = []
        current_level = 0
        current_section = None

        # Expression régulière pour détecter les titres de section
        section_pattern = re.compile(
            r'^(\d+\.)*\d+\s+([^\n]+)',
            re.MULTILINE
        )

        for match in section_pattern.finditer(text_content):
            number, title = match.groups()
            level = len(number.split("."))

            section = {
                "number": number.strip(),
                "title": title.strip(),
                "level": level,
                "subsections": []
            }

            if level == 1:
                sections.append(section)
                current_section = section
            elif current_section is not None:
                current_section["subsections"].append(section)

        return sections

    def extract_table_of_contents(self, pdf_path: str) -> List[Dict]:
        """
        Extrait la table des matières du document.

        Args:
            pdf_path: Chemin vers le fichier PDF

        Returns:
            Liste structurée de la table des matières
        """
        try:
            doc = fitz.open(pdf_path)
            toc = doc.get_toc()

            # Transformer le TOC en structure plus utilisable
            structured_toc = []
            for level, title, page in toc:
                entry = {
                    "level": level,
                    "title": title,
                    "page": page,
                }
                structured_toc.append(entry)

            doc.close()
            return structured_toc

        except Exception as e:
            self.logger.error(f"Erreur lors de l'extraction de la table des matières: {str(e)}")
            return []


# Exemple d'utilisation
def main():
    extractor = EnhancedTextExtractor()
    pdf_path = "example.pdf"

    try:
        # Extraire la structure du document
        structure = extractor.get_document_structure(pdf_path)
        print("Structure du document:")
        print(f"Titre: {structure['title']}")
        print(f"Auteur: {structure['author']}")
        print(f"Nombre de pages: {structure['total_pages']}")

        # Extraire le texte d'une page spécifique
        page_number = 1
        text_blocks = extractor.extract_text_with_layout(pdf_path, page_number)

        print(f"\nContenu de la page {page_number}:")
        for block in text_blocks:
            prefix = "  " * block.level
            if block.is_title:
                print(f"{prefix}[TITRE] {block.content}")
            else:
                print(f"{prefix}{block.content[:100]}...")

        # Extraire la table des matières
        toc = extractor.extract_table_of_contents(pdf_path)
        print("\nTable des matières:")
        for entry in toc:
            print(f"{'  ' * entry['level']}{entry['title']} (page {entry['page']})")

    except Exception as e:
        print(f"Erreur: {str(e)}")

