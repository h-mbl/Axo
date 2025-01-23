from dataclasses import dataclass
from typing import Dict, List

@dataclass
class TextBlock:
    content: str
    bbox: list
    font_size: float
    font_name: str
    font_weight: str
    text_alignment: str
    line_height: float
    rotation: float
    color: str
    page_number: int

@dataclass
class TranslationResult:
    original_text: str
    translated_text: str
    images: list
    html_path: str
    success: bool
    message: str
    page_dimensions: Dict
    blocks: List[Dict]
    metadata: Dict