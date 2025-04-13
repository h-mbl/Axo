# backend/app/services/content_organizer.py
from typing import Dict, Optional, List
from backend.app.models.data_models import ElementType, LayoutElement, ElementPriority
from backend.app.services.dynamicLayoutManager import DynamicLayoutManager
from backend.app.services.elementSpacingManager import ElementSpacingManager, ElementBounds


class ContentOrganizer:
    def __init__(self):
        self.page_width: float = 0
        self.page_height: float = 0
        self.spacing_manager: Optional[ElementSpacingManager] = None

    def _initialize_spacing_manager(self):
        """Initialise le gestionnaire d'espacement."""
        if not self.spacing_manager:
            self.spacing_manager = ElementSpacingManager(
                page_width=self.page_width,
                page_height=self.page_height
            )

    def calculate_element_priority(self, element: dict) -> ElementPriority:
        """Calculate priority based on element properties"""
        if element['type'] == 'image':
            area = (element['bbox'][2] - element['bbox'][0]) * (element['bbox'][3] - element['bbox'][1])
            if area > (self.page_width * self.page_height * 0.15):  # Large images
                return ElementPriority.CRITICAL
            return ElementPriority.HIGH

        if element.get('is_title', False):
            return ElementPriority.CRITICAL

        if element.get('font_size', 0) > 14:  # Larger text
            return ElementPriority.HIGH

        return ElementPriority.MEDIUM

    def create_layout_element(self, block: dict) -> LayoutElement:
        """Convert a block to a LayoutElement with priority information"""
        element_type = ElementType.IMAGE if block.get('type') == 'image' else ElementType.TEXT
        if element_type == ElementType.TEXT and block.get('is_title', False):
            element_type = ElementType.HEADING

        bbox = block['bbox']
        size = (bbox[2] - bbox[0], bbox[3] - bbox[1])
        original_position = (bbox[0], bbox[1])

        priority = self.calculate_element_priority(block)

        return LayoutElement(
            content=block.get('content', '') if element_type != ElementType.IMAGE else block.get('path', ''),
            element_type=element_type,
            bbox=bbox,
            priority=priority,
            size=size,
            original_position=original_position,
            font_size=block.get('font_size'),
            font_name=block.get('font_name'),
            font_weight=block.get('font_weight'),
            text_alignment=block.get('text_alignment'),
            line_height=block.get('line_height'),
            rotation=block.get('rotation'),
            color=block.get('color'),
            page_number=block.get('page_number')
        )

    def organize_blocks_into_sections(self, text_blocks: list,
                                     translated_parts: list,
                                     images: list) -> list:
        """Version améliorée avec gestion des espacements."""
        # Initialiser les dimensions de la page et le gestionnaire d'espacement
        if text_blocks:
            self.page_width = max(block['bbox'][2] for block in text_blocks)
            self.page_height = max(block['bbox'][3] for block in text_blocks)
            self._initialize_spacing_manager()

        # Traiter d'abord les images
        processed_elements = []
        for img in images:
            img_dict = self.convert_extracted_image_to_dict(img)
            bounds = ElementBounds(
                x1=img_dict['bbox'][0],
                y1=img_dict['bbox'][1],
                x2=img_dict['bbox'][2],
                y2=img_dict['bbox'][3],
                element_type='image'
            )
            adjusted_bounds = self.spacing_manager.add_element(bounds)
            img_dict['bbox'] = [adjusted_bounds.x1, adjusted_bounds.y1,
                              adjusted_bounds.x2, adjusted_bounds.y2]
            processed_elements.append(self.create_layout_element(img_dict))

        # Traiter ensuite les blocs de texte
        for block, translated_text in zip(text_blocks, translated_parts):
            block['content'] = translated_text
            bounds = ElementBounds(
                x1=block['bbox'][0],
                y1=block['bbox'][1],
                x2=block['bbox'][2],
                y2=block['bbox'][3],
                element_type='text'
            )
            adjusted_bounds = self.spacing_manager.add_element(bounds)
            block['bbox'] = [adjusted_bounds.x1, adjusted_bounds.y1,
                           adjusted_bounds.x2, adjusted_bounds.y2]
            processed_elements.append(self.create_layout_element(block))

        # Organiser en sections basées sur la position verticale
        processed_elements.sort(key=lambda x: x.bbox[1])  # Trier par position Y

        sections = []
        current_section = []
        last_y = 0

        for element in processed_elements:
            if element.element_type == ElementType.IMAGE or \
                    element.bbox[1] - last_y > self.spacing_manager.min_vertical_spacing:
                if current_section:
                    sections.append(current_section)
                current_section = []

            current_section.append(self._convert_layout_element_to_dict(element))
            last_y = element.bbox[3]

        if current_section:
            sections.append(current_section)

        return sections

    @staticmethod
    def _convert_layout_element_to_dict(element: LayoutElement) -> dict:
        """Convert LayoutElement back to dictionary format for HTML export"""
        if element.element_type == ElementType.IMAGE:
            return {
                'type': 'image',
                'path': element.content,
                'bbox': element.bbox
            }
        else:
            return {
                'type': 'text',
                'content': element.content,
                'bbox': element.bbox,
                'style': {
                    'fontSize': f"{element.font_size}px" if element.font_size else None,
                    'fontFamily': element.font_name,
                    'fontWeight': element.font_weight,
                    'textAlign': element.text_alignment,
                    'lineHeight': f"{element.line_height}px" if element.line_height else None,
                    'transform': f"rotate({element.rotation}deg)" if element.rotation else None,
                    'color': element.color
                }
            }

    @staticmethod
    def convert_extracted_image_to_dict(img) -> dict:
        """
        Convertit un objet ExtractedImage en dictionnaire pour le traitement.
        Cette méthode est essentielle pour la standardisation du format des images
        avant leur intégration dans le système de priorité.

        Args:
            img: Objet ExtractedImage contenant les informations de l'image

        Returns:
            dict: Dictionnaire contenant les informations formatées de l'image
        """
        return {
            'type': 'image',
            'path': str(img.path),
            'bbox': list(map(float, img.bbox)),
            'width': float(img.size[0]) if img.size else None,
            'height': float(img.size[1]) if img.size else None,
            'caption': str(img.caption),
            'context_text': str(img.context_text),
            'page_number': int(img.page_number),
            'marker': str(img.marker)
        }