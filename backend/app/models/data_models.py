from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from enum import Enum


class ElementType(Enum):
    TEXT = "text"
    IMAGE = "image"
    HEADING = "heading"


class ElementPriority(Enum):
    CRITICAL = 4  # Headers, large images
    HIGH = 3  # Important text blocks, medium images
    MEDIUM = 2  # Regular text
    LOW = 1  # Optional elements


@dataclass
class LayoutElement:
    """Enhanced version of the existing TextBlock with priority information"""
    content: str
    element_type: ElementType
    bbox: list
    priority: ElementPriority
    size: Tuple[float, float]  # width, height
    original_position: Tuple[float, float]  # original x, y
    relationships: List[str] = None  # IDs of related elements

    # Preserve existing TextBlock fields
    font_size: Optional[float] = None
    font_name: Optional[str] = None
    font_weight: Optional[str] = None
    text_alignment: Optional[str] = None
    line_height: Optional[float] = None
    rotation: Optional[float] = None
    color: Optional[str] = None
    page_number: Optional[int] = None