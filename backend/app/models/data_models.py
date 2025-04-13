# backend/app/models/data_models.py
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from enum import Enum


class ElementType(Enum):
    TEXT = "text"
    IMAGE = "image"
    HEADING = "heading"


class ElementPriority(Enum):
    CRITICAL = 4  # Headers, large images
    HIGH = 3      # Important text blocks, medium images
    MEDIUM = 2    # Regular text
    LOW = 1       # Optional elements


@dataclass
class LayoutElement:
    """Version améliorée de TextBlock avec informations de priorité"""
    content: str
    element_type: ElementType
    bbox: list
    priority: ElementPriority
    size: Tuple[float, float]  # width, height
    original_position: Tuple[float, float]  # original x, y
    relationships: List[str] = None  # IDs of related elements

    # Champs préservés de TextBlock
    font_size: Optional[float] = None
    font_name: Optional[str] = None
    font_weight: Optional[str] = None
    text_alignment: Optional[str] = None
    line_height: Optional[float] = None
    rotation: Optional[float] = None
    color: Optional[str] = None
    page_number: Optional[int] = None


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