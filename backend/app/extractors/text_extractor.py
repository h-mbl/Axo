from pathlib import Path
import logging
from markitdown import MarkItDown
import fitz
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import re


@dataclass
class TextBlock:
    """Classe enrichie pour représenter un bloc de texte avec des métadonnées complètes."""
    content: str
    bbox: List[float]  # Changé de tuple à list pour une meilleure sérialisation
    font_size: float
    font_name: str
    font_weight: str
    text_alignment: str
    line_height: float
    rotation: float
    color: str
    page_number: int
    is_title: bool = False  # Ajouté avec une valeur par défaut
    level: int = 0  # Ajouté avec une valeur par défaut

    def to_dict(self) -> Dict:
        """
        Convertit l'objet TextBlock en dictionnaire sérialisable.
        Cette méthode assure que toutes les valeurs sont JSON-compatibles.
        """
        block_dict = asdict(self)
        # Conversion explicite des types non-sérialisables si nécessaire
        block_dict['bbox'] = list(self.bbox)  # Assure que bbox est une liste
        # Conversion de toutes les valeurs numériques en types de base Python
        block_dict['font_size'] = float(self.font_size)
        block_dict['line_height'] = float(self.line_height)
        block_dict['rotation'] = float(self.rotation)
        return block_dict


class EnhancedTextExtractor:
    """
    Extracteur de texte PDF amélioré utilisant MarkItDown et PyMuPDF.
    Combine les capacités de structuration de MarkItDown avec l'extraction
    précise de la mise en page de PyMuPDF.
    """

    def __init__(self):
        """Initialisation avec support étendu pour l'analyse des styles."""
        self.md = MarkItDown()
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        # Nouvelles constantes pour l'analyse des styles
        self.FONT_WEIGHTS = {
            "bold": ["bold", "heavy", "black"],
            "normal": ["regular", "roman", "book"]
        }

    def _analyze_text_style(self, block: Dict) -> Dict:
        """Analyse enrichie du style d'un bloc de texte."""
        style_info = {}

        try:
            if "lines" in block and block["lines"]:
                first_line = block["lines"][0]
                if first_line["spans"]:
                    first_span = first_line["spans"][0]

                    # Extraction des informations de base
                    font_name = first_span.get("font", "")
                    font_flags = first_span.get("flags", 0)
                    font_size = first_span.get("size", 0)

                    # Détermination du poids de la police
                    font_weight = "normal"
                    font_lower = font_name.lower()
                    for weight, keywords in self.FONT_WEIGHTS.items():
                        if any(kw in font_lower for kw in keywords):
                            font_weight = weight
                            break

                    # Analyse de la couleur
                    color = first_span.get("color", (0, 0, 0))
                    if isinstance(color, (tuple, list)):
                        color = f"rgb({int(color[0] * 255)}, {int(color[1] * 255)}, {int(color[2] * 255)})"

                    # Construction du dictionnaire de style enrichi
                    style_info = {
                        "font_name": font_name,
                        "font_size": font_size,
                        "font_weight": font_weight,
                        "color": color,
                        "flags": font_flags,
                        "ascender": first_span.get("ascender", 0),
                        "descender": first_span.get("descender", 0),
                        "line_height": font_size * 1.2,  # Estimation du line-height
                        "text_alignment": self._determine_text_alignment(block),
                        "rotation": first_span.get("rotation", 0),
                        "opacity": 1.0,
                        "rendering_mode": first_span.get("rendermode", 0)
                    }

        except Exception as e:
            self.logger.warning(f"Erreur lors de l'analyse du style: {str(e)}")

        return style_info

    def _determine_text_alignment(self, block: Dict) -> str:
        """Détermine l'alignement du texte basé sur sa position."""
        try:
            if "lines" not in block or not block["lines"]:
                return "left"

            bbox = block.get("bbox", [0, 0, 0, 0])
            page_width = 595  # Largeur A4 standard en points

            # Calcul de la position relative du bloc
            block_center = (bbox[0] + bbox[2]) / 2
            relative_position = block_center / page_width

            if relative_position < 0.35:
                return "left"
            elif relative_position > 0.65:
                return "right"
            return "center"

        except Exception as e:
            self.logger.warning(f"Erreur lors de la détermination de l'alignement: {str(e)}")
            return "left"

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

    def extract_text_with_layout(self, pdf_path: str, page_number: int) -> Tuple[List[Dict], Dict]:
        """
        Version améliorée qui retourne des dictionnaires sérialisables au lieu d'objets TextBlock.
        """
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_number - 1]

            # Récupération des dimensions de la page
            page_dimensions = {
                "width": float(page.rect.width),  # Conversion explicite en float
                "height": float(page.rect.height),
                "rotation": int(page.rotation)  # Conversion explicite en int
            }

            blocks = []
            for block in page.get_text("dict")["blocks"]:
                if block["type"] == 0:  # Type texte
                    try:
                        # Extraction du style et du texte
                        style_info = self._analyze_text_style(block)
                        is_title, level = self._is_title(block, style_info)

                        # Construction du texte
                        text_content = " ".join(
                            span["text"] for line in block["lines"]
                            for span in line["spans"]
                        ).strip()

                        if text_content:
                            # Création du TextBlock avec des valeurs sûres
                            bbox = list(block["bbox"])  # Conversion explicite en liste
                            text_block = TextBlock(
                                content=text_content,
                                bbox=bbox,
                                font_size=float(style_info.get("font_size", 0)),
                                font_name=str(style_info.get("font_name", "")),
                                font_weight=str(style_info.get("font_weight", "normal")),
                                text_alignment=str(style_info.get("text_alignment", "left")),
                                line_height=float(style_info.get("line_height", 0)),
                                rotation=float(style_info.get("rotation", 0)),
                                color=str(style_info.get("color", "black")),
                                page_number=page_number,
                                is_title=bool(is_title),
                                level=int(level)
                            )
                            # Conversion en dictionnaire pour la sérialisation
                            blocks.append(text_block.to_dict())

                    except Exception as e:
                        self.logger.warning(f"Erreur lors du traitement d'un bloc: {str(e)}")
                        continue

            doc.close()
            return blocks, page_dimensions

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

    @staticmethod
    def _extract_sections(text_content: str) -> List[Dict]:
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

    @staticmethod
    def analyze_spatial_relationships(blocks: List[Dict]) -> List[List[Dict]]:
        """
        Analyse les relations spatiales entre les blocs de texte pour identifier
        les sections logiques.

        Args:
            blocks: Liste de dictionnaires représentant les blocs de texte

        Returns:
            Liste de sections, chaque section étant une liste de blocs de texte
        """
        if not blocks:
            return []

        # Analyse des espaces verticaux entre les blocs
        vertical_gaps = []
        for i in range(len(blocks) - 1):
            current_block_bottom = blocks[i]['bbox'][3]  # Accessing bbox from dict
            next_block_top = blocks[i + 1]['bbox'][1]
            gap = next_block_top - current_block_bottom
            vertical_gaps.append(gap)

        # Calcul de l'espace moyen pour identifier les séparations de section
        avg_gap = sum(vertical_gaps) / len(vertical_gaps) if vertical_gaps else 0
        section_threshold = avg_gap * 1.5  # Seuil pour identifier une nouvelle section

        # Groupement des blocs en sections
        sections = []
        current_section = []

        for i, block in enumerate(blocks):
            current_section.append(block)

            if i < len(blocks) - 1:
                current_block_bottom = block['bbox'][3]
                next_block_top = blocks[i + 1]['bbox'][1]
                gap = next_block_top - current_block_bottom

                # Créer une nouvelle section si:
                # 1. L'espace vertical est plus grand que le seuil OU
                # 2. Le bloc actuel est un titre
                if gap > section_threshold or block.get('is_title', False):
                    sections.append(current_section)
                    current_section = []

        # Ajouter la dernière section si elle existe
        if current_section:
            sections.append(current_section)

        return sections




